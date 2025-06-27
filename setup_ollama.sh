#!/bin/bash

echo "🚀 Setting up SOP Chatbot with Ollama..."

echo "⏳ Waiting for Ollama container to start..."
sleep 15

echo "📥 Pulling llama3.1 model..."
docker exec sop_ollama_new ollama pull llama3.1

echo "✅ Setup complete!"
echo "🌐 Open your browser to: http://localhost:8502"
echo "💡 Upload some SOP documents and start chatting!"