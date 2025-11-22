# OpenRouter Integration for Kimi K2 Thinking

## Overview

The Crawl4AI Indeed scraper now supports using **Kimi K2 Thinking** from [OpenRouter](https://openrouter.ai) as the LLM provider for enhanced job extraction accuracy.

## Setup

### 1. Get OpenRouter API Key

1. Sign up at [OpenRouter](https://openrouter.ai)
2. Get your API key from the dashboard
3. Set environment variable:

```bash
export OPENROUTER_API_KEY=your_api_key_here
```

Or add to `.env` file:
```
OPENROUTER_API_KEY=your_api_key_here
```

### 2. Install Requirements

Make sure you have the latest requirements:

```bash
pip install -r requirements.txt
pip install crawl4ai
crawl4ai-setup
```

## Usage

### Basic Usage with Kimi K2

The scraper will automatically use Kimi K2 Thinking when `OPENROUTER_API_KEY` is set:

```bash
# CSS extraction (fast, free)
python main.py search "software engineer" --scraper crawl4ai

# LLM extraction with Kimi K2 (high accuracy)
python main.py search "software engineer" --scraper crawl4ai --extraction-mode llm

# Hybrid mode (CSS-first, LLM fallback)
python main.py search "software engineer" --scraper crawl4ai --extraction-mode hybrid
```

### Specify Custom Model

You can specify any OpenRouter model:

```bash
python main.py search "python developer" \
  --scraper crawl4ai \
  --extraction-mode llm \
  --llm-model openrouter/moonshot-ai/kimi-k2-thinking
```

Other available OpenRouter models:
```bash
# DeepSeek
--llm-model openrouter/deepseek/deepseek-chat

# Qwen
--llm-model openrouter/qwen/qwen-2.5-72b-instruct

# Claude (via OpenRouter)
--llm-model openrouter/anthropic/claude-3.5-sonnet
```

## LLM Provider Priority

The scraper checks for API keys in this order:

1. **OPENROUTER_API_KEY** → Uses Kimi K2 Thinking by default
2. **ANTHROPIC_API_KEY** → Uses Claude Sonnet 4
3. **OPENAI_API_KEY** → Uses GPT-4o-mini

## Cost Comparison

| Provider | Model | Input (per 1M tokens) | Output (per 1M tokens) | Est. per 100 jobs |
|----------|-------|----------------------|------------------------|-------------------|
| **OpenRouter** | Kimi K2 Thinking | $0.15 | $0.50 | ~$0.05-0.20 |
| OpenAI | GPT-4o-mini | $0.15 | $0.60 | ~$0.05-0.25 |
| OpenAI | GPT-4o | $2.50 | $10.00 | ~$1.00-4.00 |
| Anthropic | Claude Sonnet 4 | $3.00 | $15.00 | ~$1.50-6.00 |

*Note: Costs vary based on page complexity and extraction mode*

## Why Kimi K2 Thinking?

**Advantages:**
- Excellent reasoning capabilities for complex extractions
- Cost-effective compared to GPT-4o/Claude
- Good at structured data extraction
- Strong performance on Chinese company names (useful for Taiwan team search)

**Best for:**
- Complex salary parsing (ranges, currencies, periods)
- Detecting remote positions from ambiguous text
- Extracting company websites from messy HTML

## Extraction Modes

### CSS Mode (Default)
```bash
--extraction-mode css
```
- Fast, deterministic
- Free (no LLM costs)
- ~85-90% accuracy
- Best for: Large volume scraping

### LLM Mode
```bash
--extraction-mode llm
```
- Highest accuracy (~95%+)
- LLM cost per page
- Best for: Critical extractions, complex pages

### Hybrid Mode (Recommended)
```bash
--extraction-mode hybrid
```
- CSS first, LLM fallback
- Balanced cost/accuracy
- Only uses LLM when CSS fails
- Best for: Production use

## Example Workflows

### Daily Job Search with Kimi K2

```bash
#!/bin/bash
# Set API key
export OPENROUTER_API_KEY=your_key

# Search with hybrid extraction
python main.py search "remote software engineer" \
  --max-results 50 \
  --scraper crawl4ai \
  --extraction-mode hybrid \
  --save

# Enrich with LinkedIn data
python main.py enrich --service coresignal --max-jobs 50

# Export results
python main.py list --min-taiwan-team 1 --export taiwan_jobs.csv
```

### High-Accuracy Extraction

For important searches where accuracy matters more than cost:

```bash
python main.py search "senior python developer" \
  --max-results 20 \
  --scraper crawl4ai \
  --extraction-mode llm \
  --llm-model openrouter/moonshot-ai/kimi-k2-thinking \
  --verbose
```

## Troubleshooting

### No LLM extraction happening

Check:
1. API key is set: `echo $OPENROUTER_API_KEY`
2. Using correct extraction mode: `--extraction-mode llm` or `--extraction-mode hybrid`
3. crawl4ai is installed: `pip show crawl4ai`

### OpenRouter API errors

Common issues:
- **Invalid API key**: Verify key at OpenRouter dashboard
- **Rate limiting**: OpenRouter has rate limits, add delays between requests
- **Model not found**: Check model name format: `openrouter/provider/model-name`

### Cost concerns

To minimize costs:
1. Use `--extraction-mode css` for most scraping
2. Use `--extraction-mode hybrid` for important searches
3. Limit `--max-results` to what you need
4. Set budget alerts in OpenRouter dashboard

## Environment Variables

```bash
# Required for OpenRouter
OPENROUTER_API_KEY=your_key

# Optional: Override default model
# (Not needed, will use Kimi K2 by default)

# Other supported providers (lower priority)
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
```

## Architecture

The scraper uses Crawl4AI's LLMExtractionStrategy with Pydantic schemas:

```python
# Automatic detection of provider
if OPENROUTER_API_KEY:
    provider = "openrouter/moonshot-ai/kimi-k2-thinking"
elif ANTHROPIC_API_KEY:
    provider = "anthropic/claude-sonnet-4"
else:
    provider = "openai/gpt-4o-mini"

# Create extraction strategy
extraction_strategy = LLMExtractionStrategy(
    llm_config=LLMConfig(provider=provider, api_key=api_key),
    schema=job_schema,
    instruction="Extract job listings..."
)
```

## Support

For issues:
- Crawl4AI: https://github.com/unclecode/crawl4ai/issues
- OpenRouter: https://openrouter.ai/docs
- This project: Create issue in repository

---

**Last Updated**: 2025-11-21
**Version**: 1.0
