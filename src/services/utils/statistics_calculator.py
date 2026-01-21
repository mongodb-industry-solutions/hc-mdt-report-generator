"""
Statistics Calculator

Handles calculation of various statistics for text processing.
Separates statistics calculation from main processing logic.
"""

from typing import Dict, Any


class StatisticsCalculator:
    """Handles calculation of text processing statistics"""
    
    @staticmethod
    def calculate_normalization_statistics(original_text: str, normalized_text: str) -> Dict[str, Any]:
        """
        Calculate statistics about the normalization process
        
        Args:
            original_text: Original text before normalization
            normalized_text: Text after normalization
            
        Returns:
            Dictionary with normalization statistics
        """
        original_char_count = len(original_text)
        normalized_char_count = len(normalized_text)
        original_word_count = len(original_text.split())
        normalized_word_count = len(normalized_text.split())
        
        return {
            "original_character_count": original_char_count,
            "normalized_character_count": normalized_char_count,
            "character_reduction_percent": StatisticsCalculator._calculate_reduction_percent(
                original_char_count, normalized_char_count
            ),
            "original_word_count": original_word_count,
            "normalized_word_count": normalized_word_count,
            "word_reduction_percent": StatisticsCalculator._calculate_reduction_percent(
                original_word_count, normalized_word_count
            )
        }
    
    @staticmethod
    def calculate_entity_statistics(extraction_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics about entity extraction results
        
        Args:
            extraction_results: Results from entity extraction
            
        Returns:
            Dictionary with entity statistics
        """
        total_entities_found = 0
        results_by_type = {}
        
        for processing_type, results in extraction_results.items():
            found_count = len(results.get("found_entities", []))
            not_found_count = len(results.get("not_found_entities", []))
            total_entities_found += found_count
            
            results_by_type[processing_type] = {
                "found": found_count,
                "not_found": not_found_count
            }
        
        return {
            "total_entities_found": total_entities_found,
            "results_by_type": results_by_type
        }
    
    @staticmethod
    def _calculate_reduction_percent(original: int, processed: int) -> float:
        """Calculate reduction percentage"""
        if original == 0:
            return 0.0
        return round((original - processed) / original * 100, 2) 