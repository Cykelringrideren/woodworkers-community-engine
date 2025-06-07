#!/usr/bin/env python3
"""
Test script for Phase 2 components.

This script tests the configuration loader, database manager,
and keyword management functionality.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from community_engine.config import ConfigLoader
from community_engine.database import DatabaseManager, KeywordManager
from community_engine.models import Post, Platform
from community_engine.logging_config import setup_logging
from datetime import datetime


def test_configuration():
    """Test configuration loading."""
    print("Testing configuration loading...")
    
    try:
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        print(f"✓ Configuration loaded successfully")
        print(f"  - Reddit subreddits: {len(config.reddit.subreddits)}")
        print(f"  - Forums configured: {len(config.forums)}")
        print(f"  - UTM base URL: {config.utm.base_url}")
        print(f"  - Max execution time: {config.performance.max_execution_time}s")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False


def test_database():
    """Test database operations."""
    print("\nTesting database operations...")
    
    try:
        # Use test database
        db = DatabaseManager("test_community_engine.db")
        
        # Test keyword operations
        keyword_manager = KeywordManager(db)
        
        # Initialize default keywords
        count = keyword_manager.initialize_default_keywords()
        print(f"✓ Initialized {count} default keywords")
        
        # Test adding custom keyword
        db.add_keyword("custom_tool", "test_category", 7)
        print("✓ Added custom keyword")
        
        # Test getting keywords
        keywords = db.get_keywords("high_value")
        print(f"✓ Retrieved {len(keywords)} high-value keywords")
        
        # Test post saving
        test_post_id = db.save_post(
            platform="reddit",
            post_id="test123",
            title="Test Post",
            content="This is a test post about table saw safety",
            author="test_user",
            url="https://reddit.com/test123",
            post_timestamp=datetime.now(),
            score=10
        )
        print(f"✓ Saved test post with ID: {test_post_id}")
        
        # Test keyword searching
        matches = keyword_manager.search_keywords("I need help with my table saw setup")
        print(f"✓ Found {len(matches)} keyword matches")
        
        # Clean up test database
        os.remove("test_community_engine.db")
        print("✓ Test database cleaned up")
        
        return True
        
    except Exception as e:
        print(f"✗ Database testing failed: {e}")
        return False


def test_models():
    """Test data models."""
    print("\nTesting data models...")
    
    try:
        # Test Post model
        post = Post(
            platform=Platform.REDDIT,
            post_id="test123",
            title="Test Post",
            content="This is a test post about woodworking",
            author="test_user",
            url="https://reddit.com/test123",
            timestamp=datetime.now()
        )
        
        print(f"✓ Created post: {post.title}")
        print(f"  - Platform: {post.platform.value}")
        print(f"  - Age: {post.age_minutes} minutes")
        print(f"  - Is recent: {post.is_recent}")
        print(f"  - Preview: {post.preview_content[:50]}...")
        
        # Test serialization
        post_dict = post.to_dict()
        post_restored = Post.from_dict(post_dict)
        print("✓ Post serialization/deserialization works")
        
        return True
        
    except Exception as e:
        print(f"✗ Model testing failed: {e}")
        return False


def test_logging():
    """Test logging configuration."""
    print("\nTesting logging configuration...")
    
    try:
        # Setup logging
        setup_logging(log_level="INFO")
        
        import logging
        logger = logging.getLogger("test")
        
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.debug("Test debug message (should not appear)")
        
        print("✓ Logging configuration works")
        return True
        
    except Exception as e:
        print(f"✗ Logging testing failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Phase 2 Component Testing ===\n")
    
    tests = [
        test_configuration,
        test_database,
        test_models,
        test_logging
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All Phase 2 components working correctly!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

