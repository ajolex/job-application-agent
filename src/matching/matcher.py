"""
Job Matching Engine

Uses Google Gemini to analyze job descriptions against user profile
and score relevance.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

import google.generativeai as genai

from src.database.db_manager import Job, MatchResult

logger = logging.getLogger(__name__)


@dataclass
class MatchScore:
    """Detailed match score breakdown."""
    overall: float
    skills_match: float
    experience_match: float
    research_match: float
    qualification_match: float
    reasoning: str
    highlights: List[str]
    concerns: List[str]
    cover_letter_path: Optional[str] = None  # Added for email attachments
    filtered_reason: Optional[str] = None  # Why job was filtered out


# Patterns that indicate visa sponsorship is NOT available
NO_VISA_PATTERNS = [
    "no visa sponsorship",
    "will not sponsor",
    "cannot sponsor",
    "not able to sponsor",
    "unable to sponsor",
    "does not sponsor",
    "won't sponsor",
    "not sponsor visa",
    "sponsorship not available",
    "sponsorship is not available",
    "no sponsorship",
    "must be authorized to work",
    "must have work authorization",
    "must have existing work authorization",
    "without sponsorship",
    "work authorization required",
]

# Patterns that indicate US citizenship/nationality is required
CITIZENSHIP_REQUIRED_PATTERNS = [
    "us citizen",
    "u.s. citizen",
    "united states citizen",
    "american citizen",
    "citizenship required",
    "must be a citizen",
    "citizens only",
    "us nationals only",
    "u.s. nationals",
    "security clearance required",  # Usually requires citizenship
    "secret clearance",
    "top secret clearance",
    "ts/sci clearance",
    "must be able to obtain security clearance",
    "us persons only",
    "u.s. persons only",
    "itar restricted",  # Export control, usually requires citizenship
    "export control",
]


def check_visa_eligibility(job_description: str) -> tuple[bool, Optional[str]]:
    """
    Check if a job is eligible for international candidates.
    
    Args:
        job_description: Full job description text
        
    Returns:
        Tuple of (is_eligible, reason_if_not_eligible)
    """
    if not job_description:
        return True, None
    
    desc_lower = job_description.lower()
    
    # Check for no visa sponsorship
    for pattern in NO_VISA_PATTERNS:
        if pattern in desc_lower:
            return False, f"No visa sponsorship: '{pattern}' found in description"
    
    # Check for citizenship requirements
    for pattern in CITIZENSHIP_REQUIRED_PATTERNS:
        if pattern in desc_lower:
            return False, f"Citizenship required: '{pattern}' found in description"
    
    return True, None


class JobMatcher:
    """
    Matches jobs against user profile using Gemini AI.
    
    Analyzes job descriptions and user profiles to determine
    relevance and generate detailed match scores.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.3,
        threshold: int = 70
    ):
        """
        Initialize job matcher.
        
        Args:
            api_key: Google Gemini API key
            model: Gemini model to use
            temperature: Generation temperature (lower = more deterministic)
            threshold: Minimum score to consider a match
        """
        self.threshold = threshold
        self.model_name = model
        self.temperature = temperature
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        
        logger.info(f"Initialized JobMatcher with model {model}")
    
    def match_job(self, job: Job, profile: Dict[str, Any]) -> MatchScore:
        """
        Match a single job against the user profile.
        
        Args:
            job: Job to match
            profile: User profile dictionary
            
        Returns:
            MatchScore with detailed breakdown
        """
        prompt = self._build_matching_prompt(job, profile)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=2048,
                )
            )
            
            # Parse the response
            return self._parse_match_response(response.text)
            
        except Exception as e:
            logger.error(f"Error matching job {job.title}: {e}")
            return MatchScore(
                overall=0,
                skills_match=0,
                experience_match=0,
                research_match=0,
                qualification_match=0,
                reasoning=f"Error during matching: {str(e)}",
                highlights=[],
                concerns=[]
            )
    
    def match_jobs(
        self,
        jobs: List[Job],
        profile: Dict[str, Any],
        filter_threshold: bool = True
    ) -> List[tuple]:
        """
        Match multiple jobs against the user profile.
        
        Args:
            jobs: List of jobs to match
            profile: User profile dictionary
            filter_threshold: If True, only return jobs above threshold
            
        Returns:
            List of (job, match_score) tuples, sorted by score
        """
        results = []
        filtered_count = 0
        
        for i, job in enumerate(jobs):
            logger.info(f"Matching job {i+1}/{len(jobs)}: {job.title}")
            
            # Check visa/citizenship eligibility first
            is_eligible, filter_reason = check_visa_eligibility(job.description or "")
            if not is_eligible:
                logger.info(f"Filtered out (visa/citizenship): {job.title} - {filter_reason}")
                filtered_count += 1
                continue
            
            score = self.match_job(job, profile)
            
            if filter_threshold and score.overall < self.threshold:
                logger.debug(f"Job below threshold ({score.overall}): {job.title}")
                continue
            
            results.append((job, score))
        
        # Sort by overall score descending
        results.sort(key=lambda x: x[1].overall, reverse=True)
        
        logger.info(f"Matched {len(results)} jobs above threshold {self.threshold}")
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} jobs due to visa/citizenship requirements")
        return results
    
    def _build_matching_prompt(self, job: Job, profile: Dict[str, Any]) -> str:
        """Build the prompt for job matching."""
        return f"""You are an expert career advisor specializing in Development Economics and Research positions.

Analyze how well this candidate matches the job posting and provide a detailed assessment.

## CANDIDATE PROFILE:
Name: {profile.get('name', 'Candidate')}
Summary: {profile.get('summary', 'Not provided')}
Skills: {', '.join(profile.get('skills', []))}
Education: {profile.get('education', 'Not provided')}
Experience: {profile.get('experience', 'Not provided')}
Research Interests: {', '.join(profile.get('research_interests', []))}
Years of Experience: {profile.get('years_of_experience', 'Unknown')}

## JOB POSTING:
Title: {job.title}
Organization: {job.organization}
Location: {job.location}
Description: {job.description[:3000] if job.description else 'Not provided'}
Requirements: {job.requirements[:1500] if job.requirements else 'Not provided'}
Deadline: {job.deadline or 'Not specified'}

## INSTRUCTIONS:
Evaluate the match and respond with a JSON object (no markdown formatting) containing:
{{
    "overall_score": <0-100>,
    "skills_match": <0-100>,
    "experience_match": <0-100>,
    "research_match": <0-100>,
    "qualification_match": <0-100>,
    "reasoning": "<2-3 sentence explanation of the match>",
    "highlights": ["<strength 1>", "<strength 2>", ...],
    "concerns": ["<gap or concern 1>", "<gap or concern 2>", ...]
}}

Score Guidelines:
- 90-100: Excellent match, candidate exceeds most requirements
- 80-89: Strong match, candidate meets most requirements
- 70-79: Good match, candidate meets key requirements
- 60-69: Moderate match, some gaps but relevant background
- Below 60: Weak match, significant gaps

Focus on Development Economics, research experience, analytical skills, and relevant qualifications.
Respond ONLY with the JSON object, no other text."""
    
    def _parse_match_response(self, response_text: str) -> MatchScore:
        """Parse the Gemini response into a MatchScore."""
        try:
            # Clean up response - remove any markdown formatting
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            data = json.loads(text)
            
            return MatchScore(
                overall=float(data.get("overall_score", 0)),
                skills_match=float(data.get("skills_match", 0)),
                experience_match=float(data.get("experience_match", 0)),
                research_match=float(data.get("research_match", 0)),
                qualification_match=float(data.get("qualification_match", 0)),
                reasoning=data.get("reasoning", ""),
                highlights=data.get("highlights", []),
                concerns=data.get("concerns", [])
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse match response as JSON: {e}")
            # Try to extract score from text
            return self._extract_score_from_text(response_text)
    
    def _extract_score_from_text(self, text: str) -> MatchScore:
        """Fallback: extract score from unstructured text."""
        import re
        
        # Try to find a score pattern
        score_match = re.search(r'(\d{1,3})\s*(?:/\s*100|%|points?)', text)
        if score_match:
            score = min(100, int(score_match.group(1)))
        else:
            # Default to moderate score if we can't parse
            score = 50
        
        return MatchScore(
            overall=score,
            skills_match=score,
            experience_match=score,
            research_match=score,
            qualification_match=score,
            reasoning=text[:500] if text else "Could not parse detailed response",
            highlights=[],
            concerns=[]
        )
    
    def to_match_result(self, job: Job, score: MatchScore) -> MatchResult:
        """Convert MatchScore to MatchResult for database storage."""
        return MatchResult(
            job_id=job.job_id,
            match_score=score.overall,
            skills_match=score.skills_match,
            experience_match=score.experience_match,
            research_match=score.research_match,
            qualification_match=score.qualification_match,
            reasoning=score.reasoning,
            matched_date=datetime.now().isoformat()
        )
    
    def get_match_summary(self, job: Job, score: MatchScore) -> str:
        """Generate a human-readable match summary."""
        summary = f"""
## {job.title} at {job.organization}

**Match Score: {score.overall}/100**

### Score Breakdown:
- Skills Match: {score.skills_match}/100
- Experience Match: {score.experience_match}/100
- Research Alignment: {score.research_match}/100
- Qualifications: {score.qualification_match}/100

### Analysis:
{score.reasoning}

### Strengths:
{chr(10).join('- ' + h for h in score.highlights) if score.highlights else '- None identified'}

### Potential Gaps:
{chr(10).join('- ' + c for c in score.concerns) if score.concerns else '- None identified'}

**Location:** {job.location}
**Deadline:** {job.deadline or 'Not specified'}
**Apply:** {job.application_url or job.url}
"""
        return summary.strip()
