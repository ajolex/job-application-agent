"""
Configuration loader for Job Application Agent.

Loads configuration from YAML file and environment variables,
with environment variables taking precedence.
"""

import os
import re
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class ProfileConfig:
    """Profile/CV configuration."""
    local_path: str = "index.html"
    cache_duration_hours: int = 24
    cache_file: str = "data/profile_cache.json"


@dataclass
class JobSearchConfig:
    """Job search configuration."""
    keywords: list = field(default_factory=lambda: ["development economics", "research"])
    locations: list = field(default_factory=lambda: ["Remote", "Global"])
    match_threshold: int = 70
    max_jobs_per_run: int = 50


@dataclass
class ScrapersConfig:
    """Scrapers configuration."""
    enabled: list = field(default_factory=lambda: ["reliefweb", "devex"])
    rate_limit_seconds: int = 2
    timeout_seconds: int = 30
    max_retries: int = 3
    rotate_user_agent: bool = True


@dataclass
class GeminiConfig:
    """Gemini API configuration."""
    model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    max_tokens: int = 4096
    safety_threshold: str = "BLOCK_ONLY_HIGH"


@dataclass
class EmailConfig:
    """Email notification configuration."""
    recipient: str = ""
    send_summary: bool = True
    attach_cover_letter: bool = True
    attach_cv: bool = True
    cv_path: str = "data/cv.pdf"
    subject_template: str = "Job Matches Found - {date} ({count} jobs)"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "data/jobs.db"
    retention_days: int = 90


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: str = "logs/job_agent.log"
    max_size_mb: int = 10
    backup_count: int = 5


@dataclass
class OutputConfig:
    """Output paths configuration."""
    cover_letters_dir: str = "output/cover_letters"
    logs_dir: str = "logs"


class Config:
    """
    Main configuration class that loads and manages all settings.
    
    Supports:
    - YAML configuration file
    - Environment variable overrides
    - Default values for all settings
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to YAML config file. If None, uses default location.
        """
        # base_path is the project root (job-application-agent/)
        # __file__ is src/config.py, so .parent.parent gets us to project root
        self.base_path = Path(__file__).parent.parent
        
        if config_path is None:
            config_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
        
        self.config_path = self.base_path / config_path
        self._raw_config: Dict[str, Any] = {}
        self._scraper_configs: Dict[str, Dict[str, Any]] = {}
        
        # Load configuration
        self._load_config()
        
        # Initialize config objects
        self.profile = self._load_profile_config()
        self.job_search = self._load_job_search_config()
        self.scrapers = self._load_scrapers_config()
        self.gemini = self._load_gemini_config()
        self.email = self._load_email_config()
        self.database = self._load_database_config()
        self.logging = self._load_logging_config()
        self.output = self._load_output_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._raw_config = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}. Using defaults.")
                self._raw_config = {}
        else:
            logger.warning(f"Config file not found at {self.config_path}. Using defaults.")
            self._raw_config = {}
        
        # Load scraper-specific configs
        self._scraper_configs = self._raw_config.get("scraper_configs", {})
    
    def _resolve_env_vars(self, value: Any) -> Any:
        """
        Resolve environment variable references in config values.
        
        Supports ${VAR_NAME} syntax.
        """
        if isinstance(value, str):
            # Find all ${VAR_NAME} patterns
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            
            for var_name in matches:
                env_value = os.environ.get(var_name, "")
                value = value.replace(f"${{{var_name}}}", env_value)
            
            return value
        elif isinstance(value, dict):
            return {k: self._resolve_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_env_vars(item) for item in value]
        return value
    
    def _get_config_value(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value with environment variable resolution."""
        section_config = self._raw_config.get(section, {})
        value = section_config.get(key, default)
        return self._resolve_env_vars(value)
    
    def _load_profile_config(self) -> ProfileConfig:
        """Load profile configuration."""
        section = self._raw_config.get("profile", {})
        return ProfileConfig(
            local_path=self._resolve_env_vars(section.get("local_path", "index.html")),
            cache_duration_hours=section.get("cache_duration_hours", 24),
            cache_file=section.get("cache_file", "data/profile_cache.json")
        )
    
    def _load_job_search_config(self) -> JobSearchConfig:
        """Load job search configuration."""
        section = self._raw_config.get("job_search", {})
        return JobSearchConfig(
            keywords=section.get("keywords", ["development economics", "research"]),
            locations=section.get("locations", ["Remote", "Global"]),
            match_threshold=section.get("match_threshold", 70),
            max_jobs_per_run=section.get("max_jobs_per_run", 50)
        )
    
    def _load_scrapers_config(self) -> ScrapersConfig:
        """Load scrapers configuration."""
        section = self._raw_config.get("scrapers", {})
        return ScrapersConfig(
            enabled=section.get("enabled", ["reliefweb", "devex"]),
            rate_limit_seconds=section.get("rate_limit_seconds", 2),
            timeout_seconds=section.get("timeout_seconds", 30),
            max_retries=section.get("max_retries", 3),
            rotate_user_agent=section.get("rotate_user_agent", True)
        )
    
    def _load_gemini_config(self) -> GeminiConfig:
        """Load Gemini API configuration."""
        section = self._raw_config.get("gemini", {})
        return GeminiConfig(
            model=section.get("model", "gemini-2.0-flash-exp"),
            temperature=section.get("temperature", 0.7),
            max_tokens=section.get("max_tokens", 4096),
            safety_threshold=section.get("safety_threshold", "BLOCK_ONLY_HIGH")
        )
    
    def _load_email_config(self) -> EmailConfig:
        """Load email configuration."""
        section = self._raw_config.get("email", {})
        recipient = self._resolve_env_vars(section.get("recipient", "${EMAIL_ADDRESS}"))
        return EmailConfig(
            recipient=recipient,
            send_summary=section.get("send_summary", True),
            attach_cover_letter=section.get("attach_cover_letter", True),
            attach_cv=section.get("attach_cv", True),
            cv_path=section.get("cv_path", "data/cv.pdf"),
            subject_template=section.get("subject_template", "Job Matches Found - {date} ({count} jobs)")
        )
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration."""
        section = self._raw_config.get("database", {})
        path = os.environ.get("DATABASE_PATH", section.get("path", "data/jobs.db"))
        return DatabaseConfig(
            path=path,
            retention_days=section.get("retention_days", 90)
        )
    
    def _load_logging_config(self) -> LoggingConfig:
        """Load logging configuration."""
        section = self._raw_config.get("logging", {})
        level = os.environ.get("LOG_LEVEL", section.get("level", "INFO"))
        return LoggingConfig(
            level=level,
            file=section.get("file", "logs/job_agent.log"),
            max_size_mb=section.get("max_size_mb", 10),
            backup_count=section.get("backup_count", 5)
        )
    
    def _load_output_config(self) -> OutputConfig:
        """Load output paths configuration."""
        section = self._raw_config.get("output", {})
        return OutputConfig(
            cover_letters_dir=section.get("cover_letters_dir", "output/cover_letters"),
            logs_dir=section.get("logs_dir", "logs")
        )
    
    def get_scraper_config(self, scraper_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific scraper.
        
        Args:
            scraper_name: Name of the scraper (e.g., 'reliefweb', 'devex')
            
        Returns:
            Dictionary with scraper-specific configuration
        """
        return self._scraper_configs.get(scraper_name, {})
    
    def get_api_key(self) -> str:
        """Get Gemini API key from environment."""
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set in environment")
        return api_key
    
    def is_dry_run(self) -> bool:
        """Check if running in dry run mode (no emails sent)."""
        return os.environ.get("DRY_RUN", "false").lower() == "true"
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert a relative path to absolute path based on project root."""
        return self.base_path / relative_path
    
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self.get_absolute_path(self.output.cover_letters_dir),
            self.get_absolute_path(self.output.logs_dir),
            self.get_absolute_path("data"),
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")


# Global config instance (lazy loaded)
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get the global configuration instance.
    
    Args:
        config_path: Optional path to config file (only used on first call)
        
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """
    Reload configuration from file.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        New Config instance
    """
    global _config
    _config = Config(config_path)
    return _config
