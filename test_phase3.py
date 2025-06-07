#!/usr/bin/env python3
"""
Test script for Phase 3 watchers.

This script tests the watcher implementations without making actual API calls.
"""

import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from community_engine.config import ConfigLoader
from community_engine.watchers import (
    RedditWatcher, LumberJocksWatcher, SawmillCreekWatcher, 
    FacebookWatcher, WatcherManager
)
from community_engine.models import Post, Platform, WatcherResult
from community_engine.logging_config import setup_logging


def test_reddit_watcher():
    """Test Reddit watcher structure."""
    print("Testing Reddit watcher...")
    
    try:
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        # Mock PRAW to avoid actual API calls
        with patch('community_engine.watchers.praw.Reddit') as mock_reddit:
            mock_instance = Mock()
            mock_reddit.return_value = mock_instance
            mock_instance.user.me.return_value = None  # Simulate successful auth
            
            watcher = RedditWatcher(config)
            
            # Test initialization
            assert watcher.reddit is not None
            print("✓ Reddit watcher initialized successfully")
            
            # Test external link detection
            assert watcher._extract_external_links("Check out https://example.com") == True
            assert watcher._extract_external_links("Just some text") == False
            print("✓ External link detection works")
            
            return True
            
    except Exception as e:
        print(f"✗ Reddit watcher test failed: {e}")
        return False


def test_forum_watchers():
    """Test forum watchers structure."""
    print("\nTesting forum watchers...")
    
    try:
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        # Test LumberJocks watcher
        lj_watcher = LumberJocksWatcher(config)
        assert lj_watcher.forum_name == "lumberjocks"
        assert lj_watcher.forum_config is not None
        print("✓ LumberJocks watcher initialized")
        
        # Test SawmillCreek watcher
        sc_watcher = SawmillCreekWatcher(config)
        assert sc_watcher.forum_name == "sawmillcreek"
        assert sc_watcher.forum_config is not None
        print("✓ SawmillCreek watcher initialized")
        
        # Test external link detection
        assert lj_watcher._extract_external_links("Visit http://example.com for more") == True
        assert lj_watcher._extract_external_links("No links here") == False
        print("✓ Forum external link detection works")
        
        return True
        
    except Exception as e:
        print(f"✗ Forum watcher test failed: {e}")
        return False


def test_facebook_watcher():
    """Test Facebook watcher structure."""
    print("\nTesting Facebook watcher...")
    
    try:
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        watcher = FacebookWatcher(config)
        
        # Test external link detection
        assert watcher._extract_external_links("Check this out: https://facebook.com/post") == True
        assert watcher._extract_external_links("Just a regular post") == False
        print("✓ Facebook watcher initialized and link detection works")
        
        return True
        
    except Exception as e:
        print(f"✗ Facebook watcher test failed: {e}")
        return False


def test_watcher_manager():
    """Test watcher manager."""
    print("\nTesting watcher manager...")
    
    try:
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        # Mock Reddit to avoid API calls
        with patch('community_engine.watchers.praw.Reddit') as mock_reddit:
            mock_instance = Mock()
            mock_reddit.return_value = mock_instance
            mock_instance.user.me.side_effect = Exception("No API key")  # Simulate auth failure
            
            manager = WatcherManager(config)
            
            # Should initialize some watchers even without valid API keys
            print(f"✓ Watcher manager initialized with {len(manager.watchers)} watchers")
            
            # Test that it can handle missing API keys gracefully
            results = manager.watch_all()
            print(f"✓ Watch all completed, got {len(results)} results")
            
            return True
            
    except Exception as e:
        print(f"✗ Watcher manager test failed: {e}")
        return False


def test_post_conversion():
    """Test post conversion methods."""
    print("\nTesting post conversion...")
    
    try:
        # Test creating a post manually
        post = Post(
            platform=Platform.REDDIT,
            post_id="test123",
            title="Test Woodworking Post",
            content="This is a test post about table saw safety and router techniques.",
            author="test_user",
            url="https://reddit.com/r/woodworking/test123",
            timestamp=datetime.now(),
            has_external_links=False
        )
        
        assert post.platform == Platform.REDDIT
        assert post.is_recent == True  # Should be recent since we just created it
        assert len(post.preview_content) <= 250
        print("✓ Post creation and properties work")
        
        # Test serialization
        post_dict = post.to_dict()
        restored_post = Post.from_dict(post_dict)
        assert restored_post.title == post.title
        assert restored_post.platform == post.platform
        print("✓ Post serialization works")
        
        return True
        
    except Exception as e:
        print(f"✗ Post conversion test failed: {e}")
        return False


def test_watcher_result():
    """Test watcher result structure."""
    print("\nTesting watcher result...")
    
    try:
        result = WatcherResult(
            platform=Platform.REDDIT,
            posts_found=10,
            posts_processed=8,
            errors=["Test error"],
            execution_time=1.5
        )
        
        assert result.platform == Platform.REDDIT
        assert result.posts_found == 10
        assert result.posts_processed == 8
        assert result.success == False  # Should be False due to errors
        print("✓ WatcherResult creation and properties work")
        
        # Test successful result
        success_result = WatcherResult(
            platform=Platform.LUMBERJOCKS,
            posts_found=5,
            posts_processed=5,
            errors=[],
            execution_time=0.8
        )
        
        assert success_result.success == True
        print("✓ WatcherResult success detection works")
        
        return True
        
    except Exception as e:
        print(f"✗ Watcher result test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Phase 3 Watcher Testing ===\n")
    
    # Setup logging
    setup_logging(log_level="WARNING")  # Reduce noise during testing
    
    tests = [
        test_reddit_watcher,
        test_forum_watchers,
        test_facebook_watcher,
        test_watcher_manager,
        test_post_conversion,
        test_watcher_result
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All Phase 3 watcher components working correctly!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

