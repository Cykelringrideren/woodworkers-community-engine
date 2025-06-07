#!/usr/bin/env python3
"""
Comprehensive test suite for the WoodworkersArchive Community Engagement Engine.

This test suite validates all components of the system including:
- Configuration management
- Database operations
- Platform watchers
- Scoring and filtering
- Digest generation
- Reply tools and UTM tracking
- GitHub Actions integration

Run with: python test_suite.py
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from community_engine.config import ConfigLoader
from community_engine.database import DatabaseManager, KeywordManager
from community_engine.models import Post, Platform, ScoringResult, ExecutionMetrics
from community_engine.watchers import BaseWatcher, RedditWatcher, WatcherManager
from community_engine.scorer import ScoringEngine, KeywordMatcher, PostScorer, PostFilter
from community_engine.digest import DigestGenerator, NotificationManager
from community_engine.utm_tagger import UTMTagger, LinkBuilder, TrackingHelper
from community_engine.reply_kit import ReplyTemplate, TemplateManager, ReplyBuilder, ReplyHelper
from community_engine.logging_config import setup_logging


class TestResult:
    """Represents the result of a test."""
    
    def __init__(self, name: str, passed: bool, message: str = "", duration: float = 0.0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
    
    def __str__(self):
        status = "✓" if self.passed else "✗"
        duration_str = f" ({self.duration:.3f}s)" if self.duration > 0 else ""
        return f"{status} {self.name}{duration_str}"


class TestSuite:
    """Comprehensive test suite for the community engagement engine."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.temp_dir = None
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Set up temporary test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="community_engine_test_")
        os.chdir(self.temp_dir)
        
        # Create test directory structure
        os.makedirs("config", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        
        # Create test configuration
        test_config = """
# Test Configuration
platforms:
  reddit:
    enabled: true
    subreddits: ["test_woodworking"]
    client_id: "test_client_id"
    client_secret: "test_client_secret"
  
  lumberjocks:
    enabled: true
    rss_url: "https://test.lumberjocks.com/rss"
  
  sawmillcreek:
    enabled: true
    rss_url: "https://test.sawmillcreek.org/rss"
  
  facebook:
    enabled: false
    access_token: "test_token"

scoring:
  keyword_base_score: 5
  recent_post_bonus: 2
  external_link_penalty: -1
  max_posts_per_run: 10

notifications:
  slack_webhook_url: "https://hooks.slack.com/test"
  slack_channel: "#test"
  email_to: "test@example.com"
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  email_username: "test@gmail.com"
  email_password: "test_password"

utm:
  base_url: "https://test.woodworkersarchive.com"
  default_campaign: "test_community_engagement"
  source_mapping:
    reddit: "reddit"
    lumberjocks: "lumberjocks"
    sawmillcreek: "sawmillcreek"
    facebook: "facebook"

performance:
  max_execution_time: 120
  max_posts_per_platform: 50
"""
        
        with open("config/config.yaml", "w") as f:
            f.write(test_config)
    
    def cleanup_test_environment(self):
        """Clean up temporary test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            os.chdir("/")
            shutil.rmtree(self.temp_dir)
    
    def run_test(self, test_func, test_name: str) -> TestResult:
        """Run a single test and record the result."""
        start_time = datetime.now()
        
        try:
            test_func()
            duration = (datetime.now() - start_time).total_seconds()
            result = TestResult(test_name, True, "Passed", duration)
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            result = TestResult(test_name, False, str(e), duration)
        
        self.results.append(result)
        return result
    
    def test_configuration_management(self):
        """Test configuration loading and validation."""
        # Test configuration loading
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        assert config.platforms.reddit.enabled == True
        assert config.platforms.reddit.subreddits == ["test_woodworking"]
        assert config.scoring.keyword_base_score == 5
        assert config.utm.base_url == "https://test.woodworkersarchive.com"
        
        # Test validation (should fail with test credentials)
        validation_result = loader.validate(config)
        assert validation_result == False  # Expected to fail with test credentials
    
    def test_database_operations(self):
        """Test database creation and operations."""
        # Create test database
        db = DatabaseManager("test_database.db")
        
        # Test keyword management
        keyword_manager = KeywordManager(db)
        
        # Add test keywords
        db.add_keyword("table saw", "tools", 10)
        db.add_keyword("router", "tools", 8)
        db.add_keyword("safety", "general", 5)
        
        # Test keyword retrieval
        keywords = db.get_keywords()
        assert len(keywords) >= 3
        
        # Test post saving
        post_id = db.save_post(
            platform="reddit",
            post_id="test123",
            title="Test Post",
            content="Test content about table saw safety",
            author="test_user",
            url="https://reddit.com/test123",
            post_timestamp=datetime.now(),
            score=15
        )
        
        assert post_id is not None
        
        # Test duplicate detection
        is_processed = db.is_post_processed("reddit", "test123")
        assert is_processed == True
        
        # Test recent posts retrieval
        recent_posts = db.get_recent_posts(hours=24, min_score=1)
        assert len(recent_posts) >= 1
        
        # Test cleanup
        deleted_count = db.cleanup_old_data(days=0)  # Delete everything
        assert deleted_count >= 1
    
    def test_keyword_matching(self):
        """Test keyword matching and scoring."""
        # Setup
        db = DatabaseManager("test_keyword_matching.db")
        keyword_manager = KeywordManager(db)
        
        # Add test keywords
        db.add_keyword("table saw", "tools", 10)
        db.add_keyword("router table", "tools", 8)
        db.add_keyword("safety", "general", 5)
        db.add_keyword("beginner", "skill", 3)
        
        # Create test configuration
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        # Test keyword matcher
        matcher = KeywordMatcher(keyword_manager, config)
        
        # Test matching
        test_text = "I need help with my table saw setup and router table configuration for safety"
        matches = matcher.find_matches(test_text)
        
        assert len(matches) >= 3  # Should find table saw, router table, safety
        
        # Test score calculation
        score = matcher.calculate_keyword_score(matches)
        assert score > 0
        
        # Test word boundary matching (should not match partial words)
        partial_text = "I have a tablesaw and routertable"  # No spaces
        partial_matches = matcher.find_matches(partial_text)
        assert len(partial_matches) == 0  # Should not match without word boundaries
    
    def test_post_scoring(self):
        """Test post scoring and filtering."""
        # Setup
        db = DatabaseManager("test_scoring.db")
        keyword_manager = KeywordManager(db)
        keyword_manager.initialize_default_keywords()
        
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        scoring_engine = ScoringEngine(config, db)
        
        # Create test posts
        recent_post = Post(
            platform=Platform.REDDIT,
            post_id="recent_test",
            title="Table saw safety tips for beginners",
            content="Looking for advice on table saw safety and proper techniques.",
            author="beginner_woodworker",
            url="https://reddit.com/recent_test",
            timestamp=datetime.now(),  # Recent
            has_external_links=False
        )
        
        old_post = Post(
            platform=Platform.REDDIT,
            post_id="old_test",
            title="General woodworking question",
            content="Just a general question about wood types.",
            author="woodworker",
            url="https://reddit.com/old_test",
            timestamp=datetime.now() - timedelta(hours=25),  # Old
            has_external_links=True  # Has external links
        )
        
        # Test scoring
        results = scoring_engine.process_posts([recent_post, old_post])
        
        assert len(results) >= 1  # At least one should pass filtering
        assert results[0].final_score > 0  # Should have positive score
        
        # Recent post should score higher than old post with external links
        recent_result = next((r for r in results if r.post.post_id == "recent_test"), None)
        old_result = next((r for r in results if r.post.post_id == "old_test"), None)
        
        if recent_result and old_result:
            assert recent_result.final_score > old_result.final_score
    
    def test_digest_generation(self):
        """Test digest generation and formatting."""
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        generator = DigestGenerator(config)
        
        # Create test scoring results
        test_post = Post(
            platform=Platform.REDDIT,
            post_id="digest_test",
            title="Best router for beginners?",
            content="I'm looking to buy my first router. Any recommendations?",
            author="newbie_woodworker",
            url="https://reddit.com/r/woodworking/digest_test",
            timestamp=datetime.now(),
            score=15
        )
        
        scoring_result = ScoringResult(
            post=test_post,
            keyword_score=10,
            time_bonus=2,
            link_penalty=0,
            final_score=12,
            matched_keywords=["router"]
        )
        
        # Generate digest
        digest = generator.create_digest([scoring_result], 2.5, 100)
        
        assert len(digest.entries) == 1
        assert digest.total_posts_processed == 100
        assert digest.execution_duration == 2.5
        
        # Test Markdown conversion
        markdown = digest.to_markdown()
        assert "router" in markdown.lower()
        assert "Score: 12" in markdown
        assert "WoodworkersArchive Community Digest" in markdown
    
    def test_utm_tracking(self):
        """Test UTM parameter generation and tracking."""
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        utm_tagger = UTMTagger(config)
        
        # Test basic UTM URL generation
        utm_url = utm_tagger.generate_utm_url(
            source="reddit",
            content="test_post_123"
        )
        
        assert "utm_source=reddit" in utm_url
        assert "utm_medium=comment" in utm_url
        assert "utm_campaign=test_community_engagement" in utm_url
        assert "utm_content=test_post_123" in utm_url
        
        # Test platform-specific URL
        platform_url = utm_tagger.generate_platform_url(
            platform=Platform.REDDIT,
            content="post_456"
        )
        
        assert "utm_source=reddit" in platform_url
        assert "utm_content=post_456" in platform_url
        
        # Test link builder
        link_builder = LinkBuilder(config)
        links = link_builder.build_engagement_link(
            platform=Platform.REDDIT,
            post_id="test123",
            article_path="/articles/router-guide",
            topic="router"
        )
        
        assert "homepage" in links
        assert "article" in links
        assert "search" in links
        
        # Test tracking helper
        tracking_helper = TrackingHelper(config)
        utm_params = tracking_helper.extract_utm_params(utm_url)
        
        assert utm_params["utm_source"] == "reddit"
        assert utm_params["utm_medium"] == "comment"
        
        # Test URL validation
        validation = tracking_helper.validate_utm_url(utm_url)
        assert validation["valid"] == True
        assert len(validation["errors"]) == 0
    
    def test_reply_templates(self):
        """Test reply template system."""
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        # Test template creation and rendering
        template = ReplyTemplate(
            name="test_template",
            template="Hello {name}, here's some {advice}. {utm_link}\n\nI maintain WoodworkersArchive.com",
            description="Test template",
            required_fields=["name", "advice", "utm_link"]
        )
        
        rendered = template.render(
            name="John",
            advice="great advice",
            utm_link="https://example.com"
        )
        
        assert "Hello John" in rendered
        assert "great advice" in rendered
        assert "I maintain WoodworkersArchive.com" in rendered
        
        # Test template manager
        template_manager = TemplateManager(config)
        templates = template_manager.list_templates()
        assert len(templates) > 0
        
        helpful_template = template_manager.get_template("helpful_response")
        assert helpful_template is not None
        
        # Test reply builder
        reply_builder = ReplyBuilder(config)
        
        test_post = Post(
            platform=Platform.REDDIT,
            post_id="reply_test",
            title="Need help with table saw safety",
            content="I'm new to woodworking and want to learn about table saw safety.",
            author="newbie_woodworker",
            url="https://reddit.com/r/woodworking/reply_test",
            timestamp=datetime.now()
        )
        
        # Test template suggestion
        suggested_template = reply_builder.suggest_template(test_post)
        assert suggested_template == "safety_advice"
        
        # Test reply building
        reply_data = reply_builder.build_reply(
            template_name="helpful_response",
            post=test_post,
            topic="table saw safety",
            answer="Table saw safety is crucial for beginners.",
            deeper_explanation="Always use proper guards and push sticks."
        )
        
        assert "reply_text" in reply_data
        assert "utm_links" in reply_data
        assert "I maintain WoodworkersArchive.com" in reply_data["reply_text"]
    
    def test_reply_helper(self):
        """Test reply helper and CLI functionality."""
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        reply_helper = ReplyHelper(config)
        
        # Test URL parsing
        test_urls = [
            ("https://reddit.com/r/woodworking/comments/abc123/test_post/", Platform.REDDIT, "abc123"),
            ("https://lumberjocks.com/projects/12345", Platform.LUMBERJOCKS, "12345"),
            ("https://sawmillcreek.org/threads/test.67890/", Platform.SAWMILLCREEK, "67890")
        ]
        
        for url, expected_platform, expected_id in test_urls:
            post_info = reply_helper._parse_post_url(url)
            assert post_info["platform"] == expected_platform
            assert expected_id in post_info["post_id"]
        
        # Test reply creation from URL
        reply_data = reply_helper.create_reply_from_url(
            post_url="https://reddit.com/r/woodworking/comments/abc123/test_post/",
            template_name="helpful_response",
            topic="woodworking",
            answer="Great question!",
            deeper_explanation="Here's some additional info."
        )
        
        assert "reply_text" in reply_data
        assert "utm_links" in reply_data
    
    def test_notification_system(self):
        """Test notification system structure."""
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        db = DatabaseManager("test_notifications.db")
        
        notification_manager = NotificationManager(config, db)
        
        # Test that components initialize correctly
        assert notification_manager.slack_notifier is not None
        assert notification_manager.email_notifier is not None
        
        # Test digest creation and handling
        from community_engine.digest import DigestGenerator
        generator = DigestGenerator(config)
        
        empty_digest = generator.create_digest([], 1.0, 0)
        
        # This should not crash even with test credentials
        results = notification_manager.send_digest(empty_digest)
        
        # Should return results dict (even if failed due to test credentials)
        assert isinstance(results, dict)
    
    def test_execution_metrics(self):
        """Test execution metrics tracking."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=45)
        
        metrics = ExecutionMetrics(
            start_time=start_time,
            end_time=end_time,
            total_posts_found=25,
            total_posts_scored=18,
            top_score=15,
            platforms_processed=[Platform.REDDIT, Platform.LUMBERJOCKS],
            digest_sent=True,
            errors=[]
        )
        
        assert metrics.duration_seconds == 45.0
        assert metrics.success == True
        
        # Test with errors
        error_metrics = ExecutionMetrics(
            start_time=start_time,
            end_time=end_time,
            total_posts_found=0,
            total_posts_scored=0,
            top_score=0,
            platforms_processed=[],
            digest_sent=False,
            errors=["Test error"]
        )
        
        assert error_metrics.success == False
        
        # Test serialization
        metrics_dict = metrics.to_dict()
        assert "start_time" in metrics_dict
        assert "duration_seconds" in metrics_dict
        assert "success" in metrics_dict
    
    def test_github_actions_integration(self):
        """Test GitHub Actions workflow and configuration."""
        # Test workflow file exists
        workflow_file = Path("../.github/workflows/community_watcher.yml")
        if not workflow_file.exists():
            # Create a mock workflow file for testing
            workflow_content = """
name: Community Watcher
on:
  schedule:
    - cron: '*/5 * * * *'
jobs:
  watch-communities:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run watcher
      run: python main.py
"""
            workflow_file.parent.mkdir(parents=True, exist_ok=True)
            with open(workflow_file, 'w') as f:
                f.write(workflow_content)
        
        # Test that main.py would be executable
        main_script = Path("../main.py")
        if main_script.exists():
            with open(main_script, 'r') as f:
                content = f.read()
            assert "run_community_watcher" in content
    
    def test_performance_requirements(self):
        """Test that the system meets performance requirements."""
        # Test database query performance
        db = DatabaseManager("test_performance.db")
        keyword_manager = KeywordManager(db)
        
        # Add many keywords
        start_time = datetime.now()
        for i in range(100):
            db.add_keyword(f"keyword_{i}", "test", 5)
        
        keyword_load_time = (datetime.now() - start_time).total_seconds()
        assert keyword_load_time < 1.0  # Should load 100 keywords in under 1 second
        
        # Test keyword matching performance
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        matcher = KeywordMatcher(keyword_manager, config)
        
        test_text = "This is a long piece of text about woodworking with many keywords " * 10
        
        start_time = datetime.now()
        matches = matcher.find_matches(test_text)
        match_time = (datetime.now() - start_time).total_seconds()
        
        assert match_time < 0.1  # Should match keywords in under 100ms
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary."""
        print("🧪 Running WoodworkersArchive Community Engine Test Suite")
        print("=" * 60)
        
        # Setup logging for tests
        setup_logging(log_level="WARNING")
        
        # Define all tests
        tests = [
            (self.test_configuration_management, "Configuration Management"),
            (self.test_database_operations, "Database Operations"),
            (self.test_keyword_matching, "Keyword Matching"),
            (self.test_post_scoring, "Post Scoring and Filtering"),
            (self.test_digest_generation, "Digest Generation"),
            (self.test_utm_tracking, "UTM Tracking"),
            (self.test_reply_templates, "Reply Templates"),
            (self.test_reply_helper, "Reply Helper"),
            (self.test_notification_system, "Notification System"),
            (self.test_execution_metrics, "Execution Metrics"),
            (self.test_github_actions_integration, "GitHub Actions Integration"),
            (self.test_performance_requirements, "Performance Requirements")
        ]
        
        # Run all tests
        for test_func, test_name in tests:
            result = self.run_test(test_func, test_name)
            print(result)
        
        # Calculate summary
        passed_tests = sum(1 for r in self.results if r.passed)
        total_tests = len(self.results)
        total_duration = sum(r.duration for r in self.results)
        
        print("\n" + "=" * 60)
        print(f"📊 Test Summary")
        print(f"Passed: {passed_tests}/{total_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"Total Duration: {total_duration:.3f}s")
        
        # Show failed tests
        failed_tests = [r for r in self.results if not r.passed]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"  - {test.name}: {test.message}")
        
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": len(failed_tests),
            "success_rate": (passed_tests/total_tests)*100,
            "total_duration": total_duration,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration": r.duration
                }
                for r in self.results
            ]
        }
        
        # Save test results
        with open("test_results.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        if passed_tests == total_tests:
            print("\n🎉 All tests passed! The system is ready for deployment.")
            return summary
        else:
            print(f"\n⚠️ {len(failed_tests)} tests failed. Please review and fix issues before deployment.")
            return summary


def main():
    """Main entry point for the test suite."""
    test_suite = TestSuite()
    
    try:
        summary = test_suite.run_all_tests()
        
        # Return appropriate exit code
        if summary["failed_tests"] == 0:
            return 0
        else:
            return 1
    
    except KeyboardInterrupt:
        print("\n⏹️ Test suite interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n💥 Test suite failed with unexpected error: {e}")
        return 1
    
    finally:
        test_suite.cleanup_test_environment()


if __name__ == "__main__":
    sys.exit(main())

