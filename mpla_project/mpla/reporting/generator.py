from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# from mpla.knowledge_base.schemas import IterationLog, PromptVersion # If needed for detailed report generation

class ReportingModule(ABC):
    """Abstract Base Class for Reporting modules.
    
    Defines the interface for generating the final outputs for the user,
    including the best prompt, logs, and elucidation.
    """

    @abstractmethod
    async def generate_final_report(
        self, 
        session_id: str
        # original_prompt_id: int # Alternative or additional identifier
    ) -> Dict[str, Any]:
        """Generates the final report for a completed refinement session.

        Args:
            session_id: The ID of the refinement session to report on.

        Returns:
            A dictionary containing the final enhanced prompt, a log of tested versions,
            and an elucidation of the refinement process.
            Example: {
                "session_id": "xyz",
                "original_prompt_text": "...",
                "final_enhanced_prompt": "...",
                "elucidation": "...",
                "iteration_logs": [...] 
            }
        """
        pass 