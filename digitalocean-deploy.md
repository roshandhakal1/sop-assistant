# Deploy to DigitalOcean App Platform

## Why DigitalOcean?
- $12/month for both services
- Easy Docker deployment
- Automatic HTTPS and domain management
- Great for production apps

## Step 1: Prepare App Spec
Create `.do/app.yaml`:

```yaml
name: sop-chatbot
services:
- name: web
  source_dir: /
  dockerfile_path: Dockerfile
  github:
    repo: your-username/sop-chatbot
    branch: main
  instance_count: 1
  instance_size_slug: basic-xxs
  ports:
  - http_port: 8501
    published_port: 80
  envs:
  - key: OLLAMA_HOST
    value: http://ollama:11434
  routes:
  - path: /
- name: ollama
  source_dir: /
  dockerfile_path: Dockerfile.ollama
  instance_count: 1
  instance_size_slug: basic-xs
  ports:
  - http_port: 11434
```

## Step 2: Create Ollama Dockerfile
Create `Dockerfile.ollama`:

```dockerfile
FROM ollama/ollama:latest

# Pre-pull the model to reduce startup time
RUN ollama serve & \
    sleep 5 && \
    ollama pull llama3.1 && \
    pkill ollama

EXPOSE 11434
CMD ["ollama", "serve"]
```

## Step 3: Deploy
1. Go to https://cloud.digitalocean.com/apps
2. Click "Create App"
3. Connect your GitHub repository
4. DigitalOcean auto-detects the configuration
5. Deploy!

## Estimated Cost: $12/month