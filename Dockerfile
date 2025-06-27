FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies with timeout and retry settings
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --timeout 300 --retries 3 -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p /app/chroma_db

# Expose Streamlit port
EXPOSE 8501

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]