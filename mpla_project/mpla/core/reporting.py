from abc import ABC, abstractmethod
from typing import Dict, Any

from mpla.knowledge_base.db_connector import KnowledgeBase
from mpla.knowledge_base.schemas import IterationLog

class ReportingModule(ABC):
    """Abstract Base Class for reporting modules."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    @abstractmethod
    async def report_iteration(self, iteration_log: IterationLog) -> Dict[str, Any]:
        """
        Records the results of a single refinement iteration.

        Args:
            iteration_log: The IterationLog object containing all data for the completed cycle.

        Returns:
            A dictionary summarizing the reported iteration, suitable for logging or display.
        """
        pass

    @abstractmethod
    async def generate_final_report(self, session_id: str) -> Dict[str, Any]:
        """
        Generates a final summary report for an entire refinement session.

        Args:
            session_id: The unique identifier for the refinement session.

        Returns:
            A comprehensive dictionary summarizing the entire session.
        """
        pass 