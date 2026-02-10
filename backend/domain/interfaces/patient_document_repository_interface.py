from abc import ABC, abstractmethod  
from typing import List, Optional, Dict, Any  
from domain.entities.patient_document import PatientDocument  
from domain.entities.report import Report  
  
class PatientDocumentRepositoryInterface(ABC):  
    """Interface for PatientDocumentRepository"""  
      
    @abstractmethod  
    async def get_by_uuid(self, *args, **kwargs) -> Any:  
        """Abstract method for get_by_uuid"""  
        pass  
      
    @abstractmethod  
    async def get_by_patient_id(self, *args, **kwargs) -> Any:  
        """Abstract method for get_by_patient_id"""  
        pass  
      
    @abstractmethod  
    async def count_by_patient_id(self, *args, **kwargs) -> Any:  
        """Abstract method for count_by_patient_id"""  
        pass  
      
    @abstractmethod  
    async def create(self, *args, **kwargs) -> Any:  
        """Abstract method for create"""  
        pass  
      
    @abstractmethod  
    async def update(self, *args, **kwargs) -> Any:  
        """Abstract method for update"""  
        pass  
      
