# SOP Assistant - Cloud Deployment Guide

## Prerequisites
- GitHub account
- Streamlit Cloud account (free at https://share.streamlit.io)
- OpenAI API key

## Deployment Steps

### 1. Prepare Repository
1. Push your code to a GitHub repository
2. Ensure all files are committed:
   - `app.py` (main application)
   - `sop_fetcher.py` (SOP management)
   - `requirements.txt` (dependencies)
   - `.streamlit/config.toml` (Streamlit configuration)
   - `.streamlit/secrets.toml` (template - DO NOT commit with real API key)

### 2. Deploy to Streamlit Cloud
1. Go to https://share.streamlit.io
2. Click "New app"
3. Connect your GitHub repository
4. Select the repository containing your SOP Assistant
5. Set the main file path: `app.py`
6. Click "Deploy"

### 3. Configure Secrets
1. In Streamlit Cloud, go to your app settings
2. Click on "Secrets" tab
3. Add the following secret:
   ```
   OPENAI_API_KEY = "your-actual-openai-api-key-here"
   ```
4. Save the secrets

### 4. Important Notes
- The app will create a `chroma_db` directory for vector storage
- The `sop_metadata.json` file will be created for tracking SOPs
- Initial SOP indexing will need to be done after deployment
- The app supports multiple file uploads (PDF, DOCX, TXT)

### 5. Post-Deployment
1. Visit your deployed app URL
2. Test the file upload functionality
3. Use the "Fetch SOPs" button to index your documents
4. Verify chat functionality works properly

## File Structure
```
sopchatbot/
├── app.py                 # Main Streamlit application
├── sop_fetcher.py         # SOP management and indexing
├── requirements.txt       # Python dependencies
├── .streamlit/
│   ├── config.toml       # Streamlit configuration
│   └── secrets.toml      # Secrets template (don't commit real keys)
├── chroma_db/            # Vector database (created at runtime)
└── sop_metadata.json     # SOP tracking metadata (created at runtime)
```

## Troubleshooting
- If deployment fails, check the logs in Streamlit Cloud
- Ensure your OpenAI API key is valid and has sufficient credits
- Verify all dependencies are listed in requirements.txt
- Check that file paths are correct in the code