"""
Thread watchers for monitoring various woodworking communities.

This module implements watchers for Reddit, LumberJocks, SawmillCreek,
and Facebook to collect recent posts and discussions.
"""

import praw
import requests
import feedparser
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

from .models import Post, Platform, WatcherResult
from .config import Config
from .logging_config import get_logger, PerformanceLogger


class BaseWatcher:
    """Base class for all platform watchers."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def watch(self) -> WatcherResult:
        """Watch the platform for new posts."""
        raise NotImplementedError("Subclasses must implement watch method")
    
    def _extract_external_links(self, text: str) -> bool:
        """Check if text contains external links."""
        # Simple regex to detect URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return bool(re.search(url_pattern, text))


class RedditWatcher(BaseWatcher):
    """Watcher for Reddit subreddits using PRAW."""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.reddit = None
        self._initialize_reddit()
    
    def _initialize_reddit(self):
        """Initialize Reddit API connection."""
        try:
            self.reddit = praw.Reddit(
                client_id=self.config.reddit.client_id,
                client_secret=self.config.reddit.client_secret,
                user_agent=self.config.reddit.user_agent
            )
            # Test connection
            self.reddit.user.me()
            self.logger.info("Reddit API connection established")
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit API: {e}")
            self.reddit = None
    
    def watch(self) -> WatcherResult:
        """Watch Reddit subreddits for new posts."""
        result = WatcherResult(platform=Platform.REDDIT, posts_found=0, posts_processed=0)
        
        if not self.reddit:
            result.errors.append("Reddit API not initialized")
            return result
        
        with PerformanceLogger("Reddit watching", self.logger):
            try:
                posts = []
                
                for subreddit_name in self.config.reddit.subreddits:
                    try:
                        subreddit = self.reddit.subreddit(subreddit_name)
                        
                        # Get new submissions
                        for submission in subreddit.new(limit=self.config.performance.posts_per_platform):
                            post = self._convert_submission_to_post(submission, subreddit_name)
                            if post:
                                posts.append(post)
                                result.posts_found += 1
                        
                        # Get recent comments from hot posts
                        for submission in subreddit.hot(limit=10):
                            submission.comments.replace_more(limit=0)
                            for comment in submission.comments[:5]:  # Top 5 comments per post
                                if hasattr(comment, 'body') and len(comment.body) > 50:
                                    post = self._convert_comment_to_post(comment, submission, subreddit_name)
                                    if post:
                                        posts.append(post)
                                        result.posts_found += 1
                        
                        self.logger.info(f"Processed subreddit: r/{subreddit_name}")
                        
                    except Exception as e:
                        error_msg = f"Error processing subreddit r/{subreddit_name}: {e}"
                        self.logger.error(error_msg)
                        result.errors.append(error_msg)
                
                result.posts_processed = len(posts)
                self.logger.info(f"Reddit watcher found {result.posts_found} posts, processed {result.posts_processed}")
                
                return result
                
            except Exception as e:
                error_msg = f"Reddit watcher failed: {e}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
                return result
    
    def _convert_submission_to_post(self, submission, subreddit_name: str) -> Optional[Post]:
        """Convert Reddit submission to Post object."""
        try:
            # Skip if too old (older than 24 hours)
            post_time = datetime.fromtimestamp(submission.created_utc)
            if (datetime.now() - post_time).total_seconds() > 86400:  # 24 hours
                return None
            
            content = submission.selftext if submission.selftext else submission.title
            has_links = self._extract_external_links(content) or bool(submission.url and not submission.is_self)
            
            return Post(
                platform=Platform.REDDIT,
                post_id=submission.id,
                title=submission.title,
                content=content[:self.config.performance.content_preview_length],
                author=str(submission.author) if submission.author else "[deleted]",
                url=f"https://reddit.com{submission.permalink}",
                timestamp=post_time,
                has_external_links=has_links
            )
            
        except Exception as e:
            self.logger.error(f"Error converting Reddit submission: {e}")
            return None
    
    def _convert_comment_to_post(self, comment, submission, subreddit_name: str) -> Optional[Post]:
        """Convert Reddit comment to Post object."""
        try:
            # Skip if too old or too short
            post_time = datetime.fromtimestamp(comment.created_utc)
            if (datetime.now() - post_time).total_seconds() > 86400:  # 24 hours
                return None
            
            if len(comment.body) < 100:  # Skip short comments
                return None
            
            has_links = self._extract_external_links(comment.body)
            
            return Post(
                platform=Platform.REDDIT,
                post_id=f"{submission.id}_{comment.id}",
                title=f"Re: {submission.title}",
                content=comment.body[:self.config.performance.content_preview_length],
                author=str(comment.author) if comment.author else "[deleted]",
                url=f"https://reddit.com{comment.permalink}",
                timestamp=post_time,
                has_external_links=has_links
            )
            
        except Exception as e:
            self.logger.error(f"Error converting Reddit comment: {e}")
            return None


class ForumWatcher(BaseWatcher):
    """Base watcher for forum-based platforms."""
    
    def __init__(self, config: Config, forum_name: str):
        super().__init__(config)
        self.forum_name = forum_name
        self.forum_config = config.forums.get(forum_name)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WoodworkersArchive Community Watcher 1.0'
        })


class LumberJocksWatcher(ForumWatcher):
    """Watcher for LumberJocks forum."""
    
    def __init__(self, config: Config):
        super().__init__(config, "lumberjocks")
    
    def watch(self) -> WatcherResult:
        """Watch LumberJocks for new posts."""
        result = WatcherResult(platform=Platform.LUMBERJOCKS, posts_found=0, posts_processed=0)
        
        if not self.forum_config:
            result.errors.append("LumberJocks configuration not found")
            return result
        
        with PerformanceLogger("LumberJocks watching", self.logger):
            try:
                posts = []
                
                # Try RSS feed first
                if self.forum_config.rss_feed:
                    posts.extend(self._fetch_from_rss())
                
                # Fallback to HTML scraping
                if not posts:
                    posts.extend(self._fetch_from_html())
                
                result.posts_found = len(posts)
                result.posts_processed = len(posts)
                
                self.logger.info(f"LumberJocks watcher found {result.posts_found} posts")
                return result
                
            except Exception as e:
                error_msg = f"LumberJocks watcher failed: {e}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
                return result
    
    def _fetch_from_rss(self) -> List[Post]:
        """Fetch posts from RSS feed."""
        posts = []
        try:
            feed = feedparser.parse(self.forum_config.rss_feed)
            
            for entry in feed.entries[:self.config.performance.posts_per_platform]:
                post = self._convert_rss_entry_to_post(entry)
                if post:
                    posts.append(post)
            
            self.logger.info(f"Fetched {len(posts)} posts from LumberJocks RSS")
            
        except Exception as e:
            self.logger.error(f"Error fetching LumberJocks RSS: {e}")
        
        return posts
    
    def _fetch_from_html(self) -> List[Post]:
        """Fetch posts by scraping HTML."""
        posts = []
        try:
            # Try to scrape the main forum page
            response = self.session.get(f"{self.forum_config.url}/topics", timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for topic links (this is a generic approach)
            topic_links = soup.find_all('a', href=re.compile(r'/topics/'))
            
            for link in topic_links[:self.config.performance.posts_per_platform]:
                try:
                    post = self._scrape_topic_page(link)
                    if post:
                        posts.append(post)
                except Exception as e:
                    self.logger.error(f"Error scraping LumberJocks topic: {e}")
            
            self.logger.info(f"Scraped {len(posts)} posts from LumberJocks HTML")
            
        except Exception as e:
            self.logger.error(f"Error scraping LumberJocks HTML: {e}")
        
        return posts
    
    def _convert_rss_entry_to_post(self, entry) -> Optional[Post]:
        """Convert RSS entry to Post object."""
        try:
            # Parse publication date
            pub_date = datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])
            
            # Skip if too old
            if (datetime.now() - pub_date).total_seconds() > 86400:  # 24 hours
                return None
            
            content = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
            has_links = self._extract_external_links(content)
            
            return Post(
                platform=Platform.LUMBERJOCKS,
                post_id=entry.id if hasattr(entry, 'id') else entry.link,
                title=entry.title,
                content=content[:self.config.performance.content_preview_length],
                author=getattr(entry, 'author', 'Unknown'),
                url=entry.link,
                timestamp=pub_date,
                has_external_links=has_links
            )
            
        except Exception as e:
            self.logger.error(f"Error converting LumberJocks RSS entry: {e}")
            return None
    
    def _scrape_topic_page(self, link) -> Optional[Post]:
        """Scrape individual topic page."""
        try:
            topic_url = urljoin(self.forum_config.url, link.get('href'))
            response = self.session.get(topic_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic information (generic approach)
            title = link.get_text(strip=True)
            content = ""
            author = "Unknown"
            
            # Try to find content and author
            content_elem = soup.find('div', class_=re.compile(r'content|post|message'))
            if content_elem:
                content = content_elem.get_text(strip=True)
            
            author_elem = soup.find('span', class_=re.compile(r'author|user|poster'))
            if author_elem:
                author = author_elem.get_text(strip=True)
            
            has_links = self._extract_external_links(content)
            
            return Post(
                platform=Platform.LUMBERJOCKS,
                post_id=topic_url,
                title=title,
                content=content[:self.config.performance.content_preview_length],
                author=author,
                url=topic_url,
                timestamp=datetime.now(),  # Approximate timestamp
                has_external_links=has_links
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping LumberJocks topic page: {e}")
            return None


class SawmillCreekWatcher(ForumWatcher):
    """Watcher for SawmillCreek forum."""
    
    def __init__(self, config: Config):
        super().__init__(config, "sawmillcreek")
    
    def watch(self) -> WatcherResult:
        """Watch SawmillCreek for new posts."""
        result = WatcherResult(platform=Platform.SAWMILLCREEK, posts_found=0, posts_processed=0)
        
        if not self.forum_config:
            result.errors.append("SawmillCreek configuration not found")
            return result
        
        with PerformanceLogger("SawmillCreek watching", self.logger):
            try:
                posts = []
                
                # Try RSS feed first
                if self.forum_config.rss_feed:
                    posts.extend(self._fetch_from_rss())
                
                # Fallback to HTML scraping
                if not posts:
                    posts.extend(self._fetch_from_html())
                
                result.posts_found = len(posts)
                result.posts_processed = len(posts)
                
                self.logger.info(f"SawmillCreek watcher found {result.posts_found} posts")
                return result
                
            except Exception as e:
                error_msg = f"SawmillCreek watcher failed: {e}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
                return result
    
    def _fetch_from_rss(self) -> List[Post]:
        """Fetch posts from RSS feed."""
        posts = []
        try:
            feed = feedparser.parse(self.forum_config.rss_feed)
            
            for entry in feed.entries[:self.config.performance.posts_per_platform]:
                post = self._convert_rss_entry_to_post(entry)
                if post:
                    posts.append(post)
            
            self.logger.info(f"Fetched {len(posts)} posts from SawmillCreek RSS")
            
        except Exception as e:
            self.logger.error(f"Error fetching SawmillCreek RSS: {e}")
        
        return posts
    
    def _fetch_from_html(self) -> List[Post]:
        """Fetch posts by scraping HTML."""
        posts = []
        try:
            # Try to scrape the main forum page
            response = self.session.get(f"{self.forum_config.url}/forum.php", timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for thread links
            thread_links = soup.find_all('a', href=re.compile(r'showthread\.php'))
            
            for link in thread_links[:self.config.performance.posts_per_platform]:
                try:
                    post = self._scrape_thread_page(link)
                    if post:
                        posts.append(post)
                except Exception as e:
                    self.logger.error(f"Error scraping SawmillCreek thread: {e}")
            
            self.logger.info(f"Scraped {len(posts)} posts from SawmillCreek HTML")
            
        except Exception as e:
            self.logger.error(f"Error scraping SawmillCreek HTML: {e}")
        
        return posts
    
    def _convert_rss_entry_to_post(self, entry) -> Optional[Post]:
        """Convert RSS entry to Post object."""
        try:
            # Parse publication date
            pub_date = datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])
            
            # Skip if too old
            if (datetime.now() - pub_date).total_seconds() > 86400:  # 24 hours
                return None
            
            content = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
            has_links = self._extract_external_links(content)
            
            return Post(
                platform=Platform.SAWMILLCREEK,
                post_id=entry.id if hasattr(entry, 'id') else entry.link,
                title=entry.title,
                content=content[:self.config.performance.content_preview_length],
                author=getattr(entry, 'author', 'Unknown'),
                url=entry.link,
                timestamp=pub_date,
                has_external_links=has_links
            )
            
        except Exception as e:
            self.logger.error(f"Error converting SawmillCreek RSS entry: {e}")
            return None
    
    def _scrape_thread_page(self, link) -> Optional[Post]:
        """Scrape individual thread page."""
        try:
            thread_url = urljoin(self.forum_config.url, link.get('href'))
            response = self.session.get(thread_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic information
            title = link.get_text(strip=True)
            content = ""
            author = "Unknown"
            
            # Try to find first post content
            post_elem = soup.find('div', id=re.compile(r'post_message_\d+'))
            if post_elem:
                content = post_elem.get_text(strip=True)
            
            # Try to find author
            author_elem = soup.find('a', class_=re.compile(r'username|bigusername'))
            if author_elem:
                author = author_elem.get_text(strip=True)
            
            has_links = self._extract_external_links(content)
            
            return Post(
                platform=Platform.SAWMILLCREEK,
                post_id=thread_url,
                title=title,
                content=content[:self.config.performance.content_preview_length],
                author=author,
                url=thread_url,
                timestamp=datetime.now(),  # Approximate timestamp
                has_external_links=has_links
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping SawmillCreek thread page: {e}")
            return None


class FacebookWatcher(BaseWatcher):
    """Watcher for Facebook groups using Graph API."""
    
    def __init__(self, config: Config):
        super().__init__(config)
    
    def watch(self) -> WatcherResult:
        """Watch Facebook groups for new posts."""
        result = WatcherResult(platform=Platform.FACEBOOK, posts_found=0, posts_processed=0)
        
        if not self.config.facebook.access_token or self.config.facebook.access_token == "YOUR_FACEBOOK_ACCESS_TOKEN":
            result.errors.append("Facebook access token not configured")
            return result
        
        with PerformanceLogger("Facebook watching", self.logger):
            try:
                posts = []
                
                for group_id in self.config.facebook.groups:
                    try:
                        group_posts = self._fetch_group_posts(group_id)
                        posts.extend(group_posts)
                        result.posts_found += len(group_posts)
                        
                    except Exception as e:
                        error_msg = f"Error processing Facebook group {group_id}: {e}"
                        self.logger.error(error_msg)
                        result.errors.append(error_msg)
                
                result.posts_processed = len(posts)
                self.logger.info(f"Facebook watcher found {result.posts_found} posts")
                
                return result
                
            except Exception as e:
                error_msg = f"Facebook watcher failed: {e}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
                return result
    
    def _fetch_group_posts(self, group_id: str) -> List[Post]:
        """Fetch posts from a Facebook group."""
        posts = []
        try:
            # Facebook Graph API endpoint
            url = f"https://graph.facebook.com/v18.0/{group_id}/feed"
            params = {
                'access_token': self.config.facebook.access_token,
                'fields': 'id,message,created_time,from,permalink_url',
                'limit': self.config.performance.posts_per_platform
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            for post_data in data.get('data', []):
                post = self._convert_facebook_post(post_data, group_id)
                if post:
                    posts.append(post)
            
            self.logger.info(f"Fetched {len(posts)} posts from Facebook group {group_id}")
            
        except Exception as e:
            self.logger.error(f"Error fetching Facebook group {group_id}: {e}")
        
        return posts
    
    def _convert_facebook_post(self, post_data: Dict[str, Any], group_id: str) -> Optional[Post]:
        """Convert Facebook post data to Post object."""
        try:
            # Parse creation time
            created_time = datetime.fromisoformat(post_data['created_time'].replace('Z', '+00:00'))
            
            # Skip if too old
            if (datetime.now() - created_time.replace(tzinfo=None)).total_seconds() > 86400:  # 24 hours
                return None
            
            message = post_data.get('message', '')
            if len(message) < 50:  # Skip short posts
                return None
            
            has_links = self._extract_external_links(message)
            
            return Post(
                platform=Platform.FACEBOOK,
                post_id=post_data['id'],
                title=message[:100] + "..." if len(message) > 100 else message,
                content=message[:self.config.performance.content_preview_length],
                author=post_data.get('from', {}).get('name', 'Unknown'),
                url=post_data.get('permalink_url', f"https://facebook.com/{post_data['id']}"),
                timestamp=created_time.replace(tzinfo=None),
                has_external_links=has_links
            )
            
        except Exception as e:
            self.logger.error(f"Error converting Facebook post: {e}")
            return None


class WatcherManager:
    """Manages all platform watchers."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        self.watchers = self._initialize_watchers()
    
    def _initialize_watchers(self) -> Dict[Platform, BaseWatcher]:
        """Initialize all watchers."""
        watchers = {}
        
        # Reddit watcher
        if self.config.reddit.client_id and self.config.reddit.client_id != "YOUR_REDDIT_CLIENT_ID":
            watchers[Platform.REDDIT] = RedditWatcher(self.config)
        
        # LumberJocks watcher
        if "lumberjocks" in self.config.forums:
            watchers[Platform.LUMBERJOCKS] = LumberJocksWatcher(self.config)
        
        # SawmillCreek watcher
        if "sawmillcreek" in self.config.forums:
            watchers[Platform.SAWMILLCREEK] = SawmillCreekWatcher(self.config)
        
        # Facebook watcher
        if self.config.facebook.access_token and self.config.facebook.access_token != "YOUR_FACEBOOK_ACCESS_TOKEN":
            watchers[Platform.FACEBOOK] = FacebookWatcher(self.config)
        
        self.logger.info(f"Initialized {len(watchers)} watchers: {list(watchers.keys())}")
        return watchers
    
    def watch_all(self) -> Dict[Platform, WatcherResult]:
        """Run all watchers and return results."""
        results = {}
        
        with PerformanceLogger("All watchers", self.logger):
            for platform, watcher in self.watchers.items():
                try:
                    result = watcher.watch()
                    results[platform] = result
                    
                    if result.success:
                        self.logger.info(f"{platform.value} watcher completed successfully: "
                                       f"{result.posts_found} posts found, {result.posts_processed} processed")
                    else:
                        self.logger.warning(f"{platform.value} watcher completed with errors: {result.errors}")
                        
                except Exception as e:
                    error_msg = f"Watcher {platform.value} failed: {e}"
                    self.logger.error(error_msg)
                    results[platform] = WatcherResult(
                        platform=platform,
                        posts_found=0,
                        posts_processed=0,
                        errors=[error_msg]
                    )
        
        return results
    
    def get_all_posts(self) -> List[Post]:
        """Get all posts from all watchers."""
        all_posts = []
        results = self.watch_all()
        
        for platform, result in results.items():
            if result.success and hasattr(result, 'posts'):
                all_posts.extend(result.posts)
        
        return all_posts

