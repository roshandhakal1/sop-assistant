# OpenAI Setup Guide

This SOP Assistant now uses OpenAI's GPT-4 instead of local LLaMA for much smarter responses!

## Quick Setup Steps

### 1. Get OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign in to your OpenAI account (or create one)
3. Click "Create new secret key"
4. Copy the API key (starts with `sk-`)

### 2. Set Environment Variable

#### For Local Development:
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

#### For Docker:
Update your docker-compose.yml or add to environment:
```yaml
environment:
  - OPENAI_API_KEY=your-api-key-here
```

#### For Cloud Deployment (Railway, etc.):
Add `OPENAI_API_KEY` as an environment variable in your deployment platform.

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
streamlit run app.py
```

## Benefits of OpenAI Integration

✅ **Much Smarter Responses** - GPT-4 understands context better than LLaMA  
✅ **No Local Resources** - Runs on any machine without GPU requirements  
✅ **Faster Responses** - OpenAI's servers are optimized for speed  
✅ **Better Language Understanding** - Superior handling of complex queries  
✅ **Consistent Performance** - No dependency on local hardware  

## Cost Information

- **gpt-4o-mini**: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- For typical SOP queries: ~$0.001-0.005 per question
- Very cost-effective for business use

## Security Notes

🔒 **Your API key is secure** - Stored only in environment variables  
🔒 **No data retention** - OpenAI doesn't store your SOP content  
🔒 **Local processing** - Documents are processed locally, only queries sent to OpenAI  

## Troubleshooting

**API Key Error**: Make sure OPENAI_API_KEY is set correctly  
**Rate Limits**: OpenAI has generous rate limits for paid accounts  
**Billing**: Monitor usage at https://platform.openai.com/usage  