"""
Unit tests for the configuration loader.
"""
import os
import tempfile
import pytest
from pathlib import Path

# Note: These tests require the project dependencies to be installed
# Run with: pytest tests/test_config.py -v


class TestConfigLoader:
    """Test the configuration loading functionality."""
    
    def test_config_file_exists(self):
        """Test that the default config file exists."""
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        assert config_path.exists(), f"Config file not found at {config_path}"
    
    def test_config_yaml_valid(self):
        """Test that the config file contains valid YAML."""
        import yaml
        
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        assert config is not None
        assert isinstance(config, dict)
    
    def test_config_has_required_sections(self):
        """Test that config has all required sections."""
        import yaml
        
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        required_sections = ['profile', 'job_search', 'scrapers', 'matching', 'email', 'database']
        for section in required_sections:
            assert section in config, f"Missing required section: {section}"
    
    def test_job_search_has_keywords(self):
        """Test that job_search section has keywords."""
        import yaml
        
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        assert 'keywords' in config['job_search']
        assert isinstance(config['job_search']['keywords'], list)
        assert len(config['job_search']['keywords']) > 0
    
    def test_match_threshold_valid(self):
        """Test that match threshold is a valid number."""
        import yaml
        
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        threshold = config['job_search'].get('match_threshold', 70)
        assert isinstance(threshold, (int, float))
        assert 0 <= threshold <= 100


class TestEnvironmentVariables:
    """Test environment variable handling."""
    
    def test_env_example_exists(self):
        """Test that .env.example file exists."""
        env_example = Path(__file__).parent.parent / ".env.example"
        assert env_example.exists(), ".env.example file not found"
    
    def test_env_example_has_required_vars(self):
        """Test that .env.example contains required variables."""
        env_example = Path(__file__).parent.parent / ".env.example"
        content = env_example.read_text()
        
        required_vars = ['GEMINI_API_KEY', 'EMAIL_ADDRESS']
        for var in required_vars:
            assert var in content, f"Missing required variable in .env.example: {var}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
