"""
Data models for the Community Engagement Engine.

This module defines the data structures used for posts, scoring,
and other core entities in the system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class Platform(Enum):
    """Supported platforms for community monitoring."""
    REDDIT = "reddit"
    LUMBERJOCKS = "lumberjocks"
    SAWMILLCREEK = "sawmillcreek"
    FACEBOOK = "facebook"


@dataclass
class Post:
    """Represents a post from any platform."""
    platform: Platform
    post_id: str
    title: str
    content: str
    author: str
    url: str
    timestamp: datetime
    score: int = 0
    keyword_matches: List[str] = field(default_factory=list)
    has_external_links: bool = False
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure platform is a Platform enum
        if isinstance(self.platform, str):
            self.platform = Platform(self.platform)
    
    @property
    def age_minutes(self) -> int:
        """Get the age of the post in minutes."""
        return int((datetime.now() - self.timestamp).total_seconds() / 60)
    
    @property
    def is_recent(self) -> bool:
        """Check if the post is recent (under 60 minutes)."""
        return self.age_minutes < 60
    
    @property
    def preview_content(self) -> str:
        """Get a preview of the content (first 250 characters)."""
        if len(self.content) <= 250:
            return self.content
        return self.content[:247] + "..."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert post to dictionary for serialization."""
        return {
            'platform': self.platform.value,
            'post_id': self.post_id,
            'title': self.title,
            'content': self.content,
            'author': self.author,
            'url': self.url,
            'timestamp': self.timestamp.isoformat(),
            'score': self.score,
            'keyword_matches': self.keyword_matches,
            'has_external_links': self.has_external_links,
            'age_minutes': self.age_minutes,
            'is_recent': self.is_recent
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        """Create post from dictionary."""
        return cls(
            platform=Platform(data['platform']),
            post_id=data['post_id'],
            title=data['title'],
            content=data['content'],
            author=data['author'],
            url=data['url'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            score=data.get('score', 0),
            keyword_matches=data.get('keyword_matches', []),
            has_external_links=data.get('has_external_links', False)
        )


@dataclass
class ScoringResult:
    """Represents the result of scoring a post."""
    post: Post
    keyword_score: int
    time_bonus: int
    link_penalty: int
    final_score: int
    matched_keywords: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scoring result to dictionary."""
        return {
            'post': self.post.to_dict(),
            'keyword_score': self.keyword_score,
            'time_bonus': self.time_bonus,
            'link_penalty': self.link_penalty,
            'final_score': self.final_score,
            'matched_keywords': self.matched_keywords
        }


@dataclass
class DigestEntry:
    """Represents an entry in a digest."""
    post: Post
    score: int
    platform_icon: str
    
    @property
    def platform_display(self) -> str:
        """Get display name for platform."""
        platform_names = {
            Platform.REDDIT: "🔴 Reddit",
            Platform.LUMBERJOCKS: "🪵 LumberJocks",
            Platform.SAWMILLCREEK: "🪚 SawmillCreek",
            Platform.FACEBOOK: "📘 Facebook"
        }
        return platform_names.get(self.post.platform, str(self.post.platform.value))


@dataclass
class Digest:
    """Represents a complete digest of posts."""
    entries: List[DigestEntry]
    generated_at: datetime
    execution_duration: float
    total_posts_processed: int
    
    def to_markdown(self) -> str:
        """Convert digest to Markdown format."""
        lines = [
            "# WoodworkersArchive Community Digest",
            f"*Generated at {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}*",
            f"*Processed {self.total_posts_processed} posts in {self.execution_duration:.1f} seconds*",
            "",
            "## Top Opportunities",
            ""
        ]
        
        if not self.entries:
            lines.append("No relevant posts found in this run.")
        else:
            for i, entry in enumerate(self.entries, 1):
                lines.extend([
                    f"### {i}. {entry.platform_display} (Score: {entry.score})",
                    f"**{entry.post.title}**",
                    f"*by {entry.post.author} • {entry.post.age_minutes} minutes ago*",
                    f"[View Post]({entry.post.url})",
                    "",
                    f"{entry.post.preview_content}",
                    ""
                ])
        
        lines.extend([
            "---",
            f"*Execution completed in {self.execution_duration:.1f} seconds*"
        ])
        
        return "\n".join(lines)
    
    def to_slack_blocks(self) -> List[Dict[str, Any]]:
        """Convert digest to Slack block format."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🪵 WoodworkersArchive Community Digest"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Generated at {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')} • "
                               f"Processed {self.total_posts_processed} posts in {self.execution_duration:.1f}s"
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]
        
        if not self.entries:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No relevant posts found in this run."
                }
            })
        else:
            for i, entry in enumerate(self.entries, 1):
                blocks.extend([
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{i}. {entry.platform_display} (Score: {entry.score})*\n"
                                   f"*{entry.post.title}*\n"
                                   f"by {entry.post.author} • {entry.post.age_minutes} minutes ago\n"
                                   f"<{entry.post.url}|View Post>"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": entry.post.preview_content
                            }
                        ]
                    }
                ])
                
                if i < len(self.entries):
                    blocks.append({"type": "divider"})
        
        return blocks


@dataclass
class WatcherResult:
    """Represents the result of a watcher run."""
    platform: Platform
    posts_found: int
    posts_processed: int
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    
    @property
    def success(self) -> bool:
        """Check if the watcher run was successful."""
        return len(self.errors) == 0


@dataclass
class EngagementOpportunity:
    """Represents a high-value engagement opportunity."""
    post: Post
    score: int
    suggested_response: Optional[str] = None
    utm_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'post': self.post.to_dict(),
            'score': self.score,
            'suggested_response': self.suggested_response,
            'utm_url': self.utm_url
        }


@dataclass
class ExecutionMetrics:
    """Represents metrics for a complete execution run."""
    start_time: datetime
    end_time: datetime
    total_posts_found: int
    total_posts_scored: int
    top_score: int
    platforms_processed: List[Platform]
    digest_sent: bool
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Get execution duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return len(self.errors) == 0 and self.duration_seconds < 120
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': self.duration_seconds,
            'total_posts_found': self.total_posts_found,
            'total_posts_scored': self.total_posts_scored,
            'top_score': self.top_score,
            'platforms_processed': [p.value for p in self.platforms_processed],
            'digest_sent': self.digest_sent,
            'errors': self.errors,
            'success': self.success
        }

