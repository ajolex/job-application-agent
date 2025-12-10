"""
Unit tests for the database manager.
"""
import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta

# Note: These tests require the project dependencies to be installed
# Run with: pytest tests/test_database.py -v


class TestDatabaseManager:
    """Test the database management functionality."""
    
    @pytest.fixture
    def db_manager(self):
        """Create a temporary database for testing."""
        from src.database.db_manager import DatabaseManager
        
        # Create a temporary file for the test database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db_path = f.name
        
        manager = DatabaseManager(temp_db_path)
        yield manager
        
        # Cleanup
        manager.close()
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
    
    def test_database_creation(self, db_manager):
        """Test that database is created with all tables."""
        cursor = db_manager.conn.cursor()
        
        # Check that tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['jobs', 'processed_jobs', 'match_results', 'cover_letters']
        for table in expected_tables:
            assert table in tables, f"Missing table: {table}"
    
    def test_add_job(self, db_manager):
        """Test adding a job to the database."""
        from src.database.db_manager import Job
        
        job = Job(
            url="https://example.com/job/123",
            title="Research Associate",
            organization="Test Org",
            location="Remote",
            description="Test description",
            posted_date="2024-01-01",
            deadline="2024-02-01",
            source="test"
        )
        
        job_id = db_manager.add_job(job)
        assert job_id is not None
        assert isinstance(job_id, int)
    
    def test_job_deduplication(self, db_manager):
        """Test that duplicate jobs are not added."""
        from src.database.db_manager import Job
        
        job = Job(
            url="https://example.com/job/456",
            title="Economist",
            organization="Test Org",
            source="test"
        )
        
        # Add job twice
        id1 = db_manager.add_job(job)
        id2 = db_manager.add_job(job)
        
        # Should return same ID
        assert id1 == id2
    
    def test_is_job_processed(self, db_manager):
        """Test job processed status checking."""
        # Initially should not be processed
        assert not db_manager.is_job_processed("https://example.com/job/789")
        
        # Mark as processed
        db_manager.mark_job_processed("https://example.com/job/789", "test_hash")
        
        # Now should be processed
        assert db_manager.is_job_processed("https://example.com/job/789")
    
    def test_get_unprocessed_jobs(self, db_manager):
        """Test getting unprocessed jobs."""
        from src.database.db_manager import Job
        
        # Add a job
        job = Job(
            url="https://example.com/job/unprocessed",
            title="Data Analyst",
            organization="Test Org",
            source="test"
        )
        db_manager.add_job(job)
        
        # Get unprocessed jobs
        unprocessed = db_manager.get_unprocessed_jobs()
        assert len(unprocessed) > 0
        assert any(j.url == "https://example.com/job/unprocessed" for j in unprocessed)
    
    def test_add_match_result(self, db_manager):
        """Test adding a match result."""
        from src.database.db_manager import Job, MatchResult
        
        # First add a job
        job = Job(
            url="https://example.com/job/match-test",
            title="Senior Economist",
            organization="Test Org",
            source="test"
        )
        job_id = db_manager.add_job(job)
        
        # Add match result
        match = MatchResult(
            job_id=job_id,
            overall_score=85.0,
            skills_score=80.0,
            experience_score=90.0,
            reasoning="Good match for skills"
        )
        result_id = db_manager.add_match_result(match)
        
        assert result_id is not None
    
    def test_get_statistics(self, db_manager):
        """Test getting database statistics."""
        stats = db_manager.get_statistics()
        
        assert 'total_jobs' in stats
        assert 'processed_jobs' in stats
        assert 'matched_jobs' in stats
        assert isinstance(stats['total_jobs'], int)


class TestJobDataclass:
    """Test the Job dataclass."""
    
    def test_job_creation(self):
        """Test creating a Job instance."""
        from src.database.db_manager import Job
        
        job = Job(
            url="https://example.com/job/1",
            title="Test Position",
            organization="Test Company",
            source="test"
        )
        
        assert job.url == "https://example.com/job/1"
        assert job.title == "Test Position"
        assert job.organization == "Test Company"
        assert job.source == "test"
    
    def test_job_optional_fields(self):
        """Test Job with optional fields."""
        from src.database.db_manager import Job
        
        job = Job(
            url="https://example.com/job/2",
            title="Another Position",
            organization="Another Company",
            location="New York",
            description="Full description here",
            salary="$100,000",
            job_type="Full-time",
            source="devex"
        )
        
        assert job.location == "New York"
        assert job.salary == "$100,000"
        assert job.job_type == "Full-time"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
