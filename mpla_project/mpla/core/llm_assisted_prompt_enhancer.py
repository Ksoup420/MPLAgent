from typing import Optional, Tuple
from .prompt_enhancer import BasePromptEnhancer
from ..knowledge_base.schemas import TargetAIProfile, PromptVersion, AIOutput
from ..external.google_gemini_orchestrator import GoogleGeminiDeploymentOrchestrator
from ..core.exceptions import EnhancementError


class LLMAssistedPromptEnhancer(BasePromptEnhancer):
    """
    A prompt enhancer that uses an LLM to refine and improve prompts.
    """
    def __init__(self, orchestrator: GoogleGeminiDeploymentOrchestrator):
        self.orchestrator = orchestrator

    def _parse_response(self, response_text: str) -> Tuple[str, str]:
        """Parses the LLM's response to extract the rationale and the new prompt."""
        try:
            rationale_part, prompt_part = response_text.split("---", 1)
            
            rationale = rationale_part.replace("Rationale:", "").strip()
            prompt = prompt_part.replace("Prompt:", "").strip()

            if not prompt:
                raise ValueError("LLM response did not contain a prompt.")

            return prompt, rationale
        except ValueError as e:
            raise EnhancementError(f"Failed to parse LLM response for enhancement: {e}. Raw response: {response_text[:200]}")

    async def enhance(self, original_prompt_text: str, ai_profile: Optional[TargetAIProfile] = None) -> Tuple[str, str]:
        """
        Uses a meta-prompt to ask an LLM to enhance the original prompt.
        """
        meta_prompt_text = (
            "As an expert in prompt engineering, your task is to refine the following prompt to improve its clarity, "
            "effectiveness, and alignment with best practices for large language models.\\n\\n"
            f'Original Prompt: "{original_prompt_text}"\\n\\n'
            "Please provide a revised version of the prompt and a brief rationale for your changes.\\n"
            "Format your response exactly as follows:\\n\\n"
            "Rationale: [Your rationale here]\\n"
            "---\\n"
            "Prompt: [Your revised prompt here]"
        )

        # We need a temporary PromptVersion and AIProfile to use the orchestrator
        temp_prompt_version = PromptVersion(prompt_text=meta_prompt_text, version_number=0, original_prompt_id=0)
        # Use a sensible default model and temperature for the meta-task
        temp_ai_profile = TargetAIProfile(
            name="gemini-1.5-flash", 
            capabilities={"type": "text-generation", "temperature": 0.5}
        )

        ai_output: Optional[AIOutput] = await self.orchestrator.deploy_and_collect(
            prompt_version=temp_prompt_version,
            ai_profile=temp_ai_profile
        )

        if not ai_output or not isinstance(ai_output.raw_output_data, dict) or "text" not in ai_output.raw_output_data:
            error_details = ai_output.raw_output_data if ai_output else "No output"
            raise EnhancementError(f"LLM call for enhancement failed or returned an invalid response. Details: {error_details}")

        response_text = ai_output.raw_output_data["text"]
        
        enhanced_prompt, rationale = self._parse_response(response_text)
        
        return enhanced_prompt, rationale 