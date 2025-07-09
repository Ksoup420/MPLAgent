from typing import Optional, Tuple
from .learning_refinement import LearningRefinementModule
from ..knowledge_base.schemas import PromptVersion, EvaluationResult, AIOutput, TargetAIProfile
from ..external.google_gemini_orchestrator import GoogleGeminiDeploymentOrchestrator
from ..core.exceptions import EnhancementError # Using EnhancementError as it's a similar process

class LLMAssistedLearningRefinementModule(LearningRefinementModule):
    """
    Uses an LLM to analyze evaluation results and suggest prompt refinements.
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
            raise EnhancementError(f"Failed to parse LLM response for refinement: {e}. Raw response: {response_text[:200]}")

    async def learn_and_refine(self, current_prompt: PromptVersion, eval_result: EvaluationResult) -> Optional[PromptVersion]:
        """
        Uses a meta-prompt to ask an LLM to refine the prompt based on evaluation scores.
        """
        if eval_result.metric_scores.get("overall_satisfaction", 0) >= 4.5:
            return None 

        meta_prompt_text = (
            "I have a prompt that is underperforming.\\n\\n"
            f'**Current Prompt:**\\n"{current_prompt.prompt_text}"\\n\\n'
            f"**Evaluation Scores:**\\n{eval_result.metric_scores}\\n\\n"
            "**Goal:** Improve the 'overall_satisfaction' score.\\n\\n"
            "Your task is to analyze the prompt and the scores, then generate a new, refined prompt that addresses the perceived weaknesses. "
            "Also, provide a brief rationale for the changes.\\n\\n"
            "Format your response exactly as follows:\\n"
            "Rationale: [Your rationale for the changes]\\n"
            "---\\n"
            "Prompt: [Your new, refined prompt]"
        )

        temp_prompt_version = PromptVersion(prompt_text=meta_prompt_text, version_number=0, original_prompt_id=0)
        temp_ai_profile = TargetAIProfile(name="gemini-1.5-flash", capabilities=["text-generation"])

        ai_output: Optional[AIOutput] = await self.orchestrator.deploy_and_collect(
            prompt_version=temp_prompt_version,
            ai_profile=temp_ai_profile
        )

        if not ai_output or not isinstance(ai_output.raw_output_data, dict) or "text" not in ai_output.raw_output_data:
            error_details = ai_output.raw_output_data if ai_output else "No output"
            raise EnhancementError(f"LLM call for learning/refinement failed. Details: {error_details}")

        response_text = ai_output.raw_output_data["text"]
        
        new_prompt_text, rationale = self._parse_response(response_text)

        return PromptVersion(
            original_prompt_id=current_prompt.original_prompt_id,
            version_number=current_prompt.version_number + 1,
            prompt_text=new_prompt_text,
            enhancement_rationale=rationale,
            target_ai_profile_id=current_prompt.target_ai_profile_id
        ) 