"""
Digest generation and notification system for the Community Engagement Engine.

This module creates digests from scored posts and sends them via Slack or email.
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .models import Post, ScoringResult, Digest, DigestEntry, Platform
from .config import Config
from .database import DatabaseManager
from .logging_config import get_logger, PerformanceLogger


class DigestGenerator:
    """Generates digests from scored posts."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
    
    def create_digest(self, scoring_results: List[ScoringResult], 
                     execution_duration: float, total_posts_processed: int) -> Digest:
        """Create a digest from scoring results."""
        entries = []
        
        for result in scoring_results:
            entry = DigestEntry(
                post=result.post,
                score=result.final_score,
                platform_icon=self._get_platform_icon(result.post.platform)
            )
            entries.append(entry)
        
        digest = Digest(
            entries=entries,
            generated_at=datetime.now(),
            execution_duration=execution_duration,
            total_posts_processed=total_posts_processed
        )
        
        self.logger.info(f"Created digest with {len(entries)} entries")
        return digest
    
    def _get_platform_icon(self, platform: Platform) -> str:
        """Get icon/emoji for platform."""
        icons = {
            Platform.REDDIT: "🔴",
            Platform.LUMBERJOCKS: "🪵",
            Platform.SAWMILLCREEK: "🪚",
            Platform.FACEBOOK: "📘"
        }
        return icons.get(platform, "📄")


class SlackNotifier:
    """Handles Slack notifications."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        self.webhook_url = config.notifications.slack_webhook_url
        self.channel = config.notifications.slack_channel
    
    def send_digest(self, digest: Digest) -> bool:
        """Send digest to Slack via webhook."""
        if not self.webhook_url or self.webhook_url == "YOUR_SLACK_WEBHOOK_URL":
            self.logger.warning("Slack webhook URL not configured")
            return False
        
        try:
            with PerformanceLogger("Slack notification", self.logger):
                # Create Slack message
                message = self._create_slack_message(digest)
                
                # Send via webhook
                response = requests.post(
                    self.webhook_url,
                    json=message,
                    timeout=10
                )
                response.raise_for_status()
                
                self.logger.info(f"Successfully sent digest to Slack with {len(digest.entries)} entries")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def _create_slack_message(self, digest: Digest) -> Dict[str, Any]:
        """Create Slack message payload."""
        if not digest.entries:
            return {
                "text": "🪵 WoodworkersArchive Community Digest",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🪵 WoodworkersArchive Community Digest"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*No relevant posts found in this run.*\n"
                                   f"Processed {digest.total_posts_processed} posts in {digest.execution_duration:.1f} seconds"
                        }
                    }
                ]
            }
        
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
                        "text": f"Generated at {digest.generated_at.strftime('%Y-%m-%d %H:%M:%S')} • "
                               f"Processed {digest.total_posts_processed} posts in {digest.execution_duration:.1f}s"
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]
        
        for i, entry in enumerate(digest.entries[:10], 1):  # Limit to 10 for Slack
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
            
            if i < len(digest.entries) and i < 10:
                blocks.append({"type": "divider"})
        
        if len(digest.entries) > 10:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"... and {len(digest.entries) - 10} more opportunities"
                    }
                ]
            })
        
        return {
            "text": "🪵 WoodworkersArchive Community Digest",
            "blocks": blocks
        }


class EmailNotifier:
    """Handles email notifications."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
    
    def send_digest(self, digest: Digest) -> bool:
        """Send digest via email."""
        if not self._is_configured():
            self.logger.warning("Email configuration incomplete")
            return False
        
        try:
            with PerformanceLogger("Email notification", self.logger):
                # Create email message
                msg = self._create_email_message(digest)
                
                # Send email
                with smtplib.SMTP(self.config.notifications.smtp_server, 
                                self.config.notifications.smtp_port) as server:
                    server.starttls()
                    server.login(
                        self.config.notifications.email_username,
                        self.config.notifications.email_password
                    )
                    server.send_message(msg)
                
                self.logger.info(f"Successfully sent digest email with {len(digest.entries)} entries")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _is_configured(self) -> bool:
        """Check if email is properly configured."""
        return all([
            self.config.notifications.smtp_server,
            self.config.notifications.email_username,
            self.config.notifications.email_password,
            self.config.notifications.email_to
        ])
    
    def _create_email_message(self, digest: Digest) -> MIMEMultipart:
        """Create email message."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"WoodworkersArchive Community Digest - {len(digest.entries)} Opportunities"
        msg['From'] = self.config.notifications.email_username
        msg['To'] = self.config.notifications.email_to
        
        # Create text version
        text_content = digest.to_markdown()
        text_part = MIMEText(text_content, 'plain')
        msg.attach(text_part)
        
        # Create HTML version
        html_content = self._markdown_to_html(text_content)
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        return msg
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """Convert Markdown to basic HTML."""
        # Simple Markdown to HTML conversion
        html = markdown_text
        
        # Headers
        html = html.replace('# ', '<h1>').replace('\n## ', '</h1>\n<h2>')
        html = html.replace('\n### ', '</h2>\n<h3>')
        
        # Bold text
        html = html.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
        
        # Italic text
        html = html.replace('*', '<em>', 1).replace('*', '</em>', 1)
        
        # Links
        import re
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        html = re.sub(link_pattern, r'<a href="\2">\1</a>', html)
        
        # Line breaks
        html = html.replace('\n', '<br>\n')
        
        # Wrap in basic HTML structure
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                h1 {{ color: #8B4513; }}
                h2 {{ color: #A0522D; }}
                h3 {{ color: #CD853F; }}
                a {{ color: #1E90FF; }}
            </style>
        </head>
        <body>
            {html}
        </body>
        </html>
        """
        
        return html


class NotificationManager:
    """Manages all notification channels."""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.logger = get_logger(__name__)
        
        self.slack_notifier = SlackNotifier(config)
        self.email_notifier = EmailNotifier(config)
    
    def send_digest(self, digest: Digest) -> Dict[str, bool]:
        """Send digest via all configured channels."""
        results = {}
        
        # Try Slack
        if self.config.notifications.slack_webhook_url:
            try:
                results['slack'] = self.slack_notifier.send_digest(digest)
                self.db_manager.save_digest_history(
                    digest_type='slack',
                    post_count=len(digest.entries),
                    success=results['slack']
                )
            except Exception as e:
                self.logger.error(f"Slack notification failed: {e}")
                results['slack'] = False
                self.db_manager.save_digest_history(
                    digest_type='slack',
                    post_count=len(digest.entries),
                    success=False,
                    error_message=str(e)
                )
        
        # Try Email
        if self.email_notifier._is_configured():
            try:
                results['email'] = self.email_notifier.send_digest(digest)
                self.db_manager.save_digest_history(
                    digest_type='email',
                    post_count=len(digest.entries),
                    success=results['email']
                )
            except Exception as e:
                self.logger.error(f"Email notification failed: {e}")
                results['email'] = False
                self.db_manager.save_digest_history(
                    digest_type='email',
                    post_count=len(digest.entries),
                    success=False,
                    error_message=str(e)
                )
        
        # Log results
        successful_channels = [channel for channel, success in results.items() if success]
        if successful_channels:
            self.logger.info(f"Digest sent successfully via: {', '.join(successful_channels)}")
        else:
            self.logger.warning("Failed to send digest via any channel")
        
        return results
    
    def send_test_notification(self) -> Dict[str, bool]:
        """Send a test notification to verify configuration."""
        from .models import Post, ScoringResult, DigestEntry
        
        # Create a test digest
        test_post = Post(
            platform=Platform.REDDIT,
            post_id="test_123",
            title="Test Post: Table Saw Safety Tips",
            content="This is a test post to verify the notification system is working correctly.",
            author="test_user",
            url="https://reddit.com/r/woodworking/test_123",
            timestamp=datetime.now(),
            score=10
        )
        
        test_entry = DigestEntry(
            post=test_post,
            score=10,
            platform_icon="🔴"
        )
        
        test_digest = Digest(
            entries=[test_entry],
            generated_at=datetime.now(),
            execution_duration=1.0,
            total_posts_processed=1
        )
        
        return self.send_digest(test_digest)

