# AI-Powered Medical Report Generator Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2+-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2+-blue.svg)](https://www.typescriptlang.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.x-green.svg)](https://www.mongodb.com/)

> AI-powered platform to ingest clinical documents, extract structured medical entities, and generate MDT reports — with a modern React UI, robust security middleware, and MongoDB persistence.

---

## 🎯 Key Aspects

The AI Powered Medical Report Generator is an enterprise-grade medical document processing platform that combines advanced AI with modern web technologies to streamline clinical workflows.

### Core Capabilities
- **Multi-format Document Ingestion**: PDF, images, text, XML, JSON (base64 or URL upload)
- **AI-Powered Entity Extraction**: Named Entity Recognition (NER) for medical entities using configurable LLM providers
- **OCR Processing**: Built-in OCR capabilities for image and PDF documents
- **MDT Report Generation**: Automated Multidisciplinary Team report creation with real-time progress tracking

### Technical Stack
- **Backend**: Python 3.11+ with FastAPI, async processing, MongoDB persistence
- **Frontend**: React 18+ with TypeScript, Vite build system, Tailwind CSS
- **Database**: MongoDB 7.x with automatic indexing and optimized queries
- **AI/ML**: Configurable LLM providers


### Demo Capabilities
- Upload and process medical documents in multiple formats
- Extract structured medical entities with real-time visualization
- Generate comprehensive MDT reports with live progress tracking
- Switch between different AI models and providers easily
- Compare generated results with original documents for validation and accuracy assessment

---

## ⚡ Fast Track: Simple Fast Deployment

Get The AI Powered Medical Report Generator running in under 5 minutes with Docker:

```bash
# 1. Clone and navigate to the project
git clone <repository-url>
cd hc-mdt-report-generator

# 2. Quick environment setup
cp environment.template .env

# 3. Edit the .env file with minimal required settings

# Set at minimum:
# SECRET_KEY=your-32-character-secret-key-here-minimum
# JWT_SECRET_KEY=your-32-character-jwt-secret-key-here-minimum
# MONGODB_URI=your-mongodb-connection-string
# MONGODB_DB=your-database-name
# DEMO_MODE=false  # Enables full functionality 

# 4. Start everything with Docker Compose
docker-compose up -d --build
```

**That's it!** Access your platform at:
- **Main Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Quick Test
1. Open http://localhost:8000 in your browser
2. Upload a test document from the `data/` folder
3. Process the document and generate an MDT report
4. View extracted entities and generated report

**Note**: The fast track uses default settings. For production or advanced features, follow the complete deployment guide below.

---

## 🔧 Step-by-Step Complete Deployment

For production environments or custom configurations, follow this comprehensive deployment guide.

### Prerequisites
- Python 3.11+ (for local development)
- Node.js 18+ and npm (for frontend development)
- Docker and Docker Compose (recommended)
- MongoDB 7.x (or use Docker MongoDB)

### Step 1: Environment Configuration

Create and configure your environment variables:

```bash
# Copy the template
cp environment.template .env
```
Now edit the `.env` file with your specific settings. At minimum, you must set the following:


**Essential Environment Variables:**

```bash
# Security (REQUIRED)
SECRET_KEY=your-generated-32-character-minimum-secret-key

# Database Configuration
MONGODB_URI=your-mongodb-connection-string
MONGODB_DB=your-database-name

# AI/LLM Provider Configuration (choose one or multiple)
LLM_PROVIDER=bedrock  # or mistral, openai, ollama

# CORS and Security (Optional)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
CORS_ALLOW_CREDENTIALS=true

# JWT Configuration (Optional - Auth disabled by default)
JWT_SECRET_KEY=your-generated-32-character-minimum-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```


### Step 2: LLM Provider Setup

Choose and configure your AI provider:

<!-- Bedrock -->
#### Option A: AWS Bedrock

If you are using sso or aws cli with configured credentials, the platform will automatically use those credentials to access Bedrock. You just need to specify the provider in your environment variables.

```bash 
# Add to your .env
LLM_PROVIDER=bedrock
```

Then run this command and authenticate with your AWS account:
```bash
aws sso login
```


#### Option B: Mistral Cloud API
```bash
# Add to your .env
MISTRAL_API_KEY=your-mistral-api-key
LLM_PROVIDER=mistral
LLM_MODEL=mistral-medium
```

#### Option C: Local LLM (Ollama)
```bash
# First, start Ollama server
ollama serve

# Pull a model (example)
ollama pull llama2

# Add to your .env
GPT_OPEN_BASE_URL=http://localhost:11434
LLM_PROVIDER=ollama
LLM_MODEL=llama2
```

### Step 3: Database Setup

#### Create your MongoDB database and user (if using external MongoDB):


### Step 4: Application Deployment

#### Method 1: Docker Compose (Recommended)
```bash
# Start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

#### Method 2: Local Development Setup

**Backend Setup:**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Run database migrations/setup
python -c "from repositories.mongo_db import create_indexes; create_indexes()"

# Start backend server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend Setup (separate terminal):**
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Step 5: Initial Configuration

1. **Access the application**: http://localhost:8000
2. **Verify health**: http://localhost:8000/health
3. **Configure LLM settings** (if not set via environment):
   - Go to Settings → LLM Configuration
   - Test your AI provider connection
4. **Upload test data**:
   - Use sample files from `data/` directory
   - Test document processing pipeline
   - Generate sample MDT reports

### Step 6: Production Considerations

**Security Hardening:**
```bash
# Set secure CORS origins
ALLOWED_ORIGINS=https://your-domain.com

# Enable security headers
ENABLE_SECURITY_HEADERS=true

# Set production secret
SECRET_KEY=your-production-secret-key-32-chars-minimum
```

**Performance Optimization:**
```bash
# Increase rate limits for production
RATE_LIMIT_PER_MINUTE=300
GENERAL_RATE_LIMIT_PER_MINUTE=500

# Configure MongoDB connection pooling
MONGODB_MAX_CONNECTIONS=100
MONGODB_MIN_CONNECTIONS=10
```

**Monitoring and Logging:**
- Use `/observability/generations` for processing metrics
- Monitor `/health` endpoint for system status
- Configure log aggregation for production environments

### Verification Steps

1. **Health Check**: `curl http://localhost:8000/health`
2. **Upload Test Document**: Use the web interface or API
3. **Process Document**: Trigger processing and verify completion
4. **Generate MDT Report**: Create a report and check real-time progress
5. **Switch LLM Provider**: Test runtime LLM switching via settings
6. **Check Logs**: Verify no errors in application logs

---

## 🏗️ Architecture Overview

### System Architecture

```
┌─────────────────┐    HTTP/WebSocket     ┌─────────────────┐
│   Frontend UI   │◄─────────────────────►│  FastAPI Backend │
│  React + Vite   │                       │   Python 3.11+   │
│  Port: 3000/8000│                       │    Port: 8000     │
└─────────────────┘                       └─────────┬───────┘
                                                    │
                                                    │ API Calls
                                                    │
                ┌─────────────┬─────────────────────┴─────────────────┐
                │             │                                       │
        ┌───────▼──────┐ ┌───▼──────┐ ┌─────────▼────┐ ┌──────▼─────────┐
        │ Controllers  │ │ Services │ │ Middleware   │ │  Repositories  │
        │              │ │          │ │              │ │                │
        │ • Patients   │ │ • OCR    │ │ • Rate Limit │ │ • Documents    │
        │ • Reports    │ │ • NER    │ │ • Validation │ │ • Reports      │
        │ • Settings   │ │ • MDT    │ │ • Security   │ │ • Users        │
        └──────────────┘ └──────────┘ └──────────────┘ └────────┬───────┘
                                                                 │
                                                                 │ PyMongo
                                                                 │
                                                      ┌──────────▼───────────┐
                                                      │     MongoDB 7.x      │
                                                      │                      │
                                                      │ Collections:         │
                                                      │ • documents          │
                                                      │ • reports            │
                                                      │ • generations        │
                                                      │ • users              │
                                                      │ • entity_configs     │
                                                      └──────────────────────┘
```

### Project Structure

```
hc-mdt-report-generator/
├── 🐳 Docker Configuration
│   ├── docker-compose.yml          # Multi-service orchestration
│   ├── Dockerfile.backend          # Python FastAPI container
│   └── Dockerfile.frontend         # React build container
│
├── 🔧 Configuration
│   ├── environment.template        # Environment variables template
│   ├── generate_env.sh            # Quick env setup script
│   └── gr_entities_definition.json # Medical entity definitions
│
├── 🖥️ Backend (Python)
│   ├── main.py                    # FastAPI application entry
│   ├── requirements.txt           # Python dependencies
│   ├── pyproject.toml            # Project metadata
│   │
│   ├── 🎯 controllers/           # API endpoints
│   │   ├── patient_document_controller.py  # Document upload/processing
│   │   ├── report_controller.py           # MDT report management
│   │   ├── settings_controller.py         # System configuration
│   │   └── entity_config_controller.py    # Entity management
│   │
│   ├── 🔨 services/              # Business logic
│   │   ├── patient_document_service.py    # Document processing
│   │   ├── mdt_report_generator.py        # Report generation
│   │   ├── entity_extraction_service.py   # NER extraction
│   │   └── ner_workflow_orchestrator.py   # AI workflow
│   │
│   ├── 💾 repositories/          # Data access layer
│   │   ├── mongo_db.py           # Database connection
│   │   ├── patient_document_repository.py # Document CRUD
│   │   └── report_repository.py          # Report CRUD
│   │
│   └── 📊 models/               # Data models
│       ├── patient_document.py   # Document schema
│       └── report.py            # Report schema
│
├── 🌐 Frontend (React + TypeScript)
│   ├── package.json              # Node dependencies
│   ├── vite.config.js           # Build configuration
│   ├── tailwind.config.js       # Styling framework
│   │
│   └── src/                     # React application
│       ├── components/          # UI components
│       ├── pages/              # Application pages
│       ├── services/           # API client
│       └── types/              # TypeScript definitions
│
├── 📄 Documentation
│   └── docs/                   # Technical documentation
│
├── 🧪 Testing
│   ├── tests/sanity/           # Pre-push sanity checks
│   ├── tests/integration/      # API integration tests
│   └── scripts/               # Utility scripts
│
└── 📊 Data
    ├── Sample medical documents for testing
    └── Entity definition templates
```

---

## 🔗 API Reference

Base URL: `http://localhost:8000`

### Core Endpoints

#### System Health
- `GET /health` - System health check
- `GET /` - API documentation links

#### Patient Document Management
**Base Path**: `/patients`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/patients` | List all patient IDs |
| `POST` | `/patients/{patient_id}/document` | Upload document (PDF/image/text) |
| `GET` | `/patients/{patient_id}/documents` | List patient documents |
| `GET` | `/patients/{patient_id}/document/{uuid}` | Get document details |
| `POST` | `/patients/{patient_id}/document/{uuid}/process` | Trigger document processing |
| `GET` | `/patients/{patient_id}/document/{uuid}/ocr` | Get OCR results |
| `DELETE` | `/patients/{patient_id}/document/{uuid}` | Delete document |

#### MDT Report Generation
**Base Path**: `/patients/{patient_id}/reports`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reports` | Create new MDT report |
| `POST` | `/reports/stream` | Generate report with live progress (SSE) |
| `GET` | `/reports` | List patient reports |
| `GET` | `/reports/{report_id}` | Get specific report |
| `GET` | `/reports/statistics` | Patient report statistics |
| `DELETE` | `/reports/{report_id}` | Delete report |

#### System Configuration
**Base Path**: `/settings`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/llm-models` | List available AI models |
| `POST` | `/llm-model` | Switch AI provider/model |
| `GET` | `/ner-config` | Get NER processing config |
| `POST` | `/ner-config` | Update NER settings |
| `POST` | `/set-env-var` | Update environment variables |
| `POST` | `/master-delete` | Clear all data (requires confirmation) |

#### Entity Management
**Base Path**: `/entity-config`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Get current entity configuration |
| `PUT` | `/` | Update entity configuration |
| `POST` | `/reset` | Reset to default entities |
| `GET` | `/validate` | Validate entity config |

#### Monitoring & Analytics
**Base Path**: `/observability`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/generations` | List AI generation logs |
| `GET` | `/generations/filters` | Available log filters |

### Request/Response Examples

#### Upload Document
```bash
curl -X POST "http://localhost:8000/patients/PATIENT001/document" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "consultation.pdf",
    "file_content": "base64-encoded-content",
    "document_type": "consultation"
  }'
```

#### Generate MDT Report (with live progress)
```bash
curl -X POST "http://localhost:8000/patients/PATIENT001/reports/stream" \
  -H "Accept: text/event-stream" \
  -d '{
    "title": "Cardiology MDT Report",
    "include_entities": ["medications", "procedures", "findings"]
  }'
```

#### Switch AI Model
```bash
curl -X POST "http://localhost:8000/settings/llm-model" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "mistral",
    "model": "mistral-medium",
    "api_key": "your-api-key"
  }'
```

### Authentication (Optional)
Authentication endpoints exist but are **disabled by default**. To enable:

1. Uncomment auth router in `backend/main.py`
2. Set JWT environment variables
3. Use `/auth/login` and `/auth/register` endpoints

---

## 🔄 Processing Workflows

### Document Processing Pipeline

```
📤 Upload Document
│
├─ Validation & Storage
│  ├─ File type validation
│  ├─ Size limits check
│  └─ Duplicate detection
│
├─ OCR Processing
│  ├─ PDF text extraction
│  ├─ Image OCR (via Mistral)
│  └─ Text normalization
│
├─ Content Analysis
│  ├─ Document categorization
│  ├─ Text preprocessing
│  └─ Structure detection
│
└─ ✅ Ready for Report Generation
```

### MDT Report Generation

```
🎯 Generate Report Request
│
├─ Entity Configuration Loading
│  ├─ Load from MongoDB
│  └─ Fallback to JSON definition
│
├─ Document Retrieval
│  ├─ Fetch processed documents
│  ├─ Apply filters (date, type)
│  └─ Prepare text chunks
│
├─ AI Processing
│  ├─ Named Entity Recognition
│  ├─ Entity extraction & validation
│  └─ Structured data creation
│
├─ Report Compilation
│  ├─ Aggregate extracted entities
│  ├─ Add metadata & statistics
│  └─ Generate final report
│
└─ 📊 Complete MDT Report
```

### Real-time Progress Tracking

The platform provides live updates during processing via Server-Sent Events (SSE):

1. **Initializing**: Setup and validation
2. **Retrieving**: Loading documents and configuration
3. **Extracting**: Text processing and preparation  
4. **Processing**: AI entity extraction
5. **Compiling**: Report generation
6. **Completed**: Final report available

---

---

## 🔒 Security & Production Considerations

### Built-in Security Features

- **Progressive Rate Limiting**: API and general request throttling
- **Input Validation**: Protection against SQL/NoSQL injection, XSS, command injection
- **Security Headers**: HSTS, X-Frame-Options, X-XSS-Protection, CSP
- **CORS Protection**: Configurable origin restrictions  
- **JWT Authentication**: Available but disabled by default

### Production Security Setup

```bash
# Secure environment variables
SECRET_KEY=your-production-secure-32-char-minimum-secret
ALLOWED_ORIGINS=https://your-domain.com,https://api.your-domain.com
CORS_ALLOW_CREDENTIALS=true
ENABLE_SECURITY_HEADERS=true

# Rate limiting for production
RATE_LIMIT_PER_MINUTE=300
GENERAL_RATE_LIMIT_PER_MINUTE=500

# Database security
MONGODB_URI=mongodb://username:password@mongodb:27017/your-database-name?authSource=admin
```

### Security Best Practices

1. **Use HTTPS in production** with proper SSL certificates
2. **Restrict CORS origins** to your domain only
3. **Set strong SECRET_KEY** (32+ characters, cryptographically secure)
4. **Enable MongoDB authentication** with dedicated user accounts
5. **Monitor rate limits** and adjust based on usage patterns
6. **Regular security updates** for all dependencies
7. **Network isolation** using Docker networks or VPNs

---

## 🧪 Testing & Quality Assurance

### Pre-Push Testing

Always run sanity tests before deployment:

```bash
# Quick sanity check
./scripts/pre-push-tests.sh

# Or run directly
pytest tests/sanity/ -v
```

**Expected Output:**
```
====================== 15 passed in 0.33s ======================
✅ All sanity checks PASSED!
   You can safely push your changes.
```

### Comprehensive Testing

```bash
# All tests with coverage
pytest tests/ --cov=backend --cov-report=html -v

# Integration tests only
pytest tests/integration/ -v

# Sanity checks only  
pytest tests/sanity/ -v
```

### Test Categories

| Test Suite | Coverage | Purpose |
|------------|----------|---------|
| **Sanity Tests** | Core functionality | Pre-push validation |
| **Integration Tests** | API endpoints | End-to-end testing |
| **Unit Tests** | Individual components | Component testing |

### Manual Testing Checklist

- [ ] Document upload (PDF, image, text)
- [ ] Document processing pipeline
- [ ] MDT report generation
- [ ] Real-time progress tracking (SSE)
- [ ] LLM provider switching
- [ ] Entity configuration management
- [ ] Error handling and validation

---

## 🛠️ Troubleshooting Guide

### Common Issues & Solutions

#### 🔴 MongoDB Connection Issues

**Problem**: Cannot connect to MongoDB
```bash
# Check MongoDB status
docker ps | grep mongo

# Restart MongoDB container
docker restart mongodb

# Check logs
docker logs mongodb
```

**Solution**: Ensure `MONGODB_URI` matches your setup:
- Local: `your-mongodb-connection-string`
- Docker: `your-mongodb-connection-string` 

#### 🔴 LLM API Errors

**Problem**: API key errors or model unavailable
```bash
# Check current configuration
curl http://localhost:8000/settings/llm-models

# Test API key
curl -X POST http://localhost:8000/settings/llm-model \
  -d '{"provider": "mistral", "model": "mistral-medium"}'
```

**Solutions**:
- Verify API keys in environment variables
- Check base URLs for local endpoints
- Ensure models are available for your account

#### 🔴 Processing Stuck/Failed

**Problem**: Documents not processing or reports failing

**Debug Steps**:
1. Check document status: `GET /patients/{id}/document/{uuid}`
2. View processing logs in Docker/console
3. Verify LLM configuration and connectivity
4. Check entity configuration: `GET /entity-config/validate`

#### 🔴 Rate Limiting Issues

**Problem**: Too many requests (429 errors)

**Solutions**:
```bash
# Increase limits in .env
RATE_LIMIT_PER_MINUTE=600
GENERAL_RATE_LIMIT_PER_MINUTE=1000

# Or wait for current window to reset
wait-retry-after-header
```

#### 🔴 Frontend/Backend Connection Issues

**Problem**: UI cannot reach API

**Check**:
1. Backend health: `curl http://localhost:8000/health`
2. CORS configuration in environment
3. Frontend API base URL settings
4. Network connectivity between services

### System Diagnostics

#### Health Check Commands
```bash
# System health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/patients

# LLM status
curl http://localhost:8000/settings/llm-models
```

#### Log Analysis
```bash
# Docker Compose logs
docker-compose logs -f backend
docker-compose logs -f mongodb

# Individual service logs
docker logs hc-mdt-report-generator-backend-1 --tail=100
```

#### Performance Monitoring
```bash
# MongoDB stats
curl http://localhost:8000/observability/generations

# System resource usage
docker stats
```

### Getting Help

1. **Check logs** first - most issues show up in application logs
2. **Verify configuration** - ensure all required environment variables are set
3. **Test components** individually - API, database, LLM connectivity
4. **Review documentation** - API docs at http://localhost:8000/docs
5. **Run diagnostic scripts** - use provided testing and setup scripts

---

## 📋 Using Demo Effectively

### Quick Demo Workflow

1. **Start the platform**: `docker-compose up -d --build`
2. **Load sample data**: Upload files from `data/` folder
3. **Process documents**: Trigger processing for uploaded documents
4. **Generate reports**: Create MDT reports with live progress tracking
5. **Explore features**: Try different AI models, entity configurations
6. **Monitor system**: Check generation logs and statistics

### Demo Scenarios

#### Scenario 1: Basic Document Processing
- Upload a cardiology consultation (`data/01_cardiology_consultation.txt`)
- Process the document and view extracted text
- Generate an MDT report
- Review extracted medical entities

#### Scenario 2: Multi-Document Patient
- Upload multiple documents for one patient
- Process all documents
- Generate comprehensive MDT report
- Compare entity extraction across documents

#### Scenario 3: AI Model Comparison
- Generate a report with one AI model
- Switch to a different provider (e.g., Mistral → OpenAI)
- Generate the same report again
- Compare results and performance

#### Scenario 4: Configuration Testing
- Modify entity configuration via UI
- Test with custom medical entities
- Validate configuration changes
- Reset to default if needed

### Demo Data Included

The `data/` folder contains:
- **Medical documents**: Cardiology, lab results, procedures
- **Test files**: Various formats (TXT, JSON, PDF examples)
- **Patient datasets**: Multi-document patient examples
- **Entity templates**: Predefined medical entity configurations

---

## 📄 License & Attribution

This project is licensed under the MIT License with Additional Terms. See the root [LICENSE](LICENSE) file for complete details.

### Key License Points
- **Open source MIT license** for general use and modification
- **Additional terms** for specific components marked as "common/shared"
- **NER component sharing rights** for MongoDB Inc. on specified components

### Attribution Requirements
When using or modifying this software:
1. Retain original copyright notices
2. Include license file in distributions  
3. Acknowledge use of the AI Powered Medical Report Generator platform in derivative works

---

**Last updated**: March 11, 2026  
**Version**: 2.0.0  
**Maintainer**: Healthcare AI Development Team

