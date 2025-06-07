"""
Manual reply kit and template system for community engagement.

This module provides templates, utilities, and tools for crafting
compliant manual replies to community posts.
"""

import os
import json
import argparse
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from .models import Post, Platform
from .utm_tagger import LinkBuilder
from .config import Config
from .logging_config import get_logger


class ReplyTemplate:
    """Represents a reply template with placeholders."""
    
    def __init__(self, name: str, template: str, description: str = "",
                 required_fields: Optional[List[str]] = None,
                 platform_specific: Optional[Platform] = None):
        self.name = name
        self.template = template
        self.description = description
        self.required_fields = required_fields or []
        self.platform_specific = platform_specific
    
    def render(self, **kwargs) -> str:
        """Render template with provided values."""
        # Ensure all required fields are provided
        missing_fields = [field for field in self.required_fields if field not in kwargs]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        # Render template
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Template placeholder not provided: {e}")
    
    def get_placeholders(self) -> List[str]:
        """Extract placeholder names from template."""
        import re
        placeholders = re.findall(r'\{([^}]+)\}', self.template)
        return list(set(placeholders))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            'name': self.name,
            'template': self.template,
            'description': self.description,
            'required_fields': self.required_fields,
            'platform_specific': self.platform_specific.value if self.platform_specific else None,
            'placeholders': self.get_placeholders()
        }


class TemplateManager:
    """Manages reply templates."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        self.templates = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default reply templates."""
        # Basic helpful response template
        self.add_template(ReplyTemplate(
            name="helpful_response",
            description="Basic helpful response with link",
            template="""
{answer}

{deeper_explanation}

{utm_link}

I maintain WoodworkersArchive.com
""".strip(),
            required_fields=["answer", "utm_link"]
        ))
        
        # Tool recommendation template
        self.add_template(ReplyTemplate(
            name="tool_recommendation",
            description="Template for tool recommendations",
            template="""
For {tool_type}, I'd recommend considering these factors:

{recommendation_points}

{additional_advice}

You might find this helpful: {utm_link}

I maintain WoodworkersArchive.com
""".strip(),
            required_fields=["tool_type", "recommendation_points", "utm_link"]
        ))
        
        # Safety advice template
        self.add_template(ReplyTemplate(
            name="safety_advice",
            description="Template for safety-related responses",
            template="""
Safety is crucial when {activity}. Here are the key points:

{safety_points}

{additional_resources}

For more detailed safety information: {utm_link}

I maintain WoodworkersArchive.com
""".strip(),
            required_fields=["activity", "safety_points", "utm_link"]
        ))
        
        # Technique explanation template
        self.add_template(ReplyTemplate(
            name="technique_explanation",
            description="Template for explaining woodworking techniques",
            template="""
{technique_name} is a great technique! Here's how to approach it:

{step_by_step}

{tips_and_tricks}

I've written more about this here: {utm_link}

I maintain WoodworkersArchive.com
""".strip(),
            required_fields=["technique_name", "step_by_step", "utm_link"]
        ))
        
        # Project guidance template
        self.add_template(ReplyTemplate(
            name="project_guidance",
            description="Template for project-related advice",
            template="""
{project_type} projects can be really rewarding! Here's my advice:

{guidance_points}

{encouragement}

Check out some similar projects here: {utm_link}

I maintain WoodworkersArchive.com
""".strip(),
            required_fields=["project_type", "guidance_points", "utm_link"]
        ))
        
        # Reddit-specific template (more casual)
        self.add_template(ReplyTemplate(
            name="reddit_casual",
            description="Casual response style for Reddit",
            platform_specific=Platform.REDDIT,
            template="""
{casual_answer}

{additional_info}

Hope this helps! {utm_link}

^(I maintain WoodworkersArchive.com)
""".strip(),
            required_fields=["casual_answer", "utm_link"]
        ))
        
        # Forum-specific template (more formal)
        self.add_template(ReplyTemplate(
            name="forum_formal",
            description="Formal response style for traditional forums",
            platform_specific=Platform.LUMBERJOCKS,
            template="""
{formal_greeting}

{detailed_response}

{conclusion}

Best regards,

{utm_link}

I maintain WoodworkersArchive.com
""".strip(),
            required_fields=["formal_greeting", "detailed_response", "utm_link"]
        ))
        
        self.logger.info(f"Loaded {len(self.templates)} default templates")
    
    def add_template(self, template: ReplyTemplate):
        """Add a template to the manager."""
        self.templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[ReplyTemplate]:
        """Get a template by name."""
        return self.templates.get(name)
    
    def list_templates(self, platform: Optional[Platform] = None) -> List[ReplyTemplate]:
        """List available templates, optionally filtered by platform."""
        templates = list(self.templates.values())
        
        if platform:
            # Include platform-specific templates and general templates
            templates = [
                t for t in templates 
                if t.platform_specific is None or t.platform_specific == platform
            ]
        
        return templates
    
    def save_templates(self, file_path: str):
        """Save templates to a JSON file."""
        template_data = {
            name: template.to_dict() 
            for name, template in self.templates.items()
        }
        
        with open(file_path, 'w') as f:
            json.dump(template_data, f, indent=2)
        
        self.logger.info(f"Saved {len(self.templates)} templates to {file_path}")
    
    def load_templates(self, file_path: str):
        """Load templates from a JSON file."""
        with open(file_path, 'r') as f:
            template_data = json.load(f)
        
        for name, data in template_data.items():
            platform = Platform(data['platform_specific']) if data['platform_specific'] else None
            template = ReplyTemplate(
                name=data['name'],
                template=data['template'],
                description=data['description'],
                required_fields=data['required_fields'],
                platform_specific=platform
            )
            self.add_template(template)
        
        self.logger.info(f"Loaded {len(template_data)} templates from {file_path}")


class ReplyBuilder:
    """Builds replies using templates and UTM links."""
    
    def __init__(self, config: Config):
        self.config = config
        self.template_manager = TemplateManager(config)
        self.link_builder = LinkBuilder(config)
        self.logger = get_logger(__name__)
    
    def build_reply(self, template_name: str, post: Post, 
                   article_path: Optional[str] = None,
                   topic: Optional[str] = None,
                   **template_vars) -> Dict[str, Any]:
        """
        Build a complete reply for a post.
        
        Args:
            template_name: Name of the template to use
            post: Post being replied to
            article_path: Specific article to link to
            topic: Topic/keyword context
            **template_vars: Variables to fill in the template
        
        Returns:
            Dictionary with reply text and metadata
        """
        # Get template
        template = self.template_manager.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # Generate UTM links
        links = self.link_builder.build_engagement_link(
            platform=post.platform,
            post_id=post.post_id,
            article_path=article_path,
            topic=topic
        )
        
        # Choose appropriate link
        utm_link = links.get('article', links.get('homepage'))
        
        # Add UTM link to template variables
        template_vars['utm_link'] = utm_link
        
        # Render template
        try:
            reply_text = template.render(**template_vars)
        except ValueError as e:
            raise ValueError(f"Template rendering failed: {e}")
        
        # Build reply metadata
        reply_data = {
            'reply_text': reply_text,
            'template_used': template_name,
            'post_info': {
                'platform': post.platform.value,
                'post_id': post.post_id,
                'title': post.title,
                'author': post.author,
                'url': post.url
            },
            'utm_links': links,
            'generated_at': datetime.now().isoformat(),
            'topic': topic,
            'article_path': article_path
        }
        
        self.logger.info(f"Built reply using template '{template_name}' for {post.platform.value} post {post.post_id}")
        
        return reply_data
    
    def suggest_template(self, post: Post) -> str:
        """Suggest an appropriate template based on post content."""
        content_lower = (post.title + " " + post.content).lower()
        
        # Simple keyword-based template suggestion
        if any(word in content_lower for word in ['safe', 'safety', 'danger', 'accident']):
            return 'safety_advice'
        elif any(word in content_lower for word in ['recommend', 'buy', 'purchase', 'tool']):
            return 'tool_recommendation'
        elif any(word in content_lower for word in ['how to', 'technique', 'method', 'way to']):
            return 'technique_explanation'
        elif any(word in content_lower for word in ['project', 'build', 'make', 'create']):
            return 'project_guidance'
        elif post.platform == Platform.REDDIT:
            return 'reddit_casual'
        elif post.platform in [Platform.LUMBERJOCKS, Platform.SAWMILLCREEK]:
            return 'forum_formal'
        else:
            return 'helpful_response'


class ReplyHelper:
    """Command-line helper for generating replies."""
    
    def __init__(self, config: Config):
        self.config = config
        self.reply_builder = ReplyBuilder(config)
        self.logger = get_logger(__name__)
    
    def create_reply_from_url(self, post_url: str, template_name: Optional[str] = None,
                            article_path: Optional[str] = None, 
                            topic: Optional[str] = None,
                            **template_vars) -> Dict[str, Any]:
        """Create a reply from a post URL."""
        # Parse platform and post ID from URL
        post_info = self._parse_post_url(post_url)
        
        # Create minimal post object
        post = Post(
            platform=post_info['platform'],
            post_id=post_info['post_id'],
            title="Post from URL",
            content="",
            author="unknown",
            url=post_url,
            timestamp=datetime.now()
        )
        
        # Use suggested template if none provided
        if not template_name:
            template_name = self.reply_builder.suggest_template(post)
        
        return self.reply_builder.build_reply(
            template_name=template_name,
            post=post,
            article_path=article_path,
            topic=topic,
            **template_vars
        )
    
    def _parse_post_url(self, url: str) -> Dict[str, Any]:
        """Parse platform and post ID from URL."""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if 'reddit.com' in domain:
            # Extract post ID from Reddit URL
            path_parts = parsed.path.split('/')
            if 'comments' in path_parts:
                post_id = path_parts[path_parts.index('comments') + 1]
            else:
                post_id = url.split('/')[-1]
            
            return {
                'platform': Platform.REDDIT,
                'post_id': post_id
            }
        
        elif 'lumberjocks.com' in domain:
            return {
                'platform': Platform.LUMBERJOCKS,
                'post_id': url.split('/')[-1]
            }
        
        elif 'sawmillcreek.org' in domain:
            return {
                'platform': Platform.SAWMILLCREEK,
                'post_id': url.split('/')[-1]
            }
        
        elif 'facebook.com' in domain:
            return {
                'platform': Platform.FACEBOOK,
                'post_id': url.split('/')[-1]
            }
        
        else:
            raise ValueError(f"Unsupported platform URL: {url}")
    
    def save_reply_to_file(self, reply_data: Dict[str, Any], output_dir: str = "replies"):
        """Save reply to a file for easy copying."""
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        platform = reply_data['post_info']['platform']
        post_id = reply_data['post_info']['post_id']
        filename = f"{timestamp}_{platform}_{post_id}.md"
        
        file_path = Path(output_dir) / filename
        
        # Create file content
        content = f"""# Reply for {platform.title()} Post

**Post URL:** {reply_data['post_info']['url']}
**Template Used:** {reply_data['template_used']}
**Generated:** {reply_data['generated_at']}

## Reply Text

{reply_data['reply_text']}

## UTM Links Used

"""
        
        for link_type, url in reply_data['utm_links'].items():
            content += f"- **{link_type.title()}:** {url}\n"
        
        content += f"""
## Post Information

- **Platform:** {reply_data['post_info']['platform']}
- **Post ID:** {reply_data['post_info']['post_id']}
- **Title:** {reply_data['post_info']['title']}
- **Author:** {reply_data['post_info']['author']}
"""
        
        # Write file
        with open(file_path, 'w') as f:
            f.write(content)
        
        self.logger.info(f"Saved reply to {file_path}")
        return str(file_path)


def create_cli_tool():
    """Create command-line interface for the reply helper."""
    def main():
        parser = argparse.ArgumentParser(description="WoodworkersArchive Reply Helper")
        parser.add_argument('--url', required=True, help='URL of the post to reply to')
        parser.add_argument('--template', help='Template name to use')
        parser.add_argument('--article', help='Article path to link to')
        parser.add_argument('--topic', help='Topic/keyword context')
        parser.add_argument('--output-dir', default='replies', help='Output directory for reply files')
        parser.add_argument('--config', default='config/config.yaml', help='Configuration file path')
        
        # Template variables
        parser.add_argument('--answer', help='Main answer content')
        parser.add_argument('--deeper-explanation', help='Additional explanation')
        parser.add_argument('--tool-type', help='Type of tool being discussed')
        parser.add_argument('--recommendation-points', help='Recommendation points')
        parser.add_argument('--additional-advice', help='Additional advice')
        parser.add_argument('--activity', help='Activity being discussed')
        parser.add_argument('--safety-points', help='Safety points')
        parser.add_argument('--technique-name', help='Name of technique')
        parser.add_argument('--step-by-step', help='Step by step instructions')
        parser.add_argument('--project-type', help='Type of project')
        parser.add_argument('--guidance-points', help='Guidance points')
        
        args = parser.parse_args()
        
        # Load configuration
        from .config import ConfigLoader
        config = ConfigLoader(args.config).load()
        
        # Create reply helper
        helper = ReplyHelper(config)
        
        # Build template variables from args
        template_vars = {}
        for key, value in vars(args).items():
            if value and key not in ['url', 'template', 'article', 'topic', 'output_dir', 'config']:
                # Convert hyphenated args to underscored template vars
                template_key = key.replace('-', '_')
                template_vars[template_key] = value
        
        try:
            # Generate reply
            reply_data = helper.create_reply_from_url(
                post_url=args.url,
                template_name=args.template,
                article_path=args.article,
                topic=args.topic,
                **template_vars
            )
            
            # Save to file
            file_path = helper.save_reply_to_file(reply_data, args.output_dir)
            
            print(f"Reply generated and saved to: {file_path}")
            print("\nReply text:")
            print("-" * 50)
            print(reply_data['reply_text'])
            print("-" * 50)
            
        except Exception as e:
            print(f"Error generating reply: {e}")
            return 1
        
        return 0
    
    return main

