from abc import ABC, abstractmethod  
from typing import Any, Dict, Optional  
from domain.entities.patient_document import PatientDocument  
  
class DocumentDataExtractionServiceInterface(ABC):  
    """Interface for DocumentDataExtractionService"""  
      
    @abstractmethod  
    async def initialize(self, *args, **kwargs) -> Any:  
        """Abstract method for initialize"""  
        pass  
      
    @abstractmethod  
    async def extract_structured_data(self, *args, **kwargs) -> Any:  
        """Abstract method for extract_structured_data"""  
        pass  
      
    @abstractmethod  
    async def get_supported_categories(self, *args, **kwargs) -> Any:  
        """Abstract method for get_supported_categories"""  
        pass  
      
    @abstractmethod  
    async def is_category_supported(self, *args, **kwargs) -> Any:  
        """Abstract method for is_category_supported"""  
        pass  
      
