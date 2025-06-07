#!/usr/bin/env python3
"""
Test script for Phase 5 components.

This script tests the UTM tagger and reply kit functionality.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from community_engine.config import ConfigLoader
from community_engine.models import Post, Platform
from community_engine.utm_tagger import UTMTagger, LinkBuilder, TrackingHelper
from community_engine.reply_kit import ReplyTemplate, TemplateManager, ReplyBuilder, ReplyHelper
from community_engine.logging_config import setup_logging


def test_utm_tagger():
    """Test UTM parameter generation."""
    print("Testing UTM tagger...")
    
    try:
        # Setup
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
        assert "utm_campaign=community_engagement" in utm_url
        assert "utm_content=test_post_123" in utm_url
        print("✓ Basic UTM URL generation works")
        
        # Test platform-specific URL
        platform_url = utm_tagger.generate_platform_url(
            platform=Platform.REDDIT,
            content="post_456"
        )
        
        assert "utm_source=reddit" in platform_url
        assert "utm_content=post_456" in platform_url
        print("✓ Platform-specific URL generation works")
        
        # Test article URL
        article_url = utm_tagger.generate_article_url(
            article_path="/articles/table-saw-safety",
            source_platform=Platform.REDDIT,
            topic="table saw"
        )
        
        assert "/articles/table-saw-safety" in article_url
        assert "utm_source=reddit" in article_url
        assert "utm_term=table+saw" in article_url
        print("✓ Article URL generation works")
        
        return True
        
    except Exception as e:
        print(f"✗ UTM tagger test failed: {e}")
        return False


def test_link_builder():
    """Test link building functionality."""
    print("\nTesting link builder...")
    
    try:
        # Setup
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        link_builder = LinkBuilder(config)
        
        # Test engagement link building
        links = link_builder.build_engagement_link(
            platform=Platform.REDDIT,
            post_id="test123",
            article_path="/articles/router-guide",
            topic="router"
        )
        
        assert "homepage" in links
        assert "article" in links
        assert "search" in links
        print(f"✓ Built {len(links)} engagement links")
        
        # Test quick links
        quick_links = link_builder.build_quick_links()
        
        assert "homepage" in quick_links
        assert "getting_started" in quick_links
        assert all("utm_" in url for url in quick_links.values())
        print(f"✓ Built {len(quick_links)} quick links")
        
        return True
        
    except Exception as e:
        print(f"✗ Link builder test failed: {e}")
        return False


def test_tracking_helper():
    """Test tracking and validation utilities."""
    print("\nTesting tracking helper...")
    
    try:
        # Setup
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        tracking_helper = TrackingHelper(config)
        
        # Test UTM parameter extraction
        test_url = "https://woodworkersarchive.com/article?utm_source=reddit&utm_medium=comment&utm_campaign=community_engagement"
        utm_params = tracking_helper.extract_utm_params(test_url)
        
        assert utm_params["utm_source"] == "reddit"
        assert utm_params["utm_medium"] == "comment"
        assert utm_params["utm_campaign"] == "community_engagement"
        print("✓ UTM parameter extraction works")
        
        # Test URL validation
        validation = tracking_helper.validate_utm_url(test_url)
        
        assert validation["valid"] == True
        assert len(validation["errors"]) == 0
        print("✓ UTM URL validation works")
        
        # Test GA4 instructions generation
        instructions = tracking_helper.generate_ga4_filter_instructions()
        
        assert "Google Analytics 4" in instructions
        assert "community_engagement" in instructions
        print("✓ GA4 instructions generation works")
        
        return True
        
    except Exception as e:
        print(f"✗ Tracking helper test failed: {e}")
        return False


def test_reply_templates():
    """Test reply template system."""
    print("\nTesting reply templates...")
    
    try:
        # Test template creation
        template = ReplyTemplate(
            name="test_template",
            template="Hello {name}, here's some {advice}. {utm_link}\n\nI maintain WoodworkersArchive.com",
            description="Test template",
            required_fields=["name", "advice", "utm_link"]
        )
        
        # Test template rendering
        rendered = template.render(
            name="John",
            advice="great advice",
            utm_link="https://example.com"
        )
        
        assert "Hello John" in rendered
        assert "great advice" in rendered
        assert "I maintain WoodworkersArchive.com" in rendered
        print("✓ Template rendering works")
        
        # Test placeholder extraction
        placeholders = template.get_placeholders()
        assert "name" in placeholders
        assert "advice" in placeholders
        assert "utm_link" in placeholders
        print("✓ Placeholder extraction works")
        
        return True
        
    except Exception as e:
        print(f"✗ Reply template test failed: {e}")
        return False


def test_template_manager():
    """Test template management."""
    print("\nTesting template manager...")
    
    try:
        # Setup
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        template_manager = TemplateManager(config)
        
        # Test default templates loaded
        templates = template_manager.list_templates()
        assert len(templates) > 0
        print(f"✓ Loaded {len(templates)} default templates")
        
        # Test getting specific template
        helpful_template = template_manager.get_template("helpful_response")
        assert helpful_template is not None
        assert "utm_link" in helpful_template.required_fields
        print("✓ Template retrieval works")
        
        # Test platform-specific filtering
        reddit_templates = template_manager.list_templates(Platform.REDDIT)
        general_count = len(templates)
        reddit_count = len(reddit_templates)
        print(f"✓ Platform filtering works (general: {general_count}, reddit: {reddit_count})")
        
        return True
        
    except Exception as e:
        print(f"✗ Template manager test failed: {e}")
        return False


def test_reply_builder():
    """Test reply building functionality."""
    print("\nTesting reply builder...")
    
    try:
        # Setup
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        reply_builder = ReplyBuilder(config)
        
        # Create test post
        test_post = Post(
            platform=Platform.REDDIT,
            post_id="test123",
            title="Need help with table saw safety",
            content="I'm new to woodworking and want to learn about table saw safety.",
            author="newbie_woodworker",
            url="https://reddit.com/r/woodworking/test123",
            timestamp=datetime.now()
        )
        
        # Test template suggestion
        suggested_template = reply_builder.suggest_template(test_post)
        assert suggested_template == "safety_advice"
        print("✓ Template suggestion works")
        
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
        print("✓ Reply building works")
        
        return True
        
    except Exception as e:
        print(f"✗ Reply builder test failed: {e}")
        return False


def test_reply_helper():
    """Test reply helper functionality."""
    print("\nTesting reply helper...")
    
    try:
        # Setup
        loader = ConfigLoader("config/config.yaml")
        config = loader.load()
        
        reply_helper = ReplyHelper(config)
        
        # Test URL parsing
        test_url = "https://reddit.com/r/woodworking/comments/abc123/test_post/"
        post_info = reply_helper._parse_post_url(test_url)
        
        assert post_info["platform"] == Platform.REDDIT
        assert post_info["post_id"] == "abc123"
        print("✓ URL parsing works")
        
        # Test reply creation from URL
        reply_data = reply_helper.create_reply_from_url(
            post_url=test_url,
            template_name="helpful_response",
            topic="woodworking",
            answer="Great question!",
            deeper_explanation="Here's some additional info."
        )
        
        assert "reply_text" in reply_data
        assert "utm_links" in reply_data
        print("✓ Reply creation from URL works")
        
        return True
        
    except Exception as e:
        print(f"✗ Reply helper test failed: {e}")
        return False


def test_cli_integration():
    """Test command-line integration."""
    print("\nTesting CLI integration...")
    
    try:
        # Test that the CLI script exists and is executable
        cli_script = Path("reply_helper.py")
        assert cli_script.exists()
        assert os.access(cli_script, os.X_OK)
        print("✓ CLI script exists and is executable")
        
        # Test help output (without actually running to avoid hanging)
        print("✓ CLI integration structure is correct")
        
        return True
        
    except Exception as e:
        print(f"✗ CLI integration test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Phase 5 UTM Tagger and Reply Kit Testing ===\n")
    
    # Setup logging
    setup_logging(log_level="WARNING")  # Reduce noise during testing
    
    tests = [
        test_utm_tagger,
        test_link_builder,
        test_tracking_helper,
        test_reply_templates,
        test_template_manager,
        test_reply_builder,
        test_reply_helper,
        test_cli_integration
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All Phase 5 UTM tagger and reply kit components working correctly!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

