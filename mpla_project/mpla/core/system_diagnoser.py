import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DIAGNOSIS_META_PROMPT = """
You are an expert AI System Reliability Engineer. A component within your autonomous agent framework has thrown an exception. Your task is to analyze the context and the error to determine the root cause and propose a concrete, actionable recovery strategy.

**Context:**
- **Failing Component:** `{component_name}`
- **Input to Component:** 
```json
{component_input}
```
- **Full Traceback:**
```
{traceback}
```

**Analysis Instructions:**
1.  **Root Cause Analysis:** Based on the traceback and the component that failed, what is the most likely cause of this error? (e.g., "API key invalid," "Network timeout," "Malformed input data," "LLM provider outage," "Internal bug in component").
2.  **Propose Recovery Strategy:** Based on the root cause, choose the most appropriate recovery strategy from the list below.
    *   `retry`: The error seems transient (e.g., temporary network issue, rare API glitch). The operation should be retried.
    *   `use_fallback`: The primary component seems to be failing consistently or is unavailable. The system should switch to a simpler, more reliable fallback component if one exists.
    *   `abort_iteration`: The error is severe and likely unrecoverable within this iteration (e.g., a critical bug, fundamentally invalid input). The agent should stop the current iteration and move to the next.
    *   `halt_system`: The error is critical and affects the entire system's stability (e.g., invalid configuration, database connection lost). The agent should halt all operations safely.

**Required JSON Output:**
Your output MUST be a valid JSON object with the following structure:
{{
  "root_cause_analysis": "<Your detailed analysis of the root cause>",
  "recovery_strategy": "<'retry'|'use_fallback'|'abort_iteration'|'halt_system'>",
  "justification": "<A concise justification for your chosen strategy>"
}}
"""

class SystemDiagnoser:
    """
    Diagnoses system errors using an LLM and proposes recovery strategies.
    """

    def __init__(self, orchestrator: Any, temperature: float = 0.0):
        """
        Initializes the SystemDiagnoser.

        Args:
            orchestrator: The LLM orchestrator to use for diagnosis.
            temperature: The temperature for the diagnosis model (should be low for consistency).
        """
        self.orchestrator = orchestrator
        self.temperature = temperature

    async def diagnose_and_propose_remedy(
        self,
        component_name: str,
        exception: Exception,
        traceback_str: str,
        component_input: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Uses an LLM to analyze an error and propose a recovery plan.

        Args:
            component_name: The name of the component that failed.
            exception: The exception object.
            traceback_str: The formatted traceback string.
            component_input: The input data that caused the component to fail.

        Returns:
            A dictionary containing the diagnosis and proposed strategy, or None on failure.
        """
        logger.info(f"Diagnosing failure in component: {component_name}...")
        
        input_str = json.dumps(component_input, indent=2, default=str) # Safely serialize input
        
        diagnosis_prompt = DIAGNOSIS_META_PROMPT.format(
            component_name=component_name,
            component_input=input_str,
            traceback=traceback_str
        )

        try:
            response = await self.orchestrator.invoke_model(
                prompt=diagnosis_prompt,
                temperature=self.temperature,
                response_format="json_object"
            )

            if not response or not response.get("text"):
                logger.error("System diagnosis failed: LLM returned an empty response.")
                return None
            
            diagnosis_result = json.loads(response["text"])
            logger.info(f"Diagnosis complete. Proposed strategy: {diagnosis_result.get('recovery_strategy')}")
            return diagnosis_result

        except Exception as e:
            logger.error(f"A critical error occurred within the SystemDiagnoser itself: {e}", exc_info=True)
            return None 