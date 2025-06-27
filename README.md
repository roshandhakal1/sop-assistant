# 🚀 SOP Intelligence Hub

Advanced AI-Powered Standard Operating Procedure Assistant for comprehensive analysis and expert guidance.

## 🌟 Features

- **Comprehensive AI Analysis**: 500-2000+ word detailed responses
- **Conversation Memory**: Maintains context across chat sessions
- **Document Upload**: Support for PDF, Word, and text files
- **SOP Database Integration**: ChromaDB-powered document search
- **Real-time Streaming**: Live response generation
- **Professional UI**: Apple-inspired clean design

## 🚀 Quick Deploy to Streamlit Cloud

### Method 1: One-Click Deploy (Recommended)

1. **Fork this repository** on GitHub
2. **Go to [share.streamlit.io](https://share.streamlit.io)**
3. **Click "New app"**
4. **Select your forked repository**
5. **Set main file path**: `app.py`
6. **Add your OpenAI API key** in Advanced settings → Secrets:
   ```toml
   OPENAI_API_KEY = "your-api-key-here"
   ```
7. **Click "Deploy"**

### Method 2: Manual Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/roshandhakal1/sop-assistant.git
   cd sop-assistant
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   # Create .streamlit/secrets.toml
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   # Edit secrets.toml and add your OpenAI API key
   ```

4. **Run locally**:
   ```bash
   streamlit run app.py
   ```

## 🔧 Configuration

### Required Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### Optional Configuration

- Model selection (GPT-4o, GPT-4o-mini, GPT-4 Turbo, GPT-3.5 Turbo)
- File upload limits
- Response length settings

## 📁 File Structure

```
├── app.py                    # Main Streamlit application
├── sop_fetcher.py           # SOP document processing
├── requirements.txt         # Python dependencies
├── .streamlit/
│   ├── config.toml          # Streamlit configuration
│   └── secrets.toml.example # Environment variables template
├── Dockerfile               # Docker configuration (for Railway)
├── railway.json            # Railway deployment config
└── README.md               # This file
```

## 🎯 Usage

1. **Upload Documents**: Drag and drop PDF, Word, or text files
2. **Ask Questions**: Type your question in the chat box
3. **Get Detailed Responses**: Receive comprehensive 500-2000+ word analyses
4. **Continue Conversations**: Follow up questions maintain context
5. **Manage Sessions**: Create multiple chat sessions for different topics

## 🔒 Security Notes

- API keys are stored securely in Streamlit Cloud secrets
- No data is stored permanently except chat sessions (local JSON)
- Documents are processed in memory only
- ChromaDB uses local file storage

## 🛠️ Technical Details

- **Framework**: Streamlit
- **AI Model**: OpenAI GPT-4o/GPT-4o-mini
- **Vector Database**: ChromaDB
- **Embeddings**: SentenceTransformers (all-MiniLM-L6-v2)
- **Document Processing**: PyPDF2, python-docx
- **UI Framework**: Custom CSS with Apple-inspired design

## 📞 Support

For issues or questions:
1. Check the GitHub Issues tab
2. Review Streamlit Cloud deployment logs
3. Verify your OpenAI API key is valid and has credits

## 🔄 Updating

To update your deployment:
1. Pull latest changes from the main repository
2. Push to your fork
3. Streamlit Cloud will automatically redeploy

---

**Deployed with ❤️ using Streamlit Cloud**
