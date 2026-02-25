// Simple test PDF generation without LLM calls
import { jsPDF } from 'jspdf';

export async function generateSimpleTestPDF(): Promise<Blob> {
  const doc = new jsPDF('portrait', 'mm', 'a4');
  
  // Simple test content
  doc.setFontSize(16);
  doc.text('Test PDF Generation', 20, 30);
  doc.setFontSize(12);
  doc.text('This is a simple test to verify PDF generation works.', 20, 50);
  doc.text('Created: ' + new Date().toLocaleDateString(), 20, 70);
  
  return doc.output('blob');
}