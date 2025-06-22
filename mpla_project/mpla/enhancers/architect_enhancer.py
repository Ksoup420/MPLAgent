"""
The ArchitectPromptEnhancer uses an LLM with a specific meta-prompt 
to recursively refine a user's prompt.
"""
import re
from typing import Optional, Tuple

from mpla.core.deployment_orchestrator import DeploymentOrchestrator
from mpla.core.prompt_enhancer import BasePromptEnhancer
from mpla.knowledge_base.schemas import TargetAIProfile, PromptVersion, AIOutput
from mpla.knowledge_base.db_connector import KnowledgeBase
from mpla.utils.logging import logger

# The meta-prompt is now stored in and loaded from the database.
# This constant is kept only for the one-time seeding process in the KB.
ARCHITECT_META_PROMPT = """
**Role:** You are a Prompt Architect AI.

**Objective:** Transform a given input prompt into a significantly more effective version, optimized for clarity, precision, and the ability to elicit high-quality responses from other AI systems.

**Input:** You will be provided with a single "Original Prompt" that requires enhancement.

**Process:**
1.  **Analyze Intent & Weaknesses:**
    *   Identify the core purpose and desired outcome of the Original Prompt.
    *   Critically diagnose ambiguities, vagueness, missing information, implicit assumptions, or structural flaws that could hinder an AI's performance.
2.  **Strategize Enhancements:**
    *   Determine necessary clarifications, contextual additions (e.g., background, constraints, illustrative examples), and structural improvements.
    *   Consider defining or refining a persona, tone, style, or specific output format for the AI that will ultimately process the enhanced prompt.
    *   Formulate changes to maximize the target AI's comprehension and minimize generic or off-target responses.
3.  **Construct Refined Prompt:**
    *   Create a new, "Enhanced Prompt." This prompt must be self-contained, precise, actionable, and ready for direct use with another AI system to achieve the original (but now clarified) intent.
4.  **Explain Rationale (Elucidation):**
    *   Provide a concise explanation detailing the key strategic changes made to the Original Prompt and the reasoning behind them. This explanation should highlight prompt engineering best practices demonstrated in the transformation.

**Output:**
Your output must be structured with clear headings.
1.  **Enhanced Prompt:**
    [The full text of the new, refined prompt]
2.  **Elucidation:**
    [Your full explanation of the changes made]

---
Now, please apply this process to the following Original Prompt.

**Original Prompt:**
"{user_prompt}"
"""

class ArchitectPromptEnhancer(BasePromptEnhancer):
    """
    An advanced prompt enhancer that uses a meta-prompt loaded from the 
    Knowledge Base to instruct an LLM to refine a given prompt.
    """

    def __init__(self, orchestrator: DeploymentOrchestrator, kb: KnowledgeBase):
        self.orchestrator = orchestrator
        self.kb = kb

    async def enhance(
        self, 
        original_prompt_text: str, 
        ai_profile: Optional[TargetAIProfile] = None
    ) -> Tuple[str, str]:
        """
        Uses the active 'architect' meta-prompt from the database to generate
        an enhanced prompt and its rationale.
        """
        logger.info("Using ArchitectPromptEnhancer to refine the prompt.")
        
        # 1. Load the active meta-prompt from the database, specifically the 'architect' one
        meta_prompt = await self.kb.get_active_meta_prompt(name_like="architect")
        if not meta_prompt or not meta_prompt.template:
            logger.error("No active 'architect' meta-prompt with a valid template found in the database. Falling back to a simple enhancement rule.")
            fallback_rationale = "Architect meta-prompt not found in the database. Applying a simple rule-based enhancement as a fallback."
            enhanced_prompt = original_prompt_text + "\n\n---\n\nInstruction: Please refine the prompt above to be clearer, more specific, and more effective for an AI assistant."
            return enhanced_prompt, fallback_rationale

        # 2. Construct the conversational history
        history = [
            meta_prompt.template,
            original_prompt_text
        ]

        # 3. Use the orchestrator's new history-based method
        logger.debug("Sending conversation to LLM for architectural enhancement.")
        
        # Use the specific temperature for the architect's LLM call.
        # The user's temperature setting is preserved in the original ai_profile for the main prompt.
        architect_ai_profile = ai_profile.model_copy(deep=True)
        if architect_ai_profile.capabilities is None:
            architect_ai_profile.capabilities = {}
        # The architect temp is now passed in via the capabilities dict
        # No need to override it here if it's passed correctly from the service layer

        ai_output: Optional[AIOutput] = await self.orchestrator.deploy_and_collect_from_history(
            history=history,
            ai_profile=architect_ai_profile
        )

        llm_response_text = None
        if ai_output and isinstance(ai_output.raw_output_data, dict):
             llm_response_text = ai_output.raw_output_data.get("text")

        if not llm_response_text:
            logger.error("Architect enhancer received no response from the LLM.")
            return original_prompt_text, "Error: No response from LLM."

        # 4. Parse the response
        enhanced_prompt, elucidation = self._parse_response(llm_response_text)

        if not enhanced_prompt:
            logger.warning("Could not parse 'Enhanced Prompt' from LLM response. Using original prompt.")
            return original_prompt_text, f"Parsing failed. LLM Response: {llm_response_text}"
        
        if not elucidation:
            logger.warning("Could not parse 'Elucidation' from LLM response.")
            elucidation = "Elucidation not provided by LLM."

        return enhanced_prompt, elucidation

    def _parse_response(self, response_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parses the LLM's response to extract the enhanced prompt and elucidation,
        expecting a clean, well-formatted output as per the meta-prompt's instructions.
        """
        try:
            # Use simple string splitting based on the strict headings we requested.
            # This is more robust than regex if the LLM follows instructions.
            prompt_heading = "**Enhanced Prompt:**"
            elucidation_heading = "**Elucidation:**"

            # Check if both headings are present
            if prompt_heading not in response_text or elucidation_heading not in response_text:
                logger.warning(f"Response did not contain the expected headings. Response: {response_text}")
                return None, None

            # Split the response text by the elucidation heading first
            parts = response_text.split(elucidation_heading)
            elucidation = parts[1].strip() if len(parts) > 1 else None

            # The first part should contain the enhanced prompt
            prompt_part = parts[0]
            # Split the first part by the prompt heading
            prompt_parts = prompt_part.split(prompt_heading)
            enhanced_prompt = prompt_parts[1].strip() if len(prompt_parts) > 1 else None

            if not enhanced_prompt:
                 logger.warning(f"Could not parse 'Enhanced Prompt' between the headings. Response: {response_text}")
            if not elucidation:
                 logger.warning(f"Could not parse 'Elucidation' after the heading. Response: {response_text}")

            return enhanced_prompt, elucidation

        except Exception as e:
            logger.error(f"Error parsing architect response: {e}\nResponse was:\n{response_text}")
            return None, None 