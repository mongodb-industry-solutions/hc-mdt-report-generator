from abc import ABC, abstractmethod  
from typing import Any, Dict, Optional  
from domain.entities.patient_document import PatientDocument  
  
class DocumentCategorizationServiceInterface(ABC):  
    """Interface for DocumentCategorizationService"""  
      
    @abstractmethod  
    async def initialize(self, *args, **kwargs) -> Any:  
        """Abstract method for initialize"""  
        pass  
      
    @abstractmethod  
    async def categorize_document(self, *args, **kwargs) -> Any:  
        """Abstract method for categorize_document"""  
        pass  
      
    @abstractmethod  
    async def get_supported_categories(self, *args, **kwargs) -> Any:  
        """Abstract method for get_supported_categories"""  
        pass  
      
