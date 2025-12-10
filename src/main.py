"""
Job Application Agent - Main Orchestrator

Coordinates all modules to:
1. Parse user profile
2. Scrape jobs from enabled sources
3. Match jobs against profile
4. Generate cover letters for matches
5. Send email notifications
6. Update database
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.config import get_config, Config
from src.profile.parser import ProfileParser
from src.database.db_manager import DatabaseManager, Job
from src.scrapers.scraper_factory import ScraperFactory
from src.matching.matcher import JobMatcher, MatchScore
from src.generator.cover_letter import CoverLetterGenerator
from src.notifications.email_sender import EmailSender

logger = logging.getLogger(__name__)


def setup_logging(config: Config) -> None:
    """Configure logging based on settings."""
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)
    
    # Create log directory
    log_dir = config.get_absolute_path(config.output.logs_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                log_dir / f"job_agent_{datetime.now().strftime('%Y%m%d')}.log"
            )
        ]
    )


class JobApplicationAgent:
    """
    Main agent that orchestrates the job application workflow.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the job application agent.
        
        Args:
            config: Configuration object. If None, loads default config.
        """
        self.config = config or get_config()
        self.config.ensure_directories()
        
        # Initialize components
        self.db = DatabaseManager(
            str(self.config.get_absolute_path(self.config.database.path))
        )
        
        self.profile_parser = ProfileParser(
            cache_path=str(self.config.get_absolute_path(self.config.profile.cache_file)),
            cache_duration_hours=self.config.profile.cache_duration_hours
        )
        
        self.scraper_factory = ScraperFactory(self.config)
        
        # These require API key, initialized lazily
        self._matcher: Optional[JobMatcher] = None
        self._cover_letter_generator: Optional[CoverLetterGenerator] = None
        self._email_sender: Optional[EmailSender] = None
    
    @property
    def matcher(self) -> JobMatcher:
        """Lazy initialization of job matcher."""
        if self._matcher is None:
            api_key = self.config.get_api_key()
            if not api_key:
                raise ValueError("GEMINI_API_KEY not configured")
            
            self._matcher = JobMatcher(
                api_key=api_key,
                model=self.config.gemini.model,
                temperature=self.config.gemini.temperature,
                threshold=self.config.job_search.match_threshold
            )
        return self._matcher
    
    @property
    def cover_letter_generator(self) -> CoverLetterGenerator:
        """Lazy initialization of cover letter generator."""
        if self._cover_letter_generator is None:
            api_key = self.config.get_api_key()
            if not api_key:
                raise ValueError("GEMINI_API_KEY not configured")
            
            self._cover_letter_generator = CoverLetterGenerator(
                api_key=api_key,
                model=self.config.gemini.model,
                temperature=self.config.gemini.temperature,
                output_dir=str(self.config.get_absolute_path(self.config.output.cover_letters_dir))
            )
        return self._cover_letter_generator
    
    @property
    def email_sender(self) -> EmailSender:
        """Lazy initialization of email sender."""
        if self._email_sender is None:
            self._email_sender = EmailSender(
                sender_email=self.config.email.recipient
            )
        return self._email_sender
    
    def run(
        self,
        skip_scraping: bool = False,
        skip_matching: bool = False,
        skip_cover_letters: bool = False,
        skip_email: bool = False,
        dry_run: bool = False
    ) -> dict:
        """
        Run the full job application workflow.
        
        Args:
            skip_scraping: Skip job scraping step
            skip_matching: Skip job matching step  
            skip_cover_letters: Skip cover letter generation
            skip_email: Skip sending email notifications
            dry_run: Run without sending emails or modifying external systems
            
        Returns:
            Dictionary with run statistics
        """
        stats = {
            "started_at": datetime.now().isoformat(),
            "jobs_scraped": 0,
            "new_jobs": 0,
            "jobs_matched": 0,
            "cover_letters_generated": 0,
            "email_sent": False,
            "errors": []
        }
        
        logger.info("=" * 50)
        logger.info("Starting Job Application Agent")
        logger.info("=" * 50)
        
        try:
            # Step 1: Parse profile
            logger.info("Step 1: Parsing user profile...")
            profile = self._parse_profile()
            profile_data = self.profile_parser.get_profile_for_matching()
            logger.info(f"Profile loaded for: {profile.name}")
            
            # Step 2: Scrape jobs
            if not skip_scraping:
                logger.info("Step 2: Scraping job boards...")
                jobs = self._scrape_jobs()
                stats["jobs_scraped"] = len(jobs)
                
                # Save to database
                stats["new_jobs"] = self.db.add_jobs(jobs)
                logger.info(f"Found {stats['jobs_scraped']} jobs, {stats['new_jobs']} new")
            else:
                logger.info("Step 2: Skipping job scraping")
            
            # Step 3: Get unprocessed jobs and match
            if not skip_matching:
                logger.info("Step 3: Matching jobs against profile...")
                unprocessed_jobs = self.db.get_unprocessed_jobs(
                    limit=self.config.job_search.max_jobs_per_run
                )
                logger.info(f"Processing {len(unprocessed_jobs)} unprocessed jobs")
                
                matched_jobs = self.matcher.match_jobs(
                    unprocessed_jobs,
                    profile_data,
                    filter_threshold=True
                )
                stats["jobs_matched"] = len(matched_jobs)
                logger.info(f"Found {stats['jobs_matched']} jobs above threshold")
                
                # Save match results
                for job, score in matched_jobs:
                    match_result = self.matcher.to_match_result(job, score)
                    self.db.save_match_result(match_result)
                    self.db.mark_job_processed(job, score.overall)
            else:
                logger.info("Step 3: Skipping job matching")
                matched_jobs = []
            
            # Step 4: Generate cover letters
            if not skip_cover_letters and matched_jobs:
                logger.info("Step 4: Generating cover letters...")
                matched_jobs = self._generate_cover_letters(matched_jobs, profile_data)
                stats["cover_letters_generated"] = len([
                    j for j, s in matched_jobs 
                    if hasattr(s, 'cover_letter_path') and s.cover_letter_path
                ])
            else:
                logger.info("Step 4: Skipping cover letter generation")
            
            # Step 5: Send email notification
            if not skip_email and matched_jobs and not dry_run:
                logger.info("Step 5: Sending email notification...")
                cv_path = str(self.config.get_absolute_path(self.config.email.cv_path))
                if not Path(cv_path).exists():
                    cv_path = None
                    logger.warning("CV file not found, email will be sent without CV attachment")
                
                stats["email_sent"] = self.email_sender.send_job_summary(
                    recipient=self.config.email.recipient,
                    matched_jobs=matched_jobs,
                    cv_path=cv_path,
                    include_cover_letters=self.config.email.attach_cover_letter
                )
            else:
                logger.info("Step 5: Skipping email notification")
            
            # Cleanup old records
            self.db.cleanup_old_records(self.config.database.retention_days)
            
        except Exception as e:
            logger.error(f"Error during run: {e}", exc_info=True)
            stats["errors"].append(str(e))
        
        stats["completed_at"] = datetime.now().isoformat()
        
        # Log summary
        logger.info("=" * 50)
        logger.info("Run completed!")
        logger.info(f"Jobs scraped: {stats['jobs_scraped']}")
        logger.info(f"New jobs: {stats['new_jobs']}")
        logger.info(f"Jobs matched: {stats['jobs_matched']}")
        logger.info(f"Cover letters: {stats['cover_letters_generated']}")
        logger.info(f"Email sent: {stats['email_sent']}")
        if stats["errors"]:
            logger.warning(f"Errors: {len(stats['errors'])}")
        logger.info("=" * 50)
        
        return stats
    
    def _parse_profile(self):
        """Parse user profile from configured source."""
        profile_path = self.config.get_absolute_path(self.config.profile.local_path)
        return self.profile_parser.parse(str(profile_path))
    
    def _scrape_jobs(self) -> List[Job]:
        """Scrape jobs from all enabled sources."""
        all_jobs = []
        keywords = self.config.job_search.keywords
        
        with self.scraper_factory as factory:
            scrapers = factory.get_enabled_scrapers()
            
            for scraper in scrapers:
                try:
                    logger.info(f"Scraping {scraper.get_name()}...")
                    jobs = scraper.scrape(keywords)
                    all_jobs.extend(jobs)
                    logger.info(f"Found {len(jobs)} jobs from {scraper.get_name()}")
                except Exception as e:
                    logger.error(f"Error scraping {scraper.get_name()}: {e}")
        
        return all_jobs
    
    def _generate_cover_letters(
        self,
        matched_jobs: List[tuple],
        profile_data: dict
    ) -> List[tuple]:
        """Generate cover letters for matched jobs."""
        updated_jobs = []
        
        for job, score in matched_jobs:
            try:
                paths = self.cover_letter_generator.generate_and_save(
                    job=job,
                    profile=profile_data,
                    match_score=score
                )
                
                # Add cover letter path to score for email attachment
                score.cover_letter_path = paths.get("pdf") or paths.get("txt")
                
                # Save to database
                if score.cover_letter_path:
                    self.db.save_cover_letter(
                        job_id=job.job_id,
                        content="",  # Content saved in file
                        file_path=score.cover_letter_path
                    )
                    self.db.mark_job_processed(
                        job, score.overall, 
                        cover_letter_path=score.cover_letter_path
                    )
                
                updated_jobs.append((job, score))
                
            except Exception as e:
                logger.error(f"Error generating cover letter for {job.title}: {e}")
                updated_jobs.append((job, score))
        
        return updated_jobs
    
    def get_statistics(self) -> dict:
        """Get database statistics."""
        return self.db.get_statistics()


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Job Application Agent - Automated job searching and application preparation"
    )
    
    parser.add_argument(
        "--config", "-c",
        help="Path to configuration file",
        default=None
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without sending emails"
    )
    
    parser.add_argument(
        "--skip-scraping",
        action="store_true",
        help="Skip job scraping step"
    )
    
    parser.add_argument(
        "--skip-matching",
        action="store_true",
        help="Skip job matching step"
    )
    
    parser.add_argument(
        "--skip-cover-letters",
        action="store_true",
        help="Skip cover letter generation"
    )
    
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Skip sending email"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics and exit"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = get_config(args.config)
    
    # Override log level if verbose
    if args.verbose:
        config.logging.level = "DEBUG"
    
    # Setup logging
    setup_logging(config)
    
    # Check for dry run from environment
    if config.is_dry_run():
        args.dry_run = True
        logger.info("Dry run mode enabled via environment variable")
    
    # Create agent
    agent = JobApplicationAgent(config)
    
    # Show stats and exit
    if args.stats:
        stats = agent.get_statistics()
        print("\n=== Database Statistics ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
        return 0
    
    # Run agent
    stats = agent.run(
        skip_scraping=args.skip_scraping,
        skip_matching=args.skip_matching,
        skip_cover_letters=args.skip_cover_letters,
        skip_email=args.skip_email,
        dry_run=args.dry_run
    )
    
    # Exit with error code if there were errors
    if stats.get("errors"):
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
