# mpla_project/mpla/core/prompt_reviser.py

import json
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

class PromptReviser:
    """
    Revises a prompt based on analysis feedback.
    """

    def __init__(self, orchestrator: Any, meta_prompt_template: str, temperature: float = 0.2):
        """
        Initializes the PromptReviser.

        Args:
            orchestrator: The deployment orchestrator to use for revision.
            meta_prompt_template: The template for the revision meta-prompt.
            temperature: The temperature to use for the revision model.
        """
        if not meta_prompt_template:
            raise ValueError("meta_prompt_template cannot be empty.")
        self.orchestrator = orchestrator
        self.meta_prompt_template = meta_prompt_template
        self.temperature = temperature

    async def revise(self, prompt: str, analysis_report: Dict[str, Any]) -> str:
        """
        Revises the prompt based on the analysis report.

        Args:
            prompt: The original prompt to revise.
            analysis_report: The analysis report from the OutputAnalyzer.

        Returns:
            The revised prompt.
        """
        if not analysis_report.get("flaws_found"):
            logger.info("No flaws found in the analysis report. Prompt revision is not required.")
            return prompt

        logger.info("Revising prompt based on feedback...")
        
        # We convert the analysis dict to a JSON string for clean insertion into the prompt.
        analysis_str = json.dumps(analysis_report, indent=2)
        
        revision_prompt = self.meta_prompt_template.format(
            prompt=prompt,
            analysis_report=analysis_str
        )

        try:
            # Use the corrected invoke_model method.
            response = await self.orchestrator.invoke_model(
                prompt=revision_prompt, 
                temperature=self.temperature
            )

            if not response or not response.get("text"):
                 raise ValueError("Revision generation returned an empty response.")

            revised_prompt = response["text"]
            logger.info("Prompt successfully revised.")
            return revised_prompt.strip()

        except Exception as e:
            logger.error("An unexpected error occurred during prompt revision: %s", e, exc_info=True)
            # As a fallback, return the original prompt
            return prompt 