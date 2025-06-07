"""
Configuration management for the Community Engagement Engine.

This module handles loading and validating configuration from YAML files,
environment variables, and provides default values.
"""

import os
import yaml
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class RedditConfig:
    """Reddit API configuration."""
    client_id: str
    client_secret: str
    user_agent: str
    subreddits: List[str] = field(default_factory=list)


@dataclass
class ForumConfig:
    """Forum configuration for RSS/HTML scraping."""
    url: str
    rss_feed: Optional[str] = None


@dataclass
class FacebookConfig:
    """Facebook Graph API configuration."""
    access_token: str
    groups: List[str] = field(default_factory=list)


@dataclass
class NotificationConfig:
    """Notification configuration for Slack and email."""
    slack_webhook_url: Optional[str] = None
    slack_channel: str = "#community-engagement"
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_to: Optional[str] = None


@dataclass
class UTMConfig:
    """UTM tracking configuration."""
    base_url: str
    default_campaign: str = "community_engagement"
    source_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class ScoringConfig:
    """Scoring algorithm configuration."""
    keyword_match: int = 5
    recent_post_bonus: int = 2
    external_link_penalty: int = -1
    max_posts_per_run: int = 20


@dataclass
class PerformanceConfig:
    """Performance and limits configuration."""
    max_execution_time: int = 120
    posts_per_platform: int = 50
    content_preview_length: int = 250


@dataclass
class LLMConfig:
    """Optional LLM configuration."""
    enabled: bool = False
    model: str = "llama3:8b"
    ollama_host: str = "http://localhost:11434"


@dataclass
class Config:
    """Main configuration class."""
    reddit: RedditConfig
    forums: Dict[str, ForumConfig]
    facebook: FacebookConfig
    notifications: NotificationConfig
    utm: UTMConfig
    scoring: ScoringConfig
    performance: PerformanceConfig
    llm: LLMConfig
    keywords: Dict[str, List[str]] = field(default_factory=dict)


class ConfigLoader:
    """Configuration loader with environment variable support."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
    
    def load(self) -> Config:
        """Load configuration from file and environment variables."""
        try:
            # Load base configuration from YAML
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Override with environment variables
            config_data = self._apply_env_overrides(config_data)
            
            # Validate and create config objects
            return self._create_config(config_data)
            
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        # Reddit overrides
        if os.getenv('REDDIT_CLIENT_ID'):
            config_data.setdefault('reddit', {})['client_id'] = os.getenv('REDDIT_CLIENT_ID')
        if os.getenv('REDDIT_CLIENT_SECRET'):
            config_data.setdefault('reddit', {})['client_secret'] = os.getenv('REDDIT_CLIENT_SECRET')
        
        # Facebook overrides
        if os.getenv('FACEBOOK_ACCESS_TOKEN'):
            config_data.setdefault('facebook', {})['access_token'] = os.getenv('FACEBOOK_ACCESS_TOKEN')
        
        # Notification overrides
        if os.getenv('SLACK_WEBHOOK_URL'):
            config_data.setdefault('notifications', {})['slack_webhook_url'] = os.getenv('SLACK_WEBHOOK_URL')
        if os.getenv('EMAIL_USERNAME'):
            config_data.setdefault('notifications', {})['email_username'] = os.getenv('EMAIL_USERNAME')
        if os.getenv('EMAIL_PASSWORD'):
            config_data.setdefault('notifications', {})['email_password'] = os.getenv('EMAIL_PASSWORD')
        
        return config_data
    
    def _create_config(self, config_data: Dict[str, Any]) -> Config:
        """Create configuration objects from loaded data."""
        # Reddit configuration
        reddit_data = config_data.get('reddit', {})
        reddit_config = RedditConfig(
            client_id=reddit_data.get('client_id', ''),
            client_secret=reddit_data.get('client_secret', ''),
            user_agent=reddit_data.get('user_agent', 'Community Watcher v1.0'),
            subreddits=reddit_data.get('subreddits', [])
        )
        
        # Forum configurations
        forums_data = config_data.get('forums', {})
        forums_config = {}
        for name, forum_data in forums_data.items():
            forums_config[name] = ForumConfig(
                url=forum_data.get('url', ''),
                rss_feed=forum_data.get('rss_feed')
            )
        
        # Facebook configuration
        facebook_data = config_data.get('facebook', {})
        facebook_config = FacebookConfig(
            access_token=facebook_data.get('access_token', ''),
            groups=facebook_data.get('groups', [])
        )
        
        # Notification configuration
        notifications_data = config_data.get('notifications', {})
        slack_data = notifications_data.get('slack', {})
        email_data = notifications_data.get('email', {})
        
        notifications_config = NotificationConfig(
            slack_webhook_url=slack_data.get('webhook_url'),
            slack_channel=slack_data.get('channel', '#community-engagement'),
            smtp_server=email_data.get('smtp_server'),
            smtp_port=email_data.get('smtp_port', 587),
            email_username=email_data.get('username'),
            email_password=email_data.get('password'),
            email_to=email_data.get('to_address')
        )
        
        # UTM configuration
        utm_data = config_data.get('utm', {})
        utm_config = UTMConfig(
            base_url=utm_data.get('base_url', 'https://woodworkersarchive.com'),
            default_campaign=utm_data.get('default_campaign', 'community_engagement'),
            source_mapping=utm_data.get('source_mapping', {})
        )
        
        # Scoring configuration
        scoring_data = config_data.get('scoring', {})
        scoring_config = ScoringConfig(
            keyword_match=scoring_data.get('keyword_match', 5),
            recent_post_bonus=scoring_data.get('recent_post_bonus', 2),
            external_link_penalty=scoring_data.get('external_link_penalty', -1),
            max_posts_per_run=scoring_data.get('max_posts_per_run', 20)
        )
        
        # Performance configuration
        performance_data = config_data.get('performance', {})
        performance_config = PerformanceConfig(
            max_execution_time=performance_data.get('max_execution_time', 120),
            posts_per_platform=performance_data.get('posts_per_platform', 50),
            content_preview_length=performance_data.get('content_preview_length', 250)
        )
        
        # LLM configuration
        llm_data = config_data.get('llm', {})
        llm_config = LLMConfig(
            enabled=llm_data.get('enabled', False),
            model=llm_data.get('model', 'llama3:8b'),
            ollama_host=llm_data.get('ollama_host', 'http://localhost:11434')
        )
        
        return Config(
            reddit=reddit_config,
            forums=forums_config,
            facebook=facebook_config,
            notifications=notifications_config,
            utm=utm_config,
            scoring=scoring_config,
            performance=performance_config,
            llm=llm_config,
            keywords=config_data.get('keywords', {})
        )
    
    def validate(self, config: Config) -> bool:
        """Validate configuration for required fields."""
        errors = []
        
        # Validate Reddit configuration
        if not config.reddit.client_id or config.reddit.client_id == "YOUR_REDDIT_CLIENT_ID":
            errors.append("Reddit client_id is required")
        if not config.reddit.client_secret or config.reddit.client_secret == "YOUR_REDDIT_CLIENT_SECRET":
            errors.append("Reddit client_secret is required")
        
        # Validate notification configuration
        if not config.notifications.slack_webhook_url and not config.notifications.email_username:
            errors.append("Either Slack webhook URL or email configuration is required")
        
        if errors:
            self.logger.error("Configuration validation failed:")
            for error in errors:
                self.logger.error(f"  - {error}")
            return False
        
        return True


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        loader = ConfigLoader()
        _config = loader.load()
        if not loader.validate(_config):
            raise ValueError("Configuration validation failed")
    return _config


def reload_config(config_path: str = "config/config.yaml") -> Config:
    """Reload configuration from file."""
    global _config
    loader = ConfigLoader(config_path)
    _config = loader.load()
    if not loader.validate(_config):
        raise ValueError("Configuration validation failed")
    return _config

