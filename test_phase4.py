#!/usr/bin/env python3
"""
Test script for Phase 4 components.

This script tests the scoring engine, digest generator, and notification system.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from community_engine.config import ConfigLoader
from community_engine.database import DatabaseManager, KeywordManager
from community_engine.models import Post, Platform
from community_engine.scorer import ScoringEngine, KeywordMatcher, PostScorer
from community_engine.digest import DigestGenerator, NotificationManager
from community_engine.logging_config import setup_logging


def test_keyword_matching():
    """Test keyword matching functionality."""
    print("Testing keyword matching...")
    
    try:
        # Setup
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        db = DatabaseManager("test_scoring.db")
        keyword_manager = KeywordManager(db)
        
        # Initialize keywords
        keyword_manager.initialize_default_keywords()
        
        # Test keyword matching
        matcher = KeywordMatcher(keyword_manager, config)
        
        # Test text with keywords
        test_text = "I need help with my table saw setup and router table configuration"
        matches = matcher.find_matches(test_text)
        
        assert len(matches) > 0, "Should find keyword matches"
        print(f"✓ Found {len(matches)} keyword matches")
        
        # Test keyword score calculation
        score = matcher.calculate_keyword_score(matches)
        assert score > 0, "Should calculate positive score"
        print(f"✓ Calculated keyword score: {score}")
        
        # Cleanup
        os.remove("test_scoring.db")
        
        return True
        
    except Exception as e:
        print(f"✗ Keyword matching test failed: {e}")
        return False


def test_post_scoring():
    """Test post scoring functionality."""
    print("\nTesting post scoring...")
    
    try:
        # Setup
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        db = DatabaseManager("test_scoring.db")
        keyword_manager = KeywordManager(db)
        keyword_manager.initialize_default_keywords()
        
        # Create scoring engine
        scoring_engine = ScoringEngine(config, db)
        
        # Create test posts
        posts = [
            Post(
                platform=Platform.REDDIT,
                post_id="test1",
                title="Table saw safety tips for beginners",
                content="I'm looking for advice on table saw safety and proper techniques.",
                author="beginner_woodworker",
                url="https://reddit.com/test1",
                timestamp=datetime.now(),  # Recent post
                has_external_links=False
            ),
            Post(
                platform=Platform.REDDIT,
                post_id="test2",
                title="General woodworking question",
                content="Just a general question about wood types.",
                author="woodworker",
                url="https://reddit.com/test2",
                timestamp=datetime.now(),
                has_external_links=True  # Has external links
            )
        ]
        
        # Score posts
        results = scoring_engine.process_posts(posts)
        
        assert len(results) > 0, "Should return scoring results"
        assert results[0].final_score > results[1].final_score, "First post should score higher"
        print(f"✓ Scored {len(results)} posts")
        print(f"  - Post 1 score: {results[0].final_score}")
        print(f"  - Post 2 score: {results[1].final_score}")
        
        # Cleanup
        os.remove("test_scoring.db")
        
        return True
        
    except Exception as e:
        print(f"✗ Post scoring test failed: {e}")
        return False


def test_digest_generation():
    """Test digest generation."""
    print("\nTesting digest generation...")
    
    try:
        # Setup
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        generator = DigestGenerator(config)
        
        # Create test scoring results
        test_post = Post(
            platform=Platform.REDDIT,
            post_id="test123",
            title="Best router for beginners?",
            content="I'm looking to buy my first router. Any recommendations?",
            author="newbie_woodworker",
            url="https://reddit.com/r/woodworking/test123",
            timestamp=datetime.now(),
            score=15
        )
        
        from community_engine.models import ScoringResult
        scoring_results = [
            ScoringResult(
                post=test_post,
                keyword_score=10,
                time_bonus=2,
                link_penalty=0,
                final_score=12,
                matched_keywords=["router"]
            )
        ]
        
        # Generate digest
        digest = generator.create_digest(scoring_results, 2.5, 100)
        
        assert len(digest.entries) == 1, "Should have one digest entry"
        assert digest.total_posts_processed == 100, "Should track total posts"
        print("✓ Generated digest successfully")
        
        # Test Markdown conversion
        markdown = digest.to_markdown()
        assert "router" in markdown.lower(), "Should contain keyword in markdown"
        assert "Score: 12" in markdown, "Should contain score in markdown"
        print("✓ Markdown conversion works")
        
        return True
        
    except Exception as e:
        print(f"✗ Digest generation test failed: {e}")
        return False


def test_notification_structure():
    """Test notification system structure."""
    print("\nTesting notification structure...")
    
    try:
        # Setup
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        db = DatabaseManager("test_notifications.db")
        
        # Test notification manager initialization
        notification_manager = NotificationManager(config, db)
        
        assert notification_manager.slack_notifier is not None, "Should initialize Slack notifier"
        assert notification_manager.email_notifier is not None, "Should initialize email notifier"
        print("✓ Notification manager initialized")
        
        # Test that it handles missing configuration gracefully
        # (Won't actually send since we don't have real credentials)
        from community_engine.digest import DigestGenerator
        generator = DigestGenerator(config)
        
        # Create empty digest
        empty_digest = generator.create_digest([], 1.0, 0)
        
        # This should not crash even with missing credentials
        results = notification_manager.send_digest(empty_digest)
        print("✓ Handles missing credentials gracefully")
        
        # Cleanup
        os.remove("test_notifications.db")
        
        return True
        
    except Exception as e:
        print(f"✗ Notification structure test failed: {e}")
        return False


def test_post_filtering():
    """Test post filtering functionality."""
    print("\nTesting post filtering...")
    
    try:
        # Setup
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        db = DatabaseManager("test_filtering.db")
        
        from community_engine.scorer import PostFilter
        filter_engine = PostFilter(config, db)
        
        # Create test posts with duplicates
        posts = [
            Post(
                platform=Platform.REDDIT,
                post_id="test1",
                title="Test post 1",
                content="Content 1",
                author="user1",
                url="https://reddit.com/test1",
                timestamp=datetime.now()
            ),
            Post(
                platform=Platform.REDDIT,
                post_id="test1",  # Duplicate
                title="Test post 1",
                content="Content 1",
                author="user1",
                url="https://reddit.com/test1",
                timestamp=datetime.now()
            ),
            Post(
                platform=Platform.LUMBERJOCKS,
                post_id="test2",
                title="Test post 2",
                content="Content 2",
                author="user2",
                url="https://lumberjocks.com/test2",
                timestamp=datetime.now()
            )
        ]
        
        # Test duplicate filtering
        filtered = filter_engine.filter_duplicates(posts)
        assert len(filtered) == 2, "Should remove duplicates"
        print("✓ Duplicate filtering works")
        
        # Test age filtering
        from datetime import timedelta
        old_post = Post(
            platform=Platform.REDDIT,
            post_id="old_post",
            title="Old post",
            content="Old content",
            author="old_user",
            url="https://reddit.com/old",
            timestamp=datetime.now() - timedelta(hours=25)  # Older than 24 hours
        )
        
        posts_with_old = filtered + [old_post]
        age_filtered = filter_engine.filter_by_age(posts_with_old, max_age_hours=24)
        assert len(age_filtered) == 2, "Should filter old posts"
        print("✓ Age filtering works")
        
        # Cleanup
        os.remove("test_filtering.db")
        
        return True
        
    except Exception as e:
        print(f"✗ Post filtering test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Phase 4 Scoring and Digest Testing ===\n")
    
    # Setup logging
    setup_logging(log_level="WARNING")  # Reduce noise during testing
    
    tests = [
        test_keyword_matching,
        test_post_scoring,
        test_digest_generation,
        test_notification_structure,
        test_post_filtering
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All Phase 4 scoring and digest components working correctly!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

