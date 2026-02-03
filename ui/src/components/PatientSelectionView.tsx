import React, { useState, useEffect } from 'react';
import { User, Search, FileText, Calendar, Users, ArrowRight, Loader } from 'lucide-react';
import { apiService } from '../services/api';
import { useI18n } from '../i18n/context';

interface PatientSelectionViewProps {
  onSelectPatient: (patientId: string) => void;
}

interface PatientInfo {
  id: string;
  documentCount: number;
  reportCount: number;
  lastActivity?: string;
}

export default function PatientSelectionView({ onSelectPatient }: PatientSelectionViewProps) {
  const { t } = useI18n();
  const [patients, setPatients] = useState<string[]>([]);
  const [patientDetails, setPatientDetails] = useState<Record<string, PatientInfo>>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Get all patients first (fast)
      const patientsResponse = await apiService.getPatients();
      const patientIds = patientsResponse.items || [];
      setPatients(patientIds);
      
      // Create basic patient info without API calls for faster loading
      const basicDetails: Record<string, PatientInfo> = {};
      patientIds.forEach(patientId => {
        basicDetails[patientId] = {
          id: patientId,
          documentCount: 0,
          reportCount: 0
        };
      });
      setPatientDetails(basicDetails);
      setIsLoading(false); // Show patients immediately
      
      // Load detailed info in background (optional)
      loadPatientDetails(patientIds);
      
    } catch (err) {
      console.error('Error loading patients:', err);
      setError('Failed to load patients. Please try again.');
      setIsLoading(false);
    }
  };

  const loadPatientDetails = async (patientIds: string[]) => {
    // Load details for each patient in background
    const details: Record<string, PatientInfo> = { ...patientDetails };
    
    // Process in smaller batches to avoid overwhelming the server
    const batchSize = 5;
    for (let i = 0; i < patientIds.length; i += batchSize) {
      const batch = patientIds.slice(i, i + batchSize);
      
      await Promise.allSettled(
        batch.map(async (patientId) => {
          try {
            // Get document count only (faster)
            const docsResponse = await apiService.getPatientDocuments(patientId, 1, 1);
            const documentCount = docsResponse.total || 0;
            let lastActivity: string | undefined;
            
            if (docsResponse.items.length > 0) {
              lastActivity = docsResponse.items[0].updated_at;
            }
            
            details[patientId] = {
              id: patientId,
              documentCount,
              reportCount: 0, // Skip report counting for faster loading
              lastActivity
            };
          } catch (err) {
            console.error(`Failed to load details for patient ${patientId}:`, err);
            // Keep basic info if loading fails
          }
        })
      );
      
      // Update UI with each batch
      setPatientDetails({ ...details });
    }
  };

  const filteredPatients = patients.filter(patientId =>
    patientId.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatLastActivity = (dateString?: string) => {
    if (!dateString) return 'No recent activity';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  };

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader className="h-12 w-12 animate-spin text-blue-600" />
          <p className="text-xl text-gray-600 font-medium">Loading patients...</p>
          <p className="text-sm text-gray-500">Please wait while we fetch patient data</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <div className="bg-red-50 border border-red-200 rounded-xl p-8 max-w-md">
            <Users className="h-16 w-16 text-red-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-red-900 mb-2">Error Loading Patients</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <button
              onClick={loadPatients}
              className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center mb-4">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-lg">
            <Users className="w-6 h-6 text-white" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Select a Patient</h1>
        <p className="text-sm text-gray-600 max-w-xl mx-auto">
          Choose a patient to view their medical documents and reports. You can search by patient ID or browse all available patients.
        </p>
      </div>

      {/* Search Bar */}
      <div className="max-w-xl mx-auto">
        <div className="relative">
          <Search className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search patients by ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm"
          />
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
          <div className="flex items-center space-x-2">
            <Users className="w-6 h-6 text-blue-600" />
            <div>
              <p className="text-xs text-blue-600 font-medium">Total Patients</p>
              <p className="text-2xl font-bold text-blue-900">{patients.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200">
          <div className="flex items-center space-x-2">
            <FileText className="w-6 h-6 text-green-600" />
            <div>
              <p className="text-xs text-green-600 font-medium">Total Documents</p>
              <p className="text-2xl font-bold text-green-900">
                {Object.values(patientDetails).reduce((sum, p) => sum + p.documentCount, 0) || '...'}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-purple-50 to-violet-50 rounded-lg p-4 border border-purple-200">
          <div className="flex items-center space-x-2">
            <Calendar className="w-6 h-6 text-purple-600" />
            <div>
              <p className="text-xs text-purple-600 font-medium">Available Patients</p>
              <p className="text-2xl font-bold text-purple-900">
                {patients.length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Patient Cards */}
      <div className="max-w-6xl mx-auto">
        {filteredPatients.length === 0 ? (
          <div className="text-center py-12">
            <Search className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No patients found</h3>
            <p className="text-sm text-gray-600">
              {searchQuery ? 'Try adjusting your search terms' : 'No patients available in the system'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredPatients.map((patientId) => {
              const details = patientDetails[patientId] || { id: patientId, documentCount: 0, reportCount: 0 };
              
              return (
                <div
                  key={patientId}
                  onClick={() => onSelectPatient(patientId)}
                  className="group bg-white rounded-xl shadow-lg border border-gray-200 hover:shadow-xl hover:border-blue-300 transition-all duration-300 cursor-pointer transform hover:-translate-y-1"
                >
                  {/* Card Header */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 rounded-t-xl border-b border-gray-100">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-md">
                          <User className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <h3 className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                            {patientId}
                          </h3>
                          <p className="text-sm text-gray-600">Patient ID</p>
                        </div>
                      </div>
                      <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-blue-600 group-hover:translate-x-1 transition-all duration-200" />
                    </div>
                  </div>

                  {/* Card Content */}
                  <div className="p-6">
                    <div className="space-y-4">
                      {/* Document and Report Counts */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-gray-50 rounded-lg p-3">
                          <div className="flex items-center space-x-2">
                            <FileText className="w-4 h-4 text-gray-600" />
                            <span className="text-sm text-gray-600">Documents</span>
                          </div>
                          <p className="text-xl font-bold text-gray-900 mt-1">
                            {details.documentCount === 0 && !details.lastActivity ? '...' : details.documentCount}
                          </p>
                        </div>
                        
                        <div className="bg-gray-50 rounded-lg p-3">
                          <div className="flex items-center space-x-2">
                            <Calendar className="w-4 h-4 text-gray-600" />
                            <span className="text-sm text-gray-600">Last Activity</span>
                          </div>
                          <p className="text-sm font-medium text-gray-700 mt-1">
                            {details.lastActivity ? formatLastActivity(details.lastActivity) : '...'}
                          </p>
                        </div>
                      </div>

                      {/* Simplified Last Activity Section - removed since it's now above */}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}