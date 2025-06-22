from abc import ABC, abstractmethod
from typing import Optional

from mpla.knowledge_base.schemas import PromptVersion, TargetAIProfile, AIOutput

class DeploymentOrchestrator(ABC):
    """Abstract Base Class for Deployment Orchestrator modules.
    
    Defines the interface for managing the deployment of prompts to target AI systems
    and collecting their outputs.
    """

    @abstractmethod
    async def deploy_and_collect(
        self, 
        prompt_version: PromptVersion, 
        ai_profile: TargetAIProfile
    ) -> Optional[AIOutput]:
        """Deploys a prompt to the target AI and collects the output.

        Args:
            prompt_version: The PromptVersion object containing the prompt text.
            ai_profile: The TargetAIProfile defining the AI system to use.

        Returns:
            An AIOutput object containing the data from the AI, or None if deployment/collection fails.
        """
        pass 