import { jsPDF } from 'jspdf';
import 'jspdf-autotable';
import { Report, ReportEntity, ReportContent } from '../types';
import reportGroupingConfig from '../config/report_grouping_config.json';

interface PDFSection {
  title: string;
  entities: ReportEntity[];
}

class MedicalPDFGenerator {
  private doc: jsPDF;
  private pageWidth: number;
  private pageHeight: number;
  private margins = { top: 30, right: 15, bottom: 30, left: 15 };
  private currentY: number = 0;
  private readonly colors = {
    primary: '#2563eb',    // Blue-600
    secondary: '#64748b',  // Slate-500
    success: '#16a34a',    // Green-600
    warning: '#d97706',    // Amber-600
    danger: '#dc2626',     // Red-600
    light: '#f8fafc',      // Slate-50
    dark: '#1e293b',       // Slate-800
    border: '#e2e8f0'      // Slate-200
  };

  // Entity ordering based on medical importance
  private readonly entityOrder = [
    "NumdosGR",
    "Nom de naissance",
    "Prénom", 
    "Sexe",
    "Date de naissance",
    "Antécédents familiaux",
    "Adresse postale",
    "Adresse électronique",
    "Hôpital",
    "Antécédents",
    "Diagnostiqué le",
    "Date de diagnostic",
    "Localisation",
    "Chimiothérapie(s) réalisée(s)",
    "Type histologique",
    "Radiothérapie réalisée",
    "Métastases à distance",
    "Chirurgie(s) réalisée(s)",
    "État général (OMS)",
    "Score G8",
    "Antécédents personnels notables",
    "Site demandeur",
    "Spécialité(s) Sollicitée",
    "Localisations du cancer",
    "Commentaire tumeur primitive",
    "Anomalie moléculaire",
    "Métastatique",
    "Site métastatique",
    "CIM-O-3",
    "Date de présentation",
    "Motifs de présentation",
    "Question posée à la RCP",
    "Proposition de la RCP",
    "Thérapie innovante",
    "Traitement hors AMM",
    "Inclusion dans un essai thérapeutique",
    "Demande complément d'examen complémentaire",
    "EVASAN"
  ];

  // Section ordering for known sections (dynamic sections will be added after these)
  private readonly sectionOrder = [
    "Informations sur le patient",
    "Rappel clinique", 
    "Caractéristiques patients et tumorales",
    "Motif de présentation",
    "Proposition DRAFT Système",
    "Proposition RCP (EXPÉRIMENTAL - Validation médicale requise)"
  ];

  // Clean section titles mapping (shorten long titles for PDF)
  private readonly cleanSectionTitles: Record<string, string> = {
    "Informations sur le patient": "Informations sur le patient",
    "Rappel clinique": "Rappel clinique",
    "Caractéristiques patients et tumorales": "Caractéristiques patients et tumorales",
    "Motif de présentation": "Motif de présentation",
    "Proposition DRAFT Système": "Proposition DRAFT Système",
    "Proposition RCP (EXPÉRIMENTAL - Validation médicale requise)": "Proposition RCP",
    "Autres informations": "Autres informations",
    // Handle legacy misspelling (missing accent)
    "Caracteristiques patients et tumorales": "Caractéristiques patients et tumorales"
  };

  constructor() {
    this.doc = new jsPDF('portrait', 'mm', 'a4');
    this.pageWidth = this.doc.internal.pageSize.getWidth();
    this.pageHeight = this.doc.internal.pageSize.getHeight();
    this.currentY = this.margins.top;
    
    // Configure PDF for proper UTF-8 support
    try {
      // Set default font to support French characters
      this.doc.setFont('helvetica', 'normal');
      
      // Set document properties for proper encoding
      this.doc.setProperties({
        title: 'Rapport MDT',
        subject: 'Rapport de Réunion de Concertation Pluridisciplinaire',
        author: 'Institut Gustave Roussy',
        creator: 'Système MDT'
      });
    } catch (error) {
      console.warn('PDF configuration warning:', error);
    }
  }

  public generateReportPDF(report: Report): Blob {
    this.addHeader(report);
    this.addReportSummary(report);
    
    if (report.content) {
      this.addEntitySections(report.content);
    }
    
    this.addFooter(report);
    this.addPageDisclaimers(); // Add AI-generated disclaimers to all pages
    
    return this.doc.output('blob');
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
    const headerHeight = 60; // Further increased height to prevent overlap
    
    // Header background
    this.doc.setFillColor(this.colors.primary);
    this.doc.rect(0, 0, this.pageWidth, headerHeight, 'F');
    
    // Logo placeholder (you can replace with actual logo)
    this.doc.setFillColor('#ffffff');
    this.doc.circle(25, 25, 8, 'F');
    this.doc.setTextColor('#2563eb');
    this.doc.setFontSize(12);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text('GR', 22, 28);
    
    // Institution name at the top
    this.doc.setTextColor('#ffffff');
    this.doc.setFontSize(11);
    this.doc.setFont('helvetica', 'normal');
    this.doc.text('Institut Gustave Roussy', 45, 18);
    
    // Main title - positioned below institution name
    this.doc.setTextColor('#ffffff');
    this.doc.setFontSize(16); // Slightly smaller to fit better
    this.doc.setFont('helvetica', 'bold');
    this.doc.text('RAPPORT DE RCP', 45, 30);
    
    // Status badge - positioned at top right with more space
    const statusColor = report.status === 'COMPLETED' ? this.colors.success : 
                       report.status === 'PROCESSING' ? this.colors.warning : this.colors.danger;
    const statusText = this.cleanText(report.status);
    const statusWidth = Math.max(30, this.doc.getTextWidth(statusText) + 8); // Dynamic width
    
    this.doc.setFillColor(statusColor);
    this.doc.roundedRect(this.pageWidth - statusWidth - 10, 10, statusWidth, 10, 2, 2, 'F');
    this.doc.setTextColor('#ffffff');
    this.doc.setFontSize(9);
    this.doc.setFont('helvetica', 'bold');
    
    // Center the status text in the badge
    const statusX = this.pageWidth - statusWidth - 10 + statusWidth/2 - this.doc.getTextWidth(statusText)/2;
    this.doc.text(statusText, statusX, 17);
    
    // Patient info in header - well separated from title and status
    this.doc.setTextColor('#ffffff');
    this.doc.setFontSize(10);
    this.doc.setFont('helvetica', 'normal');
    this.doc.text(`Patient: ${this.cleanText(report.patient_id)}`, 45, 42);
    this.doc.text(`Généré le: ${new Date(report.created_at).toLocaleDateString('fr-FR')}`, 45, 52);
    
    this.currentY = headerHeight + 15; // Proper spacing after header
  }

  private addReportSummary(report: Report): void {
    this.doc.setTextColor(this.colors.dark);
    this.doc.setFontSize(14);
    this.doc.setFont('helvetica', 'bold');
    this.doc.text(this.cleanText('Résumé du Rapport'), this.margins.left, this.currentY);
    this.currentY += 15; // Increased spacing
    
    // Summary box with dynamic height
    const summaryData = this.prepareSummaryData(report);
    const boxHeight = Math.max(40, summaryData.length * 8 + 15); // Dynamic height
    
    this.doc.setFillColor(this.colors.light);
    this.doc.setDrawColor(this.colors.border);
    this.doc.rect(this.margins.left, this.currentY, this.pageWidth - this.margins.left - this.margins.right, boxHeight, 'FD');
    
    let textY = this.currentY + 8;
    this.doc.setFontSize(10);
    this.doc.setFont('helvetica', 'normal');
    this.doc.setTextColor(this.colors.secondary);
    
    summaryData.forEach((item, index) => {
      const x = index % 2 === 0 ? this.margins.left + 5 : this.pageWidth / 2 + 5;
      if (index % 2 === 0 && index > 0) textY += 8; // Increased line spacing
      
      this.doc.setFont('helvetica', 'bold');
      this.doc.text(this.cleanText(item.label) + ':', x, textY);
      this.doc.setFont('helvetica', 'normal');
      const wrappedValue = this.wrapText(item.value, 60);
      wrappedValue.forEach((line, lineIndex) => {
        this.doc.text(line, x + 35, textY + (lineIndex * 4));
      });
    });
    
    this.currentY += boxHeight + 20; // Increased spacing after summary
  }

  private prepareSummaryData(report: Report) {
    const entitiesCount = this.getEntitiesCount(report);
    const documentsCount = report.metadata?.total_documents_processed || 0;
    
    return [
      { label: 'Documents traités', value: documentsCount.toString() },
      { label: 'Entités extraites', value: entitiesCount.toString() },
      { label: 'Taille du fichier', value: this.formatFileSize(report.file_size || 0) },
      { label: 'Mots', value: (report.word_count || 0).toString() },
      { label: 'Version', value: report.metadata?.report_version || 'N/A' },
      { label: 'Généré le', value: new Date(report.created_at).toLocaleDateString('fr-FR') }
    ];
  }

  private addEntitySections(content: ReportContent): void {
    const sections = this.organizeSections(content);
    
    sections.forEach((section, index) => {
      this.addSection(section);
      
      // Add page break between sections (except last)
      if (index < sections.length - 1) {
        this.addPageIfNeeded(60); // Reserve space for next section
      }
    });
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
    console.log("addSection");
    this.addPageIfNeeded(30); // Ensure we have space for section header
    
    // Section header
    const headerHeight = 18; // Increased height
    this.doc.setFillColor(this.colors.primary);
    this.doc.rect(this.margins.left, this.currentY, this.pageWidth - this.margins.left - this.margins.right, headerHeight, 'F');
    
    // Section title - use the pre-cleaned title from organizeSections
    this.doc.setTextColor('#ffffff');
    this.doc.setFontSize(12);
    this.doc.setFont('helvetica', 'bold');
    const textX =  this.margins.left + 5;
    this.doc.text(section.title, textX, this.currentY + 12);
    
    this.currentY += headerHeight + 10; // Increased spacing
    
    // Section entities
    section.entities.forEach((entity, index) => {
      this.addEntity(entity, index % 2 === 0);
    });
    
    this.currentY += 15; // Increased space after section
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
    
    // Processing type badge - COMMENTED OUT TO REMOVE BADGES
    // const badgeColor = this.getProcessingTypeColor(entity.processing_type);
    // this.doc.setFillColor(badgeColor);
    // this.doc.roundedRect(this.pageWidth - 70, startY + 4, 35, 7, 1, 1, 'F');
    // this.doc.setTextColor('#ffffff');
    // this.doc.setFontSize(7);
    // this.doc.setFont('helvetica', 'bold');
    // const badgeText = entity.processing_type === 'first_match' ? 'UNIQUE' :
    //                  entity.processing_type === 'multiple_match' ? 'MULTIPLE' : 'AGRÉGÉ';
    // this.doc.text(badgeText, this.pageWidth - 62, startY + 8);
    
    // Entity value(s) with improved formatting
    this.doc.setTextColor(this.colors.dark);
    this.doc.setFontSize(10);
    this.doc.setFont('helvetica', 'normal');
    
    let valueY = startY + 18;
    
    // Handle multiple match entities as proper lists
    if (entity.processing_type === 'multiple_match' && Array.isArray(entity.value)) {
      if (entity.value.length > 0) {
        entity.value.forEach((item, index) => {
          if (item && item.trim()) {
            // Add bullet point for list items
            this.doc.setFont('helvetica', 'bold');
            this.doc.text('•', this.margins.left + 8, valueY);
            this.doc.setFont('helvetica', 'normal');
            
            // Wrap text for each list item
            const wrappedItem = this.wrapText(item, this.pageWidth - this.margins.left - this.margins.right - 25);
            wrappedItem.forEach((line, lineIndex) => {
              this.doc.text(line, this.margins.left + 15, valueY + (lineIndex * 5));
            });
            valueY += Math.max(5, wrappedItem.length * 5) + 2; // Space between items
          }
        });
      } else {
        this.doc.setTextColor(this.colors.secondary);
        this.doc.text('Aucune valeur trouvée', this.margins.left + 8, valueY);
        valueY += 8;
      }
    } else {
      // Handle single values with proper text wrapping
      const value = this.getEntityDisplayValue(entity);
      const wrappedValue = this.wrapText(value, this.pageWidth - this.margins.left - this.margins.right - 15);
      
      wrappedValue.forEach(line => {
        this.doc.text(line, this.margins.left + 8, valueY);
        valueY += 5;
      });
    }
    
    // Source information (if available) with padding
    if (entity.metadata) {
      valueY += 3; // Add padding before source
      this.doc.setTextColor(this.colors.secondary);
      this.doc.setFontSize(8);
      this.doc.setFont('helvetica', 'italic');
      
      // Display Documents mobilisés if available (prioritize over sources)
      if (entity.metadata.documents_mobilises && Array.isArray(entity.metadata.documents_mobilises) && entity.metadata.documents_mobilises.length > 0) {
        const docsMobilises = entity.metadata.documents_mobilises as Array<{
          date: string;
          libnatcr: string;
          title: string;
          filename: string;
        }>;
        
        // Show header with fallback indicator if applicable
        let headerText = `Documents mobilisés (${docsMobilises.length}):`;
        if (entity.metadata.used_fallback) {
          headerText += ` [fallback - ${entity.metadata.fallback_docs_count || '?'} docs]`;
        }
        this.doc.text(headerText, this.margins.left + 8, valueY);
        valueY += 4;
        
        // List ALL documents (no limit!)
        docsMobilises.forEach((doc) => {
          const dateStr = doc.date || '--------';
          const typeStr = doc.libnatcr || 'Unknown';
          const titleStr = doc.title ? ` - ${doc.title}` : '';
          const docText = `• [${dateStr}] ${typeStr}${titleStr}`;
          
          // Wrap if needed
          const wrappedDoc = this.wrapText(docText, this.pageWidth - this.margins.left - this.margins.right - 20);
          wrappedDoc.forEach((line) => {
            this.doc.text(line, this.margins.left + 12, valueY);
            valueY += 4;
          });
        });
      }
      // Fallback to existing sources display if no documents_mobilises
      else if (entity.processing_type === 'aggregate_all_matches' && entity.metadata.sources && Array.isArray(entity.metadata.sources)) {
        // Remove duplicates by filename
        const uniqueSources = entity.metadata.sources.filter((source: any, index: number, arr: any[]) => 
          arr.findIndex((s: any) => s.filename === source.filename) === index
        );
        
        // Show source count and list
        this.doc.text(`Sources (${uniqueSources.length}):`, this.margins.left + 8, valueY);
        valueY += 4;
        
        // List ALL unique sources (no limit!)
        uniqueSources.forEach((source: any) => {
          const sourceText = `• ${this.cleanText(source.filename)}`;
          this.doc.text(sourceText, this.margins.left + 12, valueY);
          valueY += 4;
        });
      } else if (entity.metadata.filename) {
        // Handle simple entities with single source
        this.doc.text(`Source: ${this.cleanText(entity.metadata.filename)}`, this.margins.left + 8, valueY);
        valueY += 4;
        
        // Show section and page info if available
        const sectionInfo: string[] = [];
        if (entity.metadata.section_id) {
          sectionInfo.push(`Section: ${entity.metadata.section_id}`);
        }
        if (entity.metadata.page_id) {
          sectionInfo.push(`Page: ${entity.metadata.page_id}`);
        }
        if (sectionInfo.length > 0) {
          this.doc.text(sectionInfo.join('  |  '), this.margins.left + 8, valueY);
        }
      }
      
      // For aggregate entities with documents_mobilises, also show source file info
      if (entity.metadata.documents_mobilises && 
          Array.isArray(entity.metadata.documents_mobilises) && 
          entity.metadata.documents_mobilises.length > 0 && 
          entity.metadata.filename) {
        valueY += 4;
        this.doc.text(`Source: ${this.cleanText(entity.metadata.filename)}`, this.margins.left + 8, valueY);
        
        const sectionInfo: string[] = [];
        if (entity.metadata.section_id) {
          sectionInfo.push(`Section: ${entity.metadata.section_id}`);
        }
        if (entity.metadata.page_id) {
          sectionInfo.push(`Page: ${entity.metadata.page_id}`);
        }
        if (sectionInfo.length > 0) {
          valueY += 4;
          this.doc.text(sectionInfo.join('  |  '), this.margins.left + 8, valueY);
        }
      }
    }
    
    this.currentY += entityHeight + 2; // Add small gap between entities
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
          return 'Aucune valeur trouvée';
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
    
    return 'Valeur non disponible';
  }

  private calculateEntityHeight(entity: ReportEntity): number {
    const baseHeight = 25; // Base height for entity header
    let contentHeight = 0;
    
    // Calculate height based on entity type
    if (entity.processing_type === 'multiple_match' && Array.isArray(entity.value)) {
      if (entity.value.length > 0) {
        // Calculate height for each list item
        entity.value.forEach(item => {
          if (item && item.trim()) {
            const wrappedLines = this.wrapText(item, this.pageWidth - this.margins.left - this.margins.right - 25);
            contentHeight += Math.max(5, wrappedLines.length * 5) + 2; // Space between items
          }
        });
      } else {
        contentHeight = 8; // Height for "no values found" message
      }
    } else {
      // Handle single values (including aggregate_all_matches with long text)
      const value = this.getEntityDisplayValue(entity);
      const wrappedLines = this.wrapText(value, this.pageWidth - this.margins.left - this.margins.right - 15);
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
      this.doc.text(`Rapport MDT - ${report.patient_id}`, this.margins.left, this.pageHeight - 20);
      
      // Center: Generation date
      const dateText = `Généré le ${new Date(report.created_at).toLocaleDateString('fr-FR')}`;
      const dateWidth = this.doc.getTextWidth(dateText);
      this.doc.text(dateText, (this.pageWidth - dateWidth) / 2, this.pageHeight - 20);
      
      // Right: Page numbers
      const pageText = `Page ${i} sur ${totalPages}`;
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
    const disclaimerText = 'Généré par IA — usage non clinique.';
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
export const generateMedicalReportPDF = (report: Report): Blob => {
  const generator = new MedicalPDFGenerator();
  return generator.generateReportPDF(report);
};

export default MedicalPDFGenerator;