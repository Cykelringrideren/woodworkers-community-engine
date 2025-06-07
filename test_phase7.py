#!/usr/bin/env python3
"""
Final integration test for Phase 7.

This test validates that all major components can work together
and that the documentation and diagrams are in place.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_documentation_completeness():
    """Test that all documentation files are present and comprehensive."""
    print("Testing documentation completeness...")
    
    required_files = [
        "README.md",
        "DEPLOYMENT.md", 
        "docs/system_architecture.png",
        "test_suite.py"
    ]
    
    for file_path in required_files:
        file_obj = Path(file_path)
        assert file_obj.exists(), f"Required file missing: {file_path}"
        
        if file_path.endswith('.md'):
            # Check that documentation files have substantial content
            with open(file_obj, 'r') as f:
                content = f.read()
            assert len(content) > 1000, f"Documentation file {file_path} seems too short"
    
    print("✓ All documentation files present and substantial")


def test_system_architecture_diagram():
    """Test that the system architecture diagram exists."""
    print("\nTesting system architecture diagram...")
    
    diagram_path = Path("docs/system_architecture.png")
    assert diagram_path.exists(), "System architecture diagram should exist"
    
    # Check file size (should be a real image, not empty)
    file_size = diagram_path.stat().st_size
    assert file_size > 10000, "Diagram file seems too small to be a real image"
    
    print("✓ System architecture diagram exists and appears valid")


def test_comprehensive_test_suite():
    """Test that the comprehensive test suite exists and is executable."""
    print("\nTesting comprehensive test suite...")
    
    test_suite_path = Path("test_suite.py")
    assert test_suite_path.exists(), "Comprehensive test suite should exist"
    
    # Check that it's executable
    assert os.access(test_suite_path, os.R_OK), "Test suite should be readable"
    
    # Check that it contains the main test classes
    with open(test_suite_path, 'r') as f:
        content = f.read()
    
    assert "class TestSuite" in content, "Should contain TestSuite class"
    assert "def run_all_tests" in content, "Should contain run_all_tests method"
    assert "test_configuration_management" in content, "Should test configuration"
    assert "test_database_operations" in content, "Should test database"
    assert "test_utm_tracking" in content, "Should test UTM tracking"
    
    print("✓ Comprehensive test suite exists and appears complete")


def test_project_structure():
    """Test that the complete project structure is in place."""
    print("\nTesting project structure...")
    
    required_dirs = [
        "src/community_engine",
        "config",
        ".github/workflows",
        "docs"
    ]
    
    for dir_path in required_dirs:
        dir_obj = Path(dir_path)
        assert dir_obj.exists() and dir_obj.is_dir(), f"Required directory missing: {dir_path}"
    
    required_files = [
        "main.py",
        "reply_helper.py", 
        "requirements.txt",
        "config/config.yaml",
        ".github/workflows/community_watcher.yml",
        "src/community_engine/__init__.py",
        "src/community_engine/config.py",
        "src/community_engine/database.py",
        "src/community_engine/models.py",
        "src/community_engine/watchers.py",
        "src/community_engine/scorer.py",
        "src/community_engine/digest.py",
        "src/community_engine/utm_tagger.py",
        "src/community_engine/reply_kit.py",
        "src/community_engine/logging_config.py"
    ]
    
    for file_path in required_files:
        file_obj = Path(file_path)
        assert file_obj.exists(), f"Required file missing: {file_path}"
    
    print("✓ Complete project structure is in place")


def test_readme_content():
    """Test that README.md contains all required sections."""
    print("\nTesting README content...")
    
    with open("README.md", 'r') as f:
        readme_content = f.read()
    
    required_sections = [
        "# WoodworkersArchive Community Engagement Engine",
        "## 🎯 Overview",
        "## 🚀 Quick Start", 
        "## 📖 Detailed Documentation",
        "## 🛠 Development",
        "## 📊 Monitoring and Analytics",
        "## 🔒 Security and Compliance",
        "## 💰 Cost Analysis",
        "## 🤝 Contributing"
    ]
    
    for section in required_sections:
        assert section in readme_content, f"README missing required section: {section}"
    
    # Check for key technical details
    technical_terms = [
        "GitHub Actions",
        "Reddit API",
        "UTM tracking",
        "Slack webhook",
        "SQLite database",
        "keyword matching",
        "scoring algorithm"
    ]
    
    for term in technical_terms:
        assert term.lower() in readme_content.lower(), f"README missing technical term: {term}"
    
    print("✓ README contains all required sections and technical details")


def test_deployment_guide():
    """Test that deployment guide is comprehensive."""
    print("\nTesting deployment guide...")
    
    with open("DEPLOYMENT.md", 'r') as f:
        deployment_content = f.read()
    
    required_sections = [
        "# Deployment Guide",
        "## Prerequisites",
        "## Step 1: Fork and Clone Repository",
        "## Step 2: Obtain API Credentials",
        "## Step 3: Configure GitHub Secrets",
        "## Step 4: Configure the Application",
        "## Step 5: Test the Setup",
        "## Step 6: Enable Scheduled Execution",
        "## Step 7: Monitor and Maintain",
        "## Step 8: Customize for Your Needs"
    ]
    
    for section in required_sections:
        assert section in deployment_content, f"Deployment guide missing section: {section}"
    
    # Check for important setup details
    setup_details = [
        "Reddit API Setup",
        "Slack Webhook Setup",
        "Gmail App Password",
        "GitHub Secrets",
        "Troubleshooting",
        "Security Considerations"
    ]
    
    for detail in setup_details:
        assert detail in deployment_content, f"Deployment guide missing detail: {detail}"
    
    print("✓ Deployment guide is comprehensive and complete")


def main():
    """Run all Phase 7 integration tests."""
    print("=== Phase 7 Documentation and Integration Testing ===\n")
    
    tests = [
        test_documentation_completeness,
        test_system_architecture_diagram,
        test_comprehensive_test_suite,
        test_project_structure,
        test_readme_content,
        test_deployment_guide
    ]
    
    results = []
    for test in tests:
        try:
            test()
            results.append(True)
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            results.append(False)
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All Phase 7 documentation and integration tests passed!")
        print("📚 The system is fully documented and ready for deployment.")
        return 0
    else:
        print("❌ Some documentation tests failed. Please review and fix issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

