import { jsPDF } from 'jspdf';
import 'jspdf-autotable';
import { Report, ReportEntity, ReportContent } from '../types';
import reportGroupingConfig from '../config/report_grouping_config.json';

interface PDFSection {
  title: string;
  entities: ReportEntity[];
  summary?: string; // LLM-generated narrative summary
}

class MedicalPDFGenerator {
  private doc: jsPDF;
  private pageWidth: number;
  private pageHeight: number;
  private margins = { top: 30, right: 15, bottom: 30, left: 15 };
  private currentY: number = 0;
  private mongoDBLogoBase64: string | null = null;
  private readonly colors = {
    // MongoDB Primary Colors
    primary: '#10AA50',    // MongoDB Green
    mongodbGreen: '#10AA50', // MongoDB Green (alias for primary)
    forestGreen: '#116149', // Forest Green
    white: '#FFFFFF',      // White
    
    // MongoDB Neutrals
    gray95: '#F9F9F9',     // Gray 95
    gray90: '#F3F3F3',     // Gray 90
    gray60: '#6F787F',     // Gray 60
    gray45: '#4F555A',     // Gray 45
    gray30: '#3B4147',     // Gray 30
    gray15: '#232A2F',     // Gray 15
    black: '#000000',      // Black
    
    // MongoDB Supporting Colors
    skyBlue: '#43B1E5',    // Sky Blue
    sunYellow: '#FEF01B',  // Sun Yellow
    softPurple: '#866CC7', // Soft Purple
    peachOrange: '#F77B78', // Peach Orange
    
    // Legacy color mappings for compatibility
    secondary: '#6F787F',  // Gray 60
    success: '#10AA50',    // MongoDB Green
    warning: '#FEF01B',    // Sun Yellow
    danger: '#F77B78',     // Peach Orange
    light: '#F9F9F9',      // Gray 95
    dark: '#232A2F',       // Gray 15
    border: '#F3F3F3'      // Gray 90
  };

  // Entity ordering based on medical importance
  private readonly entityOrder = [
    "GRNumdos",
    "Birth Name",
    "First Name", 
    "Gender",
    "Date of Birth",
    "Family History",
    "Postal Address",
    "Email Address",
    "Hospital",
    "Medical History",
    "Diagnosed on",
    "Diagnosis Date",
    "Location",
    "Chemotherapy Performed",
    "Histological Type",
    "Radiotherapy Performed",
    "Distant Metastases",
    "Surgery Performed",
    "General Status (WHO)",
    "G8 Score",
    "Notable Personal History",
    "Referring Site",
    "Specialty Requested",
    "Cancer Locations",
    "Primary Tumor Comment",
    "Molecular Abnormality",
    "Metastatic",
    "Metastatic Site",
    "ICD-O-3",
    "Presentation Date",
    "Presentation Reasons",
    "MDT Question",
    "MDT Recommendation",
    "Innovative Therapy",
    "Off-label Treatment",
    "Inclusion in Therapeutic Trial",
    "Additional Examination Request",
    "EVASAN"
  ];

  // Section ordering for known sections (dynamic sections will be added after these)
  private readonly sectionOrder = [
    "Patient Information",
    "Clinical Summary", 
    "Patient and Tumor Characteristics",
    "Presentation Reason",
    "DRAFT System Recommendation",
    "MDT Recommendation (EXPERIMENTAL - Medical validation required)"
  ];

  // Clean section titles mapping (shorten long titles for PDF)
  private readonly cleanSectionTitles: Record<string, string> = {
    "Patient Information": "Patient Information",
    "Clinical Summary": "Clinical Summary",
    "Patient and Tumor Characteristics": "Patient & Tumor Characteristics",
    "Presentation Reason": "Presentation Reason",
    "DRAFT System Recommendation": "DRAFT System Recommendation",
    "MDT Recommendation (EXPERIMENTAL - Medical validation required)": "MDT Recommendation",
    "Other Information": "Other Information",
    // Handle legacy French titles for backward compatibility
    "Informations sur le patient": "Patient Information",
    "Rappel clinique": "Clinical Summary",
    "Caractéristiques patients et tumorales": "Patient & Tumor Characteristics",
    "Caracteristiques patients et tumorales": "Patient & Tumor Characteristics", // Handle legacy misspelling
    "Motif de présentation": "Presentation Reason",
    "Proposition DRAFT Système": "DRAFT System Recommendation",
    "Proposition RCP (EXPÉRIMENTAL - Validation médicale requise)": "MDT Recommendation",
    "Autres informations": "Other Information"
  };

  constructor() {
    this.doc = new jsPDF('portrait', 'mm', 'a4');
    this.pageWidth = this.doc.internal.pageSize.getWidth();
    this.pageHeight = this.doc.internal.pageSize.getHeight();
    this.currentY = this.margins.top;
    
    this.loadMongoDBLogo();
    
    // Configure PDF for proper UTF-8 support
    try {
      // Set default font to support French characters
      this.doc.setFont('helvetica', 'normal');
      
      // Set document properties for proper encoding
      this.doc.setProperties({
        title: 'MDT Report',
        subject: 'Multidisciplinary Team Meeting Report',
        author: 'MongoDB Healthcare',
        creator: 'MDT System'
      });
    } catch (error) {
      console.warn('PDF configuration warning:', error);
    }
  }

  private async loadMongoDBLogo(): Promise<void> {
    try {
      const response = await fetch('/mongodb_logo.png');
      if (!response.ok) {
        throw new Error(`Logo fetch failed (${response.status})`);
      }

      const blob = await response.blob();
      this.mongoDBLogoBase64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(new Error('Failed to read MongoDB logo'));
        reader.readAsDataURL(blob);
      });
    } catch (error) {
      console.warn('Failed to load MongoDB logo:', error);
      this.mongoDBLogoBase64 = null;
    }
  }

  public async generateReportPDF(report: Report, progressCallback?: (progress: number, step: string) => void): Promise<Blob> {
    const pdfStartTime = Date.now();
    const sessionId = `PDF_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    console.log(`🎯 === PDF GENERATION START [${sessionId}] ===`);
    console.log(`📋 Report: ${report.uuid} | Patient: ${report.patient_id}`);
    console.log(`📊 Report metadata: Created ${report.created_at} | Status: ${report.status}`);
    console.log(`🤖 LLM Summary Mode: ENABLED | Backend Provider: Auto-detect`);
    
    // Ensure logo is loaded before generating PDF
    progressCallback?.(0, 'Loading resources...');
    
    if (!this.mongoDBLogoBase64) {
      console.log(`🔧 Loading MongoDB logo...`);
      await this.loadMongoDBLogo();
    }

    progressCallback?.(5, 'Creating PDF structure...');
    console.log(`📄 Setting up PDF structure and header...`);
    this.addHeader(report);
    
    progressCallback?.(10, 'Adding report summary...');
    console.log(`📝 Adding report summary section...`);
    this.addReportSummary(report);
    
    if (report.content) {
      console.log(`🧠 Starting LLM-powered section processing...`);
      progressCallback?.(15, 'Processing medical sections...');
      await this.addEntitySections(report.content, report.patient_id, progressCallback);
    } else {
      console.warn(`⚠️ No report content found - skipping section processing`);
    }
    
    progressCallback?.(90, 'Adding footer and disclaimers...');
    console.log(`📄 Adding footer and disclaimers...`);
    this.addFooter(report);
    this.addPageDisclaimers();
    
    progressCallback?.(100, 'Finalizing PDF...');
    console.log(`✅ Generating final PDF blob...`);
    const pdfBlob = this.doc.output('blob');
    
    const totalDuration = Date.now() - pdfStartTime;
    console.log(`🎯 === PDF GENERATION COMPLETE [${sessionId}] ===`);
    console.log(`📊 Total generation time: ${totalDuration}ms (${Math.round(totalDuration/1000)}s)`);
    console.log(`📄 Final PDF size: ${Math.round(pdfBlob.size / 1024)}KB`);
    
    return pdfBlob;
  }

  // Helper function to convert markdown to plain text and clean encoding
  private cleanText(text: string): string {
    if (!text) return '';
    
    // First convert markdown to plain text
    let cleanedText = this.markdownToText(text);
    
    // Fix common character encoding issues specific to French text
    cleanedText = this.fixCharacterEncoding(cleanedText);
    
    // Then remove only actual control characters, preserving French/accented characters
    return cleanedText
      .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '') // Remove control chars (but preserve \x09=tab, \x0A=newline, \x0D=carriage return)
      .replace(/\uFFFD/g, '') // Remove Unicode replacement characters
      .replace(/[\u200B-\u200D\uFEFF]/g, '') // Remove zero-width spaces and BOM
      .trim();
  }

  // Fix common character encoding issues
  private fixCharacterEncoding(text: string): string {
    if (!text) return '';
    
    let fixed = text;
    
    // Fix common encoding corruption patterns for French characters
    // These replacements handle cases where UTF-8 is incorrectly decoded
    fixed = fixed.replace(/Ã©/g, 'é'); // é encoded as UTF-8 then decoded as Latin-1
    fixed = fixed.replace(/Ã¨/g, 'è'); // è
    fixed = fixed.replace(/Ã /g, 'à'); // à
    fixed = fixed.replace(/Ã§/g, 'ç'); // ç
    fixed = fixed.replace(/Ã´/g, 'ô'); // ô
    fixed = fixed.replace(/Ã¢/g, 'â'); // â
    fixed = fixed.replace(/Ãª/g, 'ê'); // ê
    fixed = fixed.replace(/Ã®/g, 'î'); // î
    fixed = fixed.replace(/Ã¹/g, 'ù'); // ù
    fixed = fixed.replace(/Ã»/g, 'û'); // û
    fixed = fixed.replace(/Ã¯/g, 'ï'); // ï
    fixed = fixed.replace(/Ã«/g, 'ë'); // ë
    
    // Fix uppercase accented characters
    fixed = fixed.replace(/Ã‰/g, 'É'); // É
    fixed = fixed.replace(/Ãˆ/g, 'È'); // È
    fixed = fixed.replace(/Ã€/g, 'À'); // À
    fixed = fixed.replace(/Ã‡/g, 'Ç'); // Ç
    fixed = fixed.replace(/Ã"/g, 'Ô'); // Ô
    fixed = fixed.replace(/Ã‚/g, 'Â'); // Â
    fixed = fixed.replace(/ÃŠ/g, 'Ê'); // Ê
    fixed = fixed.replace(/ÃŽ/g, 'Î'); // Î
    fixed = fixed.replace(/Ã™/g, 'Ù'); // Ù
    fixed = fixed.replace(/Ã›/g, 'Û'); // Û
    
    // Remove any remaining problematic characters that may appear in content
    fixed = fixed.replace(/[ØÞÝÜËì¿½]/g, ''); // Remove problematic characters
    
    // Fix additional corruption patterns - PRESERVE NEWLINES (\x0A) and CARRIAGE RETURNS (\x0D)
    fixed = fixed.replace(/[\x00-\x09\x0B\x0C\x0E-\x1F\x7F-\x9F]/g, ''); // Remove control characters but preserve \x0A (newline) and \x0D (carriage return)
    fixed = fixed.replace(/[^\w\sàâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ.,;:!?()\-\n\r]/g, ''); // Keep valid characters and newlines
    fixed = fixed.replace(/[ \t]+/g, ' '); // Normalize spaces and tabs but preserve newlines
    
    // Handle Windows-1252 to UTF-8 conversion issues
    fixed = fixed.replace(/â€™/g, "'"); // right single quotation mark
    fixed = fixed.replace(/â€œ/g, '"'); // left double quotation mark
    fixed = fixed.replace(/â€/g, '"'); // right double quotation mark
    fixed = fixed.replace(/â€¦/g, '…'); // horizontal ellipsis
    fixed = fixed.replace(/â€"/g, '–'); // en dash
    fixed = fixed.replace(/â€"/g, '—'); // em dash
    
    return fixed;
  }

  private addLogoFallback(): void {
    // MongoDB-styled fallback logo
    this.doc.setFillColor(this.colors.primary);
    this.doc.ellipse(25, 19, 3, 4, 'F');
    this.doc.setFillColor(this.colors.white);
    this.doc.ellipse(25, 19, 0.3, 3, 'F');
    this.doc.setTextColor(this.colors.white);
    this.doc.setFontSize(7);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text('MongoDB', 32, 22);
  }

  // Convert markdown formatting to plain text suitable for PDF
  private markdownToText(text: string): string {
    if (!text) return '';
    
    let converted = text;
    
    // First, normalize Unicode to ensure proper character representation
    converted = converted.normalize('NFC');
    
    // Convert markdown headers to plain text with emphasis
    converted = converted.replace(/^#{1,6}\s+(.+)$/gm, '$1'); // Remove header markers
    
    // Convert bold text (**text** or __text__)
    converted = converted.replace(/\*\*([^*]+)\*\*/g, '$1'); // **bold**
    converted = converted.replace(/__([^_]+)__/g, '$1'); // __bold__
    
    // Convert italic text (*text* or _text_)
    converted = converted.replace(/\*([^*]+)\*/g, '$1'); // *italic*
    converted = converted.replace(/_([^_]+)_/g, '$1'); // _italic_
    
    // Convert inline code (`code`)
    converted = converted.replace(/`([^`]+)`/g, '$1'); // `code`
    
    // Convert links [text](url) to just the text
    converted = converted.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
    
    // Convert strikethrough (~~text~~)
    converted = converted.replace(/~~([^~]+)~~/g, '$1');
    
    // Remove code block markers (``` or ```)
    converted = converted.replace(/```[\s\S]*?```/g, (match) => {
      // Extract content between code block markers
      return match.replace(/```[a-z]*\n?/g, '').replace(/```/g, '');
    });
    
    // Convert bullet points (- or * at start of line)
    converted = converted.replace(/^[\s]*[-*+]\s+/gm, '• '); // Convert to bullet points
    
    // Convert numbered lists (1. 2. etc.)
    converted = converted.replace(/^[\s]*\d+\.\s+/gm, '• '); // Convert to bullet points
    
    // Convert horizontal rules (---, ***, ___) to separator text
    converted = converted.replace(/^[\s]*[-*_]{3,}[\s]*$/gm, '───────────────');
    
    // Convert blockquotes (> text)
    converted = converted.replace(/^>\s+/gm, ''); // Remove blockquote markers
    
    // Convert HTML entities commonly found in markdown (more comprehensive list)
    converted = converted.replace(/&lt;/g, '<');
    converted = converted.replace(/&gt;/g, '>');
    converted = converted.replace(/&amp;/g, '&');
    converted = converted.replace(/&quot;/g, '"');
    converted = converted.replace(/&#39;/g, "'");
    converted = converted.replace(/&#x27;/g, "'");
    converted = converted.replace(/&nbsp;/g, ' ');
    converted = converted.replace(/&mdash;/g, '—');
    converted = converted.replace(/&ndash;/g, '–');
    converted = converted.replace(/&hellip;/g, '…');
    converted = converted.replace(/&laquo;/g, '«');
    converted = converted.replace(/&raquo;/g, '»');
    converted = converted.replace(/&agrave;/g, 'à');
    converted = converted.replace(/&acirc;/g, 'â');
    converted = converted.replace(/&eacute;/g, 'é');
    converted = converted.replace(/&egrave;/g, 'è');
    converted = converted.replace(/&ecirc;/g, 'ê');
    converted = converted.replace(/&icirc;/g, 'î');
    converted = converted.replace(/&ocirc;/g, 'ô');
    converted = converted.replace(/&ugrave;/g, 'ù');
    converted = converted.replace(/&ucirc;/g, 'û');
    converted = converted.replace(/&ccedil;/g, 'ç');
    
    // Handle numeric HTML entities
    converted = converted.replace(/&#(\d+);/g, (match, num) => {
      try {
        return String.fromCharCode(parseInt(num, 10));
      } catch {
        return match; // Return original if conversion fails
      }
    });
    
    // Handle hexadecimal HTML entities
    converted = converted.replace(/&#x([0-9a-fA-F]+);/g, (match, hex) => {
      try {
        return String.fromCharCode(parseInt(hex, 16));
      } catch {
        return match; // Return original if conversion fails
      }
    });
    
    // Clean up multiple spaces and line breaks
    converted = converted.replace(/[ \t]+/g, ' '); // Multiple spaces to single space
    converted = converted.replace(/\n{3,}/g, '\n\n'); // Multiple line breaks to double
    
    return converted.trim();
  }

  private addHeader(report: Report): void {
    const headerHeight = 60;

    this.doc.setFillColor(this.colors.white);
    this.doc.rect(0, 0, this.pageWidth, headerHeight, 'F');

    this.doc.setFillColor(this.colors.gray95);
    this.doc.rect(0, headerHeight - 12, this.pageWidth, 12, 'F');

    const logoX = 10;
    const logoY = 14;
    if (this.mongoDBLogoBase64) {
      try {
        this.doc.addImage(this.mongoDBLogoBase64, 'PNG', logoX, logoY - 4, 45, 12);
      } catch (error) {
        this.addLogoFallback();
      }
    } else {
      this.addLogoFallback();
    }

    const textStartX = 60;

    this.doc.setFontSize(10);
    this.doc.setFont('helvetica', 'normal');
    this.doc.setTextColor(this.colors.mongodbGreen);
    this.doc.text('MongoDB Healthcare Analytics', textStartX, 18);

    this.doc.setFontSize(16);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text('Clinical Assessment Report', textStartX, 30);

    this.doc.setFontSize(10);
    this.doc.setFont('helvetica', 'normal');
    this.doc.setTextColor(this.colors.mongodbGreen);
    this.doc.text('Multidisciplinary Team Review', textStartX, 40);

    const statusColor = report.status === 'COMPLETED' ? this.colors.mongodbGreen :
                        report.status === 'PROCESSING' ? this.colors.sunYellow : this.colors.peachOrange;
    const statusText = this.cleanText(report.status);
    const statusWidth = Math.max(36, this.doc.getTextWidth(statusText) + 10);

    this.doc.setFillColor(statusColor);
    this.doc.roundedRect(this.pageWidth - statusWidth - 15, 16, statusWidth, 12, 2, 2, 'F');
    this.doc.setTextColor(this.colors.black);
    this.doc.setFontSize(9);
    this.doc.setFont('helvetica', 'bold');
    const statusX = this.pageWidth - statusWidth - 15 + statusWidth / 2 - this.doc.getTextWidth(statusText) / 2;
    this.doc.text(statusText, statusX, 24);

    this.doc.setTextColor(this.colors.gray30);
    this.doc.setFontSize(9);
    this.doc.setFont('helvetica', 'normal');
    this.doc.text(`Patient: ${this.cleanText(report.patient_id)}`, textStartX, 54);
    this.doc.text(`Generated: ${new Date(report.created_at).toLocaleDateString('en-US')}`, this.pageWidth - 15, 54, { align: 'right' });

    this.currentY = headerHeight + 8;
  }

  private addReportSummary(report: Report): void {
    this.doc.setTextColor(this.colors.dark);
    this.doc.setFontSize(12);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text(this.cleanText('Report Summary'), this.margins.left, this.currentY);
    this.currentY += 8; // Reduced spacing
    
    // Calculate exact height based on actual content layout
    const summaryData = this.prepareSummaryData(report);
    const numberOfRows = Math.ceil(summaryData.length / 2); // 2 columns layout
    const topPadding = 4;
    const bottomPadding = 3;
    const rowHeight = 5;
    const boxHeight = topPadding + (numberOfRows * rowHeight) + bottomPadding; // Precise content-fitting height
    
    this.doc.setFillColor(this.colors.light);
    this.doc.setDrawColor(this.colors.border);
    this.doc.rect(this.margins.left, this.currentY, this.pageWidth - this.margins.left - this.margins.right, boxHeight, 'FD');
    
    let textY = this.currentY + topPadding;
    this.doc.setFontSize(9);
    this.doc.setFont('helvetica', 'normal');
    this.doc.setTextColor(this.colors.secondary);
    
    summaryData.forEach((item, index) => {
      const x = index % 2 === 0 ? this.margins.left + 5 : this.pageWidth / 2 + 5;
      if (index % 2 === 0 && index > 0) textY += rowHeight;
      
      this.doc.setFont('helvetica', 'bold');
      this.doc.text(this.cleanText(item.label) + ':', x, textY);
      this.doc.setFont('helvetica', 'normal');
      const wrappedValue = this.wrapText(item.value, 60);
      wrappedValue.forEach((line, lineIndex) => {
        this.doc.text(line, x + 32, textY + (lineIndex * 3));
      });
    });
    
    this.currentY += boxHeight + 8; // Reduced spacing after summary
  }

  private prepareSummaryData(report: Report) {
    const entitiesCount = this.getEntitiesCount(report);
    const documentsCount = report.metadata?.total_documents_processed || 0;
    
    // Translate labels English for summary (since report content is in French)
    return [
      { label: 'Documents Used', value: documentsCount.toString() },
      { label: 'Entities Extracted', value: entitiesCount.toString() },
      { label: 'File Size', value: this.formatFileSize(report.file_size || 0) },
      { label: 'Words', value: (report.word_count || 0).toString() },
      { label: 'Version', value: report.metadata?.report_version || 'N/A' },
      { label: 'Generated on', value: new Date(report.created_at).toLocaleDateString('en-US') }
    ];
  }

  private async addEntitySections(content: ReportContent, patientId: string, progressCallback?: (progress: number, step: string) => void): Promise<void> {
    const processStartTime = Date.now();
    console.log(`🎯 === PDF SECTION PROCESSING START ===`);
    console.log(`📋 Patient: ${patientId} | LLM summaries: ENABLED`);
    
    const sections = this.organizeSections(content);
    console.log(`📊 Found ${sections.length} sections to process:`);
    sections.forEach((section, index) => {
      console.log(`   ${index + 1}. "${section.title}" (${section.entities.length} entities)`);
    });
    
    const baseProgress = 15; // Starting from where generateReportPDF left off
    const sectionProgressRange = 75; // 15% to 90% = 75% range for sections
    
    // Track summary statistics
    let summaryStats = {
      total: 0,
      llm_success: 0,
      fallback_used: 0,
      failed_empty: 0,
      total_chars: 0,
      avg_response_time: 0
    };
    
    // Generate summaries for each section
    for (let i = 0; i < sections.length; i++) {
      const section = sections[i];
      const sectionStartTime = Date.now();
      
      try {
        console.log(`🔄 === SECTION ${i + 1}/${sections.length}: ${section.title} ===`);
        
        const sectionProgress = baseProgress + ((i / sections.length) * sectionProgressRange);
        progressCallback?.(sectionProgress, `Generating AI summary for ${section.title}...`);
        
        section.summary = await this.generateSectionSummary(section, patientId);
        const sectionDuration = Date.now() - sectionStartTime;
        
        // Analyze summary result
        summaryStats.total++;
        summaryStats.total_chars += (section.summary?.length || 0);
        summaryStats.avg_response_time += sectionDuration;
        
        if (!section.summary || section.summary.trim() === '') {
          summaryStats.failed_empty++;
          console.log(`❌ Section ${i + 1}: EMPTY SUMMARY (${sectionDuration}ms) - will show entity list`);
        } else if (section.summary.includes('is documented as:') || section.summary.includes('is comprehensively documented as:')) {
          summaryStats.fallback_used++;
          console.log(`🔄 Section ${i + 1}: FALLBACK SUMMARY (${sectionDuration}ms) - ${section.summary.length} chars`);
        } else {
          summaryStats.llm_success++;
          console.log(`✅ Section ${i + 1}: LLM SUCCESS (${sectionDuration}ms) - ${section.summary.length} chars`);
        }
        
        progressCallback?.(sectionProgress + (sectionProgressRange / sections.length * 0.7), `Adding ${section.title} to PDF...`);
      } catch (error) {
        const sectionDuration = Date.now() - sectionStartTime;
        summaryStats.total++;
        summaryStats.failed_empty++;
        summaryStats.avg_response_time += sectionDuration;
        
        console.error(`❌ Section ${i + 1}: EXCEPTION (${sectionDuration}ms):`, error);
        section.summary = ''; // Ensure fallback to entity listing
      }
      
      this.addSection(section);
      
      // Better spacing between sections (no forced page breaks)
      if (i < sections.length - 1) {
        this.currentY += 15; // Professional spacing between sections
      }
      
      const completedProgress = baseProgress + (((i + 1) / sections.length) * sectionProgressRange);
      progressCallback?.(completedProgress, `Completed ${i + 1}/${sections.length} sections`);
    }
    
    // Calculate final statistics
    const totalDuration = Date.now() - processStartTime;
    summaryStats.avg_response_time = summaryStats.total > 0 ? Math.round(summaryStats.avg_response_time / summaryStats.total) : 0;
    const avgCharsPerSummary = summaryStats.total > 0 ? Math.round(summaryStats.total_chars / summaryStats.total) : 0;
    
    // Log comprehensive summary
    console.log(`🎯 === PDF SECTION PROCESSING COMPLETE ===`);
    console.log(`⏱️ Total processing time: ${totalDuration}ms (${Math.round(totalDuration/1000)}s)`);
    console.log(`📊 Summary Generation Statistics:`);
    console.log(`   • Total sections processed: ${summaryStats.total}`);
    console.log(`   • LLM successes: ${summaryStats.llm_success} (${Math.round(summaryStats.llm_success/summaryStats.total*100)}%)`);
    console.log(`   • Fallback used: ${summaryStats.fallback_used} (${Math.round(summaryStats.fallback_used/summaryStats.total*100)}%)`);
    console.log(`   • Failed/Empty: ${summaryStats.failed_empty} (${Math.round(summaryStats.failed_empty/summaryStats.total*100)}%)`);
    console.log(`   • Average response time: ${summaryStats.avg_response_time}ms`);
    console.log(`   • Total characters generated: ${summaryStats.total_chars}`);
    console.log(`   • Average characters per summary: ${avgCharsPerSummary}`);
    
    // Provide actionable insights
    if (summaryStats.llm_success === 0) {
      console.error(`🚨 CRITICAL: No LLM summaries were successfully generated!`);
      console.error(`🔍 Check: Backend API, LLM service status, network connectivity`);
    } else if (summaryStats.llm_success < summaryStats.total * 0.5) {
      console.warn(`⚠️ WARNING: LLM success rate is low (${Math.round(summaryStats.llm_success/summaryStats.total*100)}%)`);
      console.warn(`🔍 Check: LLM service performance, timeout settings, entity data quality`);
    } else {
      console.log(`✅ LLM summary generation is working well (${Math.round(summaryStats.llm_success/summaryStats.total*100)}% success rate)`);
    }
  }

  private organizeSections(content: ReportContent): PDFSection[] {
    const allEntities = this.collectAllEntities(content);
    const entitiesBySection = this.groupEntitiesBySection(allEntities);
    
    // Get ALL section names from the data (dynamic discovery)
    const allSectionNames = Object.keys(entitiesBySection);
    
    // Sort sections: known sections first (in predefined order), then unknown sections alphabetically
    // "Autres informations" always goes last
    const sortedSections = allSectionNames.sort((a, b) => {
      const aIndex = this.sectionOrder.indexOf(a);
      const bIndex = this.sectionOrder.indexOf(b);
      
      // Both in predefined order - sort by position
      if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
      // Only a is in order - prioritize it
      if (aIndex !== -1) return -1;
      // Only b is in order - prioritize it
      if (bIndex !== -1) return 1;
      // Neither in order - "Autres informations" goes last
      if (a === "Autres informations") return 1;
      if (b === "Autres informations") return -1;
      // Otherwise sort alphabetically
      return a.localeCompare(b);
    });
    
    // Include ALL sections that have entities (no filtering!)
    return sortedSections
      .filter(sectionName => entitiesBySection[sectionName] && entitiesBySection[sectionName].length > 0)
      .map(sectionName => ({
        title: this.cleanSectionTitle(sectionName),
        entities: this.sortEntitiesInSection(entitiesBySection[sectionName])
      }));
  }

  private collectAllEntities(content: ReportContent): ReportEntity[] {
    const entities: ReportEntity[] = [];
    
    // Prefer ner_results if available, otherwise fallback to individual sections
    if (content.ner_results?.entities) {
      entities.push(...content.ner_results.entities);
    } else {
      if (content.first_match?.found_entities) {
        entities.push(...content.first_match.found_entities);
      }
      if (content.multiple_match?.found_entities) {
        entities.push(...content.multiple_match.found_entities);
      }
      if (content.aggregate_all_matches?.found_entities) {
        entities.push(...content.aggregate_all_matches.found_entities);
      }
    }
    
    return entities;
  }

  private groupEntitiesBySection(entities: ReportEntity[]): Record<string, ReportEntity[]> {
    const grouped: Record<string, ReportEntity[]> = {};
    
    entities.forEach(entity => {
      const sectionName = (reportGroupingConfig as Record<string, string>)[entity.entity_name] || "Autres informations";
      
      if (!grouped[sectionName]) {
        grouped[sectionName] = [];
      }
      grouped[sectionName].push(entity);
    });
    
    return grouped;
  }

  private sortEntitiesInSection(entities: ReportEntity[]): ReportEntity[] {
    return entities.sort((a, b) => {
      const aIndex = this.entityOrder.indexOf(a.entity_name);
      const bIndex = this.entityOrder.indexOf(b.entity_name);
      
      // If both are in the order list, sort by position
      if (aIndex !== -1 && bIndex !== -1) {
        return aIndex - bIndex;
      }
      
      // If only one is in the list, prioritize it
      if (aIndex !== -1) return -1;
      if (bIndex !== -1) return 1;
      
      // If neither is in the list, sort alphabetically
      return a.entity_name.localeCompare(b.entity_name);
    });
  }

  private addSection(section: PDFSection): void {
    // Calculate content height first to ensure title and content stay together
    let contentHeight = 0;
    if (section.summary && section.summary.trim()) {
      // Calculate summary height
      this.doc.setFontSize(10);
      this.doc.setFont('helvetica', 'normal');
      const summaryText = this.cleanText(section.summary);
      const wrappedText = this.wrapText(summaryText, this.pageWidth - this.margins.left - this.margins.right);
      contentHeight = wrappedText.length * 6 + 8; // lineHeight * lines + spacing
    } else {
      // Calculate entities height
      section.entities.forEach((entity) => {
        contentHeight += this.calculateEntityHeight(entity) + 2; // Small spacing between entities
      });
    }
    
    const titleHeight = 22;
    const totalHeight = titleHeight + contentHeight + 18; // title + content + final spacing
    
    // Force page break before each section (except the first one)
    if (this.currentY > 100) { // If we're past the header area, start a new page
      this.doc.addPage();
      this.currentY = this.margins.top;
    } else {
      // For first section, ensure we have space for the complete section
      this.addPageIfNeeded(totalHeight);
    }
    
    // Now ensure we have space for the complete section on current page
    this.addPageIfNeeded(totalHeight);
    
    // Section title - consistent MongoDB green styling
    this.doc.setTextColor(this.colors.mongodbGreen); // Explicit MongoDB green
    this.doc.setFontSize(13); // Slightly larger for better hierarchy
    this.doc.setFont('helvetica', 'bold');
    this.doc.text(section.title, this.margins.left, this.currentY + 14);
    
    this.currentY += 22; // Better spacing for larger title
    
    // Display summary if available, otherwise fall back to entities
    if (section.summary && section.summary.trim()) {
      this.addSectionSummaryNoPageCheck(section.summary);
    } else {
      // Fallback to entity listing
      section.entities.forEach((entity, index) => {
        this.addEntityNoPageCheck(entity, index % 2 === 0);
      });
    }
    
    this.currentY += 18; // Consistent spacing after section
  }

  private addSectionSummary(summary: string): void {
    // Set font properties FIRST so wrapText uses correct measurements
    this.doc.setTextColor(this.colors.dark);
    this.doc.setFontSize(10);
    this.doc.setFont('helvetica', 'normal');
    
    // Summary text without background box - just plain text
    const summaryText = this.cleanText(summary);
    const wrappedText = this.wrapText(summaryText, this.pageWidth - this.margins.left - this.margins.right);
    
    // Simple height calculation for text only
    const lineHeight = 6; 
    const summaryHeight = wrappedText.length * lineHeight;
    
    this.addPageIfNeeded(summaryHeight + 10);
    
    let textY = this.currentY;
    wrappedText.forEach(line => {
      // Check if we need a new page for this line
      if (textY > this.pageHeight - this.margins.bottom - 10) {
        this.doc.addPage();
        this.currentY = this.margins.top;
        textY = this.currentY;
        
        // Reset text properties on new page
        this.doc.setTextColor(this.colors.dark);
        this.doc.setFontSize(10);
        this.doc.setFont('helvetica', 'normal');
      }
      
      this.doc.text(line, this.margins.left, textY);
      textY += lineHeight;
    });
    
    this.currentY += summaryHeight + 8; // Space after summary
  }
  
  private addSectionSummaryNoPageCheck(summary: string): void {
    // Set font properties FIRST so wrapText uses correct measurements
    this.doc.setTextColor(this.colors.dark);
    this.doc.setFontSize(10);
    this.doc.setFont('helvetica', 'normal');
    
    // Summary text without background box - just plain text
    const summaryText = this.cleanText(summary);
    const wrappedText = this.wrapText(summaryText, this.pageWidth - this.margins.left - this.margins.right);
    
    // Simple height calculation for text only
    const lineHeight = 6;
    
    let textY = this.currentY;
    wrappedText.forEach(line => {
      this.doc.text(line, this.margins.left, textY);
      textY += lineHeight;
    });
    
    this.currentY = textY + 8; // Space after summary
  }

  private async generateSectionSummary(section: PDFSection, patientId: string): Promise<string> {
    const startTime = Date.now();
    const sectionId = `${section.title}_${Math.random().toString(36).substr(2, 9)}`;
    
    try {
      console.log(`🎯 [${sectionId}] === LLM SUMMARY GENERATION START ===`);
      console.log(`🔄 [${sectionId}] Section: "${section.title}" | Patient: ${patientId} | Entities: ${section.entities.length}`);
      
      // Better entity filtering - check for actual meaningful values
      const entitiesWithValues = section.entities.filter(entity => {
        const value = entity.aggregated_value || entity.value;
        if (!value) return false;
        
        // Handle different value types
        if (Array.isArray(value)) {
          return value.some(v => v && String(v).trim().length > 0);
        }
        
        const valueStr = String(value).trim();
        return valueStr.length > 0 && valueStr !== 'null' && valueStr !== 'undefined';
      });
      
      console.log(`📊 [${sectionId}] Entity filtering: ${entitiesWithValues.length}/${section.entities.length} have meaningful values`);
      console.log(`🔍 [${sectionId}] Sample entities:`, entitiesWithValues.slice(0, 2).map(e => ({
        name: e.entity_name, 
        value: String(e.aggregated_value || e.value).substring(0, 100) + (String(e.aggregated_value || e.value).length > 100 ? '...' : '')
      })));
      
      if (entitiesWithValues.length === 0) {
        console.log(`⚠️ [${sectionId}] SKIP: No entities with meaningful values for ${section.title}`);
        return '';
      }
      
      // Import API service
      console.log(`🔧 [${sectionId}] Loading API service...`);
      const { apiService } = await import('./api');
      
      // Prepare comprehensive entity data
      const entityData = entitiesWithValues.map(entity => {
        let value = entity.aggregated_value || entity.value;
        
        // Handle array values
        if (Array.isArray(value)) {
          value = value.filter(v => v && String(v).trim()).join('; ');
        }
        
        return {
          name: entity.entity_name,
          value: String(value).trim(),
          processing_type: entity.processing_type
        };
      });
      
      console.log(`📤 [${sectionId}] Sending API request to /patients/${patientId}/reports/section-summary`);
      console.log(`📊 [${sectionId}] Payload: ${entityData.length} entities | Timeout: 60s`);
      console.log(`🔍 [${sectionId}] Sample entity data:`, entityData.slice(0, 2).map(e => ({
        name: e.name,
        valueLength: e.value.length,
        valuePreview: e.value.substring(0, 150) + (e.value.length > 150 ? '...' : '')
      })));
      
      const requestStartTime = Date.now();
      
      // Call API to generate section summary with extended timeout
      const response = await apiService.api.post(`/patients/${patientId}/reports/section-summary`, {
        section_title: section.title,
        entities: entityData
      }, {
        timeout: 60000  // 60 seconds for comprehensive summary generation
      });
      
      const requestDuration = Date.now() - requestStartTime;
      console.log(`📥 [${sectionId}] API Response received in ${requestDuration}ms`);
      console.log(`📊 [${sectionId}] Response status: ${response.status} | Data available: ${!!response.data}`);
      console.log(`🔍 [${sectionId}] Response structure:`, Object.keys(response.data || {}));
      
      const summary = response.data?.summary || '';
      console.log(`📊 [${sectionId}] Summary extracted: ${summary.length} characters`);
      
      if (!summary) {
        console.warn(`⚠️ [${sectionId}] EMPTY SUMMARY: API returned empty or null summary`);
        console.log(`🔍 [${sectionId}] Full API response:`, response.data);
        return '';
      }
      
      // Analyze the summary type and quality
      const analysisTime = Date.now();
      let summaryType = 'UNKNOWN';
      let qualityScore = 'POOR';
      
      if (summary.includes('is documented as:') || summary.includes('is comprehensively documented as:')) {
        summaryType = 'FALLBACK';
        qualityScore = 'BASIC';
        console.log(`🔄 [${sectionId}] FALLBACK SUMMARY DETECTED (backend fallback function used)`);
        console.log(`⚠️ [${sectionId}] This indicates LLM generation failed or returned insufficient content`);
      } else if (summary.length < 100) {
        summaryType = 'SHORT';
        qualityScore = 'POOR';
        console.log(`⚠️ [${sectionId}] SHORT SUMMARY (likely LLM failure or minimal content)`);
      } else if (summary.length > 200 && !summary.includes('documented as')) {
        summaryType = 'LLM_COMPREHENSIVE';
        qualityScore = 'GOOD';
        console.log(`🤖 [${sectionId}] COMPREHENSIVE LLM SUMMARY (likely successful AI generation)`);
      } else {
        summaryType = 'LLM_BASIC';
        qualityScore = 'FAIR';
        console.log(`🤖 [${sectionId}] BASIC LLM SUMMARY (successful but limited AI generation)`);
      }
      
      const totalDuration = Date.now() - startTime;
      console.log(`✅ [${sectionId}] === SUMMARY GENERATION COMPLETE ===`);
      console.log(`📊 [${sectionId}] Summary type: ${summaryType} | Quality: ${qualityScore} | Length: ${summary.length} chars`);
      console.log(`⏱️ [${sectionId}] Total time: ${totalDuration}ms (API: ${requestDuration}ms, Analysis: ${Date.now() - analysisTime}ms)`);
      console.log(`📝 [${sectionId}] Summary preview (first 200 chars):`, summary.substring(0, 200) + (summary.length > 200 ? '...' : ''));
      
      if (summaryType === 'FALLBACK') {
        console.warn(`🚨 [${sectionId}] ACTION NEEDED: LLM summary generation is not working properly for this section`);
      }
      
      return summary;
      
    } catch (error) {
      const totalDuration = Date.now() - startTime;
      console.error(`❌ [${sectionId}] === SUMMARY GENERATION FAILED ===`);
      console.error(`❌ [${sectionId}] Error after ${totalDuration}ms:`, error);
      console.error(`❌ [${sectionId}] Error type: ${(error as Error).constructor.name}`);
      console.error(`❌ [${sectionId}] Error message:`, (error as Error).message);
      
      if ((error as any).response) {
        console.error(`❌ [${sectionId}] HTTP Status:`, (error as any).response.status);
        console.error(`❌ [${sectionId}] Response data:`, (error as any).response.data);
        console.error(`❌ [${sectionId}] Response headers:`, (error as any).response.headers);
      } else if ((error as any).request) {
        console.error(`❌ [${sectionId}] Network error - request made but no response`);
        console.error(`❌ [${sectionId}] Request details:`, (error as any).request);
      } else {
        console.error(`❌ [${sectionId}] Setup error:`, (error as Error).message);
      }
      
      console.error(`❌ [${sectionId}] Full error stack:`, (error as Error).stack);
      console.warn(`🔄 [${sectionId}] Returning empty string - PDF will fall back to entity listing`);
      return ''; // Return empty string to trigger fallback
    }
  }

  private addEntity(entity: ReportEntity, isEven: boolean): void {
    const entityHeight = this.calculateEntityHeight(entity);
    this.addPageIfNeeded(entityHeight + 5); // Add buffer space
    
    const startY = this.currentY;
    
    // Entity background (alternating colors)
    const bgColor = isEven ? '#ffffff' : this.colors.light;
    this.doc.setFillColor(bgColor);
    this.doc.rect(this.margins.left, startY, this.pageWidth - this.margins.left - this.margins.right, entityHeight, 'F');
    
    // Entity border
    this.doc.setDrawColor(this.colors.border);
    this.doc.rect(this.margins.left, startY, this.pageWidth - this.margins.left - this.margins.right, entityHeight, 'D');
    
    // Entity name - clean text to fix invalid characters
    this.doc.setTextColor(this.colors.primary);
    this.doc.setFontSize(11);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text(this.cleanText(entity.entity_name), this.margins.left + 5, startY + 10);
    
    // Add entity values
    let currentEntityY = startY + 16;
    entity.values?.forEach((value, index) => {
      if (currentEntityY > this.pageHeight - this.margins.bottom - 20) {
        this.doc.addPage();
        this.currentY = this.margins.top;
        currentEntityY = this.currentY;
      }
      
      this.doc.setTextColor(this.colors.gray60);
      this.doc.setFontSize(9);
      this.doc.setFont('helvetica', 'normal');
      
      // Value text with proper cleaning
      const valueText = this.cleanText(value.value);
      const maxWidth = this.pageWidth - this.margins.left - this.margins.right - 10;
      const wrappedValueLines = this.wrapText(valueText, maxWidth);
      
      wrappedValueLines.forEach(line => {
        this.doc.text(line, this.margins.left + 5, currentEntityY);
        currentEntityY += 5;
      });
      
      if (index < (entity.values?.length ?? 0) - 1) {
        currentEntityY += 2;
      }
    });
    
    this.currentY = currentEntityY + 5;
  }
  
  private addEntityNoPageCheck(entity: ReportEntity, isEven: boolean): void {
    const entityHeight = this.calculateEntityHeight(entity);
    
    const startY = this.currentY;
    
    // Entity background (alternating colors)
    const bgColor = isEven ? '#ffffff' : this.colors.light;
    this.doc.setFillColor(bgColor);
    this.doc.rect(this.margins.left, startY, this.pageWidth - this.margins.left - this.margins.right, entityHeight, 'F');
    
    // Entity border
    this.doc.setDrawColor(this.colors.border);
    this.doc.rect(this.margins.left, startY, this.pageWidth - this.margins.left - this.margins.right, entityHeight, 'D');
    
    // Entity name - clean text to fix invalid characters
    this.doc.setTextColor(this.colors.primary);
    this.doc.setFontSize(11);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text(this.cleanText(entity.entity_name), this.margins.left + 5, startY + 10);
    
    // Add entity values
    let currentEntityY = startY + 16;
    entity.values?.forEach((value, index) => {
      this.doc.setTextColor(this.colors.gray60);
      this.doc.setFontSize(9);
      this.doc.setFont('helvetica', 'normal');
      
      // Value text with proper cleaning
      const valueText = this.cleanText(value.value);
      const maxWidth = this.pageWidth - this.margins.left - this.margins.right - 10;
      const wrappedValueLines = this.wrapText(valueText, maxWidth);
      
      wrappedValueLines.forEach(line => {
        this.doc.text(line, this.margins.left + 5, currentEntityY);
        currentEntityY += 5;
      });
      
      if (index < (entity.values?.length ?? 0) - 1) {
        currentEntityY += 2;
      }
    });
    
    this.currentY = currentEntityY + 5;
  }

  private getEntityDisplayValue(entity: ReportEntity): string {
    // Priority: aggregated_value > value > values array
    if (entity.aggregated_value && entity.aggregated_value.trim()) {
      return this.cleanText(entity.aggregated_value);
    }
    
    if (entity.value) {
      // Handle array values (multiple_match processing type)
      if (Array.isArray(entity.value)) {
        if (entity.value.length === 0) {
          return 'No value found';
        }
        return entity.value
          .filter(v => v && v.trim())
          .map(v => this.cleanText(v))
          .join(' • ');
      }
      // Handle string values (first_match, aggregate_all_matches processing types)
      else if (entity.value.trim()) {
        return this.cleanText(entity.value);
      }
    }
    
    if (entity.values && entity.values.length > 0) {
      return entity.values
        .map(v => this.cleanText(v.value))
        .filter(v => v && v.trim())
        .join(' • ');
    }
    
    return 'Value not available';
  }

  private calculateEntityHeight(entity: ReportEntity): number {
    // Set consistent font properties for accurate width measurements
    this.doc.setFontSize(10);
    this.doc.setFont('helvetica', 'normal');
    
    const baseHeight = 25; // Base height for entity header
    let contentHeight = 0;
    
    // Calculate height based on entity type
    if (entity.processing_type === 'multiple_match' && Array.isArray(entity.value)) {
      if (entity.value.length > 0) {
        // Calculate height for each list item
        entity.value.forEach(item => {
          if (item && item.trim()) {
            const wrappedLines = this.wrapText(item, this.pageWidth - this.margins.left - this.margins.right - 15);
            contentHeight += Math.max(5, wrappedLines.length * 5) + 2; // Space between items
          }
        });
      } else {
        contentHeight = 8; // Height for "no values found" message
      }
    } else {
      // Handle single values (including aggregate_all_matches with long text)
      const value = this.getEntityDisplayValue(entity);
      const wrappedLines = this.wrapText(value, this.pageWidth - this.margins.left - this.margins.right);
      contentHeight = wrappedLines.length * 5;
      
      // Add extra padding for very long texts (more than 10 lines)
      if (wrappedLines.length > 10) {
        contentHeight += 10; // Extra padding for readability
      }
    }
    
    // Calculate source information height
    let sourceHeight = 0;
    if (entity.metadata) {
      // Account for documents_mobilises (prioritized in rendering) - ALL documents
      if (entity.metadata.documents_mobilises && Array.isArray(entity.metadata.documents_mobilises) && entity.metadata.documents_mobilises.length > 0) {
        const docsMobilises = entity.metadata.documents_mobilises as any[];
        
        let calculatedDocsHeight = 3 + 4; // Initial padding + header line
        
        // Calculate height for ALL documents (no limit!)
        for (const doc of docsMobilises) {
          const dateStr = doc?.date || '--------';
          const typeStr = doc?.libnatcr || 'Unknown';
          const titleStr = doc?.title ? ` - ${doc.title}` : '';
          const docText = `• [${dateStr}] ${typeStr}${titleStr}`;
          const maxDocWidth = this.pageWidth - this.margins.left - this.margins.right - 20;
          const docWrappedLines = this.wrapText(docText, maxDocWidth);
          calculatedDocsHeight += Math.max(4, docWrappedLines.length * 5);
        }
        
        // Add extra safety padding
        calculatedDocsHeight += 20;
        
        // Add height for source file info shown after documents_mobilises
        if (entity.metadata.filename) {
          calculatedDocsHeight += 8; // Source line
          if (entity.metadata.section_id || entity.metadata.page_id) {
            calculatedDocsHeight += 4; // Section/page line
          }
        }
        
        sourceHeight = calculatedDocsHeight;
      }
      // Fallback to sources calculation - ALL sources
      else if (entity.processing_type === 'aggregate_all_matches' && entity.metadata.sources && Array.isArray(entity.metadata.sources)) {
        // Calculate height for ALL sources
        const uniqueSources = entity.metadata.sources.filter((source: any, index: number, arr: any[]) => 
          arr.findIndex((s: any) => s.filename === source.filename) === index
        );
        
        let calculatedSourceHeight = 3 + 4; // Initial padding + header line
        
        // Calculate height for ALL sources (no limit!)
        for (const source of uniqueSources) {
          if (source && source.filename) {
            const sourceText = `• ${this.cleanText(source.filename)}`;
            const maxSourceWidth = this.pageWidth - this.margins.left - this.margins.right - 20;
            const sourceWrappedLines = this.wrapText(sourceText, maxSourceWidth);
            calculatedSourceHeight += Math.max(4, sourceWrappedLines.length * 5);
          } else {
            calculatedSourceHeight += 5;
          }
        }
        
        // Add extra safety padding
        calculatedSourceHeight += 20;
        
        sourceHeight = calculatedSourceHeight;
      } else if (entity.metadata.filename) {
        sourceHeight = 15; // For single source
        // Add height for section/page info
        if (entity.metadata.section_id || entity.metadata.page_id) {
          sourceHeight += 8;
        }
      }
    }
    
    // Calculate total height with proper spacing
    const totalContentHeight = contentHeight + sourceHeight;
    const paddingHeight = Math.max(30, totalContentHeight * 0.15); // Increased minimum padding and percentage
    
    return Math.max(baseHeight, totalContentHeight + paddingHeight);
  }

  private wrapText(text: string, maxWidth: number): string[] {
    if (!text || text.trim() === '') return [''];
    
    // Clean and normalize text - preserve newlines
    const cleanedText = this.cleanText(text);
    
    // First split by explicit newlines to honor manual line breaks
    const paragraphs = cleanedText.split(/\r?\n/);
    const allLines: string[] = [];
    
    paragraphs.forEach(paragraph => {
      if (!paragraph.trim()) {
        // Empty line - add it to preserve spacing
        allLines.push('');
        return;
      }
      
      // Wrap each paragraph separately
      const words = paragraph.split(/\s+/); // Split on whitespace
      let currentLine = '';
      
      words.forEach(word => {
        if (!word) return; // Skip empty words
        
        const testLine = currentLine ? `${currentLine} ${word}` : word;
        const textWidth = this.doc.getTextWidth(testLine);
        
        if (textWidth <= maxWidth) {
          currentLine = testLine;
        } else {
          if (currentLine) {
            allLines.push(currentLine);
            
            // Check if the single word is too long
            if (this.doc.getTextWidth(word) > maxWidth) {
              // Break long words by character
              const brokenWords = this.breakLongWord(word, maxWidth);
              allLines.push(...brokenWords.slice(0, -1)); // Add all but last
              currentLine = brokenWords[brokenWords.length - 1]; // Last part becomes current line
            } else {
              currentLine = word;
            }
          } else {
            // Single word is too long, break it
            const brokenWords = this.breakLongWord(word, maxWidth);
            allLines.push(...brokenWords.slice(0, -1)); // Add all but last
            currentLine = brokenWords[brokenWords.length - 1]; // Last part becomes current line
          }
        }
      });
      
      if (currentLine) {
        allLines.push(currentLine);
      }
    });
    
    return allLines.length > 0 ? allLines : [''];
  }

  // Helper function to break long words
  private breakLongWord(word: string, maxWidth: number): string[] {
    const chars = word.split('');
    const lines: string[] = [];
    let currentLine = '';
    
    chars.forEach(char => {
      const testLine = currentLine + char;
      if (this.doc.getTextWidth(testLine) <= maxWidth) {
        currentLine = testLine;
      } else {
        if (currentLine) {
          lines.push(currentLine);
        }
        currentLine = char;
      }
    });
    
    if (currentLine) {
      lines.push(currentLine);
    }
    
    return lines.length > 0 ? lines : [word];
  }

  private addPageIfNeeded(requiredHeight: number): void {
    if (this.currentY + requiredHeight > this.pageHeight - this.margins.bottom) {
      this.doc.addPage();
      this.currentY = this.margins.top;
    }
  }

  private addFooter(report: Report): void {
    const totalPages = this.doc.getNumberOfPages();
    
    for (let i = 1; i <= totalPages; i++) {
      this.doc.setPage(i);
      
      // Footer line - moved higher to accommodate disclaimer
      this.doc.setDrawColor(this.colors.border);
      this.doc.line(this.margins.left, this.pageHeight - 25, this.pageWidth - this.margins.right, this.pageHeight - 25);
      
      // Footer text - moved higher to accommodate disclaimer
      this.doc.setTextColor(this.colors.secondary);
      this.doc.setFontSize(8);
      this.doc.setFont('helvetica', 'normal');
      
      // Left: Report info
      this.doc.text(`MDT Report - ${report.patient_id}`, this.margins.left, this.pageHeight - 20);
      
      // Center: Generation date
      const dateText = `Generated on ${new Date(report.created_at).toLocaleDateString('en-US')}`;
      const dateWidth = this.doc.getTextWidth(dateText);
      this.doc.text(dateText, (this.pageWidth - dateWidth) / 2, this.pageHeight - 20);
      
      // Right: Page numbers
      const pageText = `Page ${i} of ${totalPages}`;
      const pageWidth = this.doc.getTextWidth(pageText);
      this.doc.text(pageText, this.pageWidth - this.margins.right - pageWidth, this.pageHeight - 20);
    }
  }

  private getProcessingTypeColor(type: string): string {
    switch (type) {
      case 'first_match': return this.colors.success;
      case 'multiple_match': return this.colors.warning;
      case 'aggregate_all_matches': return this.colors.primary;
      default: return this.colors.secondary;
    }
  }

  private getEntitiesCount(report: Report): number {
    if (!report.content) return 0;
    
    // Check for new structure first (ner_results.entities)
    if (report.content.ner_results?.entities) {
      return report.content.ner_results.entities.length;
    }
    
    // Check for summary count if available
    if (report.content.ner_results?.summary?.total_entities) {
      return report.content.ner_results.summary.total_entities;
    }
    
    // Check content.summary for total count
    if (report.content.summary?.entities_extracted) {
      return report.content.summary.entities_extracted;
    }
    
    // Fallback to counting from individual sections
    let count = 0;
    if (report.content.first_match?.found_entities) {
      count += report.content.first_match.found_entities.length;
    }
    if (report.content.multiple_match?.found_entities) {
      count += report.content.multiple_match.found_entities.length;
    }
    if (report.content.aggregate_all_matches?.found_entities) {
      count += report.content.aggregate_all_matches.found_entities.length;
    }
    
    // Try to extract from collectAllEntities method for consistency
    if (count === 0) {
      const allEntities = this.collectAllEntities(report.content);
      return allEntities.length;
    }
    
    return count;
  }

  private formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // Clean and validate section titles
  private cleanSectionTitle(title: string): string {
    if (!title) return 'Section';
    
    // Check if we have a direct mapping for this title
    if (this.cleanSectionTitles[title]) {
      return this.cleanSectionTitles[title];
    }
    
    // Apply basic text cleaning and normalization
    let cleaned = this.cleanText(title).trim();
    
    // Check again after cleaning
    if (this.cleanSectionTitles[cleaned]) {
      return this.cleanSectionTitles[cleaned];
    }
    
    // If no mapping found, return the cleaned version
    return cleaned || 'Section inconnue';
  }

  private addPageDisclaimers(): void {
    const disclaimerText = 'Generated by AI — Not for clinical use.';
    const totalPages = this.doc.getNumberOfPages();
    
    for (let i = 1; i <= totalPages; i++) {
      this.doc.setPage(i);
      
      // Top margin disclaimer (skip on first page to avoid header overlap)
      if (i > 1) {
        // Subtle border line above disclaimer
        this.doc.setDrawColor('#E5E7EB');
        this.doc.setLineWidth(0.1);
        this.doc.line(this.margins.left, 10, this.pageWidth - this.margins.right, 10);
        
        // Top disclaimer text
        this.doc.setTextColor('#6B7280'); // Medium gray for better visibility
        this.doc.setFontSize(7);
        this.doc.setFont('helvetica', 'italic');
        
        const topWidth = this.doc.getTextWidth(disclaimerText);
        const topX = (this.pageWidth - topWidth) / 2;
        this.doc.text(disclaimerText, topX, 13); // Below the line
      }
      
      // Bottom margin disclaimer with subtle styling
      // Subtle border line above disclaimer
      this.doc.setDrawColor('#E5E7EB');
      this.doc.setLineWidth(0.1);
      this.doc.line(this.margins.left, this.pageHeight - 12, this.pageWidth - this.margins.right, this.pageHeight - 12);
      
      // Bottom disclaimer text
      this.doc.setTextColor('#6B7280'); // Medium gray for better visibility
      this.doc.setFontSize(7);
      this.doc.setFont('helvetica', 'italic');
      
      const bottomWidth = this.doc.getTextWidth(disclaimerText);
      const bottomX = (this.pageWidth - bottomWidth) / 2;
      this.doc.text(disclaimerText, bottomX, this.pageHeight - 8); // Above the existing footer
    }
  }
}

// Export function for easy usage
export const generateMedicalReportPDF = async (
  report: Report, 
  progressCallback?: (progress: number, step: string) => void
): Promise<Blob> => {
  const generator = new MedicalPDFGenerator();
  return await generator.generateReportPDF(report, progressCallback);
};

export default MedicalPDFGenerator;