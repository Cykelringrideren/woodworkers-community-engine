"""
Scoring and filtering system for the Community Engagement Engine.

This module implements keyword matching, post scoring, and filtering
to identify high-value engagement opportunities.
"""

import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

from .models import Post, ScoringResult, Platform
from .database import DatabaseManager, KeywordManager
from .config import Config
from .logging_config import get_logger, PerformanceLogger


class KeywordMatcher:
    """Handles keyword matching and scoring."""
    
    def __init__(self, keyword_manager: KeywordManager, config: Config):
        self.keyword_manager = keyword_manager
        self.config = config
        self.logger = get_logger(__name__)
        
        # Cache keywords for performance
        self._keyword_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes
    
    def _get_keywords(self) -> List[Tuple[str, str, int]]:
        """Get keywords with caching."""
        now = datetime.now()
        
        if (self._keyword_cache is None or 
            self._cache_timestamp is None or 
            (now - self._cache_timestamp).total_seconds() > self._cache_ttl):
            
            self._keyword_cache = self.keyword_manager.db.get_keywords()
            self._cache_timestamp = now
            self.logger.debug(f"Refreshed keyword cache with {len(self._keyword_cache)} keywords")
        
        return self._keyword_cache
    
    def find_matches(self, text: str) -> List[Tuple[str, str, int]]:
        """Find keyword matches in text."""
        if not text:
            return []
        
        text_lower = text.lower()
        matches = []
        keywords = self._get_keywords()
        
        for keyword, category, score_value in keywords:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                matches.append((keyword, category, score_value))
        
        return matches
    
    def calculate_keyword_score(self, matches: List[Tuple[str, str, int]]) -> int:
        """Calculate total keyword score from matches."""
        if not matches:
            return 0
        
        # Sum up all keyword scores, but cap individual keyword contributions
        total_score = 0
        keyword_counts = {}
        
        for keyword, category, score_value in matches:
            # Count occurrences of each keyword
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            
            # Apply diminishing returns for repeated keywords
            if keyword_counts[keyword] == 1:
                total_score += score_value
            elif keyword_counts[keyword] == 2:
                total_score += score_value // 2
            # No additional score for 3+ occurrences
        
        return total_score


class PostScorer:
    """Scores posts based on keywords, timing, and other factors."""
    
    def __init__(self, config: Config, keyword_matcher: KeywordMatcher):
        self.config = config
        self.keyword_matcher = keyword_matcher
        self.logger = get_logger(__name__)
    
    def score_post(self, post: Post) -> ScoringResult:
        """Score a single post."""
        # Find keyword matches
        title_matches = self.keyword_matcher.find_matches(post.title)
        content_matches = self.keyword_matcher.find_matches(post.content)
        
        # Combine matches (remove duplicates)
        all_matches = title_matches + content_matches
        unique_matches = list(set(all_matches))
        
        # Calculate keyword score
        keyword_score = self.keyword_matcher.calculate_keyword_score(unique_matches)
        
        # Calculate time bonus
        time_bonus = 0
        if post.is_recent:
            time_bonus = self.config.scoring.recent_post_bonus
        
        # Calculate link penalty
        link_penalty = 0
        if post.has_external_links:
            link_penalty = self.config.scoring.external_link_penalty
        
        # Calculate final score
        final_score = keyword_score + time_bonus + link_penalty
        
        # Update post with matches and score
        post.keyword_matches = [match[0] for match in unique_matches]
        post.score = final_score
        
        matched_keywords = [match[0] for match in unique_matches]
        
        return ScoringResult(
            post=post,
            keyword_score=keyword_score,
            time_bonus=time_bonus,
            link_penalty=link_penalty,
            final_score=final_score,
            matched_keywords=matched_keywords
        )
    
    def score_posts(self, posts: List[Post]) -> List[ScoringResult]:
        """Score multiple posts."""
        results = []
        
        with PerformanceLogger(f"Scoring {len(posts)} posts", self.logger):
            for post in posts:
                try:
                    result = self.score_post(post)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Error scoring post {post.post_id}: {e}")
        
        # Sort by score descending
        results.sort(key=lambda x: x.final_score, reverse=True)
        
        self.logger.info(f"Scored {len(results)} posts, top score: {results[0].final_score if results else 0}")
        
        return results


class PostFilter:
    """Filters posts based on various criteria."""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.logger = get_logger(__name__)
    
    def filter_duplicates(self, posts: List[Post]) -> List[Post]:
        """Remove duplicate posts based on platform and post_id."""
        seen = set()
        filtered = []
        
        for post in posts:
            key = (post.platform.value, post.post_id)
            if key not in seen:
                seen.add(key)
                filtered.append(post)
            else:
                self.logger.debug(f"Filtered duplicate post: {post.post_id}")
        
        return filtered
    
    def filter_processed(self, posts: List[Post]) -> List[Post]:
        """Remove posts that have already been processed."""
        filtered = []
        
        for post in posts:
            if not self.db_manager.is_post_processed(post.platform.value, post.post_id):
                filtered.append(post)
            else:
                self.logger.debug(f"Filtered already processed post: {post.post_id}")
        
        return filtered
    
    def filter_by_age(self, posts: List[Post], max_age_hours: int = 24) -> List[Post]:
        """Filter posts by age."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        filtered = []
        
        for post in posts:
            if post.timestamp >= cutoff_time:
                filtered.append(post)
            else:
                self.logger.debug(f"Filtered old post: {post.post_id} ({post.age_minutes} minutes old)")
        
        return filtered
    
    def filter_by_score(self, scoring_results: List[ScoringResult], min_score: int = 1) -> List[ScoringResult]:
        """Filter scoring results by minimum score."""
        filtered = [result for result in scoring_results if result.final_score >= min_score]
        
        self.logger.info(f"Filtered {len(scoring_results)} results to {len(filtered)} with min score {min_score}")
        
        return filtered
    
    def filter_top_posts(self, scoring_results: List[ScoringResult]) -> List[ScoringResult]:
        """Keep only the top posts per run."""
        max_posts = self.config.scoring.max_posts_per_run
        
        if len(scoring_results) <= max_posts:
            return scoring_results
        
        top_results = scoring_results[:max_posts]
        self.logger.info(f"Filtered to top {max_posts} posts from {len(scoring_results)} total")
        
        return top_results


class ScoringEngine:
    """Main scoring engine that coordinates all scoring operations."""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.keyword_manager = KeywordManager(db_manager)
        self.keyword_matcher = KeywordMatcher(self.keyword_manager, config)
        self.scorer = PostScorer(config, self.keyword_matcher)
        self.filter = PostFilter(config, db_manager)
        self.logger = get_logger(__name__)
    
    def process_posts(self, posts: List[Post]) -> List[ScoringResult]:
        """Process posts through the complete scoring pipeline."""
        with PerformanceLogger("Complete scoring pipeline", self.logger):
            # Filter posts
            filtered_posts = self.filter.filter_duplicates(posts)
            filtered_posts = self.filter.filter_processed(filtered_posts)
            filtered_posts = self.filter.filter_by_age(filtered_posts)
            
            self.logger.info(f"Filtered {len(posts)} posts to {len(filtered_posts)} for scoring")
            
            if not filtered_posts:
                return []
            
            # Score posts
            scoring_results = self.scorer.score_posts(filtered_posts)
            
            # Filter by score and limit results
            scoring_results = self.filter.filter_by_score(scoring_results)
            scoring_results = self.filter.filter_top_posts(scoring_results)
            
            # Save posts to database
            self._save_posts_to_db(scoring_results)
            
            return scoring_results
    
    def _save_posts_to_db(self, scoring_results: List[ScoringResult]):
        """Save scored posts to database."""
        for result in scoring_results:
            try:
                # Save post
                post_db_id = self.db_manager.save_post(
                    platform=result.post.platform.value,
                    post_id=result.post.post_id,
                    title=result.post.title,
                    content=result.post.content,
                    author=result.post.author,
                    url=result.post.url,
                    post_timestamp=result.post.timestamp,
                    score=result.final_score
                )
                
                # Save scoring history
                if post_db_id:
                    self.db_manager.save_scoring_history(
                        post_db_id=post_db_id,
                        keyword_matches=result.matched_keywords,
                        base_score=result.keyword_score,
                        time_bonus=result.time_bonus,
                        link_penalty=result.link_penalty,
                        final_score=result.final_score
                    )
                
            except Exception as e:
                self.logger.error(f"Error saving post {result.post.post_id} to database: {e}")
    
    def get_top_opportunities(self, hours: int = 24, min_score: int = 5) -> List[ScoringResult]:
        """Get top engagement opportunities from recent posts."""
        recent_posts_data = self.db_manager.get_recent_posts(hours=hours, min_score=min_score)
        
        scoring_results = []
        for post_data in recent_posts_data:
            # Convert database record back to Post and ScoringResult
            post = Post(
                platform=Platform(post_data['platform']),
                post_id=post_data['post_id'],
                title=post_data['title'],
                content=post_data['content'],
                author=post_data['author'],
                url=post_data['url'],
                timestamp=datetime.fromisoformat(post_data['post_timestamp']),
                score=post_data['score']
            )
            
            # Create a basic scoring result (detailed scoring history would need separate query)
            result = ScoringResult(
                post=post,
                keyword_score=post_data['score'],  # Simplified
                time_bonus=0,
                link_penalty=0,
                final_score=post_data['score'],
                matched_keywords=[]
            )
            
            scoring_results.append(result)
        
        return scoring_results

