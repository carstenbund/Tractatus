# LLM Setup Guide

This document explains how to configure AI-powered philosophical analysis for the Tractatus application using Anthropic Claude, OpenAI GPT, or Ollama (local models).

## Overview

The Tractatus application supports three LLM providers for AI-powered commentary and analysis:

1. **Anthropic Claude** (Best Quality) - Advanced reasoning capabilities ideal for philosophical analysis
2. **OpenAI GPT** (Good Quality) - Cost-effective cloud alternative with good performance
3. **Ollama** (Free & Local) - Run open-source models locally without API keys or usage costs

The application automatically selects the available provider based on environment variables and local services, with priority given to cloud providers for quality.

## Quick Start

### Option 1: Using Anthropic Claude (Recommended for Quality)

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

### Option 3: Using Ollama (Free, Local, No API Key)

```bash
# Install Ollama from https://ollama.ai

# Pull a model (one-time setup)
ollama pull llama3.2

# Start Ollama server (if not already running)
ollama serve

# Start the application (no API key needed!)
python app.py
# or
python trcli.py
```

## Provider Selection Priority

The application tries to initialize LLM clients in this order:

1. **Anthropic Claude** - If `ANTHROPIC_API_KEY` is set (best quality)
2. **OpenAI GPT** - If `OPENAI_API_KEY` is set (good quality)
3. **Ollama** - If Ollama server is running (local, free, private)
4. **Echo Client** - Fallback when no providers are available (for testing)

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

### Ollama (Local Models)

- `llama3.2` (default) - Meta's latest Llama model, excellent reasoning capabilities
- `llama3.1` - Previous Llama generation, still very capable
- `mistral` - Mistral AI's efficient 7B model, good quality/speed balance
- `phi3` - Microsoft's compact but surprisingly capable model
- `qwen2.5` - Alibaba's multilingual model, good for multiple languages
- And 100+ more available at https://ollama.ai/library

**Note:** Ollama provides **complete privacy** (all processing local), **zero costs**, and works **offline**. Quality depends on the model and your hardware (GPU recommended for best performance).

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

### Setting up Ollama (Local, No API Key Required)

Ollama allows you to run open-source models locally on your computer - completely free, private, and offline-capable.

**Installation:**

1. **Install Ollama** (one-time):
   - **macOS/Linux:** Visit [ollama.ai](https://ollama.ai) and download installer
   - **Command line:** `curl -fsSL https://ollama.ai/install.sh | sh`

2. **Pull a model** (one-time per model):
   ```bash
   # Recommended: Llama 3.2 (excellent quality, ~2GB)
   ollama pull llama3.2

   # Alternative: Mistral (fast, ~4GB)
   ollama pull mistral

   # Lightweight: Phi3 (small, ~2GB)
   ollama pull phi3
   ```

3. **Start Ollama server** (each time):
   ```bash
   # Start in background
   ollama serve

   # Or use as systemd service (Linux)
   systemctl start ollama
   ```

4. **Verify it's working:**
   ```bash
   ollama list  # Shows installed models
   ```

**Optional Environment Variables:**

```bash
# Use a different model (default: llama3.2)
export OLLAMA_MODEL="mistral"

# Use remote Ollama server (default: http://localhost:11434)
export OLLAMA_HOST="http://remote-server:11434"
```

**Hardware Requirements:**
- **Minimum:** 8GB RAM, CPU-only (slow but works)
- **Recommended:** 16GB RAM, NVIDIA GPU with 6GB+ VRAM (much faster)
- **Optimal:** 32GB RAM, NVIDIA GPU with 12GB+ VRAM

**Model Size vs Quality:**
- Small models (2-4GB): Phi3, Llama3.2 - Fast, good for basic analysis
- Medium models (4-8GB): Mistral, Llama3.1 - Balanced quality/speed
- Large models (8GB+): Llama3.1 70B, Qwen2.5 - Best quality, requires powerful GPU

### Persistent Configuration

Add the export statement to your shell profile for permanent configuration:

```bash
# For bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc

# For zsh
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc

# For Ollama (optional, if not using defaults)
echo 'export OLLAMA_MODEL="mistral"' >> ~/.bashrc
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

**Solution:** Export your Anthropic API key, or use OpenAI or Ollama instead.

### "Missing OPENAI_API_KEY" Error

**Solution:** Export your OpenAI API key, or use Anthropic or Ollama instead.

### "Cannot connect to Ollama server" Error

**Cause:** Ollama is not running or not accessible.

**Solution:**
```bash
# Check if Ollama is running
ollama list

# If not running, start it
ollama serve

# If model not found, pull it
ollama pull llama3.2
```

### Ollama Responses are Slow

**Cause:** Running on CPU without GPU acceleration.

**Solutions:**
1. Use a smaller model: `export OLLAMA_MODEL="phi3"`
2. Ensure GPU drivers are installed (NVIDIA CUDA for best performance)
3. Reduce max_tokens: `config set llm_max_tokens 1000`

### Responses are Truncated

**Solution:** Increase `llm_max_tokens` in your config:

```bash
config set llm_max_tokens 3000
```

### "[Placeholder LLM]" Responses

**Cause:** No LLM providers are available.

**Solutions:**
1. Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` for cloud providers
2. Install and run Ollama for free local inference
3. Check that Ollama is running if you have it installed

## Cost Considerations

### Anthropic Claude Pricing (as of 2024)

- **Claude 3.5 Sonnet:** $3.00 / 1M input tokens, $15.00 / 1M output tokens
- **Claude 3.5 Haiku:** $0.25 / 1M input tokens, $1.25 / 1M output tokens

**Typical cost per request:** $0.02-0.05 (Sonnet), $0.005-0.015 (Haiku)

### OpenAI GPT Pricing (as of 2024)

- **GPT-4o-mini:** $0.15 / 1M input tokens, $0.60 / 1M output tokens
- **GPT-4o:** $5.00 / 1M input tokens, $15.00 / 1M output tokens

**Typical cost per request:** $0.001-0.002 (4o-mini), $0.015-0.05 (4o)

### Ollama (Local) Pricing

- **Cost per request:** $0 (completely free!)
- **Setup cost:** $0 (open source)
- **Hardware:** Uses your existing computer (GPU recommended but not required)

**Trade-offs:**
- ✅ **Advantages:** Free, private, offline-capable, no API limits
- ⚠️ **Considerations:** Quality varies by model, slower without GPU, uses disk space (~2-8GB per model)

**Typical Usage Comparison:**

| Provider | Prompt | Response | Cost/Request | Quality | Speed |
|----------|--------|----------|--------------|---------|-------|
| Claude Sonnet | ~500 tokens | ~1500 tokens | $0.03 | Excellent | Fast |
| GPT-4o-mini | ~500 tokens | ~1500 tokens | $0.001 | Very Good | Fast |
| Ollama (Llama3.2) | ~500 tokens | ~1500 tokens | $0 | Good | Medium* |

*Speed depends on hardware (GPU vs CPU)

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

# For Ollama with Mistral
client = OllamaLLMClient(model="mistral")
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

# Option 1: Configure Anthropic (best quality)
export ANTHROPIC_API_KEY="sk-ant-..."

# Option 2: Configure OpenAI (good quality, widely available)
export OPENAI_API_KEY="sk-..."

# Option 3: Configure Ollama (free, local, no API key)
ollama pull llama3.2
ollama serve

# Verify configuration
python trcli.py
# Run: config show llm_max_tokens
# Should show: 2000 (default)
```

This configuration provides high-quality, complete philosophical analysis without truncation issues.
