from abc import ABC, abstractmethod
from typing import Optional, Tuple, List

from mpla.knowledge_base.schemas import TargetAIProfile, PromptVersion

class BasePromptEnhancer(ABC):
    """Abstract Base Class for Prompt Enhancer modules.
    
    Defines the interface for applying the "Prompt Architect" methodology
    to analyze, strategize, and construct refined prompts.
    """

    @abstractmethod
    async def enhance(
        self, 
        original_prompt_text: str, 
        ai_profile: Optional[TargetAIProfile] = None,
        # previous_prompt_version: Optional[PromptVersion] = None, # Could be used for context
        # evaluation_of_previous: Optional_EvaluationResult] = None # For refinement steps
    ) -> Tuple[str, str]: # Returns (enhanced_prompt_text, rationale)
        """Applies the enhancement logic to a prompt.

        Args:
            original_prompt_text: The text of the prompt to enhance.
            ai_profile: Optional profile of the target AI system.
            
        Returns:
            A tuple containing the enhanced prompt text and the rationale for the changes.
        """
        pass

class RuleBasedPromptEnhancer(BasePromptEnhancer):
    """An initial, rule-based implementation of the Prompt Enhancer.
    
    Applies a few simple, predefined rules to enhance a prompt.
    """

    async def enhance(
        self, 
        original_prompt_text: str, 
        ai_profile: Optional[TargetAIProfile] = None
    ) -> Tuple[str, str]:
        """Enhances the prompt using a series of predefined rules.

        Args:
            original_prompt_text: The text of the prompt to enhance.
            ai_profile: Optional profile of the target AI system (currently unused by these basic rules).
            
        Returns:
            A tuple containing the enhanced prompt text and the rationale for the changes.
        """
        enhanced_prompt = original_prompt_text
        applied_rules_rationale: List[str] = []

        # Rule 1: Add a default persona if none seems present.
        # Simple check: if prompt doesn't start with common persona-setting phrases.
        # A more sophisticated check would involve NLP to understand existing persona.
        persona_keywords = ["you are", "act as", "your role is", "behave like"]
        if not any(keyword in enhanced_prompt.lower()[:50] for keyword in persona_keywords):
            persona_prefix = "You are a helpful and insightful AI assistant. "
            enhanced_prompt = persona_prefix + enhanced_prompt
            applied_rules_rationale.append("Added a default 'helpful AI assistant' persona for role clarity.")

        # Rule 2: Request conciseness for very short prompts that aren't specific about output length.
        # (Assuming words are space-separated)
        prompt_word_count = len(enhanced_prompt.split())
        length_keywords = ["concise", "brief", "short", "summary", "detailed", "long", "elaborate", "words", "sentences", "paragraphs"]
        if prompt_word_count < 15 and not any(keyword in enhanced_prompt.lower() for keyword in length_keywords):
            conciseness_suffix = " Please provide a clear and concise response."
            if not enhanced_prompt.endswith((".", "?", "!")):
                enhanced_prompt += "."
            enhanced_prompt += conciseness_suffix
            applied_rules_rationale.append("Appended a request for conciseness due to the original prompt's brevity.")

        # Rule 3: Suggest structure for questions.
        if enhanced_prompt.strip().endswith("?"):
            structure_suggestion_suffix = " If appropriate, consider structuring your answer clearly, perhaps using bullet points for key details or a step-by-step explanation."
            if not enhanced_prompt.endswith((".", "?", "!")): # Should usually end with '?' but defensive
                 enhanced_prompt += "."
            enhanced_prompt += structure_suggestion_suffix
            applied_rules_rationale.append("Suggested a structured answer format as the prompt is a question.")
        
        # Rule 4: Add a polite closing if not already seeming like a command
        # This is a very simplistic check
        if not enhanced_prompt.strip().endswith(("?", "!")) and "please" not in enhanced_prompt.lower():
            if not any(enhanced_prompt.lower().startswith(cmd) for cmd in ["generate", "create", "write", "list", "explain"]):
                 politeness_suffix = " Thank you."
                 if not enhanced_prompt.endswith("."):
                     enhanced_prompt += "."
                 enhanced_prompt += politeness_suffix
                 applied_rules_rationale.append("Added a polite closing statement.")

        if not applied_rules_rationale:
            rationale = "No specific enhancement rules triggered. Original prompt deemed sufficient by basic rules."
        else:
            rationale = "Enhancements applied: " + " ".join(applied_rules_rationale)
        
        return enhanced_prompt, rationale

# Example Usage (for testing within this file)
# async def test_enhancer():
#     enhancer = RuleBasedPromptEnhancer()

#     prompts_to_test = [
#         "What is a black hole?",
#         "Tell me about an LLM.",
#         "Generate a python function to sort a list",
#         "The weather today",
#         "You are an expert historian. Describe the fall of Rome."
#     ]

#     for p_text in prompts_to_test:
#         enhanced, expl = await enhancer.enhance(p_text)
#         print(f"Original: {p_text}")
#         print(f"Enhanced: {enhanced}")
#         print(f"Rationale: {expl}")
#         print("---")

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(test_enhancer()) 