/**
 * ProcessingPipeline Component
 * 
 * Visual pipeline showing document processing steps with animated icons
 */

import React from 'react';
import {
  Upload,
  FileText,
  User,
  FolderTree,
  Database,
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
  ArrowRight
} from 'lucide-react';
import { ProcessingStatus, ProcessingStep } from '../types';

// Default pipeline steps if not provided
const DEFAULT_STEPS: ProcessingStep[] = [
  { id: 'upload', name: 'Upload', order: 1 },
  { id: 'text_extraction', name: 'Text Extraction', order: 2 },
  { id: 'patient_id', name: 'Patient ID', order: 3 },
  { id: 'categorization', name: 'Categorization', order: 4 },
  { id: 'data_extraction', name: 'Data Extraction', order: 5 },
  { id: 'complete', name: 'Complete', order: 6 }
];

// Icon mapping for each step
const STEP_ICONS: Record<string, React.FC<{ className?: string }>> = {
  upload: Upload,
  text_extraction: FileText,
  patient_id: User,
  categorization: FolderTree,
  data_extraction: Database,
  complete: CheckCircle2
};

interface ProcessingPipelineProps {
  status: ProcessingStatus;
  compact?: boolean;
  showLabels?: boolean;
  darkMode?: boolean;
}

type StepStatus = 'completed' | 'current' | 'pending' | 'failed';

function getStepStatus(
  stepId: string,
  currentStep?: string,
  completedSteps?: string[],
  overallStatus?: string
): StepStatus {
  // If overall status is failed, mark current step as failed
  if (overallStatus === 'failed' && stepId === currentStep) {
    return 'failed';
  }
  
  // Check if step is completed
  if (completedSteps?.includes(stepId)) {
    return 'completed';
  }
  
  // Check if this is the current step
  if (stepId === currentStep) {
    return 'current';
  }
  
  return 'pending';
}

function StepIcon({
  stepId,
  stepStatus,
  className = ''
}: {
  stepId: string;
  stepStatus: StepStatus;
  className?: string;
}) {
  const IconComponent = STEP_ICONS[stepId] || Circle;
  
  if (stepStatus === 'current') {
    return (
      <div className={`relative ${className}`}>
        <Loader2 className="w-full h-full text-blue-500 animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <IconComponent className="w-1/2 h-1/2 text-blue-600" />
        </div>
      </div>
    );
  }
  
  if (stepStatus === 'completed') {
    return (
      <div className={`relative ${className}`}>
        <CheckCircle2 className="w-full h-full text-green-500" />
      </div>
    );
  }
  
  if (stepStatus === 'failed') {
    return (
      <div className={`relative ${className}`}>
        <XCircle className="w-full h-full text-red-500" />
      </div>
    );
  }
  
  // Pending
  return (
    <div className={`relative ${className}`}>
      <Circle className="w-full h-full text-gray-300" />
      <div className="absolute inset-0 flex items-center justify-center">
        <IconComponent className="w-1/2 h-1/2 text-gray-400" />
      </div>
    </div>
  );
}

function StepConnector({ status }: { status: 'completed' | 'pending' }) {
  return (
    <div className="flex items-center mx-1">
      <div 
        className={`h-0.5 w-4 transition-colors duration-300 ${
          status === 'completed' ? 'bg-green-500' : 'bg-gray-300'
        }`}
      />
      <ArrowRight 
        className={`w-3 h-3 -ml-1.5 transition-colors duration-300 ${
          status === 'completed' ? 'text-green-500' : 'text-gray-300'
        }`}
      />
    </div>
  );
}

export default function ProcessingPipeline({
  status,
  compact = false,
  showLabels = true,
  darkMode = false
}: ProcessingPipelineProps) {
  const steps = status.steps || DEFAULT_STEPS;
  const currentStep = status.current_step;
  const completedSteps = status.completed_steps || [];
  const overallStatus = status.status;
  const progress = status.progress || 0;
  
  // Sort steps by order
  const sortedSteps = [...steps].sort((a, b) => a.order - b.order);
  
  if (compact) {
    // Compact view - horizontal icons with progress bar
    return (
      <div className="flex flex-col gap-2">
        {/* Progress bar */}
        <div className="relative h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${
              overallStatus === 'failed' 
                ? 'bg-red-500' 
                : overallStatus === 'completed'
                  ? 'bg-green-500'
                  : 'bg-blue-500'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
        
        {/* Icons */}
        <div className="flex items-center justify-between">
          {sortedSteps.map((step, index) => {
            const stepStatus = getStepStatus(step.id, currentStep, completedSteps, overallStatus);
            const IconComponent = STEP_ICONS[step.id] || Circle;
            
            return (
              <div key={step.id} className="flex items-center">
                <div 
                  className={`
                    w-6 h-6 rounded-full flex items-center justify-center transition-all duration-300
                    ${stepStatus === 'completed' ? 'bg-green-100' : ''}
                    ${stepStatus === 'current' ? 'bg-blue-100' : ''}
                    ${stepStatus === 'failed' ? 'bg-red-100' : ''}
                    ${stepStatus === 'pending' ? 'bg-gray-100' : ''}
                  `}
                  title={step.name}
                >
                  {stepStatus === 'current' ? (
                    <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                  ) : stepStatus === 'completed' ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  ) : stepStatus === 'failed' ? (
                    <XCircle className="w-4 h-4 text-red-500" />
                  ) : (
                    <IconComponent className="w-3 h-3 text-gray-400" />
                  )}
                </div>
                {index < sortedSteps.length - 1 && (
                  <div 
                    className={`h-0.5 w-4 mx-0.5 transition-colors duration-300 ${
                      stepStatus === 'completed' ? 'bg-green-400' : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }
  
  // Full view - horizontal with labels (no card wrapper - parent provides container)
  return (
    <div>
      {/* Progress bar */}
      <div className={`relative h-2 rounded-full overflow-hidden mb-4 ${darkMode ? 'bg-white/10' : 'bg-gray-100'}`}>
        <div 
          className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${
            overallStatus === 'failed' 
              ? 'bg-gradient-to-r from-red-400 to-red-500' 
              : overallStatus === 'completed'
                ? 'bg-gradient-to-r from-green-400 to-green-500'
                : 'bg-gradient-to-r from-blue-400 to-blue-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
      
      {/* Steps */}
      <div className="flex items-start justify-between overflow-x-hidden">
        {sortedSteps.map((step, index) => {
          const stepStatus = getStepStatus(step.id, currentStep, completedSteps, overallStatus);
          const isLast = index === sortedSteps.length - 1;
          
          return (
            <React.Fragment key={step.id}>
              <div className="flex flex-col items-center flex-1 min-w-0">
                <StepIcon 
                  stepId={step.id} 
                  stepStatus={stepStatus} 
                  className="w-8 h-8"
                />
                {showLabels && (
                  <span className={`
                    mt-2 text-xs text-center font-medium transition-colors duration-300 truncate max-w-full px-1
                    ${stepStatus === 'completed' ? (darkMode ? 'text-green-400' : 'text-green-600') : ''}
                    ${stepStatus === 'current' ? (darkMode ? 'text-blue-400' : 'text-blue-600') : ''}
                    ${stepStatus === 'failed' ? (darkMode ? 'text-red-400' : 'text-red-600') : ''}
                    ${stepStatus === 'pending' ? (darkMode ? 'text-slate-500' : 'text-gray-400') : ''}
                  `}>
                    {step.name}
                  </span>
                )}
              </div>
              {!isLast && (
                <div className="flex-shrink-0 pt-3">
                  <StepConnector 
                    status={completedSteps?.includes(step.id) ? 'completed' : 'pending'} 
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
      
      {/* Current step label */}
      {currentStep && overallStatus !== 'completed' && (
        <div className={`mt-4 pt-3 border-t ${darkMode ? 'border-white/10' : 'border-gray-100'}`}>
          <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-gray-500'}`}>
            {overallStatus === 'failed' ? (
              <span className={darkMode ? 'text-red-400' : 'text-red-600'}>
                Failed at: <span className="font-medium">{steps.find(s => s.id === currentStep)?.name || currentStep}</span>
              </span>
            ) : (
              <>
                Currently: <span className={`font-medium ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                  {steps.find(s => s.id === currentStep)?.name || currentStep}
                </span>
              </>
            )}
          </p>
        </div>
      )}
      
      {/* Error message */}
      {status.error && (
        <div className={`mt-3 p-2 rounded text-xs ${
          darkMode 
            ? 'bg-red-500/20 border border-red-500/30 text-red-300' 
            : 'bg-red-50 border border-red-200 text-red-700'
        }`}>
          {status.error}
        </div>
      )}
    </div>
  );
}

/**
 * Inline mini pipeline for table rows
 */
export function MiniPipeline({ status }: { status: ProcessingStatus }) {
  const steps = status.steps || DEFAULT_STEPS;
  const completedSteps = status.completed_steps || [];
  const currentStep = status.current_step;
  const overallStatus = status.status;
  
  // Sort steps by order
  const sortedSteps = [...steps].sort((a, b) => a.order - b.order);
  
  return (
    <div className="flex items-center gap-1">
      {sortedSteps.map((step) => {
        const stepStatus = getStepStatus(step.id, currentStep, completedSteps, overallStatus);
        
        return (
          <div
            key={step.id}
            className={`
              w-2.5 h-2.5 rounded-full transition-all duration-300
              ${stepStatus === 'completed' ? 'bg-green-500' : ''}
              ${stepStatus === 'current' ? 'bg-blue-500 animate-pulse' : ''}
              ${stepStatus === 'failed' ? 'bg-red-500' : ''}
              ${stepStatus === 'pending' ? 'bg-gray-300' : ''}
            `}
            title={`${step.name}: ${stepStatus}`}
          />
        );
      })}
    </div>
  );
}
