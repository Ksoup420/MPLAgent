import asyncio
from typing import Dict, Any
from fastapi.encoders import jsonable_encoder

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
        return jsonable_encoder(saved_log)

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
            return {"content": "## Final Report\n\nNo iterations were found for this session."}

        # Fetch details for all iterations concurrently for efficiency
        async def process_iteration(it: IterationLog):
            prompt_version, evaluation_result, original_prompt = await asyncio.gather(
                self.kb.get(PromptVersion, it.active_prompt_version_id) if it.active_prompt_version_id else asyncio.sleep(0, result=None),
                self.kb.get(EvaluationResult, it.evaluation_result_id) if it.evaluation_result_id else asyncio.sleep(0, result=None),
                self.kb.get(OriginalPrompt, it.original_prompt_id) if it.original_prompt_id else asyncio.sleep(0, result=None)
            )
            # We return the raw model objects here
            return {
                "iteration_log": it,
                "prompt_version": prompt_version,
                "evaluation_result": evaluation_result,
                "original_prompt": original_prompt,
            }

        processed_iterations = await asyncio.gather(*[process_iteration(it) for it in iterations])

        # Populate the report dictionary from the processed data
        if processed_iterations and processed_iterations[0]["original_prompt"]:
             report["initial_prompt"] = processed_iterations[0]["original_prompt"]

        report["iterations"] = processed_iterations
        
        last_successful_iteration = next((it for it in reversed(processed_iterations) 
                                             if it.get('iteration_log').status == 'completed' and it.get('prompt_version')), None)

        if last_successful_iteration and last_successful_iteration.get('prompt_version'):
            report["final_prompt"] = last_successful_iteration['prompt_version']
            report['status'] = 'completed_successfully'
        else:
            report['status'] = 'completed_with_errors'

        # --- Generate Markdown Content ---
        content_lines = [
            f"# Final Report for Session: `{session_id}`",
            f"**Status:** {report['status'].replace('_', ' ').title()}",
            "---"
        ]
        
        if report.get('initial_prompt'):
            content_lines.append("## Initial Prompt")
            content_lines.append(f"> {report['initial_prompt'].text}")
            content_lines.append("\n")

        content_lines.append("## Iteration Summary")
        for i, it_data in enumerate(report['iterations']):
            content_lines.append(f"### Iteration {i+1}")
            if it_data.get('prompt_version'):
                content_lines.append(f"**Prompt:** `{it_data['prompt_version'].prompt_text}`")
            if it_data.get('evaluation_result'):
                scores = ', '.join([f"{k}: {v:.2f}" for k, v in it_data['evaluation_result'].metric_scores.items()])
                content_lines.append(f"**Evaluation:** {scores}")
            content_lines.append("\n")

        if report.get('final_prompt'):
            content_lines.append("## Best Performing Prompt")
            content_lines.append("```")
            content_lines.append(report['final_prompt'].prompt_text)
            content_lines.append("```")

        report_content = "\n".join(content_lines)

        return {"content": report_content} 