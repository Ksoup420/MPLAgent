from typing import Dict, Any

from mpla.core.evaluation_engine import EvaluationEngine, BasicEvaluationEngine
from mpla.core.llm_evaluation_engine import LLMEvaluationEngine
from mpla.external.google_gemini_orchestrator import GoogleGeminiOrchestrator
from mpla.utils.logging import logger

def create_evaluation_engine(settings: Dict[str, Any], orchestrator: GoogleGeminiOrchestrator) -> EvaluationEngine:
    """
    Factory function to create an evaluation engine based on provided settings.

    Args:
        settings: A dictionary containing the configuration, including the 'evaluation_mode'.
                  'evaluation_mode' can be 'basic' or 'llm_assisted'.
        orchestrator: The LLM orchestrator instance, required for the LLMEvaluationEngine.

    Returns:
        An instance of an EvaluationEngine.
    
    Raises:
        ValueError: If an unknown evaluation mode is specified.
    """
    evaluation_mode = settings.get("evaluation_mode", "basic")
    logger.info(f"Creating evaluation engine with mode: {evaluation_mode}")

    if evaluation_mode == "llm_assisted":
        # Specific model for evaluation can be part of the settings in the future
        return LLMEvaluationEngine(orchestrator=orchestrator, evaluation_model="gemini-1.5-flash")
    elif evaluation_mode == "basic":
        return BasicEvaluationEngine()
    else:
        raise ValueError(f"Unknown evaluation mode: {evaluation_mode}") 