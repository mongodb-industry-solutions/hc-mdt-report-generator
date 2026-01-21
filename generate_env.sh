#!/bin/bash

echo "🚀 Generating MINIMAL LOCAL GPU environment configuration..."
echo "============================================================"

# Generate fresh security keys
SECRET_KEY=$(openssl rand -hex 32)

cat > .env << EOF
# ========================================
# MINIMAL LOCAL GPU CONFIGURATION
# ========================================

# Core Application
SECRET_KEY=${SECRET_KEY}

# Database
MONGODB_URI=mongodb://mongodb:27017/clarityGR
MONGODB_DB=clarityGR


# GPT-Open configuration
# Linux/Ubuntu server: write a concrete value resolvable from containers
GPT_OPEN_BASE_URL=http://host.docker.internal:8080
GPT_OPEN_MODEL=${GPT_OPEN_MODEL:-gpt-open}
GPT_OPEN_TIMEOUT=${GPT_OPEN_TIMEOUT:-3000.0}
GPT_OPEN_TEMPERATURE=${GPT_OPEN_TEMPERATURE:-0.1}
GPT_OPEN_MAX_TOKENS=${GPT_OPEN_MAX_TOKENS:-7000}

# ========================================
# DUMMY VALUES (required by settings.py but not used in local mode)
# ========================================
MISTRAL_API_KEY=

# ========================================
# NER processing configuration
# ========================================
NER_MAX_ENTITIES_PER_BATCH=${NER_MAX_ENTITIES_PER_BATCH:-6}
NER_MAX_CONTENT_SIZE=${NER_MAX_CONTENT_SIZE:-4000}
NER_CHUNK_OVERLAPPING=${NER_CHUNK_OVERLAPPING:-200}
NER_MAX_CONCURRENT_REQUESTS=${NER_MAX_CONCURRENT_REQUESTS:-1}
EOF

