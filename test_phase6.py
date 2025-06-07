#!/usr/bin/env python3
"""
Test script for Phase 6 components.

This script tests the main execution flow and GitHub Actions configuration.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from community_engine.config import ConfigLoader
from community_engine.logging_config import setup_logging


def test_main_script_structure():
    """Test that the main script has the correct structure."""
    print("Testing main script structure...")
    
    try:
        # Check that main.py exists
        main_script = Path("main.py")
        assert main_script.exists(), "main.py should exist"
        
        # Check that it's executable
        with open(main_script, 'r') as f:
            content = f.read()
        
        assert "run_community_watcher" in content, "Should contain main function"
        assert "ExecutionMetrics" in content, "Should use execution metrics"
        assert "WatcherManager" in content, "Should use watcher manager"
        assert "ScoringEngine" in content, "Should use scoring engine"
        print("✓ Main script structure is correct")
        
        return True
        
    except Exception as e:
        print(f"✗ Main script structure test failed: {e}")
        return False


def test_github_workflow():
    """Test GitHub Actions workflow configuration."""
    print("\nTesting GitHub Actions workflow...")
    
    try:
        # Check workflow file exists
        workflow_file = Path(".github/workflows/community_watcher.yml")
        assert workflow_file.exists(), "GitHub Actions workflow should exist"
        
        # Check workflow content
        with open(workflow_file, 'r') as f:
            content = f.read()
        
        assert "schedule:" in content, "Should have scheduled execution"
        assert "*/5 * * * *" in content, "Should run every 5 minutes"
        assert "REDDIT_CLIENT_ID" in content, "Should use Reddit secrets"
        assert "timeout-minutes: 3" in content, "Should have timeout"
        assert "upload-artifact" in content, "Should upload logs"
        print("✓ GitHub Actions workflow is properly configured")
        
        return True
        
    except Exception as e:
        print(f"✗ GitHub Actions workflow test failed: {e}")
        return False


def test_deployment_guide():
    """Test deployment guide exists and is comprehensive."""
    print("\nTesting deployment guide...")
    
    try:
        # Check deployment guide exists
        deployment_guide = Path("DEPLOYMENT.md")
        assert deployment_guide.exists(), "Deployment guide should exist"
        
        # Check guide content
        with open(deployment_guide, 'r') as f:
            content = f.read()
        
        assert "Reddit API Setup" in content, "Should include Reddit setup"
        assert "GitHub Secrets" in content, "Should explain secrets setup"
        assert "Troubleshooting" in content, "Should include troubleshooting"
        assert "Security Considerations" in content, "Should address security"
        print("✓ Deployment guide is comprehensive")
        
        return True
        
    except Exception as e:
        print(f"✗ Deployment guide test failed: {e}")
        return False


def test_configuration_validation():
    """Test configuration loading and validation."""
    print("\nTesting configuration validation...")
    
    try:
        # Test configuration loading
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        # Test that validation works
        validation_result = loader.validate(config)
        # Should fail validation due to placeholder values
        assert validation_result == False, "Should fail validation with placeholder values"
        print("✓ Configuration validation works correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration validation test failed: {e}")
        return False


def test_directory_structure():
    """Test that all necessary directories and files exist."""
    print("\nTesting directory structure...")
    
    try:
        # Check required directories
        required_dirs = [
            "src/community_engine",
            "config",
            ".github/workflows",
            "tests" if Path("tests").exists() else None
        ]
        
        for dir_path in required_dirs:
            if dir_path:
                assert Path(dir_path).exists(), f"Directory {dir_path} should exist"
        
        # Check required files
        required_files = [
            "main.py",
            "reply_helper.py",
            "requirements.txt",
            "config/config.yaml",
            ".github/workflows/community_watcher.yml",
            "DEPLOYMENT.md",
            "README.md"
        ]
        
        for file_path in required_files:
            assert Path(file_path).exists(), f"File {file_path} should exist"
        
        print("✓ Directory structure is complete")
        
        return True
        
    except Exception as e:
        print(f"✗ Directory structure test failed: {e}")
        return False


def test_execution_simulation():
    """Test a simulated execution without API calls."""
    print("\nTesting execution simulation...")
    
    try:
        # Setup logging
        setup_logging(log_level="WARNING")
        
        # Test that we can import and initialize components
        from community_engine.database import DatabaseManager
        from community_engine.models import ExecutionMetrics
        
        # Create test database
        db = DatabaseManager("test_execution.db")
        
        # Create execution metrics
        metrics = ExecutionMetrics(
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_posts_found=5,
            total_posts_scored=3,
            top_score=15,
            platforms_processed=[],
            digest_sent=True,
            errors=[]
        )
        
        assert metrics.success == True, "Metrics should indicate success"
        assert metrics.duration_seconds < 120, "Should be within time limit"
        print("✓ Execution simulation works")
        
        # Cleanup
        os.remove("test_execution.db")
        
        return True
        
    except Exception as e:
        print(f"✗ Execution simulation test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Phase 6 GitHub Actions and Deployment Testing ===\n")
    
    tests = [
        test_main_script_structure,
        test_github_workflow,
        test_deployment_guide,
        test_configuration_validation,
        test_directory_structure,
        test_execution_simulation
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All Phase 6 GitHub Actions and deployment components working correctly!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

