"""
Database Manager for Job Application Agent.

Handles SQLite database operations for tracking processed jobs,
application status, and generated cover letters.
"""

import sqlite3
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Represents a job posting."""
    job_id: str
    url: str
    title: str
    organization: str
    location: str
    description: str
    posted_date: Optional[str] = None
    deadline: Optional[str] = None
    requirements: Optional[str] = None
    application_url: Optional[str] = None
    source: str = ""
    raw_data: Optional[str] = None
    
    @classmethod
    def generate_id(cls, url: str, title: str, organization: str) -> str:
        """Generate a unique job ID from URL, title, and organization."""
        content = f"{url}|{title}|{organization}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class ProcessedJob:
    """Represents a processed job record."""
    job_id: str
    url: str
    title: str
    organization: str
    source: str
    match_score: float
    processed_date: str
    cover_letter_path: Optional[str] = None
    application_status: str = "pending"
    notes: Optional[str] = None


@dataclass 
class MatchResult:
    """Represents a job match result."""
    job_id: str
    match_score: float
    skills_match: float
    experience_match: float
    research_match: float
    qualification_match: float
    reasoning: str
    matched_date: str


class DatabaseManager:
    """
    Manages SQLite database for job tracking.
    
    Tables:
    - jobs: Raw job postings scraped from sources
    - processed_jobs: Jobs that have been matched and processed
    - match_results: Detailed match scores for jobs
    - cover_letters: Generated cover letters
    """
    
    def __init__(self, db_path: str = "data/jobs.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Jobs table - raw scraped jobs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    organization TEXT NOT NULL,
                    location TEXT,
                    description TEXT,
                    posted_date TEXT,
                    deadline TEXT,
                    requirements TEXT,
                    application_url TEXT,
                    source TEXT NOT NULL,
                    raw_data TEXT,
                    scraped_date TEXT NOT NULL,
                    UNIQUE(url, title, organization)
                )
            """)
            
            # Processed jobs table - jobs that have been matched
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_jobs (
                    job_id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    organization TEXT NOT NULL,
                    source TEXT NOT NULL,
                    match_score REAL NOT NULL,
                    processed_date TEXT NOT NULL,
                    cover_letter_path TEXT,
                    application_status TEXT DEFAULT 'pending',
                    notes TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                )
            """)
            
            # Match results table - detailed match scores
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_results (
                    job_id TEXT PRIMARY KEY,
                    match_score REAL NOT NULL,
                    skills_match REAL,
                    experience_match REAL,
                    research_match REAL,
                    qualification_match REAL,
                    reasoning TEXT,
                    matched_date TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                )
            """)
            
            # Cover letters table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cover_letters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    file_path TEXT,
                    generated_date TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_scraped_date ON jobs(scraped_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_jobs_date ON processed_jobs(processed_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_jobs_score ON processed_jobs(match_score)")
            
            logger.info(f"Database initialized at {self.db_path}")
    
    def add_job(self, job: Job) -> bool:
        """
        Add a job to the database.
        
        Args:
            job: Job object to add
            
        Returns:
            True if job was added, False if it already exists
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO jobs (
                        job_id, url, title, organization, location, description,
                        posted_date, deadline, requirements, application_url,
                        source, raw_data, scraped_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id, job.url, job.title, job.organization,
                    job.location, job.description, job.posted_date,
                    job.deadline, job.requirements, job.application_url,
                    job.source, job.raw_data, datetime.now().isoformat()
                ))
                logger.debug(f"Added job: {job.title} at {job.organization}")
                return True
            except sqlite3.IntegrityError:
                logger.debug(f"Job already exists: {job.title} at {job.organization}")
                return False
    
    def add_jobs(self, jobs: List[Job]) -> int:
        """
        Add multiple jobs to the database.
        
        Args:
            jobs: List of Job objects
            
        Returns:
            Number of jobs successfully added
        """
        added = 0
        for job in jobs:
            if self.add_job(job):
                added += 1
        logger.info(f"Added {added}/{len(jobs)} jobs to database")
        return added
    
    def job_exists(self, job_id: str) -> bool:
        """Check if a job already exists in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,))
            return cursor.fetchone() is not None
    
    def is_job_processed(self, job_id: str) -> bool:
        """Check if a job has already been processed (matched)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_jobs WHERE job_id = ?", (job_id,))
            return cursor.fetchone() is not None
    
    def get_unprocessed_jobs(self, source: Optional[str] = None, limit: int = 100) -> List[Job]:
        """
        Get jobs that haven't been processed yet.
        
        Args:
            source: Optional filter by source
            limit: Maximum number of jobs to return
            
        Returns:
            List of unprocessed Job objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if source:
                cursor.execute("""
                    SELECT j.* FROM jobs j
                    LEFT JOIN processed_jobs p ON j.job_id = p.job_id
                    WHERE p.job_id IS NULL AND j.source = ?
                    ORDER BY j.scraped_date DESC
                    LIMIT ?
                """, (source, limit))
            else:
                cursor.execute("""
                    SELECT j.* FROM jobs j
                    LEFT JOIN processed_jobs p ON j.job_id = p.job_id
                    WHERE p.job_id IS NULL
                    ORDER BY j.scraped_date DESC
                    LIMIT ?
                """, (limit,))
            
            jobs = []
            for row in cursor.fetchall():
                jobs.append(Job(
                    job_id=row["job_id"],
                    url=row["url"],
                    title=row["title"],
                    organization=row["organization"],
                    location=row["location"],
                    description=row["description"],
                    posted_date=row["posted_date"],
                    deadline=row["deadline"],
                    requirements=row["requirements"],
                    application_url=row["application_url"],
                    source=row["source"],
                    raw_data=row["raw_data"]
                ))
            
            return jobs
    
    def mark_job_processed(
        self,
        job: Job,
        match_score: float,
        cover_letter_path: Optional[str] = None,
        notes: Optional[str] = None
    ) -> None:
        """
        Mark a job as processed.
        
        Args:
            job: Job object
            match_score: Match score from matching engine
            cover_letter_path: Path to generated cover letter
            notes: Optional notes
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO processed_jobs (
                    job_id, url, title, organization, source,
                    match_score, processed_date, cover_letter_path,
                    application_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, job.url, job.title, job.organization,
                job.source, match_score, datetime.now().isoformat(),
                cover_letter_path, "pending", notes
            ))
            logger.debug(f"Marked job as processed: {job.title} (score: {match_score})")
    
    def save_match_result(self, result: MatchResult) -> None:
        """Save detailed match result."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO match_results (
                    job_id, match_score, skills_match, experience_match,
                    research_match, qualification_match, reasoning, matched_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.job_id, result.match_score, result.skills_match,
                result.experience_match, result.research_match,
                result.qualification_match, result.reasoning, result.matched_date
            ))
    
    def save_cover_letter(self, job_id: str, content: str, file_path: Optional[str] = None) -> int:
        """
        Save a generated cover letter.
        
        Args:
            job_id: Job ID
            content: Cover letter content
            file_path: Optional file path where cover letter is saved
            
        Returns:
            Cover letter ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cover_letters (job_id, content, file_path, generated_date)
                VALUES (?, ?, ?, ?)
            """, (job_id, content, file_path, datetime.now().isoformat()))
            return cursor.lastrowid
    
    def get_matched_jobs(
        self,
        min_score: float = 0,
        since_date: Optional[str] = None,
        limit: int = 100
    ) -> List[ProcessedJob]:
        """
        Get processed jobs with match scores above threshold.
        
        Args:
            min_score: Minimum match score
            since_date: Only get jobs processed since this date (ISO format)
            limit: Maximum number of jobs to return
            
        Returns:
            List of ProcessedJob objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM processed_jobs
                WHERE match_score >= ?
            """
            params = [min_score]
            
            if since_date:
                query += " AND processed_date >= ?"
                params.append(since_date)
            
            query += " ORDER BY match_score DESC, processed_date DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            jobs = []
            for row in cursor.fetchall():
                jobs.append(ProcessedJob(
                    job_id=row["job_id"],
                    url=row["url"],
                    title=row["title"],
                    organization=row["organization"],
                    source=row["source"],
                    match_score=row["match_score"],
                    processed_date=row["processed_date"],
                    cover_letter_path=row["cover_letter_path"],
                    application_status=row["application_status"],
                    notes=row["notes"]
                ))
            
            return jobs
    
    def get_job_by_id(self, job_id: str) -> Optional[Job]:
        """Get a job by its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            
            if row:
                return Job(
                    job_id=row["job_id"],
                    url=row["url"],
                    title=row["title"],
                    organization=row["organization"],
                    location=row["location"],
                    description=row["description"],
                    posted_date=row["posted_date"],
                    deadline=row["deadline"],
                    requirements=row["requirements"],
                    application_url=row["application_url"],
                    source=row["source"],
                    raw_data=row["raw_data"]
                )
            return None
    
    def get_match_result(self, job_id: str) -> Optional[MatchResult]:
        """Get match result for a job."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM match_results WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            
            if row:
                return MatchResult(
                    job_id=row["job_id"],
                    match_score=row["match_score"],
                    skills_match=row["skills_match"],
                    experience_match=row["experience_match"],
                    research_match=row["research_match"],
                    qualification_match=row["qualification_match"],
                    reasoning=row["reasoning"],
                    matched_date=row["matched_date"]
                )
            return None
    
    def update_application_status(self, job_id: str, status: str, notes: Optional[str] = None) -> None:
        """Update the application status for a job."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if notes:
                cursor.execute("""
                    UPDATE processed_jobs
                    SET application_status = ?, notes = ?
                    WHERE job_id = ?
                """, (status, notes, job_id))
            else:
                cursor.execute("""
                    UPDATE processed_jobs
                    SET application_status = ?
                    WHERE job_id = ?
                """, (status, job_id))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total jobs
            cursor.execute("SELECT COUNT(*) FROM jobs")
            stats["total_jobs"] = cursor.fetchone()[0]
            
            # Jobs by source
            cursor.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source")
            stats["jobs_by_source"] = dict(cursor.fetchall())
            
            # Processed jobs
            cursor.execute("SELECT COUNT(*) FROM processed_jobs")
            stats["processed_jobs"] = cursor.fetchone()[0]
            
            # Average match score
            cursor.execute("SELECT AVG(match_score) FROM processed_jobs")
            avg = cursor.fetchone()[0]
            stats["avg_match_score"] = round(avg, 2) if avg else 0
            
            # Jobs above threshold
            cursor.execute("SELECT COUNT(*) FROM processed_jobs WHERE match_score >= 70")
            stats["matched_jobs"] = cursor.fetchone()[0]
            
            # Application status breakdown
            cursor.execute("""
                SELECT application_status, COUNT(*)
                FROM processed_jobs
                GROUP BY application_status
            """)
            stats["status_breakdown"] = dict(cursor.fetchall())
            
            return stats
    
    def cleanup_old_records(self, retention_days: int = 90) -> int:
        """
        Remove old job records.
        
        Args:
            retention_days: Keep records newer than this many days
            
        Returns:
            Number of records deleted
        """
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete old cover letters
            cursor.execute("""
                DELETE FROM cover_letters
                WHERE generated_date < ?
            """, (cutoff_date,))
            
            # Delete old match results
            cursor.execute("""
                DELETE FROM match_results
                WHERE matched_date < ?
            """, (cutoff_date,))
            
            # Delete old processed jobs
            cursor.execute("""
                DELETE FROM processed_jobs
                WHERE processed_date < ?
            """, (cutoff_date,))
            
            # Delete old jobs
            cursor.execute("""
                DELETE FROM jobs
                WHERE scraped_date < ?
            """, (cutoff_date,))
            deleted = cursor.rowcount
            
            logger.info(f"Cleaned up {deleted} old job records")
            return deleted
