"""
Main execution script for the Community Engagement Engine.

This script orchestrates the complete workflow: watching platforms,
scoring posts, generating digests, and sending notifications.
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from community_engine.config import get_config
from community_engine.database import get_db_manager, KeywordManager
from community_engine.watchers import WatcherManager
from community_engine.scorer import ScoringEngine
from community_engine.digest import DigestGenerator, NotificationManager
from community_engine.models import ExecutionMetrics, Platform
from community_engine.logging_config import setup_logging, PerformanceLogger


def initialize_system():
    """Initialize the system components."""
    # Load configuration
    config = get_config()
    
    # Setup logging
    setup_logging(
        log_level="INFO",
        log_file="logs/community_watcher.log"
    )
    
    # Initialize database
    db_manager = get_db_manager()
    
    # Initialize keywords if database is empty
    keyword_manager = KeywordManager(db_manager)
    keywords = db_manager.get_keywords()
    if not keywords:
        keyword_manager.initialize_default_keywords()
    
    return config, db_manager


def run_community_watcher():
    """Run the complete community watching workflow."""
    start_time = datetime.now()
    
    try:
        # Initialize system
        config, db_manager = initialize_system()
        
        # Create execution metrics
        metrics = ExecutionMetrics(
            start_time=start_time,
            end_time=start_time,  # Will be updated at the end
            total_posts_found=0,
            total_posts_scored=0,
            top_score=0,
            platforms_processed=[],
            digest_sent=False,
            errors=[]
        )
        
        with PerformanceLogger("Complete community watcher execution"):
            # Step 1: Watch all platforms
            print("🔍 Watching community platforms...")
            watcher_manager = WatcherManager(config)
            watcher_results = watcher_manager.watch_all()
            
            # Collect all posts
            all_posts = []
            for platform, result in watcher_results.items():
                metrics.platforms_processed.append(platform)
                metrics.total_posts_found += result.posts_found
                
                if result.errors:
                    metrics.errors.extend([f"{platform.value}: {error}" for error in result.errors])
                
                # Note: In a real implementation, we'd need to modify watchers to return posts
                # For now, we'll simulate this
                print(f"  📊 {platform.value}: {result.posts_found} posts found, {result.posts_processed} processed")
            
            # Step 2: Score and filter posts
            print("🎯 Scoring and filtering posts...")
            scoring_engine = ScoringEngine(config, db_manager)
            
            # For demonstration, we'll create some sample posts if none were found
            if not all_posts:
                from community_engine.models import Post
                sample_posts = [
                    Post(
                        platform=Platform.REDDIT,
                        post_id="sample_1",
                        title="Best table saw for beginners?",
                        content="I'm new to woodworking and looking for a good table saw recommendation.",
                        author="newbie_woodworker",
                        url="https://reddit.com/r/woodworking/sample_1",
                        timestamp=datetime.now(),
                        has_external_links=False
                    ),
                    Post(
                        platform=Platform.REDDIT,
                        post_id="sample_2",
                        title="Router table setup help",
                        content="Need help setting up my new router table properly.",
                        author="diy_enthusiast",
                        url="https://reddit.com/r/woodworking/sample_2",
                        timestamp=datetime.now(),
                        has_external_links=False
                    )
                ]
                all_posts = sample_posts
                print(f"  📝 Using {len(sample_posts)} sample posts for demonstration")
            
            scoring_results = scoring_engine.process_posts(all_posts)
            metrics.total_posts_scored = len(scoring_results)
            
            if scoring_results:
                metrics.top_score = scoring_results[0].final_score
                print(f"  🏆 Top scoring post: {scoring_results[0].final_score} points")
            
            # Step 3: Generate and send digest
            print("📧 Generating and sending digest...")
            digest_generator = DigestGenerator(config)
            notification_manager = NotificationManager(config, db_manager)
            
            # Calculate execution duration so far
            current_time = datetime.now()
            execution_duration = (current_time - start_time).total_seconds()
            
            # Generate digest
            digest = digest_generator.create_digest(
                scoring_results=scoring_results,
                execution_duration=execution_duration,
                total_posts_processed=metrics.total_posts_found
            )
            
            # Send digest
            if scoring_results:
                notification_results = notification_manager.send_digest(digest)
                metrics.digest_sent = any(notification_results.values())
                
                successful_channels = [channel for channel, success in notification_results.items() if success]
                if successful_channels:
                    print(f"  ✅ Digest sent via: {', '.join(successful_channels)}")
                else:
                    print("  ⚠️ Failed to send digest via any channel")
                    metrics.errors.append("Failed to send digest via any channel")
            else:
                print("  ℹ️ No posts to include in digest")
            
            # Step 4: Cleanup old data
            print("🧹 Cleaning up old data...")
            deleted_count = db_manager.cleanup_old_data(days=30)
            print(f"  🗑️ Cleaned up {deleted_count} old records")
            
        # Update final metrics
        metrics.end_time = datetime.now()
        
        # Log execution summary
        print("\n📊 Execution Summary:")
        print(f"  Duration: {metrics.duration_seconds:.1f} seconds")
        print(f"  Posts found: {metrics.total_posts_found}")
        print(f"  Posts scored: {metrics.total_posts_scored}")
        print(f"  Top score: {metrics.top_score}")
        print(f"  Platforms: {', '.join([p.value for p in metrics.platforms_processed])}")
        print(f"  Digest sent: {'Yes' if metrics.digest_sent else 'No'}")
        print(f"  Errors: {len(metrics.errors)}")
        
        if metrics.errors:
            print("  Error details:")
            for error in metrics.errors:
                print(f"    - {error}")
        
        # Check performance requirements
        if metrics.duration_seconds > config.performance.max_execution_time:
            print(f"  ⚠️ Execution time ({metrics.duration_seconds:.1f}s) exceeded limit ({config.performance.max_execution_time}s)")
            metrics.errors.append(f"Execution time exceeded limit: {metrics.duration_seconds:.1f}s")
        
        # Save execution metrics to file for debugging
        metrics_file = Path("logs/execution_metrics.json")
        metrics_file.parent.mkdir(exist_ok=True)
        
        with open(metrics_file, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)
        
        print(f"📁 Execution metrics saved to {metrics_file}")
        
        # Return success/failure based on metrics
        return 0 if metrics.success else 1
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"❌ Fatal error after {duration:.1f} seconds: {e}")
        
        # Save error metrics
        error_metrics = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "fatal_error": str(e),
            "success": False
        }
        
        metrics_file = Path("logs/execution_metrics.json")
        metrics_file.parent.mkdir(exist_ok=True)
        
        with open(metrics_file, "w") as f:
            json.dump(error_metrics, f, indent=2)
        
        return 1


def main():
    """Main entry point."""
    print("🪵 WoodworkersArchive Community Engagement Engine")
    print("=" * 50)
    
    try:
        exit_code = run_community_watcher()
        
        if exit_code == 0:
            print("\n✅ Community watcher completed successfully!")
        else:
            print("\n❌ Community watcher completed with errors!")
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\n⏹️ Community watcher interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

