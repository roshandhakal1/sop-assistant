# Deploy to Railway (Recommended)

## Step 1: Prepare for Cloud Deployment

1. Create a `railway.json` file:
```json
{
  "deploy": {
    "startCommand": "streamlit run app.py --server.port $PORT --server.address 0.0.0.0"
  }
}
```

2. Create a cloud-optimized `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p chroma_db processed_documents.json

# Expose port
EXPOSE 8501

# Start command
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

## Step 2: Deploy to Railway

1. **Sign up:** Go to https://railway.app and sign up with GitHub
2. **Connect GitHub:** Link your GitHub account
3. **Push to GitHub:** Create a new repository and push your code
4. **Deploy on Railway:**
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your SOP Chatbot repository
   - Railway will automatically detect and deploy

## Step 3: Environment Variables
Set these in Railway dashboard:
- `OLLAMA_HOST=http://ollama-service:11434` (if using separate Ollama)
- `PORT=8501`

## Step 4: Custom Domain (Optional)
- Railway provides: `your-app.railway.app`
- Add custom domain in Railway dashboard

## Estimated Cost: $10-15/month