FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    chainlit \
    pydantic \
    python-dotenv \
    google generativeai \
    websockets \
    openai-agents

# Copy project files into container
COPY . .

# Ensure writable .chainlit and .files directories
RUN mkdir -p /app/.chainlit /app/.files && chmod -R 777 /app/.chainlit /app/.files

# Expose Chainlit default port
EXPOSE 7860

# Start Chainlit
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "7860"]






