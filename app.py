#!/usr/bin/env python3
"""
SOP Assistant - Apple-Inspired UI Design
Clean, minimal, and elegant interface following Apple's design principles
"""

import os
import streamlit as st
from pathlib import Path
import time
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import json
from datetime import datetime
from openai import OpenAI
import docx
import PyPDF2
import io
from sop_fetcher import SOPFetcher

# Fix for ChromaDB SQLite version issue
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class SOPAssistant:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        if 'embedding_model' not in st.session_state:
            st.session_state.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_model = st.session_state.embedding_model
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.chroma_client.get_or_create_collection("sop_documents")
    
    def extract_text_from_file(self, uploaded_file):
        """Extract text from uploaded document"""
        try:
            if uploaded_file.type == "application/pdf":
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
            
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                doc = docx.Document(io.BytesIO(uploaded_file.read()))
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            
            elif uploaded_file.type == "text/plain":
                return str(uploaded_file.read(), "utf-8")
            
            else:
                return "Unsupported file type"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def search_sops(self, query: str) -> List[Dict]:
        try:
            embedding = self.embedding_model.encode(query)
            results = self.collection.query(
                query_embeddings=[embedding.tolist()],
                n_results=5,
                include=['documents', 'metadatas', 'distances']
            )
            
            return [{
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'similarity': 1 - results['distances'][0][i]
            } for i in range(len(results['documents'][0]))]
        except:
            return []
    
    def generate_response(self, query: str, chunks: List[Dict], uploaded_context: str = "", total_sops: int = 0, conversation_history: List[Dict] = None):
        context = ""
        
        # Add uploaded document context first (higher priority)
        if uploaded_context:
            context += f"UPLOADED DOCUMENTS FROM USER:\n{uploaded_context[:12000]}\n\n"
        
        # Add SOP context (expand context size)
        if chunks:
            context += "SOP DATABASE DOCUMENTS:\n" + "\n\n".join([
                f"Document: {chunk['metadata']['source']}\n{chunk['text'][:800]}"
                for chunk in chunks[:5]
            ])
        
        # Check if query is asking for total count
        if any(phrase in query.lower() for phrase in ["how many", "total count", "number of sop", "count of sop"]) and total_sops > 0:
            context = f"IMPORTANT: The total number of SOPs in the system is {total_sops}.\n\n" + context
        
        # Build conversation context
        conversation_context = ""
        if conversation_history and len(conversation_history) > 0:
            conversation_context = "PREVIOUS CONVERSATION CONTEXT:\n"
            # Include last 4 messages (2 exchanges) for context
            recent_messages = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
            for msg in recent_messages:
                role = "User" if msg["role"] == "user" else "Assistant"
                content = msg["content"][:600] + "..." if len(msg["content"]) > 600 else msg["content"]
                conversation_context += f"{role}: {content}\n\n"
            conversation_context += "---\n\n"
        
        # Create comprehensive prompt
        if uploaded_context and chunks:
            prompt = f"""{conversation_context}You are a professional SOP assistant with access to uploaded documents and SOP database. 

Current question: "{query}"

{context}

Instructions:
1. Consider the conversation history above when answering
2. Provide EXTREMELY comprehensive, detailed responses (aim for 500-2000+ words - be thorough!)
3. If uploaded documents are available, prioritize them but also reference SOPs when relevant
4. Give specific examples, step-by-step guidance, and practical implementation details
5. Reference specific documents you're using and quote relevant sections
6. If this is a follow-up question, acknowledge previous context and build upon it extensively
7. Include background information, context, best practices, and potential pitfalls
8. Use multiple sections, bullet points, numbered lists, and detailed explanations"""
        
        elif uploaded_context:
            doc_count = uploaded_context.count("=== DOCUMENT")
            doc_text = "documents" if doc_count > 1 else "document"
            
            prompt = f"""{conversation_context}You are analyzing {doc_count} uploaded {doc_text}.

Current question: "{query}"

{context}

Instructions:
1. Consider the conversation history above when answering
2. Provide EXTREMELY comprehensive, detailed analysis (aim for 500-2000+ words - be thorough!)
3. Analyze the uploaded {doc_text} thoroughly with deep insights
4. Give specific details, examples, and quotes from the documents
5. If this is a follow-up question, build upon previous responses extensively
6. Structure your response with clear headings, bullet points, and multiple sections
7. Include context, implications, best practices, and actionable recommendations
8. Provide detailed explanations and comprehensive coverage of all relevant aspects"""
        
        elif chunks:
            prompt = f"""{conversation_context}You are a professional SOP assistant.

Current question: "{query}"

{context}

Instructions:
1. Consider the conversation history above when answering
2. Provide EXTREMELY comprehensive, detailed responses (aim for 500-2000+ words - be thorough!)
3. Give specific step-by-step procedures with detailed explanations
4. Reference the SOP documents you're using and quote relevant sections
5. If this is a follow-up question, acknowledge and build upon previous context extensively
6. Include practical examples, tips, best practices, and potential challenges
7. Provide background context, detailed explanations, and comprehensive coverage
8. Use multiple sections, bullet points, and structured formatting for clarity"""
        
        else:
            prompt = f"""{conversation_context}You are a professional SOP assistant.

Current question: "{query}"

Instructions:
1. Consider the conversation history above when answering
2. Provide helpful guidance based on general SOP best practices
3. Give EXTREMELY comprehensive responses (aim for 500-2000+ words - be thorough!)
4. If this is a follow-up question, acknowledge previous context extensively
5. Include detailed explanations, best practices, and comprehensive guidance
6. Use multiple sections, examples, and structured formatting for clarity
7. Ask clarifying questions if needed, but provide extensive information regardless"""
        
        return prompt

    def stream_response(self, messages: List[Dict], model: str = "gpt-4o-mini"):
        try:
            # Set max tokens based on model
            max_tokens = 16000 if "gpt-4o" in model else 4000  # Max out the tokens
            
            stream = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                temperature=0.3,
                max_tokens=max_tokens,  # Maxed out token limit
                top_p=0.9
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"Error: {str(e)}"

def load_chat_sessions():
    try:
        if Path("chat_sessions.json").exists():
            with open("chat_sessions.json", 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_chat_sessions(chat_sessions):
    try:
        with open("chat_sessions.json", 'w') as f:
            json.dump(chat_sessions, f, indent=2)
    except:
        pass

def generate_chat_title(message: str) -> str:
    msg = message.lower()
    if "how many" in msg: return "SOP Count Query"
    elif "invoice" in msg: return "Invoice Process"
    elif "payment" in msg: return "Payment Procedures"
    elif "check" in msg: return "Check Process"
    elif "payable" in msg: return "Accounts Payable"
    else: return " ".join(message.split()[:4]) + "..."

def main():
    st.set_page_config(
        page_title="SOP Intelligence Hub",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apple-inspired CSS styling
    st.markdown("""
    <style>
    /* Import SF Pro font family (fallback to system fonts) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Reset and base styles */
    * {
        font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* Root variables (Apple-like color system) */
    :root {
        --primary-blue: #007AFF;
        --primary-blue-hover: #0056CC;
        --secondary-blue: #F0F8FF;
        --gray-1: #F2F2F7;
        --gray-2: #E5E5EA;
        --gray-3: #D1D1D6;
        --gray-4: #C7C7CC;
        --gray-5: #AEAEB2;
        --gray-6: #8E8E93;
        --text-primary: #1D1D1F;
        --text-secondary: #86868B;
        --background: #FFFFFF;
        --surface: #FBFBFD;
        --border: rgba(0, 0, 0, 0.1);
        --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.1);
        --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.12);
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --blur: blur(20px);
    }
    
    /* App background */
    .stApp {
        background: var(--surface);
        min-height: 100vh;
    }
    
    /* Main container reset */
    .main .block-container {
        padding: 1rem 2rem !important;
        padding-bottom: 120px !important;
        margin: 0 !important;
        max-width: none !important;
        width: 100% !important;
        background: none !important;
    }
    
    /* Sidebar styling (Apple-like) */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.8) !important;
        backdrop-filter: var(--blur) !important;
        border-right: 1px solid var(--border) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: transparent !important;
        padding-top: 1rem !important;
    }
    
    /* Typography system */
    h1 {
        font-size: 2.125rem !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        letter-spacing: -0.02em !important;
        color: var(--text-primary) !important;
        margin-bottom: 0.5rem !important;
    }
    
    h2 {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        line-height: 1.3 !important;
        color: var(--text-primary) !important;
        margin-bottom: 1rem !important;
    }
    
    h3 {
        font-size: 1.125rem !important;
        font-weight: 600 !important;
        line-height: 1.4 !important;
        color: var(--text-primary) !important;
        margin-bottom: 0.75rem !important;
    }
    
    p, div, span, label {
        color: var(--text-primary) !important;
        font-size: 0.9375rem !important;
        line-height: 1.5 !important;
        font-weight: 400 !important;
    }
    
    /* Header design */
    .app-header {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: var(--blur);
        border-bottom: 1px solid var(--border);
        padding: 1rem 2rem;
        position: sticky;
        top: 0;
        z-index: 100;
        margin-bottom: 0;
    }
    
    .header-content {
        max-width: 1200px;
        margin: 0 auto;
        text-align: center;
    }
    
    .header-subtitle {
        color: var(--text-secondary) !important;
        font-size: 1rem !important;
        font-weight: 400 !important;
        margin-top: 0.25rem !important;
    }
    
    /* Button system (Apple-like) */
    .stButton > button {
        background: var(--primary-blue) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        padding: 0.75rem 1.25rem !important;
        font-weight: 500 !important;
        font-size: 0.9375rem !important;
        line-height: 1 !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: var(--shadow-sm) !important;
        cursor: pointer !important;
        min-height: auto !important;
        height: auto !important;
    }
    
    .stButton > button:hover {
        background: var(--primary-blue-hover) !important;
        transform: translateY(-1px) !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    /* Secondary buttons (chat history) */
    .stButton > button[kind="secondary"] {
        background: var(--background) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--gray-2) !important;
        box-shadow: none !important;
        text-align: left !important;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background: var(--gray-1) !important;
        border-color: var(--gray-3) !important;
        transform: none !important;
    }
    
    /* Primary button variant for active states */
    .stButton > button[type="primary"] {
        background: var(--primary-blue) !important;
        color: white !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    /* Chat message containers */
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 1rem 2rem;
    }
    
    .message-container {
        margin-bottom: 1.5rem;
        animation: slideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* User messages */
    .user-message {
        background: var(--primary-blue) !important;
        color: white !important;
        padding: 1rem 1.25rem !important;
        border-radius: var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg) !important;
        margin: 0 0 0 20% !important;
        box-shadow: var(--shadow-md) !important;
        position: relative !important;
    }
    
    .user-message * {
        color: white !important;
    }
    
    /* Assistant messages */
    .assistant-message {
        background: var(--background) !important;
        color: var(--text-primary) !important;
        padding: 1rem 1.25rem !important;
        border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm) !important;
        margin: 0 20% 0 0 !important;
        box-shadow: var(--shadow-md) !important;
        border: 1px solid var(--gray-2) !important;
        position: relative !important;
    }
    
    .assistant-message * {
        color: var(--text-primary) !important;
    }
    
    /* Welcome message */
    .welcome-container {
        background: var(--background);
        border-radius: var(--radius-lg);
        padding: 2rem;
        margin: 2rem auto;
        max-width: 600px;
        text-align: center;
        box-shadow: var(--shadow-md);
        border: 1px solid var(--gray-2);
    }
    
    .welcome-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin-top: 1.5rem;
    }
    
    .suggestion-button {
        background: var(--gray-1) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--gray-3) !important;
        border-radius: var(--radius-md) !important;
        padding: 1rem !important;
        font-weight: 500 !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        text-align: left !important;
        min-height: auto !important;
        height: auto !important;
    }
    
    .suggestion-button:hover {
        background: var(--secondary-blue) !important;
        border-color: var(--primary-blue) !important;
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    /* Source cards */
    .source-card {
        background: var(--secondary-blue) !important;
        border: 1px solid rgba(0, 122, 255, 0.2) !important;
        border-radius: var(--radius-md) !important;
        padding: 0.875rem 1rem !important;
        margin: 0.5rem 0 !important;
        color: var(--primary-blue) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        box-shadow: var(--shadow-sm) !important;
        border-left: 3px solid var(--primary-blue) !important;
    }
    
    .source-card * {
        color: var(--primary-blue) !important;
    }
    
    /* Input area */
    .input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: var(--blur);
        border-top: 1px solid var(--border);
        padding: 1rem 2rem 1.5rem;
        z-index: 100;
    }
    
    .input-inner {
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* File uploader styling */
    .stFileUploader {
        margin-bottom: 1rem !important;
    }
    
    .stFileUploader > div {
        background: var(--gray-1) !important;
        border: 2px dashed var(--gray-4) !important;
        border-radius: var(--radius-md) !important;
        padding: 1rem !important;
        text-align: center !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stFileUploader > div:hover {
        background: var(--secondary-blue) !important;
        border-color: var(--primary-blue) !important;
    }
    
    .stFileUploader label {
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
    }
    
    /* Text area input */
    .stTextArea > div > div > textarea {
        background: var(--background) !important;
        border: 2px solid var(--gray-3) !important;
        border-radius: var(--radius-md) !important;
        padding: 1rem !important;
        font-size: 0.9375rem !important;
        line-height: 1.5 !important;
        color: var(--text-primary) !important;
        resize: none !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary-blue) !important;
        box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1) !important;
        outline: none !important;
    }
    
    .stTextArea > div > div > textarea::placeholder {
        color: var(--text-secondary) !important;
        font-weight: 400 !important;
    }
    
    /* Sidebar chat list */
    .chat-list-item {
        margin-bottom: 0.5rem !important;
    }
    
    .chat-list-item button {
        width: 100% !important;
        text-align: left !important;
        padding: 0.75rem 1rem !important;
        border-radius: var(--radius-md) !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    
    /* Metrics styling */
    .stMetric {
        background: var(--background) !important;
        border-radius: var(--radius-md) !important;
        padding: 1rem !important;
        border: 1px solid var(--gray-2) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    .stMetric > div {
        text-align: center !important;
    }
    
    .stMetric label {
        color: var(--text-secondary) !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    
    .stMetric > div > div {
        color: var(--text-primary) !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        margin-top: 0.25rem !important;
    }
    
    /* Selectbox styling */
    .stSelectbox > div > div {
        background: var(--background) !important;
        border: 1px solid var(--gray-3) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    .stSelectbox label {
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Success/info messages */
    .stSuccess {
        background: rgba(52, 199, 89, 0.1) !important;
        color: #1B5E20 !important;
        border: 1px solid rgba(52, 199, 89, 0.3) !important;
        border-radius: var(--radius-md) !important;
        padding: 1rem !important;
        font-weight: 500 !important;
    }
    
    .stInfo {
        background: var(--secondary-blue) !important;
        color: var(--primary-blue) !important;
        border: 1px solid rgba(0, 122, 255, 0.3) !important;
        border-radius: var(--radius-md) !important;
        padding: 1rem !important;
        font-weight: 500 !important;
    }
    
    /* Edit button styling */
    .edit-button {
        background: var(--gray-1) !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--gray-3) !important;
        border-radius: 50% !important;
        width: 32px !important;
        height: 32px !important;
        padding: 0 !important;
        font-size: 0.75rem !important;
        margin-top: 0.5rem !important;
    }
    
    .edit-button:hover {
        background: var(--gray-2) !important;
        color: var(--text-primary) !important;
    }
    
    /* Delete/Clear buttons in sidebar */
    [data-testid="stSidebar"] .stButton > button[key*="delete_"],
    [data-testid="stSidebar"] .stButton > button[key="clear_all_chats"] {
        background: transparent !important;
        color: var(--text-secondary) !important;
        border: 1px solid transparent !important;
        padding: 0.25rem !important;
        min-height: 32px !important;
        font-size: 0.875rem !important;
    }
    
    [data-testid="stSidebar"] .stButton > button[key*="delete_"]:hover,
    [data-testid="stSidebar"] .stButton > button[key="clear_all_chats"]:hover {
        background: rgba(255, 59, 48, 0.1) !important;
        color: #FF3B30 !important;
        border-color: rgba(255, 59, 48, 0.2) !important;
    }
    
    /* Clear current chat button */
    .stButton > button[key="clear_current_chat"] {
        background: transparent !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--gray-3) !important;
        padding: 0.5rem !important;
        min-height: 36px !important;
        font-size: 1rem !important;
        float: right !important;
    }
    
    .stButton > button[key="clear_current_chat"]:hover {
        background: rgba(255, 59, 48, 0.1) !important;
        color: #FF3B30 !important;
        border-color: rgba(255, 59, 48, 0.2) !important;
    }
    
    
    /* Scrollable chat area */
    .chat-messages {
        max-height: calc(100vh - 250px);
        overflow-y: auto;
        padding-right: 0.5rem;
    }
    
    /* Custom scrollbar */
    .chat-messages::-webkit-scrollbar {
        width: 6px;
    }
    
    .chat-messages::-webkit-scrollbar-track {
        background: var(--gray-1);
        border-radius: 3px;
    }
    
    .chat-messages::-webkit-scrollbar-thumb {
        background: var(--gray-4);
        border-radius: 3px;
    }
    
    .chat-messages::-webkit-scrollbar-thumb:hover {
        background: var(--gray-5);
    }
    
    /* Hide Streamlit elements in sidebar */
    .css-1y4p8pa {
        padding-top: 1rem !important;
    }
    
    /* Hide the form submit button completely */
    [data-testid="stForm"] button {
        display: none !important;
    }
    
    [data-testid="stForm"] > div > div > div > div > button {
        display: none !important;
    }
    
    /* SOP Fetch Section */
    .sop-fetch-info {
        background: var(--gray-1);
        border-radius: var(--radius-md);
        padding: 0.75rem;
        margin: 0.5rem 0;
        font-size: 0.875rem;
        color: var(--text-secondary);
    }
    
    .sop-fetch-warning {
        background: rgba(255, 149, 0, 0.1);
        color: #FF6B00;
        border: 1px solid rgba(255, 149, 0, 0.3);
        border-radius: var(--radius-md);
        padding: 0.75rem;
        margin: 0.5rem 0;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .user-message {
            margin: 0 0 0 10% !important;
        }
        
        .assistant-message {
            margin: 0 10% 0 0 !important;
        }
        
        .welcome-grid {
            grid-template-columns: 1fr !important;
        }
        
        .input-container {
            padding: 1rem !important;
        }
        
        .chat-container {
            padding: 1rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check API key
    if not os.environ.get('OPENAI_API_KEY'):
        st.error("⚠️ OpenAI API key required")
        st.stop()
    
    # Initialize
    if 'assistant' not in st.session_state:
        with st.spinner("Loading SOP Assistant..."):
            st.session_state.assistant = SOPAssistant()
    
    if 'chat_sessions' not in st.session_state:
        st.session_state.chat_sessions = load_chat_sessions()
    
    if 'current_chat_id' not in st.session_state:
        if st.session_state.chat_sessions:
            st.session_state.current_chat_id = list(st.session_state.chat_sessions.keys())[0]
        else:
            chat_id = f"chat_{int(time.time())}"
            st.session_state.chat_sessions[chat_id] = {
                'title': 'New Chat',
                'messages': [],
                'created': datetime.now().isoformat()
            }
            st.session_state.current_chat_id = chat_id
    
    # Get stats
    try:
        collection = chromadb.PersistentClient(path="./chroma_db").get_or_create_collection("sop_documents")
        chunk_count = collection.count()
        if chunk_count > 0:
            metadata = collection.get(include=['metadatas'])
            sop_count = len(set(m.get('source', '') for m in metadata['metadatas']))
        else:
            sop_count = 0
    except:
        sop_count = 0
    
    # Header
    st.markdown("""
    <div class="app-header">
        <div class="header-content">
            <h1>🚀 SOP Intelligence Hub</h1>
            <p class="header-subtitle">Advanced AI-Powered Standard Operating Procedure Assistant | Comprehensive Analysis & Expert Guidance</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar with creative grouping
    with st.sidebar:
        # Header section
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0; margin-bottom: 1rem;">
            <h2 style="margin: 0; color: var(--text-primary); font-size: 1.25rem;">🚀 Intelligence Hub</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Chat Management Section
        with st.container():
            st.markdown("**💬 Conversations**")
            
            # New Chat Button
            if st.button("+ New Chat", use_container_width=True, key="new_chat_btn"):
                chat_id = f"chat_{int(time.time())}"
                st.session_state.chat_sessions[chat_id] = {
                    'title': 'New Chat',
                    'messages': [],
                    'created': datetime.now().isoformat()
                }
                st.session_state.current_chat_id = chat_id
                save_chat_sessions(st.session_state.chat_sessions)
                st.rerun()
            
            # Clear all button
            col_title, col_clear = st.columns([3, 1])
            with col_clear:
                if st.button("🗑️", key="clear_all_chats", help="Clear all chats"):
                    if 'confirm_clear_all' not in st.session_state:
                        st.session_state.confirm_clear_all = True
                        st.rerun()
            
            # Confirmation for clear all
            if 'confirm_clear_all' in st.session_state and st.session_state.confirm_clear_all:
                st.warning("⚠️ Delete all chat history?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("Yes", key="confirm_yes", type="primary"):
                        # Create a new default chat
                        chat_id = f"chat_{int(time.time())}"
                        st.session_state.chat_sessions = {
                            chat_id: {
                                'title': 'New Chat',
                                'messages': [],
                                'created': datetime.now().isoformat()
                            }
                        }
                        st.session_state.current_chat_id = chat_id
                        save_chat_sessions(st.session_state.chat_sessions)
                        del st.session_state.confirm_clear_all
                        st.rerun()
                with col_no:
                    if st.button("No", key="confirm_no"):
                        del st.session_state.confirm_clear_all
                        st.rerun()
            
            # Individual chats (only show chats with messages)
            for chat_id, chat_data in st.session_state.chat_sessions.items():
                # Skip empty chats unless it's the only one or the current active chat
                if not chat_data.get('messages', []) and len(st.session_state.chat_sessions) > 1 and chat_id != st.session_state.current_chat_id:
                    continue
                    
                is_active = st.session_state.current_chat_id == chat_id
                title = chat_data.get('title', 'Untitled Chat')
                
                col1, col2 = st.columns([5, 1])
                with col1:
                    if st.button(
                        title,
                        key=f"chat_{chat_id}",
                        use_container_width=True,
                        type="secondary"
                    ):
                        st.session_state.current_chat_id = chat_id
                        st.rerun()
                
                with col2:
                    # Only show delete button if we have more than one chat
                    if len(st.session_state.chat_sessions) > 1:
                        if st.button("🗑️", key=f"delete_{chat_id}", help=f"Delete '{title}'"):
                            # Delete the chat
                            del st.session_state.chat_sessions[chat_id]
                            
                            # If we deleted the current chat, switch to another
                            if st.session_state.current_chat_id == chat_id:
                                st.session_state.current_chat_id = list(st.session_state.chat_sessions.keys())[0]
                            
                            save_chat_sessions(st.session_state.chat_sessions)
                            st.rerun()
        
        st.markdown("---")
        
        # AI Configuration Section
        with st.container():
            st.markdown("**🤖 AI Configuration**")
            model_options = {
                "GPT-4o": "gpt-4o",
                "GPT-4o-mini": "gpt-4o-mini", 
                "GPT-4 Turbo": "gpt-4-turbo",
                "GPT-3.5 Turbo": "gpt-3.5-turbo"
            }
            
            if 'selected_model' not in st.session_state:
                st.session_state.selected_model = "gpt-4o-mini"
            
            selected_model_name = st.selectbox(
                "Model:",
                options=list(model_options.keys()),
                index=list(model_options.values()).index(st.session_state.selected_model),
                label_visibility="collapsed"
            )
            st.session_state.selected_model = model_options[selected_model_name]
        
        st.markdown("---")
        
        # SOP Management Section
        with st.container():
            st.markdown("**🔄 SOP Management**")
            
            # Initialize fetcher
            if 'sop_fetcher' not in st.session_state:
                st.session_state.sop_fetcher = SOPFetcher()
            
            # Get fetch status
            fetch_status = st.session_state.sop_fetcher.get_fetch_status()
            
            # Display last fetch info
            if fetch_status["last_fetch"]:
                st.caption(f"📅 {fetch_status['last_fetch_formatted']}")
                st.caption(f"📁 {fetch_status['total_files']} files indexed")
                
                # Check for updates
                if fetch_status["needs_update"]:
                    st.warning("⚠️ Updates available")
            else:
                st.info("📁 No SOPs indexed yet")
            
            # Fetch button
            if st.button("🔄 Sync SOPs", use_container_width=True, key="fetch_sops_btn"):
                with st.spinner("Analyzing SOP directory..."):
                    # Analyze what needs to be done
                    new_files, modified_files, deleted_files = st.session_state.sop_fetcher.analyze_directory()
                    
                    # Show preview
                    total_changes = len(new_files) + len(modified_files) + len(deleted_files)
                    
                    if total_changes > 0:
                        st.info(f"Found {len(new_files)} new, {len(modified_files)} modified, {len(deleted_files)} deleted files")
                        
                        # Progress bar for fetching
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        def update_progress(progress, message):
                            progress_bar.progress(progress)
                            status_text.text(message)
                        
                        # Fetch and index
                        results = st.session_state.sop_fetcher.fetch_and_index_sops(update_progress)
                        
                        # Clear progress indicators
                        progress_bar.empty()
                        status_text.empty()
                        
                        # Show results
                        if results["errors"]:
                            st.error(f"Completed with {len(results['errors'])} errors")
                            for error in results["errors"][:5]:  # Show first 5 errors
                                st.caption(error)
                        else:
                            st.success(f"✅ Successfully processed {results['total_processed']} files!")
                        
                        # Update the SOP count
                        collection = chromadb.PersistentClient(path="./chroma_db").get_or_create_collection("sop_documents")
                        metadata = collection.get(include=['metadatas'])
                        sop_count = len(set(m.get('source', '') for m in metadata['metadatas']))
                        
                        st.rerun()
                    else:
                        st.success("✅ All SOPs are up to date!")
        
        st.markdown("---")
        
        # Documents in current chat
        current_chat = st.session_state.chat_sessions[st.session_state.current_chat_id]
        if 'documents' in current_chat and current_chat['documents']:
            with st.container():
                st.markdown("**📄 Session Documents**")
                for doc_name in current_chat['documents'].keys():
                    st.markdown(f"📎 {doc_name}", help=f"Attached to this chat")
            st.markdown("---")
        
        # Statistics at the bottom
        st.markdown("---")
        with st.container():
            st.markdown("**📊 Statistics**")
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("SOPs", sop_count, label_visibility="collapsed")
                st.caption("📚 Total SOPs")
            with col_stat2:
                st.metric("Model", selected_model_name.replace('GPT-', ''), label_visibility="collapsed")
                st.caption("🧠 AI Model")
    
    # Main content area
    # Messages
    current_chat = st.session_state.chat_sessions[st.session_state.current_chat_id]
    
    if not current_chat['messages']:
        # Welcome message
        st.markdown("""
        <div class="welcome-container">
            <h3>🚀 Welcome to SOP Intelligence Hub</h3>
            <p>Your advanced AI-powered assistant for comprehensive Standard Operating Procedure analysis, guidance, and expert consultation. Upload documents for deep analysis or ask questions for detailed, professional insights.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Suggestion buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 How many SOPs do we have?", key="q1", help="Get SOP count"):
                st.session_state.temp_query = "How many SOPs do we have?"
                st.rerun()
            if st.button("💳 How do I process an invoice?", key="q2", help="Invoice procedures"):
                st.session_state.temp_query = "How do I process an invoice?"
                st.rerun()
        with col2:
            if st.button("💰 What are payment procedures?", key="q3", help="Payment process"):
                st.session_state.temp_query = "What are payment procedures?"
                st.rerun()
            if st.button("📋 Show accounts payable process", key="q4", help="AP process"):
                st.session_state.temp_query = "Show accounts payable process"
                st.rerun()
    else:
        # Clear current chat button
        col_space, col_clear = st.columns([10, 1])
        with col_clear:
            if st.button("🗑️", key="clear_current_chat", help="Clear this chat"):
                current_chat['messages'] = []
                current_chat['title'] = 'New Chat'
                save_chat_sessions(st.session_state.chat_sessions)
                st.rerun()
        
        # Chat messages
        st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
        
        for i, msg in enumerate(current_chat['messages']):
            st.markdown('<div class="message-container">', unsafe_allow_html=True)
            
            if msg["role"] == "user":
                # User message with edit functionality
                col_msg, col_edit = st.columns([20, 1])
                with col_msg:
                    st.markdown(f"""
                    <div class="user-message">
                        <strong>You</strong><br>{msg["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                with col_edit:
                    if st.button("✏️", key=f"edit_{i}", help="Edit message"):
                        st.session_state.editing_message = i
                        st.session_state.edit_content = msg["content"]
                        st.rerun()
                
                # Edit interface
                if 'editing_message' in st.session_state and st.session_state.editing_message == i:
                    st.text_area("Edit your message:", 
                               value=st.session_state.edit_content, 
                               key=f"edit_text_{i}",
                               height=100)
                    
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("💾 Save", key=f"save_{i}"):
                            new_content = st.session_state[f"edit_text_{i}"]
                            if new_content.strip():
                                # Update and regenerate
                                current_chat['messages'][i]['content'] = new_content
                                current_chat['messages'] = current_chat['messages'][:i+1]
                                
                                del st.session_state.editing_message
                                del st.session_state.edit_content
                                
                                save_chat_sessions(st.session_state.chat_sessions)
                                
                                # Regenerate response
                                with st.spinner("Regenerating response..."):
                                    uploaded_context_edit = ""
                                    document_sources_edit = []
                                    
                                    sop_chunks = st.session_state.assistant.search_sops(new_content)
                                    all_sources_edit = document_sources_edit + sop_chunks
                                    
                                    # Get conversation history up to the edited message
                                    conversation_history_edit = current_chat['messages'][:i] if i > 0 else []
                                    
                                    ai_prompt = st.session_state.assistant.generate_response(
                                        new_content, sop_chunks, uploaded_context_edit, sop_count, conversation_history_edit
                                    )
                                    
                                    # Build message array for OpenAI API
                                    messages_edit = [
                                        {"role": "system", "content": """You are a professional SOP assistant. Your responses should be:
- EXTREMELY comprehensive and detailed (aim for 500-2000+ words - be as thorough as possible!)
- Conversational and engaging, acknowledging previous context extensively
- Well-structured with multiple clear headings, bullet points, numbered lists, and detailed examples
- Practical with comprehensive step-by-step guidance and implementation details
- Reference specific documents and sources, including relevant quotes
- Build upon previous conversation context naturally and extensively
- Include background information, context, best practices, potential pitfalls, and comprehensive explanations
- Use detailed formatting with sections, subsections, and thorough coverage of all aspects
- Never be brief - always provide maximum detail and comprehensive coverage"""},
                                        {"role": "user", "content": ai_prompt}
                                    ]
                                    
                                    response_placeholder = st.empty()
                                    full_response = ""
                                    
                                    for token in st.session_state.assistant.stream_response(messages_edit, st.session_state.selected_model):
                                        full_response += token
                                        response_placeholder.markdown(f"""
                                        <div class="assistant-message">
                                            <strong>SOP Assistant</strong><br>{full_response}▌
                                        </div>
                                        """, unsafe_allow_html=True)
                                    
                                    current_chat['messages'].append({
                                        "role": "assistant",
                                        "content": full_response,
                                        "sources": all_sources_edit
                                    })
                                
                                save_chat_sessions(st.session_state.chat_sessions)
                                st.rerun()
                    
                    with col_cancel:
                        if st.button("❌ Cancel", key=f"cancel_{i}"):
                            del st.session_state.editing_message
                            del st.session_state.edit_content
                            st.rerun()
            
            else:
                # Assistant message
                st.markdown(f"""
                <div class="assistant-message">
                    <strong>SOP Assistant</strong><br>{msg["content"]}
                </div>
                """, unsafe_allow_html=True)
                
                # Sources
                if "sources" in msg and msg["sources"]:
                    st.markdown("**📚 Source Documents:**")
                    
                    unique_sources = set()
                    for chunk in msg["sources"]:
                        source_name = chunk['metadata']['source']
                        if source_name not in unique_sources:
                            unique_sources.add(source_name)
                            st.markdown(f"""
                            <div class="source-card">
                                📄 {source_name}
                            </div>
                            """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)  # Close message-container
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close chat-messages
    
    # Fixed input area at bottom (always show regardless of chat state)
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    st.markdown('<div class="input-inner">', unsafe_allow_html=True)
    
    # Input layout: text area on left, file upload on right
    col_input, col_upload = st.columns([4, 1])
    
    with col_upload:
        uploaded_files = st.file_uploader(
            "📎",
            type=['pdf', 'docx', 'txt'],
            key=f"chat_uploader_{st.session_state.current_chat_id}",
            help="Upload PDF, Word, or text files",
            label_visibility="collapsed",
            accept_multiple_files=True
        )
    
    with col_input:
        # Show attachment status
        if uploaded_files:
            if len(uploaded_files) == 1:
                st.success(f"📎 {uploaded_files[0].name}")
            else:
                st.success(f"📎 {len(uploaded_files)} files attached")
                with st.expander("View attached files"):
                    for file in uploaded_files:
                        st.markdown(f"• {file.name}")
        
        # Use form to capture Enter key (no visible button)
        with st.form(key="chat_form", clear_on_submit=True):
            prompt = st.text_area(
                "Message",
                placeholder="Ask about your SOPs... (Press Enter to send)",
                height=60,
                key="chat_input",
                label_visibility="collapsed"
            )
            # Completely hidden submit button 
            send_clicked = st.form_submit_button("", use_container_width=False, disabled=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close input-inner
    st.markdown('</div>', unsafe_allow_html=True)  # Close input-container
    
    # Process message
    if send_clicked and prompt.strip():
        prompt = prompt.strip()
        current_chat = st.session_state.chat_sessions[st.session_state.current_chat_id]
        
        # Get uploaded files context if available
        uploaded_context = ""
        uploaded_file_names = []
        document_sources = []
        
        if uploaded_files:
            with st.spinner(f"Processing {len(uploaded_files)} uploaded document(s)..."):
                all_contexts = []
                
                if 'documents' not in current_chat:
                    current_chat['documents'] = {}
                
                for i, uploaded_file in enumerate(uploaded_files, 1):
                    file_context = st.session_state.assistant.extract_text_from_file(uploaded_file)
                    file_name = uploaded_file.name
                    
                    # Store each document
                    current_chat['documents'][file_name] = file_context
                    uploaded_file_names.append(file_name)
                    
                    # Format each document clearly with separators
                    formatted_doc = f"""
=== DOCUMENT {i} OF {len(uploaded_files)}: {file_name} ===
{file_context}
=== END OF DOCUMENT {i} ==="""
                    
                    all_contexts.append(formatted_doc)
                    
                    # Add to document sources with high priority
                    document_sources.append({
                        'text': file_context[:500] + "..." if len(file_context) > 500 else file_context,
                        'metadata': {'source': file_name, 'type': 'uploaded_document'},
                        'similarity': 1.0
                    })
                
                # Combine all uploaded document contexts with clear separators
                uploaded_context = "\n\n".join(all_contexts)
        
        # Add user message
        user_display_content = prompt
        if uploaded_file_names:
            if len(uploaded_file_names) == 1:
                user_display_content = f"{prompt}\n\n📎 **Attached:** {uploaded_file_names[0]}"
            else:
                files_list = "\n".join([f"📎 {name}" for name in uploaded_file_names])
                user_display_content = f"{prompt}\n\n**Attached files:**\n{files_list}"
        
        current_chat['messages'].append({"role": "user", "content": user_display_content})
        
        # Update title if first message
        if len(current_chat['messages']) == 1:
            current_chat['title'] = generate_chat_title(prompt)
        
        save_chat_sessions(st.session_state.chat_sessions)
        
        # Generate response
        with st.spinner("Analyzing and generating response..."):
            # If documents are uploaded, prioritize them and severely limit SOP search
            if uploaded_context:
                # For questions about uploaded documents, don't search SOPs at all
                sop_keywords = ["sop", "standard operating", "procedure", "database", "all documents"]
                if any(keyword in prompt.lower() for keyword in sop_keywords):
                    sop_chunks = st.session_state.assistant.search_sops(prompt)[:2]  # Very limited
                else:
                    sop_chunks = []  # Focus ONLY on uploaded documents
            else:
                # No uploaded documents, search SOPs normally
                sop_chunks = st.session_state.assistant.search_sops(prompt)
            
            # Check for references to previously uploaded documents
            referenced_docs = {}
            if 'documents' in current_chat and not uploaded_context:  # Only if no new files uploaded
                for doc_name, doc_content in current_chat['documents'].items():
                    if doc_name not in uploaded_file_names:  # Don't duplicate newly uploaded files
                        doc_base_name = doc_name.split('.')[0].lower()
                        prompt_lower = prompt.lower()
                        
                        if (doc_name.lower() in prompt_lower or 
                            doc_base_name in prompt_lower or
                            any(word in prompt_lower for word in doc_base_name.split('_')) or
                            any(word in prompt_lower for word in doc_base_name.split(' ')) or
                            'earlier' in prompt_lower or 
                            'previous' in prompt_lower or
                            'from before' in prompt_lower):
                            
                            referenced_docs[doc_name] = doc_content
                            document_sources.append({
                                'text': doc_content[:500] + "..." if len(doc_content) > 500 else doc_content,
                                'metadata': {'source': doc_name, 'type': 'uploaded_document'},
                                'similarity': 1.0
                            })
            
            # Combine all document contexts
            all_uploaded_context = uploaded_context
            if referenced_docs:
                for doc_name, doc_content in referenced_docs.items():
                    all_uploaded_context += f"\n\nPreviously uploaded document '{doc_name}':\n{doc_content}"
            
            # Prioritize document sources over SOP chunks
            all_sources = document_sources + sop_chunks
            
            # Get conversation history (exclude current message)
            conversation_history = current_chat['messages'][:-1] if len(current_chat['messages']) > 0 else []
            
            ai_prompt = st.session_state.assistant.generate_response(
                prompt, sop_chunks, all_uploaded_context, sop_count, conversation_history
            )
            
            # Build message array for OpenAI API
            messages = [
                {"role": "system", "content": """You are a professional SOP assistant. Your responses should be:
- EXTREMELY comprehensive and detailed (aim for 500-2000+ words - be as thorough as possible!)
- Conversational and engaging, acknowledging previous context extensively
- Well-structured with multiple clear headings, bullet points, numbered lists, and detailed examples
- Practical with comprehensive step-by-step guidance and implementation details
- Reference specific documents and sources, including relevant quotes
- Build upon previous conversation context naturally and extensively
- Include background information, context, best practices, potential pitfalls, and comprehensive explanations
- Use detailed formatting with sections, subsections, and thorough coverage of all aspects
- Never be brief - always provide maximum detail and comprehensive coverage"""},
                {"role": "user", "content": ai_prompt}
            ]
            
            # Stream response
            response_placeholder = st.empty()
            full_response = ""
            
            for token in st.session_state.assistant.stream_response(messages, st.session_state.selected_model):
                full_response += token
                response_placeholder.markdown(f"""
                <div class="assistant-message">
                    <strong>SOP Assistant</strong><br>{full_response}▌
                </div>
                """, unsafe_allow_html=True)
            
            current_chat['messages'].append({
                "role": "assistant",
                "content": full_response,
                "sources": all_sources
            })
        
        save_chat_sessions(st.session_state.chat_sessions)
        # Don't try to modify the text_area widget's state directly
        st.rerun()
    
    # Handle temp query from buttons
    if 'temp_query' in st.session_state:
        current_chat = st.session_state.chat_sessions[st.session_state.current_chat_id]
        prompt = st.session_state.temp_query
        del st.session_state.temp_query
        
        current_chat['messages'].append({"role": "user", "content": prompt})
        
        if len(current_chat['messages']) == 1:
            current_chat['title'] = generate_chat_title(prompt)
        
        save_chat_sessions(st.session_state.chat_sessions)
        st.rerun()

if __name__ == "__main__":
    main()