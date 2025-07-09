from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import json

from mpla.knowledge_base.schemas import AIOutput, EvaluationResult
from mpla.core.evaluation_engine import EvaluationEngine
from mpla.external.google_gemini_orchestrator import GoogleGeminiOrchestrator
from mpla.utils.logging import logger

class LLMEvaluationEngine(EvaluationEngine):
    """
    An advanced implementation of the EvaluationEngine that uses a large language model
    to perform a qualitative and quantitative assessment of AI output.
    """

    def __init__(self, orchestrator: GoogleGeminiOrchestrator, evaluation_model: str = "gemini-1.5-flash"):
        """
        Initializes the LLM-based evaluation engine.

        Args:
            orchestrator: The LLM orchestrator to use for making evaluation calls.
            evaluation_model: The specific model to use for evaluation.
        """
        self.orchestrator = orchestrator
        self.evaluation_model = evaluation_model
        
    async def evaluate(
        self, 
        ai_output: AIOutput,
        metrics_config: Dict[str, Any]
    ) -> Optional[EvaluationResult]:
        """
        Evaluates the given AI output using an LLM.

        Args:
            ai_output: The AIOutput object to evaluate.
            metrics_config: User-defined goals or metrics that the AI output should be measured against.
                           Example: {"user_objective": "Create a python function for quicksort", "quality_dimensions": ["clarity", "efficiency", "correctness"]}

        Returns:
            An EvaluationResult object containing the LLM-generated scores and analysis.
        """
        if not ai_output or not ai_output.raw_output_data:
            logger.warning("LLM EvaluationEngine: No AI output data to evaluate.")
            return None

        text_to_evaluate = self._extract_text(ai_output)
        if not text_to_evaluate:
            logger.warning("LLM EvaluationEngine: No text found in AI output to evaluate.")
            return EvaluationResult(
                ai_output_id=ai_output.id or -1,
                metric_scores={"error": 1, "overall_satisfaction": 0},
                qualitative_feedback="No evaluable text content found in AI output.",
                target_metrics_snapshot=metrics_config
            )

        meta_prompt = self._build_evaluation_prompt(text_to_evaluate, metrics_config)
        
        try:
            # We need a generic way to call the LLM, maybe a method on the orchestrator
            # This part needs to be adapted to how orchestrators actually work
            # For now, let's assume a generic 'invoke' method exists.
            # This is a conceptual implementation detail to be refined.
            response = await self.orchestrator.invoke_model(
                model=self.evaluation_model, 
                prompt=meta_prompt,
                temperature=0.1, # Low temperature for consistent evaluation
                response_format="json_object" # Request structured output
            )

            if not response or not response.get("text"):
                logger.error("LLM evaluation failed: No response from model.")
                return None
            
            eval_data = json.loads(response["text"])

            return EvaluationResult(
                ai_output_id=ai_output.id or -1,
                metric_scores=eval_data.get("metric_scores", {}),
                qualitative_feedback=eval_data.get("qualitative_feedback", "No feedback provided."),
                target_metrics_snapshot=metrics_config
            )

        except json.JSONDecodeError:
            logger.error("LLM evaluation failed: Could not decode JSON from model response.")
            # Maybe retry logic here in a future version
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during LLM evaluation: {e}")
            return None

    def _extract_text(self, ai_output: AIOutput) -> str:
        """Extracts the text to be evaluated from the AIOutput object."""
        if isinstance(ai_output.raw_output_data, str):
            return ai_output.raw_output_data
        elif isinstance(ai_output.raw_output_data, dict):
            return ai_output.raw_output_data.get("text", "")
        return ""

    def _build_evaluation_prompt(self, generated_text: str, metrics_config: Dict[str, Any]) -> str:
        """Constructs the meta-prompt for the evaluation LLM."""
        
        user_objective = metrics_config.get("user_objective", "No specific objective provided.")
        quality_dimensions = metrics_config.get("quality_dimensions", ["clarity", "relevance", "completeness"])

        return f"""
You are an expert AI Output Quality Analyst. Your task is to evaluate a generated piece of text based on a user's objective and a set of quality dimensions. Provide your analysis in a structured JSON format.

**User's Objective:**
{user_objective}

**Generated Text to Evaluate:**
---
{generated_text}
---

**Instructions:**
1.  **Analyze:** Carefully read the generated text and compare it against the user's objective.
2.  **Score:** For each quality dimension listed below, provide a score from 0.0 to 5.0, where 0.0 is "Fails Completely" and 5.0 is "Exceeds Expectations".
3.  **Overall Score:** Provide an "overall_satisfaction" score based on a holistic assessment.
4.  **Feedback:** Provide concise, constructive, qualitative feedback explaining your reasoning for the scores.

**Quality Dimensions to Score:**
- {', '.join(quality_dimensions)}

**Required JSON Output Format:**
{{
  "metric_scores": {{
    "quality_dimension_1": <score_float>,
    "quality_dimension_2": <score_float>,
    ...
    "overall_satisfaction": <score_float>
  }},
  "qualitative_feedback": "<Your detailed analysis and reasoning here>"
}}

**BEGIN EVALUATION:**
""" 