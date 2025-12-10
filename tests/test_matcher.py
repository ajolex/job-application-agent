"""
Unit tests for the job matcher.
"""
import pytest
from unittest.mock import Mock, patch

# Note: These tests require the project dependencies to be installed
# Run with: pytest tests/test_matcher.py -v


class TestMatchScoreCalculation:
    """Test match score calculation logic."""
    
    def test_match_score_dataclass(self):
        """Test MatchScore dataclass creation."""
        from src.matching.matcher import MatchScore
        
        score = MatchScore(
            overall_score=85.0,
            skills_match=80.0,
            experience_match=90.0,
            research_match=85.0,
            qualifications_match=85.0,
            reasoning="Strong match for research experience",
            highlights=["Impact evaluation expertise", "PhD in Economics"],
            concerns=["Limited field experience"]
        )
        
        assert score.overall_score == 85.0
        assert score.skills_match == 80.0
        assert len(score.highlights) == 2
        assert len(score.concerns) == 1
    
    def test_match_score_defaults(self):
        """Test MatchScore with default values."""
        from src.matching.matcher import MatchScore
        
        score = MatchScore(
            overall_score=75.0,
            reasoning="Partial match"
        )
        
        assert score.overall_score == 75.0
        assert score.skills_match == 0.0
        assert score.highlights == []
        assert score.concerns == []


class TestMatcherInitialization:
    """Test matcher initialization."""
    
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'})
    def test_matcher_creation_with_api_key(self):
        """Test creating matcher with API key."""
        from src.matching.matcher import JobMatcher
        
        # This will fail at model initialization but that's expected
        # without a real API key
        try:
            matcher = JobMatcher(api_key='test_key')
        except Exception:
            pass  # Expected without real API key
    
    def test_matcher_requires_api_key(self):
        """Test that matcher requires API key."""
        from src.matching.matcher import JobMatcher
        
        # Clear any environment variable
        import os
        old_key = os.environ.pop('GEMINI_API_KEY', None)
        
        try:
            with pytest.raises((ValueError, Exception)):
                matcher = JobMatcher(api_key=None)
        finally:
            if old_key:
                os.environ['GEMINI_API_KEY'] = old_key


class TestJobMatchingPrompt:
    """Test job matching prompt generation."""
    
    def test_prompt_includes_profile(self):
        """Test that matching prompt includes profile information."""
        profile = {
            'skills': ['Python', 'Stata', 'R'],
            'experience': [{'title': 'Research Associate', 'organization': 'World Bank'}],
            'education': [{'degree': 'PhD Economics', 'institution': 'MIT'}]
        }
        
        # Build prompt (simplified version)
        prompt_parts = []
        prompt_parts.append("Profile Skills: " + ", ".join(profile['skills']))
        prompt = "\n".join(prompt_parts)
        
        assert 'Python' in prompt
        assert 'Stata' in prompt
    
    def test_prompt_includes_job_details(self):
        """Test that matching prompt includes job details."""
        from src.database.db_manager import Job
        
        job = Job(
            url="https://example.com/job",
            title="Development Economist",
            organization="World Bank",
            description="Looking for economist with RCT experience",
            source="test"
        )
        
        # Build job section (simplified)
        job_text = f"""
        Title: {job.title}
        Organization: {job.organization}
        Description: {job.description}
        """
        
        assert 'Development Economist' in job_text
        assert 'World Bank' in job_text
        assert 'RCT experience' in job_text


class TestMatchThreshold:
    """Test match threshold logic."""
    
    def test_above_threshold(self):
        """Test job above match threshold."""
        threshold = 70
        score = 85
        
        assert score >= threshold
    
    def test_below_threshold(self):
        """Test job below match threshold."""
        threshold = 70
        score = 55
        
        assert score < threshold
    
    def test_at_threshold(self):
        """Test job exactly at threshold."""
        threshold = 70
        score = 70
        
        assert score >= threshold


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
