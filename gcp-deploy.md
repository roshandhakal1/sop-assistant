# Deploy to Google Cloud Run

## Why Google Cloud Run?
- Pay only for what you use
- Scales to zero when not used
- Can handle high traffic
- $5-20/month depending on usage

## Step 1: Prepare for Cloud Run

Create `cloudbuild.yaml`:
```yaml
steps:
# Build the container image
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/$PROJECT_ID/sop-chatbot:latest', '.']
# Push the container image to Container Registry
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'gcr.io/$PROJECT_ID/sop-chatbot:latest']
# Deploy container image to Cloud Run
- name: 'gcr.io/cloud-builders/gcloud'
  args:
  - 'run'
  - 'deploy'
  - 'sop-chatbot'
  - '--image'
  - 'gcr.io/$PROJECT_ID/sop-chatbot:latest'
  - '--region'
  - 'us-central1'
  - '--platform'
  - 'managed'
  - '--allow-unauthenticated'
  - '--memory'
  - '2Gi'
  - '--cpu'
  - '2'
  - '--max-instances'
  - '10'
images:
- 'gcr.io/$PROJECT_ID/sop-chatbot:latest'
```

## Step 2: Cloud-Optimized Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Create directories
RUN mkdir -p chroma_db

# Use Cloud Run's PORT environment variable
EXPOSE $PORT

# Start command that uses Cloud Run's PORT
CMD streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

## Step 3: Deploy Commands
```bash
# Set up gcloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and deploy
gcloud builds submit --config cloudbuild.yaml

# Set environment variables
gcloud run services update sop-chatbot \
    --region us-central1 \
    --set-env-vars OLLAMA_HOST=YOUR_OLLAMA_URL
```

## Estimated Cost: $5-20/month (usage-based)