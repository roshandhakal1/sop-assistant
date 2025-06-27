#!/usr/bin/env python3
"""
Simple SOP Assistant - Minimal working version
"""

import streamlit as st
from openai import OpenAI
import os

def main():
    st.set_page_config(
        page_title="SOP Intelligence Hub",
        page_icon="🚀",
        layout="wide"
    )
    
    st.title("🚀 SOP Intelligence Hub")
    st.markdown("Your AI-powered assistant for comprehensive analysis and guidance")
    
    # Simple API key handling
    api_key = None
    
    # Try secrets first
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except:
        pass
    
    # Try environment
    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY')
    
    # Manual input if nothing works
    if not api_key:
        api_key = st.text_input("Enter your OpenAI API Key:", type="password")
        if not api_key:
            st.warning("Please enter your OpenAI API key to continue")
            st.stop()
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Simple chat interface
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask me about your SOPs..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate response
            with st.chat_message("assistant"):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a professional SOP assistant. Provide detailed, comprehensive responses (500-1500 words) about Standard Operating Procedures. Include step-by-step guidance, best practices, and thorough explanations."},
                            *st.session_state.messages
                        ],
                        max_tokens=3000,
                        temperature=0.3
                    )
                    
                    assistant_response = response.choices[0].message.content
                    st.markdown(assistant_response)
                    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.info("Please check your API key is valid and has credits")
    
    except Exception as e:
        st.error(f"Failed to initialize OpenAI client: {str(e)}")
        st.info("Please check your API key format")

if __name__ == "__main__":
    main()