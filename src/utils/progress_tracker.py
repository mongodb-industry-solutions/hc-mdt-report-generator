# utils/progress_tracker.py  
"""Progress tracking for long-running operations."""  
  
import json  
import os  
import asyncio  
import logging  
import tempfile  
import atexit  
from typing import Dict, Any, Optional  
from datetime import datetime, timedelta  
from dataclasses import asdict  
  
from domain.entities.ner_models import ProcessingProgress  
  
logger = logging.getLogger(__name__)  
  
class ProgressTracker:  
    """Tracks and persists progress for long-running extractions."""  
      
    def __init__(self, save_interval: int = 10):  
        self.save_interval = save_interval  
        self.progress: Optional[ProcessingProgress] = None  
        self._last_save_time = None  
        self._temp_dir = tempfile.mkdtemp(prefix="progress_tracking_")  
        self._created_files = []  
        # Register cleanup function to run when Python exits  
        atexit.register(self._cleanup_files)  
          
    async def start_tracking(  
        self,   
        total_documents: int,   
        total_entities: int,  
        session_id: str = None  
    ) -> None:  
        """Start progress tracking for a new session."""  
          
        session_id = session_id or f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  
          
        self.progress = ProcessingProgress(  
            total_documents=total_documents,  
            processed_documents=0,  
            total_entities=total_entities,  
            found_entities=0,  
            failed_extractions=0,  
            start_time=datetime.utcnow()  
        )  
          
        await self._save_progress(session_id)  
        logger.info(f"Started tracking session: {session_id}")  
      
    async def update_progress(  
        self,  
        processed_docs: int = 0,  
        found_entities: int = 0,  
        failed_extractions: int = 0,  
        session_id: str = None  
    ) -> None:  
        """Update progress counters."""  
          
        if not self.progress:  
            logger.warning("Progress tracking not started")  
            return  
          
        self.progress.processed_documents += processed_docs  
        self.progress.found_entities += found_entities  
        self.progress.failed_extractions += failed_extractions  
          
        # Calculate estimated completion  
        if self.progress.processed_documents > 0:  
            elapsed_time = datetime.utcnow() - self.progress.start_time  
            avg_time_per_doc = elapsed_time / self.progress.processed_documents  
            remaining_docs = self.progress.total_documents - self.progress.processed_documents  
            self.progress.estimated_completion = datetime.utcnow() + (avg_time_per_doc * remaining_docs)  
          
        # Save periodically  
        if self._should_save():  
            await self._save_progress(session_id)  
      
    def _should_save(self) -> bool:  
        """Check if progress should be saved."""  
        if not self._last_save_time:  
            return True  
          
        return (datetime.utcnow() - self._last_save_time).seconds >= self.save_interval  
      
    async def _save_progress(self, session_id: str = None) -> None:  
        """Save progress to file in temporary directory."""  
        if not self.progress:  
            return  
          
        try:  
            filename = f"progress_{session_id or 'default'}.json"  
            filepath = os.path.join(self._temp_dir, filename)  
            progress_data = asdict(self.progress)  
              
            # Convert datetime objects to strings  
            for key, value in progress_data.items():  
                if isinstance(value, datetime):  
                    progress_data[key] = value.isoformat()  
              
            with open(filepath, 'w') as f:  
                json.dump(progress_data, f, indent=2)  
              
            # Track created files for cleanup  
            if filepath not in self._created_files:  
                self._created_files.append(filepath)  
              
            self._last_save_time = datetime.utcnow()  
            logger.debug(f"Progress saved to {filepath}")  
              
        except Exception as e:  
            logger.error(f"Failed to save progress: {e}")  
      
    async def load_progress(self, session_id: str) -> Optional[ProcessingProgress]:  
        """Load progress from file in temporary directory."""  
        filename = f"progress_{session_id}.json"  
        filepath = os.path.join(self._temp_dir, filename)  
          
        if not os.path.exists(filepath):  
            return None  
          
        try:  
            with open(filepath, 'r') as f:  
                data = json.load(f)  
              
            # Convert datetime strings back to datetime objects  
            for key in ['start_time', 'estimated_completion']:  
                if data.get(key):  
                    data[key] = datetime.fromisoformat(data[key])  
              
            return ProcessingProgress(**data)  
              
        except Exception as e:  
            logger.error(f"Failed to load progress: {e}")  
            return None  
      
    def _cleanup_files(self) -> None:  
        """Clean up temporary progress files."""  
        try:  
            for filepath in self._created_files:  
                if os.path.exists(filepath):  
                    os.remove(filepath)  
                    logger.debug(f"Cleaned up progress file: {filepath}")  
              
            # Remove temporary directory if it exists and is empty  
            if os.path.exists(self._temp_dir) and not os.listdir(self._temp_dir):  
                os.rmdir(self._temp_dir)  
                logger.debug(f"Cleaned up temporary directory: {self._temp_dir}")  
              
        except Exception as e:  
            logger.error(f"Failed to cleanup progress files: {e}")  
      
    def cleanup(self) -> None:  
        """Manually trigger cleanup of progress files."""  
        self._cleanup_files()  
