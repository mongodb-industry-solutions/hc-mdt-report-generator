from abc import ABC, abstractmethod  
from typing import Any, Dict, Optional  
from domain.entities.patient_document import PatientDocument  
  
class DocumentOCRServiceInterface(ABC):  
    """Interface for DocumentOCRService"""  
      
    @abstractmethod  
    async def initialize(self, *args, **kwargs) -> Any:  
        """Abstract method for initialize"""  
        pass  
      
    @abstractmethod  
    async def extract_text(self, *args, **kwargs) -> Any:  
        """Abstract method for extract_text"""  
        pass  
      
    @abstractmethod  
    async def extract_metadata(self, *args, **kwargs) -> Any:  
        """Abstract method for extract_metadata"""  
        pass  
      
