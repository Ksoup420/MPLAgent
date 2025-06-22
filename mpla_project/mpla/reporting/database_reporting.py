import asyncio
from typing import Dict, Any

from mpla.core.reporting import ReportingModule
from mpla.knowledge_base.db_connector import KnowledgeBase
from mpla.knowledge_base.schemas import IterationLog, OriginalPrompt, PromptVersion, EvaluationResult


class DatabaseReportingModule(ReportingModule):
    """
    Handles generation of reports by fetching and aggregating data from the knowledge base.
    """
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    async def report_iteration(self, iteration_log: IterationLog) -> Dict[str, Any]:
        """
        Saves the full IterationLog object to the database.
        This is the crucial step that persists the record of the iteration itself.
        """
        saved_log = await self.kb.add(iteration_log)
        return saved_log.model_dump()

    async def generate_final_report(self, session_id: str) -> Dict[str, Any]:
        """
        Generates a comprehensive final report for a given session by aggregating
        all related data from the database.
        """
        report = {
            "session_id": session_id,
            "status": "completed",
            "iterations": [],
            "final_prompt": None,
            "initial_prompt": None,
        }

        iterations = await self.kb.get_iterations_for_session(session_id)
        if not iterations:
            report["status"] = "no_iterations_found"
            return report

        if iterations[0].original_prompt_id:
            original_prompt_obj = await self.kb.get(OriginalPrompt, iterations[0].original_prompt_id)
            report["initial_prompt"] = original_prompt_obj.model_dump() if original_prompt_obj else None

        async def process_iteration(it: IterationLog) -> dict:
            iteration_data = it.model_dump()
            if it.active_prompt_version_id:
                prompt_version = await self.kb.get(PromptVersion, it.active_prompt_version_id)
                iteration_data['prompt_version'] = prompt_version.model_dump() if prompt_version else None
            if it.evaluation_result_id:
                evaluation_result = await self.kb.get(EvaluationResult, it.evaluation_result_id)
                iteration_data['evaluation_result'] = evaluation_result.model_dump() if evaluation_result else None
            return iteration_data

        report["iterations"] = await asyncio.gather(*[process_iteration(it) for it in iterations])
        
        last_successful_iteration = next((it for it in reversed(report['iterations']) 
                                             if it.get('status') == 'completed' and it.get('prompt_version')), None)

        if last_successful_iteration and last_successful_iteration.get('prompt_version'):
            report["final_prompt"] = last_successful_iteration['prompt_version']
            report['status'] = 'completed_successfully'
        else:
            report['status'] = 'completed_with_errors'

        return report 