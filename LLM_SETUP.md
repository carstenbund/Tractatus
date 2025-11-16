# LLM Setup Guide

This document explains how to configure AI-powered philosophical analysis for the Tractatus application using either Anthropic Claude or OpenAI GPT models.

## Overview

The Tractatus application supports two LLM providers for AI-powered commentary and analysis:

1. **Anthropic Claude** (Recommended) - Advanced reasoning capabilities ideal for philosophical analysis
2. **OpenAI GPT** - Cost-effective alternative with good performance

The application automatically selects the available provider based on environment variables, with Anthropic taking priority if both are configured.

## Quick Start

### Option 1: Using Anthropic Claude (Recommended)

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Start the application
python app.py
# or
python trcli.py
```

### Option 2: Using OpenAI GPT

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Start the application
python app.py
# or
python trcli.py
```

## Provider Selection Priority

The application tries to initialize LLM clients in this order:

1. **Anthropic Claude** - If `ANTHROPIC_API_KEY` is set
2. **OpenAI GPT** - If `OPENAI_API_KEY` is set
3. **Echo Client** - Fallback when no API keys are configured (for testing)

## Supported Models

### Anthropic Claude

- `claude-3-5-sonnet-20241022` (default) - Most capable, excellent for complex philosophical reasoning
- `claude-3-5-haiku-20241022` - Faster and more cost-effective
- `claude-3-opus-20240229` - Previous generation flagship model

**Note:** Claude Sonnet 3.5 is specifically optimized for tasks requiring nuanced understanding and careful reasoning, making it ideal for philosophical text analysis.

### OpenAI GPT

- `gpt-4o-mini` (default) - Cost-effective for most tasks
- `gpt-4o` - Most capable GPT-4 optimized model
- `gpt-4-turbo` - Previous generation flagship model

## Configuration

### Max Tokens

The default maximum response length is **2000 tokens**, which provides complete, high-quality philosophical analysis without truncation.

You can adjust this in your `~/.trclirc` configuration file:

```json
{
  "llm_max_tokens": 2000,
  "lang": "en"
}
```

Valid range: 100-8000 tokens

### Response Truncation

**Previous Issue (Fixed):** Earlier versions used 500-600 token limits, causing responses to be cut off mid-sentence.

**Current Behavior:**
- Default: 2000 tokens - sufficient for complete analysis
- Anthropic client: Falls back to 2000 if not configured
- OpenAI client: Falls back to 2000 if not configured

If you experience truncation, increase `llm_max_tokens` in your config:

```bash
# Via CLI
config set llm_max_tokens 3000

# Or edit ~/.trclirc directly
```

## API Key Setup

### Getting an Anthropic API Key

1. Visit [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Export it in your shell:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

### Getting an OpenAI API Key

1. Visit [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Export it in your shell:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

### Persistent Configuration

Add the export statement to your shell profile for permanent configuration:

```bash
# For bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc

# For zsh
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
```

## Usage Examples

### CLI Agent Commands

```bash
# Start the CLI
python trcli.py

# Get AI commentary on a proposition
trcli> get 1.1
trcli> ag:comment

# Compare multiple propositions
trcli> ag:comparison 1 1.1 1.2

# Use custom prompt
trcli> get 2.01
trcli> ag:comment "Explain this in simple terms"
```

### Web API

```bash
# Start the web server
python app.py

# Make API request
curl -X POST http://localhost:8000/api/agent \
  -H "Content-Type: application/json" \
  -d '{
    "action": "comment",
    "targets": ["1.1"],
    "language": "en"
  }'
```

## Troubleshooting

### "Missing ANTHROPIC_API_KEY" Error

**Solution:** Export your Anthropic API key or switch to OpenAI.

### "Missing OPENAI_API_KEY" Error

**Solution:** Export your OpenAI API key or switch to Anthropic.

### Responses are Truncated

**Solution:** Increase `llm_max_tokens` in your config:

```bash
config set llm_max_tokens 3000
```

### "[Placeholder LLM]" Responses

**Cause:** No API keys are configured.

**Solution:** Set either `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`.

## Cost Considerations

### Anthropic Claude Pricing (as of 2024)

- **Claude 3.5 Sonnet:** $3.00 / 1M input tokens, $15.00 / 1M output tokens
- **Claude 3.5 Haiku:** $0.25 / 1M input tokens, $1.25 / 1M output tokens

### OpenAI GPT Pricing (as of 2024)

- **GPT-4o-mini:** $0.15 / 1M input tokens, $0.60 / 1M output tokens
- **GPT-4o:** $5.00 / 1M input tokens, $15.00 / 1M output tokens

**Typical Usage:**
- Average prompt: ~500 tokens (system + proposition text)
- Average response: ~1000-2000 tokens
- Cost per request: $0.02-0.05 (Claude Sonnet), $0.001-0.002 (GPT-4o-mini)

### Cost Optimization

1. **Use caching:** The application automatically caches responses to avoid redundant API calls
2. **Choose appropriate model:** Use Haiku or GPT-4o-mini for simpler queries
3. **Adjust max_tokens:** Lower `llm_max_tokens` for shorter, cheaper responses

## Advanced Configuration

### Switching Models

To use a different model, modify the service initialization in `tractatus_service.py`:

```python
# For Anthropic Haiku
client = AnthropicLLMClient(model="claude-3-5-haiku-20241022")

# For OpenAI GPT-4o
client = OpenAILLMClient(model="gpt-4o")
```

### Response Caching

Responses are automatically cached in `.agent_cache/` to reduce costs and improve performance. The cache is keyed by action + prompt hash.

To clear the cache:

```bash
rm -rf .agent_cache/
```

## Support

For issues or questions:
- Check the main [README.md](README.md)
- Review [WEB_INTERFACE.md](WEB_INTERFACE.md) for API documentation
- File issues on GitHub

## Summary

**Recommended Setup:**
```bash
# Install dependencies
pip install -r requirements.txt

# Configure Anthropic (recommended)
export ANTHROPIC_API_KEY="sk-ant-..."

# Or configure OpenAI (alternative)
export OPENAI_API_KEY="sk-..."

# Verify configuration
python trcli.py
# Run: config show llm_max_tokens
# Should show: 2000 (default)
```

This configuration provides high-quality, complete philosophical analysis without truncation issues.
