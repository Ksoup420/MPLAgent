from typing import Dict, Any

from mpla.core.reporting import ReportingModule
from mpla.knowledge_base.db_connector import KnowledgeBase
from mpla.knowledge_base.schemas import IterationLog

class DatabaseReportingModule(ReportingModule):
    """
    A reporting module that persists iteration data to the configured knowledge base.
    """

    def __init__(self, kb: KnowledgeBase):
        """
        Initializes the DatabaseReportingModule.

        Args:
            kb: An instance of a KnowledgeBase implementation (e.g., SQLiteKnowledgeBase).
        """
        super().__init__(kb)

    async def report_iteration(self, iteration_log: IterationLog) -> Dict[str, Any]:
        """
        Saves the full IterationLog object to the database.

        The agent is responsible for constructing the IterationLog with all necessary IDs.
        This method's primary job is to persist it.

        Args:
            iteration_log: The IterationLog object for the completed cycle.

        Returns:
            A dictionary representation of the saved log for confirmation.
        """
        if not self.kb:
            raise ConnectionError("KnowledgeBase is not available to the reporting module.")
        
        saved_log = await self.kb.add(iteration_log)
        print(f"Iteration {saved_log.iteration_number} for session {saved_log.session_id} saved to database with ID {saved_log.id}.")
        
        return saved_log.model_dump()

    async def generate_final_report(self, session_id: str) -> Dict[str, Any]:
        """
        Generates a final report by retrieving all iterations for a session from the database.

        Args:
            session_id: The unique identifier for the refinement session.

        Returns:
            A dictionary summarizing the session, including all iteration data.
        """
        if not self.kb:
            raise ConnectionError("KnowledgeBase is not available to the reporting module.")

        iterations = await self.kb.get_iterations_for_session(session_id)
        
        if not iterations:
            return {"error": f"No iterations found for session ID {session_id}"}

        # Find the best performing iteration based on the evaluation result's overall score
        best_iteration = None
        highest_score = -1

        for it in iterations:
            if it.evaluation_result:
                # Assuming overall_satisfaction is the key metric
                current_score = it.evaluation_result.metric_scores.get('overall_satisfaction', -1)
                if current_score > highest_score:
                    highest_score = current_score
                    best_iteration = it
        
        final_report = {
            "session_id": session_id,
            "total_iterations": len(iterations),
            "original_prompt_id": iterations[0].original_prompt_id,
            "best_iteration_id": best_iteration.id if best_iteration else None,
            "best_prompt_version_id": best_iteration.active_prompt_version_id if best_iteration else None,
            "highest_satisfaction_score": highest_score,
            "iterations": [it.model_dump(exclude_none=True) for it in iterations]
        }
        
        return final_report 