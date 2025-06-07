# WoodworkersArchive Community Engagement Engine

A comprehensive, automated system for monitoring woodworking communities, scoring posts for relevance, and facilitating transparent community engagement. Built to run entirely on free service tiers with GitHub Actions automation.

## 🎯 Overview

The WoodworkersArchive Community Engagement Engine is a sophisticated tool designed to help woodworking websites and content creators engage meaningfully with their communities across multiple platforms. The system automatically monitors Reddit, LumberJocks, SawmillCreek, and Facebook for relevant discussions, scores them based on configurable keywords and criteria, and generates actionable digests for manual engagement.

### Key Features

- **Multi-Platform Monitoring**: Automatically watches Reddit subreddits, forum RSS feeds, and Facebook groups
- **Intelligent Scoring**: Advanced keyword matching with configurable scoring algorithms
- **Automated Digests**: Slack and email notifications with top engagement opportunities
- **Manual Reply Tools**: Template-based reply system with UTM tracking for ROI measurement
- **Free Deployment**: Runs entirely on GitHub Actions free tier (2,000 minutes/month)
- **Transparent Engagement**: All replies include required disclosure for ethical community participation

### Architecture

The system follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Processing    │    │   Outputs       │
│                 │    │                 │    │                 │
│ • Reddit API    │───▶│ • Keyword       │───▶│ • Slack Digest  │
│ • RSS Feeds     │    │   Matching      │    │ • Email Digest  │
│ • Facebook API  │    │ • Post Scoring  │    │ • Reply Tools   │
│ • Forum Scraping│    │ • Filtering     │    │ • UTM Tracking  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- GitHub account
- Reddit application credentials
- Slack workspace (optional)
- Gmail account with app password (optional)

### 1. Deploy to GitHub Actions

1. **Fork this repository** to your GitHub account

2. **Set up Reddit API credentials**:
   - Go to https://www.reddit.com/prefs/apps
   - Create a new "Script" application
   - Note the Client ID and Client Secret

3. **Configure GitHub Secrets**:
   - Go to your repository Settings → Secrets and variables → Actions
   - Add these secrets:
     - `REDDIT_CLIENT_ID`: Your Reddit app client ID
     - `REDDIT_CLIENT_SECRET`: Your Reddit app client secret
     - `SLACK_WEBHOOK_URL`: Your Slack webhook URL (optional)
     - `EMAIL_USERNAME`: Your Gmail address (optional)
     - `EMAIL_PASSWORD`: Your Gmail app password (optional)

4. **Enable GitHub Actions**:
   - Go to the Actions tab in your repository
   - Enable workflows if prompted
   - The system will automatically start monitoring every 5 minutes

### 2. Test the System

Run a manual test to verify everything is working:

1. Go to Actions → Community Watcher
2. Click "Run workflow"
3. Monitor the execution logs
4. Check for Slack/email notifications

### 3. Customize Configuration

Edit `config/config.yaml` to customize:
- Subreddits to monitor
- Keywords and scoring
- Notification preferences
- UTM tracking parameters

## 📖 Detailed Documentation

### System Components

#### 1. Data Collection (`watchers.py`)

The system monitors multiple platforms simultaneously:

**Reddit Integration**
- Uses PRAW (Python Reddit API Wrapper) for official API access
- Monitors configurable subreddits for new posts
- Respects Reddit's rate limits (60 requests/minute)
- Extracts post metadata, content, and engagement metrics

**Forum Integration**
- LumberJocks: RSS feed parsing with fallback to HTML scraping
- SawmillCreek: RSS feed parsing with custom content extraction
- Handles various forum software types and structures

**Facebook Integration**
- Uses Graph API for group monitoring (requires permissions)
- Extracts public posts from woodworking groups
- Handles API versioning and rate limiting

#### 2. Content Processing (`scorer.py`)

**Keyword Matching Engine**
- Configurable keyword database with categories and scores
- Word boundary matching to avoid false positives
- Diminishing returns for repeated keywords
- Case-insensitive matching with stemming support

**Scoring Algorithm**
```
Final Score = Keyword Score + Time Bonus + Link Penalty

Where:
- Keyword Score: Sum of matched keyword values (5 points default)
- Time Bonus: +2 points for posts less than 2 hours old
- Link Penalty: -1 point for posts with external links
```

**Post Filtering**
- Duplicate detection across platforms
- Age filtering (configurable, default 24 hours)
- Minimum score thresholds
- Previously processed post tracking

#### 3. Digest Generation (`digest.py`)

**Markdown Generation**
- Structured digest format with post summaries
- Platform icons and engagement metrics
- Direct links to original posts
- Execution statistics and performance metrics

**Multi-Channel Notifications**
- Slack webhook integration with rich formatting
- SMTP email with HTML and plain text versions
- Configurable notification thresholds
- Delivery confirmation and error handling

#### 4. Manual Engagement Tools (`reply_kit.py`)

**Template System**
- Pre-built templates for common scenarios (safety, tools, techniques)
- Platform-specific formatting (Reddit vs. forums)
- Required disclosure integration
- Custom template creation support

**UTM Tracking (`utm_tagger.py`)**
- Automatic UTM parameter generation
- Platform-specific source mapping
- Campaign and content tracking
- Google Analytics 4 integration guide

### Configuration Reference

The system uses YAML configuration with environment variable overrides:

```yaml
# Platform Configuration
platforms:
  reddit:
    enabled: true
    subreddits: ["woodworking", "BeginnerWoodWorking", "handtools"]
    client_id: "${REDDIT_CLIENT_ID}"
    client_secret: "${REDDIT_CLIENT_SECRET}"
  
  lumberjocks:
    enabled: true
    rss_url: "https://lumberjocks.com/rss"
  
  sawmillcreek:
    enabled: true
    rss_url: "https://sawmillcreek.org/rss"

# Scoring Configuration
scoring:
  keyword_base_score: 5
  recent_post_bonus: 2
  external_link_penalty: -1
  max_posts_per_run: 10

# Notification Configuration
notifications:
  slack_webhook_url: "${SLACK_WEBHOOK_URL}"
  email_to: "your-email@example.com"
  smtp_server: "smtp.gmail.com"
  smtp_port: 587

# UTM Tracking
utm:
  base_url: "https://woodworkersarchive.com"
  default_campaign: "community_engagement"
  source_mapping:
    reddit: "reddit"
    lumberjocks: "lumberjocks"
    sawmillcreek: "sawmillcreek"
```

### Database Schema

The system uses SQLite database for data persistence:

```sql
-- Keywords table
CREATE TABLE keywords (
    id INTEGER PRIMARY KEY,
    keyword TEXT UNIQUE,
    category TEXT,
    score_value INTEGER,
    created_at TIMESTAMP
);

-- Posts table
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    platform TEXT,
    post_id TEXT,
    title TEXT,
    content TEXT,
    author TEXT,
    url TEXT,
    post_timestamp TIMESTAMP,
    score INTEGER,
    processed_at TIMESTAMP,
    UNIQUE(platform, post_id)
);

-- Execution history
CREATE TABLE execution_history (
    id INTEGER PRIMARY KEY,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    posts_processed INTEGER,
    digest_sent BOOLEAN,
    errors TEXT
);
```

## 🛠 Development

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/woodworkers-community-engine.git
   cd woodworkers-community-engine
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**:
   ```bash
   export REDDIT_CLIENT_ID="your_client_id"
   export REDDIT_CLIENT_SECRET="your_client_secret"
   export SLACK_WEBHOOK_URL="your_webhook_url"
   ```

4. **Run tests**:
   ```bash
   python test_phase2.py  # Test core components
   python test_phase3.py  # Test watchers
   python test_phase4.py  # Test scoring
   python test_phase5.py  # Test reply tools
   python test_phase6.py  # Test deployment
   ```

5. **Run the system locally**:
   ```bash
   python main.py
   ```

### Testing Framework

The project includes comprehensive tests for each component:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Cross-component functionality
- **Mock Tests**: API interaction simulation
- **Performance Tests**: Execution time validation

### Adding New Platforms

To add support for a new platform:

1. **Create a new watcher class**:
   ```python
   class NewPlatformWatcher(BaseWatcher):
       def watch(self) -> WatcherResult:
           # Implementation here
           pass
   ```

2. **Add platform to enum**:
   ```python
   class Platform(Enum):
       NEW_PLATFORM = "new_platform"
   ```

3. **Update configuration**:
   ```yaml
   platforms:
     new_platform:
       enabled: true
       # Platform-specific config
   ```

4. **Add to watcher manager**:
   ```python
   if config.platforms.new_platform.enabled:
       watchers.append(NewPlatformWatcher(config))
   ```

### Performance Optimization

The system is optimized for GitHub Actions' 3-minute timeout:

- **Concurrent API calls** where possible
- **Efficient database queries** with proper indexing
- **Caching mechanisms** for keyword lookups
- **Batch processing** for multiple posts
- **Early termination** on timeout approach

## 📊 Monitoring and Analytics

### Execution Metrics

Each run generates detailed metrics:

```json
{
  "start_time": "2024-01-15T10:30:00Z",
  "end_time": "2024-01-15T10:32:15Z",
  "duration_seconds": 135.2,
  "total_posts_found": 25,
  "total_posts_scored": 18,
  "top_score": 15,
  "platforms_processed": ["reddit", "lumberjocks"],
  "digest_sent": true,
  "errors": []
}
```

### Google Analytics Integration

The UTM tracking system integrates with Google Analytics 4:

1. **Custom Events**: Track community engagement clicks
2. **Custom Dimensions**: Platform, content type, campaign
3. **Conversion Tracking**: Measure engagement ROI
4. **Audience Segmentation**: Community-driven traffic analysis

### Performance Monitoring

Key performance indicators:

- **Execution Time**: Target < 120 seconds per run
- **API Rate Limits**: Monitor usage across platforms
- **Success Rate**: Track successful digest deliveries
- **Engagement Quality**: Monitor reply template effectiveness

## 🔒 Security and Compliance

### Data Privacy

- **No Personal Data Storage**: Only public post metadata is stored
- **Secure Credential Management**: All API keys stored as GitHub secrets
- **Data Retention**: Automatic cleanup of old data (30-day default)
- **Audit Logging**: Complete execution history tracking

### Platform Compliance

**Reddit Terms of Service**
- Uses official API with proper authentication
- Respects rate limits and usage guidelines
- No vote manipulation or spam behavior
- Transparent disclosure in all interactions

**Forum Guidelines**
- RSS feed usage within acceptable limits
- No aggressive scraping or server overload
- Respectful of robots.txt and site policies
- Manual engagement only, no automated posting

**Community Standards**
- All replies include required disclosure
- No misleading or deceptive practices
- Genuine value-added contributions only
- Respect for community rules and moderators

### Security Best Practices

- **Secrets Management**: Never commit credentials to repository
- **Access Control**: Minimal required permissions for APIs
- **Error Handling**: Graceful failure without data exposure
- **Dependency Management**: Regular security updates

## 💰 Cost Analysis

### Free Tier Usage

The system is designed to operate entirely within free service limits:

**GitHub Actions**
- **Allocation**: 2,000 minutes/month
- **Usage**: ~150 minutes/month (5-minute intervals, 2-minute execution)
- **Headroom**: 92% remaining capacity

**API Costs**
- **Reddit API**: Free with rate limits
- **Slack Webhooks**: Free tier includes unlimited webhooks
- **Gmail SMTP**: Free with app passwords
- **Facebook Graph API**: Free tier available (limited)

**Storage Requirements**
- **Database**: < 10MB typical usage
- **Logs**: < 50MB/month with 7-day retention
- **Artifacts**: Minimal GitHub Actions storage

### Scaling Considerations

For higher volume usage:

- **GitHub Actions Pro**: $0.008/minute beyond free tier
- **Dedicated Server**: $5-10/month VPS alternative
- **API Upgrades**: Premium tiers for higher rate limits
- **Storage**: Minimal costs for database scaling

## 🤝 Contributing

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-platform`
3. **Make changes** with appropriate tests
4. **Run the test suite**: Ensure all tests pass
5. **Submit a pull request** with detailed description

### Code Standards

- **Python Style**: Follow PEP 8 guidelines
- **Documentation**: Comprehensive docstrings for all functions
- **Testing**: Minimum 80% code coverage
- **Type Hints**: Use type annotations throughout
- **Error Handling**: Graceful failure with informative messages

### Issue Reporting

When reporting issues, include:

- **Environment details**: Python version, OS, dependencies
- **Configuration**: Sanitized config file (remove secrets)
- **Execution logs**: Full error messages and stack traces
- **Expected behavior**: What should have happened
- **Reproduction steps**: How to recreate the issue

## 📚 Additional Resources

### API Documentation

- [Reddit API (PRAW)](https://praw.readthedocs.io/)
- [Facebook Graph API](https://developers.facebook.com/docs/graph-api/)
- [Slack Webhooks](https://api.slack.com/messaging/webhooks)
- [GitHub Actions](https://docs.github.com/en/actions)

### Community Guidelines

- [Reddit Content Policy](https://www.redditinc.com/policies/content-policy)
- [LumberJocks Community Guidelines](https://lumberjocks.com/guidelines)
- [SawmillCreek Forum Rules](https://sawmillcreek.org/rules)

### Analytics and Tracking

- [Google Analytics 4](https://support.google.com/analytics/answer/10089681)
- [UTM Parameter Guide](https://support.google.com/analytics/answer/1033863)
- [Campaign Tracking Best Practices](https://support.google.com/analytics/answer/1037445)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PRAW Team**: Excellent Reddit API wrapper
- **GitHub Actions**: Reliable free automation platform
- **Woodworking Community**: Inspiration and feedback
- **Open Source Contributors**: Various libraries and tools used

---

**Disclaimer**: This tool is designed for transparent, ethical community engagement. All automated replies include the required disclosure: "I maintain WoodworkersArchive.com". Users are responsible for complying with platform terms of service and community guidelines.

