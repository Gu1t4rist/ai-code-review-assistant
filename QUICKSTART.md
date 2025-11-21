# Quick Start Guide

## Prerequisites

- Python 3.11+
- GitLab instance with API access
- OpenAI or Anthropic API key
- Docker (optional, for containerized deployment)

## Installation

### Option 1: Local Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-code-review-assistant
   ```

2. **Run setup script**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Configure environment**
   ```bash
   nano .env
   ```
   
   Required variables:
   - `GITLAB_URL`: Your GitLab instance URL
   - `GITLAB_TOKEN`: Personal access token with API scope
   - `GITLAB_WEBHOOK_SECRET`: Secret for webhook verification
   - `AI_PROVIDER`: Choose `openai` or `anthropic`
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`: Your API key

4. **Test the installation**
   ```bash
   source venv/bin/activate
   pytest
   ```

### Option 2: Docker Setup

1. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

3. **Check logs**
   ```bash
   docker-compose logs -f ai-code-review
   ```

## Usage

### 1. Webhook Mode (Recommended)

Start the webhook server to automatically review MRs:

```bash
# Local
python -m ai_code_review.main webhook

# Docker
docker-compose up -d
```

The server will listen on `http://localhost:8000` (configurable via `PORT` env var).

### 2. Configure GitLab Webhook

1. Go to your GitLab project
2. Navigate to **Settings → Webhooks**
3. Add new webhook:
   - **URL**: `http://your-server:8000/webhook`
   - **Secret Token**: Same as `GITLAB_WEBHOOK_SECRET` in `.env`
   - **Trigger**: Select "Merge request events"
   - **Enable SSL verification**: Recommended for production

### 3. Manual Review Mode

Review a specific MR on demand:

```bash
python -m ai_code_review.main review \
  --project-id 123 \
  --mr-iid 45
```

## First Review

1. Create a test MR in GitLab
2. The AI agent will automatically:
   - Analyze the code changes
   - Check for security issues
   - Evaluate performance
   - Assess code quality
   - Post comments with findings
   - Generate a summary report
   - Apply appropriate labels

## Configuration

### Adjust Review Standards

Edit `config/standards.yaml` to customize:
- Code quality rules
- Security checks
- Performance thresholds
- Test coverage requirements

### Feature Flags

Control features via `.env`:
```env
ENABLE_SECURITY_SCAN=true
ENABLE_PERFORMANCE_CHECK=true
ENABLE_STYLE_CHECK=true
ENABLE_AUTO_LABELING=true
```

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### View Metrics
```bash
curl http://localhost:8000/api/v1/metrics
```

### Grafana Dashboard (Docker)
Access at `http://localhost:3000` (default credentials: admin/admin)

## Troubleshooting

### Issue: Webhook not receiving events
**Solution**:
1. Check GitLab webhook settings
2. Verify `GITLAB_WEBHOOK_SECRET` matches
3. Ensure server is accessible from GitLab
4. Check firewall/network settings

### Issue: AI review fails
**Solution**:
1. Verify API key is correct
2. Check API quota/limits
3. Review logs for errors
4. Test with a smaller MR

### Issue: Comments not posted
**Solution**:
1. Verify GitLab token has API scope
2. Check project permissions
3. Ensure token user has developer+ access

## Next Steps

1. **Customize prompts**: Edit `src/ai_code_review/ai/prompts.py`
2. **Add custom checks**: Extend `CodeReviewEngine` class
3. **Integrate with CI/CD**: Add to your pipeline
4. **Set up monitoring**: Configure Prometheus/Grafana
5. **Train the model**: Collect feedback to improve accuracy

## Support

For issues or questions:
- Check logs: `docker-compose logs -f` or `tail -f logs/app.log`
- Review documentation in `README.md`
- Open an issue in the repository

## Performance Tips

1. **Limit MR size**: Set `MAX_FILES_FOR_REVIEW` and `MAX_LINES_PER_MR`
2. **Use caching**: Enable `CACHE_ENABLED=true`
3. **Adjust timeout**: Increase `REVIEW_TIMEOUT` for large MRs
4. **Rate limiting**: Configure `MAX_REQUESTS_PER_MINUTE`
