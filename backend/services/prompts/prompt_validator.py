"""
Prompt Validator

Validation functions to ensure prompts meet quality standards and best practices.
This module provides automated checks for prompt quality, consistency, and completeness.
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from .prompt_config import PromptStandards

@dataclass
class ValidationResult:
    """Result of prompt validation"""
    is_valid: bool
    score: float  # 0.0 to 1.0
    warnings: List[str]
    errors: List[str]
    suggestions: List[str]

class PromptValidator:
    """Validator for prompt quality and standards compliance"""
    
    def __init__(self):
        self.standards = PromptStandards()
    
    def validate_system_prompt(self, prompt: str) -> ValidationResult:
        """
        Validate a system prompt for quality and standards compliance.
        
        Args:
            prompt: The system prompt to validate
            
        Returns:
            ValidationResult with validation details
        """
        warnings = []
        errors = []
        suggestions = []
        score = 1.0
        
        # Check length
        if len(prompt) > self.standards.MAX_SYSTEM_PROMPT_LENGTH:
            warnings.append(f"System prompt exceeds recommended length ({len(prompt)} > {self.standards.MAX_SYSTEM_PROMPT_LENGTH})")
            score -= 0.1
        
        # Check for role definition
        if not self._has_role_definition(prompt):
            errors.append("System prompt missing clear role definition (e.g., 'You are a...', 'Your role is...')")
            score -= 0.3
        
        # Check for task description
        if not self._has_task_description(prompt):
            warnings.append("System prompt may be missing clear task description")
            score -= 0.2
        
        # Check for output format guidance
        if not self._has_output_format(prompt):
            suggestions.append("Consider adding output format guidance to system prompt")
            score -= 0.1
        
        # Check clarity indicators
        clarity_score = self._assess_clarity(prompt)
        if clarity_score < 0.7:
            warnings.append("Prompt may lack clarity - consider using more specific language")
            score -= 0.2
        
        # Check for consistency issues
        consistency_issues = self._check_consistency(prompt)
        if consistency_issues:
            warnings.extend(consistency_issues)
            score -= 0.1 * len(consistency_issues)
        
        # Ensure score doesn't go below 0
        score = max(0.0, score)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            score=score,
            warnings=warnings,
            errors=errors,
            suggestions=suggestions
        )
    
    def validate_user_prompt(self, prompt: str, template_vars: Optional[List[str]] = None) -> ValidationResult:
        """
        Validate a user prompt template for quality and standards compliance.
        
        Args:
            prompt: The user prompt template to validate
            template_vars: List of expected template variables
            
        Returns:
            ValidationResult with validation details
        """
        warnings = []
        errors = []
        suggestions = []
        score = 1.0
        
        # Check length
        if len(prompt) > self.standards.MAX_USER_PROMPT_LENGTH:
            warnings.append(f"User prompt exceeds recommended length ({len(prompt)} > {self.standards.MAX_USER_PROMPT_LENGTH})")
            score -= 0.1
        
        # Check for template variables
        found_vars = self._extract_template_vars(prompt)
        if template_vars:
            missing_vars = set(template_vars) - set(found_vars)
            if missing_vars:
                errors.append(f"Missing template variables: {', '.join(missing_vars)}")
                score -= 0.3
        
        # Check for clear instructions
        if not self._has_clear_instructions(prompt):
            warnings.append("Prompt may lack clear, actionable instructions")
            score -= 0.2
        
        # Check for examples
        if not self._has_examples(prompt):
            suggestions.append("Consider adding examples to improve prompt clarity")
            score -= 0.1
        
        # Check for output format specification
        if not self._has_output_format_spec(prompt):
            warnings.append("Prompt should specify expected output format")
            score -= 0.2
        
        # Ensure score doesn't go below 0
        score = max(0.0, score)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            score=score,
            warnings=warnings,
            errors=errors,
            suggestions=suggestions
        )
    
    def validate_prompt_function(self, func_name: str, docstring: str, parameters: List[str]) -> ValidationResult:
        """
        Validate a prompt generation function for completeness.
        
        Args:
            func_name: Name of the function
            docstring: Function docstring
            parameters: List of function parameters
            
        Returns:
            ValidationResult with validation details
        """
        warnings = []
        errors = []
        suggestions = []
        score = 1.0
        
        # Check naming convention
        if not func_name.startswith('create_') and not func_name.endswith('_prompt'):
            suggestions.append("Consider using naming convention 'create_*_prompt' for prompt functions")
            score -= 0.1
        
        # Check docstring presence
        if not docstring or len(docstring.strip()) < 50:
            warnings.append("Function should have comprehensive docstring")
            score -= 0.2
        
        # Check parameter documentation
        if parameters and docstring:
            documented_params = self._extract_documented_params(docstring)
            undocumented = set(parameters) - set(documented_params)
            if undocumented:
                warnings.append(f"Parameters not documented: {', '.join(undocumented)}")
                score -= 0.1
        
        # Ensure score doesn't go below 0
        score = max(0.0, score)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            score=score,
            warnings=warnings,
            errors=errors,
            suggestions=suggestions
        )
    
    def _has_role_definition(self, prompt: str) -> bool:
        """Check if prompt has clear role definition"""
        role_patterns = [
            r"you are (?:a|an|the)",
            r"your role is",
            r"you will act as",
            r"you function as"
        ]
        return any(re.search(pattern, prompt.lower()) for pattern in role_patterns)
    
    def _has_task_description(self, prompt: str) -> bool:
        """Check if prompt has task description"""
        task_patterns = [
            r"your task is",
            r"you (?:should|must|need to|will)",
            r"the goal is",
            r"objective:"
        ]
        return any(re.search(pattern, prompt.lower()) for pattern in task_patterns)
    
    def _has_output_format(self, prompt: str) -> bool:
        """Check if prompt mentions output format"""
        format_patterns = [
            r"format",
            r"response",
            r"output",
            r"return",
            r"provide"
        ]
        return any(re.search(pattern, prompt.lower()) for pattern in format_patterns)
    
    def _assess_clarity(self, prompt: str) -> float:
        """Assess prompt clarity (0.0 to 1.0)"""
        clarity_indicators = [
            len(re.findall(r'\b(?:specific|clear|exact|precise)\b', prompt.lower())),
            len(re.findall(r'\b(?:must|should|need to|required)\b', prompt.lower())),
            len(re.findall(r'\b(?:example|instance|sample)\b', prompt.lower())),
            1 if '```' in prompt or '<' in prompt else 0,  # Has formatting examples
        ]
        return min(1.0, sum(clarity_indicators) / 10.0)
    
    def _check_consistency(self, prompt: str) -> List[str]:
        """Check for consistency issues"""
        issues = []
        
        # Check for mixed terminology
        if 'document' in prompt.lower() and 'file' in prompt.lower():
            issues.append("Mixed terminology: 'document' and 'file' - consider using one consistently")
        
        # Check for mixed formats (JSON/XML)
        if 'json' in prompt.lower() and 'xml' in prompt.lower():
            issues.append("Mixed output formats mentioned - clarify which format to use")
        
        return issues
    
    def _extract_template_vars(self, prompt: str) -> List[str]:
        """Extract template variables from prompt"""
        return re.findall(r'\{(\w+)\}', prompt)
    
    def _has_clear_instructions(self, prompt: str) -> bool:
        """Check if prompt has clear instructions"""
        instruction_patterns = [
            r"(?:analyze|extract|identify|determine|categorize)",
            r"(?:follow these|according to|based on)",
            r"(?:step \d|first|then|finally)"
        ]
        return any(re.search(pattern, prompt.lower()) for pattern in instruction_patterns)
    
    def _has_examples(self, prompt: str) -> bool:
        """Check if prompt includes examples"""
        example_patterns = [
            r"example",
            r"for instance",
            r"such as",
            r"```.*```",
            r"<.*>.*</.*>"
        ]
        return any(re.search(pattern, prompt.lower(), re.DOTALL) for pattern in example_patterns)
    
    def _has_output_format_spec(self, prompt: str) -> bool:
        """Check if prompt specifies output format"""
        format_patterns = [
            r"(?:json|xml|csv|format)",
            r"<[^>]+>",
            r"```",
            r"response format",
            r"output should"
        ]
        return any(re.search(pattern, prompt.lower()) for pattern in format_patterns)
    
    def _extract_documented_params(self, docstring: str) -> List[str]:
        """Extract documented parameters from docstring"""
        # Look for Args: section and parameter names
        args_match = re.search(r'args?:(.*?)(?:\n\s*\n|\nreturns?:|\nraises?:|\Z)', docstring.lower(), re.DOTALL)
        if not args_match:
            return []
        
        args_section = args_match.group(1)
        return re.findall(r'^\s*(\w+):', args_section, re.MULTILINE)

def validate_all_prompts() -> Dict[str, ValidationResult]:
    """
    Validate all prompts in the system.
    
    Returns:
        Dictionary mapping prompt names to validation results
    """
    validator = PromptValidator()
    results = {}
    
    # This would be implemented to scan all prompt files and validate them
    # For now, returning empty dict as placeholder
    return results

def generate_validation_report(results: Dict[str, ValidationResult]) -> str:
    """
    Generate a human-readable validation report.
    
    Args:
        results: Dictionary of validation results
        
    Returns:
        Formatted validation report
    """
    lines = ["# Prompt Validation Report", ""]
    
    total_prompts = len(results)
    valid_prompts = sum(1 for r in results.values() if r.is_valid)
    avg_score = sum(r.score for r in results.values()) / total_prompts if total_prompts > 0 else 0
    
    lines.extend([
        f"## Summary",
        f"- Total prompts: {total_prompts}",
        f"- Valid prompts: {valid_prompts}",
        f"- Average score: {avg_score:.2f}",
        ""
    ])
    
    for name, result in results.items():
        lines.extend([
            f"## {name}",
            f"- Valid: {'✅' if result.is_valid else '❌'}",
            f"- Score: {result.score:.2f}",
            ""
        ])
        
        if result.errors:
            lines.append("**Errors:**")
            lines.extend(f"- {error}" for error in result.errors)
            lines.append("")
        
        if result.warnings:
            lines.append("**Warnings:**")
            lines.extend(f"- {warning}" for warning in result.warnings)
            lines.append("")
        
        if result.suggestions:
            lines.append("**Suggestions:**")
            lines.extend(f"- {suggestion}" for suggestion in result.suggestions)
            lines.append("")
    
    return "\n".join(lines) 