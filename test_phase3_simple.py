#!/usr/bin/env python3
"""
Simple test script for Phase 3 watchers (no network calls).

This script tests the watcher implementations without making actual network calls.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from community_engine.config import ConfigLoader
from community_engine.models import Post, Platform, WatcherResult
from community_engine.logging_config import setup_logging


def test_basic_functionality():
    """Test basic watcher functionality without network calls."""
    print("Testing basic watcher functionality...")
    
    try:
        # Test configuration loading
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        print("✓ Configuration loaded successfully")
        
        # Test Post model
        post = Post(
            platform=Platform.REDDIT,
            post_id="test123",
            title="Test Woodworking Post",
            content="This is a test post about table saw safety.",
            author="test_user",
            url="https://reddit.com/r/woodworking/test123",
            timestamp=datetime.now(),
            has_external_links=False
        )
        
        assert post.platform == Platform.REDDIT
        assert post.is_recent == True
        print("✓ Post model works correctly")
        
        # Test WatcherResult
        result = WatcherResult(
            platform=Platform.REDDIT,
            posts_found=5,
            posts_processed=5,
            errors=[],
            execution_time=1.0
        )
        
        assert result.success == True
        print("✓ WatcherResult model works correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False


def test_import_structure():
    """Test that all watcher modules can be imported."""
    print("\nTesting import structure...")
    
    try:
        from community_engine.watchers import (
            BaseWatcher, RedditWatcher, LumberJocksWatcher, 
            SawmillCreekWatcher, FacebookWatcher, WatcherManager
        )
        print("✓ All watcher classes imported successfully")
        
        # Test that classes have required methods
        assert hasattr(BaseWatcher, 'watch')
        assert hasattr(RedditWatcher, 'watch')
        assert hasattr(LumberJocksWatcher, 'watch')
        assert hasattr(SawmillCreekWatcher, 'watch')
        assert hasattr(FacebookWatcher, 'watch')
        assert hasattr(WatcherManager, 'watch_all')
        print("✓ All required methods present")
        
        return True
        
    except Exception as e:
        print(f"✗ Import structure test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Phase 3 Watcher Testing (No Network) ===\n")
    
    # Setup logging
    setup_logging(log_level="ERROR")  # Minimize output
    
    # Import datetime here to avoid issues
    from datetime import datetime
    globals()['datetime'] = datetime
    
    tests = [
        test_import_structure,
        test_basic_functionality
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All Phase 3 watcher components structure is correct!")
        print("Note: Network functionality will be tested in integration tests.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

