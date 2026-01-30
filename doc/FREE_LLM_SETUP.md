# Free LLM Setup Guide

## Quick Start - Choose ONE Option

### ⭐ Option 1: Hugging Face (EASIEST - Recommended)

**Pros**: No installation, free API, works immediately  
**Cons**: Requires internet, rate limits

1. **Get Free API Key** (2 minutes)
   - Go to: https://huggingface.co/settings/tokens
   - Click "New token" → Name it "rqsm-engine" → Create
   - Copy the token

2. **Configure**
   ```bash
   # Edit .env file
   LLM_PROVIDER=huggingface
   HUGGINGFACE_API_KEY=hf_your_token_here
   HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.2
   ```

3. **Install**
   ```bash
   pip install huggingface-hub
   ```

4. **Done!** Ready to use

---

### 🖥️ Option 2: Ollama (100% FREE - No API Key)

**Pros**: Completely free, no API keys, works offline  
**Cons**: Requires installation, uses disk space (~4GB)

1. **Install Ollama**
   - Windows: https://ollama.ai/download/windows
   - Run installer, follow prompts

2. **Download Model** (one-time)
   ```bash
   ollama pull llama2
   # Or smaller/faster:
   ollama pull llama2:7b
   ```

3. **Configure**
   ```bash
   # Edit .env file
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama2
   ```

4. **Start Ollama** (must be running)
   ```bash
   # Runs in background automatically after install
   # Or manually start: ollama serve
   ```

5. **Done!** Ready to use

---

### 🌐 Option 3: Google Gemini (Good Free Tier)

**Pros**: Google quality, 1,500 requests/day free  
**Cons**: Requires Google account, API key

1. **Get Free API Key**
   - Go to: https://makersuite.google.com/app/apikey
   - Click "Create API Key"
   - Copy the key

2. **Configure**
   ```bash
   # Edit .env file
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your_api_key_here
   GEMINI_MODEL=gemini-pro
   ```

3. **Install**
   ```bash
   pip install google-generativeai
   ```

4. **Done!** Ready to use

---

## Quick Comparison

| Provider | Cost | Setup Time | Quality | Speed | Offline |
|----------|------|------------|---------|-------|---------|
| **Hugging Face** | FREE | 2 min | Good | Medium | ❌ |
| **Ollama** | FREE | 10 min | Good | Fast | ✅ |
| **Gemini** | FREE | 5 min | Very Good | Fast | ❌ |
| OpenAI | $$ | 5 min | Excellent | Very Fast | ❌ |

**Recommendation**: Start with **Hugging Face** (easiest), switch to **Ollama** if you want offline/faster.

---

## Testing Your Setup

### Test Script
```bash
python test_llm.py
```

### Manual Test
```python
from app.llm.client import LLMClient

# Initialize
client = LLMClient()

# Test
response = client.generate("Explain what a neural network is in one sentence.")
print(response)
```

---

## Switching Providers

Just change one line in `.env`:
```bash
# Switch to Hugging Face
LLM_PROVIDER=huggingface

# Switch to Ollama
LLM_PROVIDER=ollama

# Switch to Gemini
LLM_PROVIDER=gemini
```

Restart your app and it uses the new provider!

---

## Troubleshooting

### Hugging Face: "Model is loading"
- Wait 20 seconds, try again
- Model needs to "warm up" on first request

### Ollama: "Cannot connect"
- Make sure Ollama is running: `ollama serve`
- Check if installed: `ollama --version`

### Gemini: "API key invalid"
- Check key is copied correctly
- Verify at: https://makersuite.google.com/app/apikey

### All: "ImportError"
- Install missing package: `pip install [package-name]`

---

## Free Models Comparison

### Hugging Face Options
```bash
# Balanced (recommended)
HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.2

# Faster, smaller
HUGGINGFACE_MODEL=microsoft/phi-2

# Larger, better quality
HUGGINGFACE_MODEL=meta-llama/Llama-2-13b-chat-hf
```

### Ollama Options
```bash
# Balanced
OLLAMA_MODEL=llama2

# Faster (3B params)
OLLAMA_MODEL=phi

# Better quality
OLLAMA_MODEL=mistral

# Code-focused
OLLAMA_MODEL=codellama
```

---

## Cost Comparison

| Provider | Cost/Month | Free Tier | Limit |
|----------|-----------|-----------|-------|
| **Hugging Face** | $0 | ✅ Forever | Rate limits |
| **Ollama** | $0 | ✅ Forever | None |
| **Gemini** | $0 | ✅ Forever | 1,500/day |
| OpenAI GPT-3.5 | ~$5-20 | 3 months trial | Pay per use |

**For Capstone Demo**: Any free option is perfect!

---

## Next Steps

1. Pick a provider from above
2. Follow setup instructions
3. Edit `.env` file
4. Run `python test_llm.py`
5. Start building! 🚀

---

**Recommended for Demo**: Hugging Face (no installation) or Ollama (faster, offline)
