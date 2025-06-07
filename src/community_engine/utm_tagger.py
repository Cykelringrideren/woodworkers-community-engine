"""
UTM parameter generation and link tracking utilities.

This module provides tools for generating UTM-tagged URLs for tracking
community engagement and measuring ROI.
"""

from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from typing import Dict, Optional
from datetime import datetime

from .models import Platform
from .config import Config
from .logging_config import get_logger


class UTMTagger:
    """Generates UTM-tagged URLs for tracking purposes."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
    
    def generate_utm_url(self, 
                        base_url: Optional[str] = None,
                        source: Optional[str] = None,
                        medium: str = "comment",
                        campaign: Optional[str] = None,
                        content: Optional[str] = None,
                        term: Optional[str] = None) -> str:
        """
        Generate a UTM-tagged URL.
        
        Args:
            base_url: Base URL to tag (defaults to config base_url)
            source: Traffic source (e.g., 'reddit', 'lumberjocks')
            medium: Marketing medium (defaults to 'comment')
            campaign: Campaign name (defaults to config default_campaign)
            content: Content identifier (optional)
            term: Keyword term (optional)
        
        Returns:
            UTM-tagged URL
        """
        # Use defaults from config
        if base_url is None:
            base_url = self.config.utm.base_url
        
        if campaign is None:
            campaign = self.config.utm.default_campaign
        
        # Build UTM parameters
        utm_params = {
            'utm_medium': medium,
            'utm_campaign': campaign
        }
        
        if source:
            utm_params['utm_source'] = source
        
        if content:
            utm_params['utm_content'] = content
        
        if term:
            utm_params['utm_term'] = term
        
        # Parse base URL to handle existing query parameters
        parsed_url = urlparse(base_url)
        existing_params = parse_qs(parsed_url.query)
        
        # Convert existing params to flat dict (take first value if multiple)
        flat_params = {k: v[0] if v else '' for k, v in existing_params.items()}
        
        # Add UTM parameters
        flat_params.update(utm_params)
        
        # Rebuild URL
        new_query = urlencode(flat_params)
        new_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))
        
        self.logger.debug(f"Generated UTM URL: {new_url}")
        return new_url
    
    def generate_platform_url(self, platform: Platform, 
                            content: Optional[str] = None,
                            campaign: Optional[str] = None) -> str:
        """
        Generate UTM URL for a specific platform.
        
        Args:
            platform: Platform enum
            content: Content identifier (optional)
            campaign: Campaign name (optional)
        
        Returns:
            UTM-tagged URL for the platform
        """
        # Get source mapping from config
        source = self.config.utm.source_mapping.get(platform.value, platform.value)
        
        return self.generate_utm_url(
            source=source,
            content=content,
            campaign=campaign
        )
    
    def generate_post_specific_url(self, platform: Platform, post_id: str,
                                 topic: Optional[str] = None) -> str:
        """
        Generate UTM URL specific to a post/thread.
        
        Args:
            platform: Platform where the post is located
            post_id: Unique identifier of the post
            topic: Topic or keyword related to the post
        
        Returns:
            UTM-tagged URL with post-specific tracking
        """
        # Create content identifier
        content = f"{platform.value}_{post_id}"
        
        return self.generate_platform_url(
            platform=platform,
            content=content,
            campaign=f"{self.config.utm.default_campaign}_{topic}" if topic else None
        )
    
    def generate_article_url(self, article_path: str, 
                           source_platform: Platform,
                           topic: Optional[str] = None) -> str:
        """
        Generate UTM URL for a specific article.
        
        Args:
            article_path: Path to the article (e.g., '/articles/table-saw-safety')
            source_platform: Platform where this link will be shared
            topic: Topic or keyword context
        
        Returns:
            UTM-tagged URL for the article
        """
        # Construct full article URL
        base_url = self.config.utm.base_url.rstrip('/')
        article_url = f"{base_url}{article_path}"
        
        # Generate UTM parameters
        source = self.config.utm.source_mapping.get(source_platform.value, source_platform.value)
        content = f"article_{article_path.split('/')[-1]}"
        
        return self.generate_utm_url(
            base_url=article_url,
            source=source,
            content=content,
            term=topic
        )


class LinkBuilder:
    """High-level interface for building various types of tracking links."""
    
    def __init__(self, config: Config):
        self.config = config
        self.utm_tagger = UTMTagger(config)
        self.logger = get_logger(__name__)
    
    def build_engagement_link(self, platform: Platform, post_id: str,
                            article_path: Optional[str] = None,
                            topic: Optional[str] = None) -> Dict[str, str]:
        """
        Build a complete set of engagement links for a post.
        
        Args:
            platform: Platform where engagement will happen
            post_id: ID of the post being responded to
            article_path: Specific article to link to (optional)
            topic: Topic/keyword context
        
        Returns:
            Dictionary with different link types
        """
        links = {}
        
        # Homepage link
        links['homepage'] = self.utm_tagger.generate_post_specific_url(
            platform=platform,
            post_id=post_id,
            topic=topic
        )
        
        # Article link (if specified)
        if article_path:
            links['article'] = self.utm_tagger.generate_article_url(
                article_path=article_path,
                source_platform=platform,
                topic=topic
            )
        
        # Search results link (for topic-specific content)
        if topic:
            search_path = f"/search?q={topic.replace(' ', '+')}"
            links['search'] = self.utm_tagger.generate_article_url(
                article_path=search_path,
                source_platform=platform,
                topic=topic
            )
        
        self.logger.info(f"Built {len(links)} engagement links for {platform.value} post {post_id}")
        return links
    
    def build_quick_links(self) -> Dict[str, str]:
        """Build a set of commonly used quick links."""
        quick_links = {
            'homepage': self.config.utm.base_url,
            'getting_started': '/getting-started',
            'tool_reviews': '/tool-reviews',
            'project_plans': '/project-plans',
            'safety_guides': '/safety',
            'community': '/community'
        }
        
        # Add UTM parameters to each link
        utm_links = {}
        for name, path in quick_links.items():
            if path.startswith('/'):
                full_url = self.config.utm.base_url.rstrip('/') + path
            else:
                full_url = path
            
            utm_links[name] = self.utm_tagger.generate_utm_url(
                base_url=full_url,
                source='manual',
                content=f'quick_link_{name}'
            )
        
        return utm_links


class TrackingHelper:
    """Helper utilities for tracking and analytics."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
    
    def extract_utm_params(self, url: str) -> Dict[str, str]:
        """Extract UTM parameters from a URL."""
        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        
        utm_params = {}
        for key, values in params.items():
            if key.startswith('utm_') and values:
                utm_params[key] = values[0]
        
        return utm_params
    
    def generate_ga4_filter_instructions(self) -> str:
        """Generate instructions for setting up GA4 filters."""
        instructions = f"""
# Google Analytics 4 Setup Instructions

## Event Filter for Community Engagement

To track clicks from the community engagement engine, set up the following custom event in GA4:

### 1. Create Custom Event
- Go to GA4 > Configure > Events
- Click "Create event"
- Name: `community_engagement_click`

### 2. Event Conditions
Set up conditions to capture page views with UTM parameters:
- Event name equals: `page_view`
- utm_campaign contains: `{self.config.utm.default_campaign}`

### 3. Custom Dimensions
Create these custom dimensions to track engagement sources:
- `engagement_source` (utm_source)
- `engagement_platform` (utm_source)
- `engagement_content` (utm_content)
- `engagement_term` (utm_term)

### 4. Conversion Event
Mark `community_engagement_click` as a conversion event to track ROI.

### 5. Audience Creation
Create audiences based on:
- Users who triggered `community_engagement_click`
- Users from specific platforms (Reddit, LumberJocks, etc.)

### 6. Reporting
Use the following reports to measure engagement:
- Acquisition > Traffic acquisition (filter by utm_campaign)
- Engagement > Events (filter by community_engagement_click)
- Conversions > Conversion events

### 7. Real-time Testing
Use GA4 DebugView to test UTM tracking:
1. Enable debug mode in your browser
2. Visit a UTM-tagged URL
3. Check DebugView for the event

### Example UTM Parameters Used:
- utm_source: {', '.join(self.config.utm.source_mapping.values())}
- utm_medium: comment
- utm_campaign: {self.config.utm.default_campaign}
- utm_content: platform_postid
- utm_term: topic keywords
"""
        return instructions
    
    def validate_utm_url(self, url: str) -> Dict[str, any]:
        """Validate a UTM-tagged URL."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'utm_params': {}
        }
        
        try:
            # Extract UTM parameters
            utm_params = self.extract_utm_params(url)
            validation_result['utm_params'] = utm_params
            
            # Check required parameters
            required_params = ['utm_source', 'utm_medium', 'utm_campaign']
            for param in required_params:
                if param not in utm_params:
                    validation_result['errors'].append(f"Missing required parameter: {param}")
                    validation_result['valid'] = False
            
            # Check parameter values
            if 'utm_medium' in utm_params and utm_params['utm_medium'] != 'comment':
                validation_result['warnings'].append("utm_medium is not 'comment' as expected")
            
            if 'utm_campaign' in utm_params and self.config.utm.default_campaign not in utm_params['utm_campaign']:
                validation_result['warnings'].append(f"utm_campaign doesn't contain expected value: {self.config.utm.default_campaign}")
            
            # Check URL structure
            parsed_url = urlparse(url)
            if not parsed_url.scheme:
                validation_result['errors'].append("URL missing scheme (http/https)")
                validation_result['valid'] = False
            
            if not parsed_url.netloc:
                validation_result['errors'].append("URL missing domain")
                validation_result['valid'] = False
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"URL parsing error: {str(e)}")
        
        return validation_result

