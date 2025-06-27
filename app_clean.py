#!/usr/bin/env python3
"""
SOP Assistant - Clean Version
Simple, working layout with fixed sidebar
"""

import os
import streamlit as st
from pathlib import Path
import chromadb
import time
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import json
from datetime import datetime
from openai import OpenAI
import docx
import PyPDF2
import io

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
    
    def generate_response(self, query: str, chunks: List[Dict], uploaded_context: str = ""):
        if not chunks and not uploaded_context:
            return "I couldn't find relevant information in your SOPs or uploaded documents."
        
        context = ""
        
        # Add uploaded document context first (higher priority)
        if uploaded_context:
            context += f"UPLOADED DOCUMENT CONTENT:\n{uploaded_context[:3000]}\n\n"
        
        # Add SOP context
        if chunks:
            context += "RELEVANT SOP DOCUMENTS:\n" + "\n\n".join([
                f"Document: {chunk['metadata']['source']}\n{chunk['text'][:500]}"
                for chunk in chunks[:3]
            ])
        
        # Create focused prompt based on what's available
        if uploaded_context and chunks:
            prompt = f"""You are analyzing both an uploaded document and existing SOP documents to answer this question: "{query}"

{context}

Please provide a comprehensive answer that:
1. Primarily analyzes the uploaded document content in relation to the question
2. Cross-references with relevant SOP information when applicable
3. Gives specific, actionable information
4. Clearly indicates which source you're referencing"""
        
        elif uploaded_context:
            prompt = f"""You are analyzing an uploaded document to answer this question: "{query}"

{context}

Please provide a detailed analysis of the uploaded document that:
1. Directly addresses the question asked
2. Extracts relevant information from the document
3. Provides specific details, steps, or insights from the document content
4. Organizes the information in a clear, professional manner"""
        
        else:
            prompt = f"""Answer this question using the SOP documents provided: "{query}"

{context}

Provide a clear, professional answer with specific steps if applicable."""
        
        return prompt

    def stream_response(self, prompt: str, model: str = "gpt-4o-mini"):
        try:
            stream = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a professional SOP assistant. Provide clear, actionable guidance based on the provided documents."},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
                temperature=0.3
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
        page_title="SOP Assistant",
        page_icon="🧠",
        layout="wide"
    )
    
    # Clean CSS
    st.markdown("""
    <style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* Main layout */
    .main .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: none !important;
    }
    
    .app-layout {
        display: flex;
        height: 100vh;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Sidebar */
    .sidebar {
        width: 300px;
        background: rgba(255, 255, 255, 0.95);
        padding: 1rem;
        overflow-y: auto;
        border-right: 1px solid rgba(102, 126, 234, 0.2);
    }
    
    /* Main content */
    .main-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        background: white;
        margin: 1rem;
        margin-left: 0;
        border-radius: 0 20px 20px 0;
    }
    
    /* Chat area */
    .chat-area {
        flex: 1;
        padding: 2rem;
        overflow-y: auto;
    }
    
    /* Input area */
    .input-area {
        border-top: 1px solid #eee;
        padding: 1rem 2rem;
        background: #f8f9fa;
    }
    
    /* Messages */
    .user-message {
        background: rgba(102, 126, 234, 0.1);
        padding: 1rem;
        border-radius: 12px;
        margin: 1rem 0;
        margin-left: 20%;
    }
    
    .assistant-message {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 12px;
        margin: 1rem 0;
        margin-right: 20%;
    }
    
    /* File uploader */
    .stFileUploader > div {
        background: rgba(102, 126, 234, 0.1) !important;
        border: 2px dashed rgba(102, 126, 234, 0.3) !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }
    
    /* Text area */
    .stTextArea textarea {
        border-radius: 8px !important;
        border: 2px solid rgba(102, 126, 234, 0.3) !important;
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
    
    # Layout
    st.markdown('<div class="app-layout">', unsafe_allow_html=True)
    
    # Sidebar
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.header("💬 SOP Assistant")
        
        # New chat button
        if st.button("+ New Chat", use_container_width=True):
            chat_id = f"chat_{int(time.time())}"
            st.session_state.chat_sessions[chat_id] = {
                'title': 'New Chat',
                'messages': [],
                'created': datetime.now().isoformat()
            }
            st.session_state.current_chat_id = chat_id
            save_chat_sessions(st.session_state.chat_sessions)
            st.rerun()
        
        st.divider()
        
        # Chat list
        for chat_id, chat_data in st.session_state.chat_sessions.items():
            is_active = st.session_state.current_chat_id == chat_id
            title = chat_data.get('title', 'Untitled Chat')
            
            if st.button(
                title,
                key=f"chat_{chat_id}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.current_chat_id = chat_id
                st.rerun()
        
        st.divider()
        
        # Model selection
        st.subheader("🤖 AI Model")
        model_options = {
            "GPT-4o": "gpt-4o",
            "GPT-4o-mini": "gpt-4o-mini", 
            "GPT-4 Turbo": "gpt-4-turbo",
            "GPT-3.5 Turbo": "gpt-3.5-turbo"
        }
        
        if 'selected_model' not in st.session_state:
            st.session_state.selected_model = "gpt-4o-mini"
        
        selected_model_name = st.selectbox(
            "Choose AI Model:",
            options=list(model_options.keys()),
            index=list(model_options.values()).index(st.session_state.selected_model),
            help="Select which GPT model to use for responses"
        )
        st.session_state.selected_model = model_options[selected_model_name]
        
        st.divider()
        
        # Stats
        st.subheader("📊 Stats")
        st.metric("📚 SOPs", sop_count)
        st.metric("🧠 Current Model", selected_model_name)
    
    # Main content
    with col2:
        current_chat = st.session_state.chat_sessions[st.session_state.current_chat_id]
        
        # Messages
        if not current_chat['messages']:
            st.info("👋 Welcome! Ask me anything about your SOPs or upload a document.")
        else:
            for msg in current_chat['messages']:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class="user-message">
                        <strong>You:</strong> {msg["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="assistant-message">
                        <strong>SOP Assistant:</strong> {msg["content"]}
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
                                st.markdown(f"📄 {source_name}")
        
        st.divider()
        
        # Input area
        uploaded_file = st.file_uploader(
            "📎 Attach document",
            type=['pdf', 'docx', 'txt'],
            help="Upload PDF, Word, or text files"
        )
        
        if uploaded_file:
            st.success(f"📎 **{uploaded_file.name}** attached!")
        
        # Text input with form
        with st.form("chat_form", clear_on_submit=True):
            prompt = st.text_area(
                "Your message:",
                placeholder="Ask about your SOPs...",
                height=80,
                label_visibility="collapsed"
            )
            submit_button = st.form_submit_button("Send", use_container_width=True, type="primary")
        
        # Process message
        if submit_button and prompt.strip():
            # Get uploaded file context if available
            uploaded_context = ""
            uploaded_file_name = ""
            document_sources = []
            
            if uploaded_file:
                with st.spinner("Processing uploaded document..."):
                    uploaded_context = st.session_state.assistant.extract_text_from_file(uploaded_file)
                    uploaded_file_name = uploaded_file.name
                    
                    # Store document in chat session for future reference
                    if 'documents' not in current_chat:
                        current_chat['documents'] = {}
                    current_chat['documents'][uploaded_file_name] = uploaded_context
                    
                    # Add document info to sources
                    document_sources = [{
                        'text': uploaded_context[:500] + "..." if len(uploaded_context) > 500 else uploaded_context,
                        'metadata': {'source': uploaded_file_name, 'type': 'uploaded_document'},
                        'similarity': 1.0
                    }]
            
            # Add user message
            user_display_content = prompt
            if uploaded_file_name:
                user_display_content = f"{prompt}\n\n📎 **Attached:** {uploaded_file_name}"
            
            current_chat['messages'].append({"role": "user", "content": user_display_content})
            
            # Update title if first message
            if len(current_chat['messages']) == 1:
                current_chat['title'] = generate_chat_title(prompt)
            
            save_chat_sessions(st.session_state.chat_sessions)
            
            # Generate response
            with st.spinner("Generating response..."):
                # Search SOPs for relevant content
                sop_chunks = st.session_state.assistant.search_sops(prompt)
                
                # Combine SOP chunks with document sources
                all_sources = document_sources + sop_chunks
                
                # Generate AI response
                ai_prompt = st.session_state.assistant.generate_response(prompt, sop_chunks, uploaded_context)
                
                # Stream response
                response_placeholder = st.empty()
                full_response = ""
                
                for token in st.session_state.assistant.stream_response(ai_prompt, st.session_state.selected_model):
                    full_response += token
                    response_placeholder.markdown(f"""
                    <div class="assistant-message">
                        <strong>SOP Assistant:</strong> {full_response}▌
                    </div>
                    """, unsafe_allow_html=True)
                
                # Add assistant response
                current_chat['messages'].append({
                    "role": "assistant",
                    "content": full_response,
                    "sources": all_sources
                })
            
            save_chat_sessions(st.session_state.chat_sessions)
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()