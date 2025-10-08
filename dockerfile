FROM python:3.10-slim

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# working dir
WORKDIR /app

# Install system dependencies (git, build tools, postgres client libs, node/npm)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    ca-certificates \
    git \
    nodejs \
    npm \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt /app/
RUN pip install --upgrade pip \
 && pip install -r /app/requirements.txt

# Copy the application code
COPY . /app

# Install Bootstrap (v3) via npm
# Install in project root (creates node_modules). If you prefer inside static/ adjust --prefix.
RUN npm init -y \
 && npm install bootstrap@3 --no-audit --no-fund

# Make entrypoint executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 5000

# Start script: the entrypoint will handle DB wait and migrations then start server
CMD ["/app/entrypoint.sh"]
