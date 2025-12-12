# GitHub Scraping AI

AI-powered GitHub project discovery. Automatically finds interesting repositories matching your interests and sends daily notifications to Discord.

## Features

- **Smart Filtering**: Uses LLM to evaluate repositories against your natural language interests
- **Keyword Search**: Filter GitHub search with custom keywords (OR logic)
- **Fork Exclusion**: Automatically filters out forked repositories
- **Multi-Provider Support**: Works with OpenAI, Anthropic (Claude), or Google (Gemini)
- **Async & Concurrent**: Fetches READMEs concurrently for faster processing
- **Daily Discovery**: Fetches top starred repos from the last 24 hours
- **Discord Notifications**: Rich embeds with repo details and AI reasoning
- **Rejected Repos Log**: Logs rejected repos with reasons for prompt fine-tuning
- **Deduplication**: Tracks seen repos to avoid duplicates
- **Dry Run Mode**: Test without sending to Discord

## How It Works

```
GitHub API → Fetch top 1000 new repos → LLM evaluates each against your prompt → Discord notification
```

1. Queries GitHub for repositories created in the last 24h, sorted by stars
2. Fetches README excerpts for context
3. Sends each repo + your interests to an LLM for evaluation
4. Posts matching repos to Discord with the AI's reasoning
5. Caches seen repos to prevent duplicates

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- API key for one of: OpenAI, Anthropic, or Google
- GitHub personal access token
- Discord webhook URL

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/github-scraping-agent-ai.git
cd github-scraping-agent-ai

# Install dependencies
uv sync
```

### Configuration

1. **Copy example files:**
   ```bash
   cp config.example.json config.json
   cp prompt.example.md prompt.md
   ```

2. **Edit `config.json`** with your credentials:
   ```json
   {
     "github": {
       "token": "ghp_your_github_token",
       "keywords": ["kubernetes", "devops", "terraform"]
     },
     "llm": {
       "provider": "openai",
       "model": "gpt-4o-mini",
       "api_key": "sk-your-api-key"
     },
     "discord": {
       "webhook_url": "https://discord.com/api/webhooks/..."
     },
     "settings": {
       "max_repos": 1000,
       "readme_max_chars": 500,
       "batch_size": 10,
       "cache_days": 30
     }
   }
   ```

   **Keywords** (optional): Narrow GitHub search to repos matching any keyword. Uses OR logic - repos containing "kubernetes" OR "devops" OR "terraform" in name, description, or README. Leave empty `[]` to search all recent repos.

3. **Edit `prompt.md`** with your interests:
   ```markdown
   I'm interested in:
   - AI/ML tools, especially LLM applications
   - Developer productivity tools
   - Python libraries

   I'm NOT interested in:
   - Cryptocurrency projects
   - Tutorial repositories
   ```

### Supported LLM Providers

| Provider | Config Value | Recommended Model | Notes |
|----------|--------------|-------------------|-------|
| OpenAI | `openai` | `gpt-4o-mini` | Good balance of cost/quality |
| Anthropic | `anthropic` | `claude-3-haiku-20240307` | Fast and accurate |
| Google | `google` | `gemini-1.5-flash` | Has free tier |

## Usage

```bash
# Run discovery pipeline
uv run python -m src.main

# Dry run - see results without posting to Discord
uv run python -m src.main --dry-run

# Override date range (for testing)
uv run python -m src.main --since 2024-12-10

# Custom config paths
uv run python -m src.main --config my-config.json --prompt my-prompt.md

# Custom rejected repos log path
uv run python -m src.main --rejected-log /path/to/rejected.log
```

### Rejected Repos Log

The pipeline logs rejected repositories to `rejected_repos.log` (configurable with `--rejected-log`). This helps fine-tune your `prompt.md`:

```
[2025-12-12 09:07:20] owner/some-repo (150⭐)
  URL: https://github.com/owner/some-repo
  Description: A machine learning framework
  Language: Python
  Topics: ai, ml, deep-learning
  Reason: This is an AI/ML framework which is explicitly excluded in the prompt.
```

### Automated Daily Runs (Cron)

```bash
# Run daily at 9 AM
0 9 * * * cd /path/to/github-scraping-agent-ai && uv run python -m src.main >> /var/log/github-scraping.log 2>&1
```

## Kubernetes Deployment

A Helm chart is included for deploying as a CronJob on Kubernetes.

### Quick Install

```bash
helm install github-scraping-agent-ai ./chart \
  --set config.github.token=ghp_xxx \
  --set config.llm.apiKey=sk-xxx \
  --set config.discord.webhookUrl=https://discord.com/api/webhooks/xxx
```

### Using Existing Secret (Recommended)

```bash
# Create secret with your credentials
kubectl create secret generic github-scraping-agent-ai-secrets \
  --from-literal=github-token=ghp_xxx \
  --from-literal=llm-api-key=sk-xxx \
  --from-literal=discord-webhook=https://discord.com/api/webhooks/xxx

# Install chart referencing the secret
helm install github-scraping-agent-ai ./chart \
  --set existingSecret.name=github-scraping-agent-ai-secrets
```

### Custom Values

Create a `my-values.yaml`:

```yaml
schedule: "0 9 * * *"  # Daily at 9 AM

config:
  github:
    keywords: ["kubernetes", "devops", "terraform", "helm"]
  llm:
    provider: openai
    model: gpt-4o-mini
  settings:
    maxRepos: 500
    since: "1d"

prompt: |
  I'm interested in:
  - Kubernetes tools and operators
  - DevOps and CI/CD tooling
  - Infrastructure as Code

  I'm NOT interested in:
  - AI/ML projects
  - Cryptocurrency

existingSecret:
  name: github-scraping-agent-ai-secrets
```

```bash
helm install github-scraping-agent-ai ./chart -f my-values.yaml
```

### Docker

```bash
docker pull ghcr.io/soulkyu/github-scraping-agent-ai:latest

docker run -v $(pwd)/config.json:/app/config.json \
           -v $(pwd)/prompt.md:/app/prompt.md \
           ghcr.io/soulkyu/github-scraping-agent-ai:latest
```

## Project Structure

```
github-scraping-agent-ai/
├── src/
│   ├── main.py          # CLI and pipeline orchestration
│   ├── config.py        # Configuration loading
│   ├── prompt.py        # Prompt file loading
│   ├── github.py        # GitHub API client
│   ├── discord.py       # Discord webhook client
│   ├── cache.py         # Deduplication cache
│   └── llm/
│       ├── base.py      # Provider interface
│       ├── factory.py   # Provider factory
│       ├── openai_provider.py
│       ├── anthropic_provider.py
│       └── google_provider.py
├── tests/               # 40 comprehensive tests
├── config.example.json  # Example configuration
├── prompt.example.md    # Example interests prompt
└── pyproject.toml       # Project dependencies
```

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest -v

# Run tests with coverage
uv run pytest --cov=src
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`uv run pytest`)
5. Commit with conventional commits (`feat:`, `fix:`, `docs:`, etc.)
6. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built with [Claude Code](https://claude.ai/code) by Anthropic
- Uses the [GitHub REST API](https://docs.github.com/en/rest)
- Discord notifications via [Webhooks](https://discord.com/developers/docs/resources/webhook)
