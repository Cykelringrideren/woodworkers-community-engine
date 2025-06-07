"""
Database management for the Community Engagement Engine.

This module handles SQLite database operations for storing keywords,
post metadata, and scoring history.
"""

import sqlite3
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path


class DatabaseManager:
    """Manages SQLite database operations."""
    
    def __init__(self, db_path: str = "data/community_engine.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Keywords table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    score_value INTEGER NOT NULL DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Posts table for tracking processed posts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    author TEXT,
                    url TEXT,
                    score INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    post_timestamp TIMESTAMP,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, post_id)
                )
            """)
            
            # Scoring history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scoring_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    keyword_matches TEXT,  -- JSON array of matched keywords
                    base_score INTEGER,
                    time_bonus INTEGER,
                    link_penalty INTEGER,
                    final_score INTEGER,
                    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts (id)
                )
            """)
            
            # Digest history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS digest_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    digest_type TEXT NOT NULL,  -- 'slack' or 'email'
                    post_count INTEGER,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_platform_timestamp ON posts(platform, post_timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_score ON posts(score DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_category ON keywords(category)")
            
            conn.commit()
            self.logger.info("Database initialized successfully")
    
    def add_keyword(self, keyword: str, category: str = "general", score_value: int = 5) -> bool:
        """Add a new keyword to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO keywords (keyword, category, score_value, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (keyword.lower(), category, score_value))
                conn.commit()
                self.logger.info(f"Added keyword: {keyword} (category: {category}, score: {score_value})")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error adding keyword {keyword}: {e}")
            return False
    
    def remove_keyword(self, keyword: str) -> bool:
        """Remove a keyword from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM keywords WHERE keyword = ?", (keyword.lower(),))
                if cursor.rowcount > 0:
                    conn.commit()
                    self.logger.info(f"Removed keyword: {keyword}")
                    return True
                else:
                    self.logger.warning(f"Keyword not found: {keyword}")
                    return False
        except sqlite3.Error as e:
            self.logger.error(f"Error removing keyword {keyword}: {e}")
            return False
    
    def get_keywords(self, category: Optional[str] = None) -> List[Tuple[str, str, int]]:
        """Get keywords from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if category:
                    cursor.execute("""
                        SELECT keyword, category, score_value 
                        FROM keywords 
                        WHERE category = ?
                        ORDER BY score_value DESC, keyword
                    """, (category,))
                else:
                    cursor.execute("""
                        SELECT keyword, category, score_value 
                        FROM keywords 
                        ORDER BY category, score_value DESC, keyword
                    """)
                return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error getting keywords: {e}")
            return []
    
    def bulk_import_keywords(self, keywords_dict: Dict[str, List[str]]) -> int:
        """Bulk import keywords from a dictionary."""
        imported_count = 0
        
        # Define score values for different categories
        category_scores = {
            'high_value': 8,
            'medium_value': 5,
            'low_value': 3,
            'general': 5
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for category, keyword_list in keywords_dict.items():
                    score_value = category_scores.get(category, 5)
                    
                    for keyword in keyword_list:
                        try:
                            cursor.execute("""
                                INSERT OR REPLACE INTO keywords (keyword, category, score_value, updated_at)
                                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                            """, (keyword.lower(), category, score_value))
                            imported_count += 1
                        except sqlite3.Error as e:
                            self.logger.error(f"Error importing keyword {keyword}: {e}")
                
                conn.commit()
                self.logger.info(f"Bulk imported {imported_count} keywords")
                
        except sqlite3.Error as e:
            self.logger.error(f"Error during bulk import: {e}")
        
        return imported_count
    
    def save_post(self, platform: str, post_id: str, title: str, content: str, 
                  author: str, url: str, post_timestamp: datetime, score: int = 0) -> Optional[int]:
        """Save a post to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO posts 
                    (platform, post_id, title, content, author, url, score, post_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (platform, post_id, title, content, author, url, score, post_timestamp))
                
                post_db_id = cursor.lastrowid
                conn.commit()
                return post_db_id
                
        except sqlite3.Error as e:
            self.logger.error(f"Error saving post {post_id}: {e}")
            return None
    
    def save_scoring_history(self, post_db_id: int, keyword_matches: List[str], 
                           base_score: int, time_bonus: int, link_penalty: int, 
                           final_score: int) -> bool:
        """Save scoring history for a post."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO scoring_history 
                    (post_id, keyword_matches, base_score, time_bonus, link_penalty, final_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (post_db_id, json.dumps(keyword_matches), base_score, time_bonus, link_penalty, final_score))
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Error saving scoring history: {e}")
            return False
    
    def get_recent_posts(self, hours: int = 24, min_score: int = 0) -> List[Dict[str, Any]]:
        """Get recent posts above a minimum score."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                since_time = datetime.now() - timedelta(hours=hours)
                
                cursor.execute("""
                    SELECT * FROM posts 
                    WHERE processed_at > ? AND score >= ?
                    ORDER BY score DESC, post_timestamp DESC
                """, (since_time, min_score))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            self.logger.error(f"Error getting recent posts: {e}")
            return []
    
    def is_post_processed(self, platform: str, post_id: str) -> bool:
        """Check if a post has already been processed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM posts WHERE platform = ? AND post_id = ?
                """, (platform, post_id))
                return cursor.fetchone() is not None
                
        except sqlite3.Error as e:
            self.logger.error(f"Error checking if post is processed: {e}")
            return False
    
    def save_digest_history(self, digest_type: str, post_count: int, 
                          success: bool = True, error_message: Optional[str] = None) -> bool:
        """Save digest sending history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO digest_history (digest_type, post_count, success, error_message)
                    VALUES (?, ?, ?, ?)
                """, (digest_type, post_count, success, error_message))
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Error saving digest history: {e}")
            return False
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """Clean up old data to keep database size manageable."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # Delete old posts and related data
                cursor.execute("DELETE FROM scoring_history WHERE scored_at < ?", (cutoff_date,))
                cursor.execute("DELETE FROM posts WHERE processed_at < ?", (cutoff_date,))
                cursor.execute("DELETE FROM digest_history WHERE sent_at < ?", (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                # Vacuum to reclaim space
                cursor.execute("VACUUM")
                
                self.logger.info(f"Cleaned up {deleted_count} old records")
                return deleted_count
                
        except sqlite3.Error as e:
            self.logger.error(f"Error during cleanup: {e}")
            return 0


class KeywordManager:
    """High-level keyword management interface."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    def initialize_default_keywords(self):
        """Initialize database with default woodworking keywords."""
        default_keywords = {
            'high_value': [
                'table saw', 'router', 'jointer', 'planer', 'bandsaw', 
                'drill press', 'dust collection', 'workshop setup',
                'miter saw', 'circular saw', 'hand plane', 'chisel set'
            ],
            'medium_value': [
                'wood finish', 'sanding', 'glue up', 'mortise', 'tenon', 
                'dovetail', 'pocket hole', 'wood stain', 'polyurethane',
                'clamps', 'measuring tools', 'safety equipment'
            ],
            'low_value': [
                'wood species', 'lumber', 'hardwood', 'softwood', 'plywood',
                'project ideas', 'beginner tips', 'wood grain', 'cutting board'
            ]
        }
        
        imported_count = self.db.bulk_import_keywords(default_keywords)
        self.logger.info(f"Initialized {imported_count} default keywords")
        return imported_count
    
    def get_keyword_dict(self) -> Dict[str, List[str]]:
        """Get all keywords organized by category."""
        keywords = self.db.get_keywords()
        result = {}
        
        for keyword, category, score_value in keywords:
            if category not in result:
                result[category] = []
            result[category].append(keyword)
        
        return result
    
    def search_keywords(self, text: str) -> List[Tuple[str, str, int]]:
        """Search for keywords that match in the given text."""
        text_lower = text.lower()
        all_keywords = self.db.get_keywords()
        matches = []
        
        for keyword, category, score_value in all_keywords:
            if keyword in text_lower:
                matches.append((keyword, category, score_value))
        
        return matches


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

