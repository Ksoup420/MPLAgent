from abc import ABC, abstractmethod
from typing import Optional, List
import copy # To deepcopy prompt object for modification

from mpla.knowledge_base.schemas import PromptVersion, EvaluationResult

class LearningRefinementModule(ABC):
    """Abstract Base Class for Learning and Refinement modules.
    
    Defines the interface for analyzing evaluation results and generating
    an improved version of a prompt.
    """

    @abstractmethod
    async def learn_and_refine(
        self, 
        current_prompt_version: PromptVersion,
        evaluation_result: EvaluationResult
    ) -> Optional[PromptVersion]:
        """Analyzes evaluation and refines the prompt.

        Args:
            current_prompt_version: The prompt version that was just evaluated.
            evaluation_result: The EvaluationResult for the output of the current_prompt_version.

        Returns:
            A new PromptVersion object with the refined prompt, or None if no refinement is proposed.
        """
        pass

class RuleBasedLearningRefinementModule(LearningRefinementModule):
    """
    A basic learning and refinement module that applies predefined rules
    to modify a prompt based on its evaluation results.
    """

    # Define thresholds for scores (assuming a 0-5 scale from BasicEvaluationEngine)
    LOW_SCORE_THRESHOLD = 2.5 # Score below which a metric is considered poor
    ACCEPTABLE_SCORE_THRESHOLD = 3.5 # Score above which a metric might be okay but could improve

    async def learn_and_refine(
        self, 
        current_prompt: PromptVersion,
        eval_result: EvaluationResult
    ) -> Optional[PromptVersion]:
        
        # For the web UI demo, we want to ensure the refinement cycle always continues.
        # This module will now append a generic refinement instruction on each iteration
        # to guarantee a new version is created and displayed to the user.
        
        original_text = current_prompt.prompt_text
        iteration = current_prompt.version_number
        
        # Append a new, generic instruction based on the iteration number
        new_instruction = f" (Refinement #{iteration}: Please improve the response further.)"
        new_prompt_text = original_text + new_instruction
        
        rationale = f"Appended a generic instruction to force iterative refinement for demonstration purposes. Iteration: {iteration}."

        next_prompt_version = PromptVersion(
            original_prompt_id=current_prompt.original_prompt_id,
            version_number=current_prompt.version_number + 1,
            prompt_text=new_prompt_text,
            enhancement_rationale=rationale,
            target_ai_profile_id=current_prompt.target_ai_profile_id,
        )
        return next_prompt_version