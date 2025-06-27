# SOP Assistant - Railway Deployment Guide

## Prerequisites
- Railway account (https://railway.app)
- GitHub account
- OpenAI API key

## Deployment Steps

### 1. Prepare Repository
1. Push your code to GitHub repository
2. The `.gitignore` file protects your SOPs folder and secrets
3. Ensure `railway.json` is included

### 2. Deploy to Railway
1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will auto-detect it's a Python project

### 3. Configure Environment Variables
In Railway dashboard, go to Variables tab and add:
```
OPENAI_API_KEY=your-actual-openai-api-key-here
PORT=8000
```

### 4. Railway Configuration
The `railway.json` file configures:
- Build process using Nixpacks
- Start command for Streamlit
- Port binding for Railway

### 5. Domain Setup
- Railway provides a custom domain automatically
- You can also connect your own domain in settings

## Important Notes
- Your SOPs folder is protected by `.gitignore` - it won't be pushed to GitHub
- You'll need to manually upload SOPs to the deployed environment or modify the path
- ChromaDB will persist on Railway's volumes
- Railway has better performance than Streamlit Cloud for larger applications

## Post-Deployment
1. Visit your Railway app URL
2. Test file upload functionality
3. Note: SOP fetching won't work until you either:
   - Upload SOPs manually to the server
   - Modify `sop_fetcher.py` to use a cloud storage solution
   - Use the file upload feature instead

## Alternative: Cloud Storage Integration
For production, consider modifying the app to:
- Store SOPs in AWS S3, Google Cloud Storage, or similar
- Use environment variables for storage paths
- Implement secure file access