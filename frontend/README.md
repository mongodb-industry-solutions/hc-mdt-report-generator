# Medical Document Processing Frontend

A modern Next.js application for managing medical documents and generating MDT (Multi-Disciplinary Team) reports with real-time progress tracking and entity extraction visualization.

## Technology Stack

- **Framework**: Next.js 14 (App Router)
- **Frontend**: React 18 with TypeScript
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Build Tool**: Next.js (migrated from Vite)
- **Deployment**: Docker with multi-stage builds

## Features

### 🏥 Patient Management
- **Patient ID Selection**: Easy patient identification and switching
- **Document Organization**: View all documents for a specific patient with status tracking
- **Real-time Updates**: Automatic refresh of document processing status

### 📄 Document Management
- **Multi-file Upload**: Drag-and-drop interface supporting various file formats
- **Progress Tracking**: Real-time upload and processing progress visualization
- **Status Monitoring**: Track document processing through queued → processing → completed states
- **Metadata Display**: View document categorization and extracted entity counts

### 📊 MDT Report Generation
- **Automated Report Creation**: Generate comprehensive MDT reports from processed documents
- **Progress Streaming**: Real-time progress updates during report generation
- **Entity Classification**: View extracted entities organized by processing type:
  - **First Match**: Single-value entities (patient name, ID, etc.)
  - **Multiple Match**: Multi-value entities (diagnoses, treatments)
  - **Aggregate**: Summarized entities with source tracking

### 👁️ Report Visualization
- **Interactive Side Panel**: View report details without leaving the main interface
- **Entity Explorer**: Expandable entity cards with source document references
- **Summary Statistics**: Document counts, entity totals, and processing metadata
- **Multi-format Download**: Export reports as JSON or PDF


### 🌍 Internationalization
- **Bilingual Support**: Complete English and French language support
- **Dynamic Language Switching**: Instant interface updates when changing languages
- **Localized Content**: All text, dates, times, and medical terminology properly localized
- **French as Default**: Application defaults to French for medical professionals
- **Persistent Preferences**: Language choice saved in browser for returning users

### ⚙️ Configuration
- **API Configuration**: Flexible backend URL configuration
- **Language Selection**: Easy switching between English and French
- **Connection Status**: Real-time connection monitoring
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Tech Stack

- **React 18** with TypeScript for type safety
- **Vite** for fast development and building
- **Tailwind CSS** for modern, responsive styling
- **Lucide React** for beautiful icons
- **date-fns** for date formatting
- **axios** for API communication
- **react-dropzone** for file upload handling
- **React Context API** for internationalization state management

## File Format Support

The application supports the following medical document formats:
- **PDF** documents (lab reports, discharge summaries, etc.)
- **Images** (PNG, JPG, JPEG) for scanned documents
- **Text files** (TXT, CSV, JSON, XML)
- **Office documents** (DOCX, PPTX)

Maximum file size: 50MB per file

## Installation

### Prerequisites
- Node.js 18+ and npm (or yarn/pnpm)
- A running instance of the Medical Document Processing Backend

### Setup
1. **Install Dependencies**
   ```bash
   cd ui
   npm install
   ```

2. **Start Development Server**
   ```bash
   npm run dev
   ```
   The application will be available at `http://localhost:3000`

3. **Build for Production**
   ```bash
   npm run build
   ```

## Configuration

### Backend API Connection
The application uses an **API proxy pattern** through Next.js API routes for seamless backend connectivity:

1. **Proxy Route**: All frontend API calls go to `/api/internal/*` endpoints
2. **Server-Side Proxy**: Next.js API route proxies requests to backend using `BACKEND_URL` 
3. **Environment-Based**: `BACKEND_URL` is configured server-side only for security
4. **Service Discovery**: Works seamlessly with Kubernetes service names

**Environment Configuration**:
- **Development**: `BACKEND_URL=http://localhost:8000` (or auto-detected)
- **Staging**: `BACKEND_URL=http://staging-backend-service:8000` 
- **Production**: `BACKEND_URL=http://production-backend-service:8000`

**Settings Panel Override**:
- Click the **Settings** button (⚙️) to manually override the API endpoint
- Useful for debugging or connecting to different backend instances

## Usage Guide

### 1. Patient Selection
- Enter the patient ID in the header input field
- The application automatically loads documents and reports for the selected patient

### 2. Document Upload
1. Navigate to the **Upload** tab
2. Configure document settings:
   - **Document Type**: Select from predefined medical document types
   - **Source**: Specify where the document originated
   - **Notes**: Add optional notes for the document
3. Drag and drop files or click to select files
4. Monitor upload and processing progress

### 3. Document Management
- **Documents Tab**: View all uploaded documents with their processing status
- **Status Indicators**: 
  - 🟡 Queued: Awaiting processing
  - 🔵 Processing: Currently being analyzed
  - 🟢 Done: Successfully processed with extracted data
  - 🔴 Failed: Processing encountered errors
- **Metadata**: View document category, extracted entity count, and processing timestamps

### 4. Report Generation
1. Navigate to the **Reports** tab
2. Click **Generate New Report** to create an MDT report
3. Optionally add a custom title
4. Monitor real-time progress:
   - Document retrieval
   - Text extraction
   - Entity recognition
   - Report compilation
5. View completed reports in the list

### 5. Report Viewing
1. Click **View** on any completed report
2. The report viewer opens in a side panel
3. Navigate through entity categories using tabs:
   - **First Match**: Single-instance entities
   - **Multiple Match**: Multi-instance entities  
   - **Aggregate**: Summarized entities
4. Expand entity cards to see source document details
5. Download reports in JSON or PDF format

### 6. Language Management
1. **Language Switcher**: Click the globe icon (🌍) in the top-right header
2. **Available Languages**: 
   - **Français** (French) - Default language
   - **English** - Full English translation
3. **Instant Updates**: All interface elements update immediately upon language change
4. **Persistent Choice**: Language preference saved automatically for future visits
5. **Localized Elements**:
   - Navigation labels and buttons
   - Medical terminology and query suggestions
   - Date/time formatting
   - Conversation management interface
   - All tooltips and help text

## API Integration

The frontend communicates with the backend through these main endpoints:

### Document Management
- `GET /patients/{id}/documents` - List patient documents
- `POST /patients/{id}/document` - Upload new document
- `GET /patients/{id}/document/{uuid}` - Get document details

### Report Management
- `GET /patients/{id}/reports` - List patient reports
- `POST /patients/{id}/reports` - Generate new report
- `POST /patients/{id}/reports/stream` - Generate with progress updates

## Development

### Project Structure
```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── DocumentsList.tsx      # Patient document management
│   │   ├── FileUpload.tsx          # Document upload interface
│   │   ├── ReportsList.tsx         # MDT reports listing
│   │   ├── ReportViewer.tsx        # Report visualization
│   │   ├── PatientSelector.tsx     # Patient ID selection
│   │   ├── SettingsPanel.tsx       # Configuration panel
│   │   ├── LanguageSwitcher.tsx    # Bilingual language toggle
│   │   ├── PDFPreviewModal.tsx     # PDF document preview
│   │   └── ReportGenerationDialog.tsx # Report creation dialog
│   ├── i18n/               # Internationalization system
│   │   ├── context.tsx              # I18n React context
│   │   └── translations.ts          # English/French translations
│   ├── services/           # API service layer
│   │   ├── api.ts                   # Backend API communication
│   │   └── pdfGenerator.ts          # PDF export functionality
│   ├── types/              # TypeScript type definitions
│   │   └── index.ts                 # Application type definitions
│   ├── App.tsx             # Main application component
│   ├── main.tsx            # Application entry point
│   └── index.css           # Global styles and Tailwind imports
├── public/                 # Static assets
│   └── medical-icon.svg             # Application icon
├── package.json            # Dependencies and scripts
├── next.config.js          # Next.js configuration
├── tailwind.config.js      # Tailwind CSS configuration
└── tsconfig.json           # TypeScript configuration
```

### Available Scripts
- `npm run dev` - Start Next.js development server (port 3000)
- `npm run build` - Build for production
- `npm run start` - Start production server (port 8080)
- `npm run lint` - Run Next.js ESLint
- `npm run type-check` - TypeScript type checking

### Styling Guidelines
- Uses Tailwind CSS utility classes
- Custom CSS classes defined in `src/index.css`
- Responsive design with mobile-first approach
- Medical theme colors (medical-* color palette)

## Deployment

### Production Build
```bash
npm run build
```

The build artifacts will be generated in the `dist/` directory.

### Docker Deployment
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Verify the backend server is running
   - Check the API base URL in settings
   - Ensure CORS is properly configured on the backend

2. **File Upload Failures**
   - Check file size (max 50MB)
   - Verify file format is supported
   - Ensure sufficient server storage space

3. **Report Generation Stuck**
   - Verify patient has processed documents
   - Check backend logs for processing errors
   - Ensure all required services are running

4. **UI Performance Issues**
   - Clear browser cache
   - Check for large file uploads
   - Monitor browser memory usage

5. **Language Switching Issues**
   - Clear localStorage if language doesn't persist: `localStorage.removeItem('medical-app-language')`
   - Refresh page if translations don't update immediately
   - Verify browser supports localStorage


### Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes with proper TypeScript types
4. Add appropriate tests
5. Follow the existing code style
6. Submit a pull request

## License

This project is part of the Gustave Roussy Medical Document Processing System. 