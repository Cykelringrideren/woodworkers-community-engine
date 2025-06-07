# Deployment Guide

This guide walks you through deploying the WoodworkersArchive Community Engagement Engine on GitHub Actions.

## Prerequisites

- GitHub account
- Reddit application credentials
- Slack workspace (optional)
- Gmail account with app password (optional)
- Facebook developer account (optional)

## Step 1: Fork and Clone Repository

1. Fork this repository to your GitHub account
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/woodworkers-community-engine.git
   cd woodworkers-community-engine
   ```

## Step 2: Obtain API Credentials

### Reddit API Setup

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill in the form:
   - **Name**: WoodworkersArchive Community Watcher
   - **App type**: Script
   - **Description**: Community engagement monitoring tool
   - **About URL**: https://woodworkersarchive.com
   - **Redirect URI**: http://localhost:8080
4. Note down the **Client ID** (under the app name) and **Client Secret**

### Slack Webhook Setup (Optional)

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name your app and select your workspace
4. Go to "Incoming Webhooks" and activate them
5. Click "Add New Webhook to Workspace"
6. Select the channel where you want notifications
7. Copy the webhook URL

### Gmail App Password Setup (Optional)

1. Enable 2-factor authentication on your Gmail account
2. Go to Google Account settings → Security → 2-Step Verification
3. At the bottom, click "App passwords"
4. Generate an app password for "Mail"
5. Use this password (not your regular Gmail password)

### Facebook Graph API Setup (Optional)

1. Go to https://developers.facebook.com/
2. Create a new app
3. Add the "Facebook Login" product
4. Generate a User Access Token with appropriate permissions
5. Note: Facebook API access may require app review for production use

## Step 3: Configure GitHub Secrets

1. Go to your forked repository on GitHub
2. Click Settings → Secrets and variables → Actions
3. Add the following repository secrets:

### Required Secrets

- `REDDIT_CLIENT_ID`: Your Reddit app client ID
- `REDDIT_CLIENT_SECRET`: Your Reddit app client secret

### Optional Secrets

- `SLACK_WEBHOOK_URL`: Your Slack webhook URL
- `EMAIL_USERNAME`: Your Gmail address
- `EMAIL_PASSWORD`: Your Gmail app password
- `FACEBOOK_ACCESS_TOKEN`: Your Facebook access token

## Step 4: Configure the Application

1. Copy the sample configuration:
   ```bash
   cp config/config.yaml config/config.yaml.local
   ```

2. Edit `config/config.yaml` with your preferences:
   - Update subreddit lists
   - Configure forum URLs
   - Adjust scoring parameters
   - Set UTM tracking parameters

3. Commit your configuration changes:
   ```bash
   git add config/config.yaml
   git commit -m "Configure application settings"
   git push origin main
   ```

## Step 5: Test the Setup

### Local Testing

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export REDDIT_CLIENT_ID="your_client_id"
   export REDDIT_CLIENT_SECRET="your_client_secret"
   export SLACK_WEBHOOK_URL="your_webhook_url"  # Optional
   ```

3. Run a test:
   ```bash
   python main.py
   ```

### GitHub Actions Testing

1. Go to your repository → Actions
2. Click on "Community Watcher" workflow
3. Click "Run workflow" to trigger a manual run
4. Monitor the execution and check logs

## Step 6: Enable Scheduled Execution

The workflow is configured to run every 5 minutes automatically. To modify the schedule:

1. Edit `.github/workflows/community_watcher.yml`
2. Change the cron expression in the `schedule` section
3. Commit and push the changes

### Cron Schedule Examples

- Every 5 minutes: `*/5 * * * *`
- Every 15 minutes: `*/15 * * * *`
- Every hour: `0 * * * *`
- Every 2 hours: `0 */2 * * *`

## Step 7: Monitor and Maintain

### Monitoring Execution

1. Check the Actions tab for workflow runs
2. Review execution logs and artifacts
3. Monitor Slack/email notifications

### Maintenance Tasks

1. **Weekly**: Review execution metrics and adjust keywords
2. **Monthly**: Check API rate limits and usage
3. **Quarterly**: Update dependencies and review configuration

### Troubleshooting

#### Common Issues

1. **API Rate Limits**
   - Reddit: 60 requests per minute
   - Facebook: Varies by app type
   - Solution: Reduce polling frequency or implement backoff

2. **Authentication Failures**
   - Check that secrets are correctly set
   - Verify API credentials are still valid
   - Ensure 2FA is properly configured for Gmail

3. **Execution Timeouts**
   - Default timeout is 3 minutes
   - Optimize database queries
   - Reduce number of posts processed per run

4. **No Posts Found**
   - Check subreddit names and forum URLs
   - Verify API permissions
   - Review keyword configuration

#### Debug Mode

Enable debug logging by running the workflow manually with debug mode enabled:

1. Go to Actions → Community Watcher
2. Click "Run workflow"
3. Check "Enable debug logging"
4. Click "Run workflow"

## Step 8: Customize for Your Needs

### Adding New Keywords

1. Edit the keywords section in `config/config.yaml`
2. Or add them programmatically:
   ```python
   from community_engine.database import get_db_manager
   db = get_db_manager()
   db.add_keyword("new_keyword", "category", score_value=5)
   ```

### Adding New Platforms

1. Create a new watcher class in `src/community_engine/watchers.py`
2. Inherit from `BaseWatcher`
3. Implement the `watch()` method
4. Add platform to the `WatcherManager`

### Customizing Templates

1. Edit templates in `src/community_engine/reply_kit.py`
2. Or create custom templates:
   ```python
   from community_engine.reply_kit import TemplateManager
   manager = TemplateManager(config)
   manager.add_template(your_custom_template)
   ```

## Security Considerations

1. **Never commit API keys** to the repository
2. **Use GitHub secrets** for all sensitive information
3. **Regularly rotate** API keys and passwords
4. **Monitor API usage** to detect unauthorized access
5. **Review permissions** regularly

## Cost Considerations

This system is designed to run entirely on free tiers:

- **GitHub Actions**: 2,000 minutes/month free
- **Reddit API**: Free with rate limits
- **Slack**: Free tier includes webhooks
- **Gmail**: Free with app passwords
- **Facebook API**: Free tier available

### Estimated Usage

- **GitHub Actions**: ~150 minutes/month (5-minute intervals, 2-minute execution)
- **API Calls**: Well within free tier limits
- **Storage**: Minimal (logs and database)

## Support and Troubleshooting

### Getting Help

1. Check the logs in GitHub Actions artifacts
2. Review the troubleshooting section above
3. Check API documentation for rate limits
4. Verify configuration against the sample

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Legal and Compliance

1. **Respect platform terms of service**
2. **Include required disclosures** in all replies
3. **Follow community guidelines** for each platform
4. **Monitor for policy changes** in APIs and platforms
5. **Maintain transparency** about automated tools

---

**Note**: This tool is designed for transparent community engagement. All generated replies include the required disclosure: "I maintain WoodworkersArchive.com"

