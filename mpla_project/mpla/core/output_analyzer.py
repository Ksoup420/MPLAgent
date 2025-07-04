# mpla_project/mpla/core/output_analyzer.py

import json
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

class OutputAnalyzer:
    """
    Analyzes the output of a generated prompt to identify flaws.
    """

    def __init__(self, orchestrator: Any, meta_prompt_template: str, temperature: float = 0.0):
        """
        Initializes the OutputAnalyzer.

        Args:
            orchestrator: The deployment orchestrator to use for analysis.
            meta_prompt_template: The template for the analysis meta-prompt.
            temperature: The temperature to use for the analysis model.
        """
        if not meta_prompt_template:
            raise ValueError("meta_prompt_template cannot be empty.")
        self.orchestrator = orchestrator
        self.meta_prompt_template = meta_prompt_template
        self.temperature = temperature

    async def analyze(self, prompt: str, output: str) -> Dict[str, Any]:
        """
        Analyzes the given prompt's output for flaws.

        Args:
            prompt: The prompt that was used to generate the output.
            output: The output generated by the prompt.

        Returns:
            A dictionary containing the analysis results.
        """
        logger.info("Analyzing prompt output with an AI critic...")
        analysis_prompt = self.meta_prompt_template.format(prompt=prompt, output=output)

        try:
            # Use invoke_model and request a JSON response directly.
            response = await self.orchestrator.invoke_model(
                prompt=analysis_prompt,
                temperature=self.temperature,
                response_format="json_object"
            )
            
            if not response or not response.get("text"):
                raise ValueError("Analysis generation returned an empty response.")

            analysis_result = json.loads(response["text"])
            logger.info(f"Analysis successful: {analysis_result.get('feedback_summary')}")
            return analysis_result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from analysis response: {response.get('text', '') if response else 'No response'}", exc_info=True)
            return {
                "flaws_found": True,
                "feedback_summary": "Error: The AI critic returned a response that was not valid JSON.",
                "analysis_summary": {}
            }
        except Exception as e:
            logger.error("An unexpected error occurred during output analysis: %s", e, exc_info=True)
            return {
                "flaws_found": True,
                "feedback_summary": f"An unexpected error occurred: {e}",
                "analysis_summary": {}
            } 