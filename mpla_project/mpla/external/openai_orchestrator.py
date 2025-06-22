import os
import httpx
from typing import Optional, Dict, Any, List

from mpla.core.deployment_orchestrator import DeploymentOrchestrator
from mpla.knowledge_base.schemas import PromptVersion, TargetAIProfile, AIOutput

# Load .env file for local development if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv() # take environment variables from .env.
except ImportError:
    pass # python-dotenv not found, proceed without it (rely on system env vars)

DEFAULT_OPENAI_API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-3.5-turbo" # A common, cost-effective model

class OpenAIDeploymentOrchestrator(DeploymentOrchestrator):
    """A DeploymentOrchestrator for interacting with OpenAI's Chat Completions API."""

    def __init__(self, api_key: str, api_base: Optional[str] = None):
        """
        Initializes the orchestrator.

        Args:
            api_key: The OpenAI API key.
            api_base: The OpenAI API base URL (optional).
        """
        self.api_key = api_key
        self.api_base = api_base or DEFAULT_OPENAI_API_BASE
        self.client = httpx.AsyncClient()

    async def deploy_and_collect(
        self, 
        prompt_version: PromptVersion, 
        ai_profile: TargetAIProfile
    ) -> Optional[AIOutput]:
        """Deploys a prompt to the OpenAI API and collects the output.

        Args:
            prompt_version: The PromptVersion object containing the prompt text.
            ai_profile: The TargetAIProfile. The `name` field is used as the model name (e.g., "gpt-4").
                        The `capabilities` field could in future versions hold parameters like temperature, max_tokens.

        Returns:
            An AIOutput object containing the data from the AI, or None if deployment/collection fails.
        """
        if not self.api_key:
            print(f"Error: OpenAI API key was not provided to the orchestrator.")
            return None

        model_name = ai_profile.name if ai_profile.name else DEFAULT_MODEL
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Constructing a simple payload. This can be extended to include roles, history, etc.
        # For now, we treat the prompt_text as a single user message.
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": prompt_version.prompt_text}
            ],
        }

        # Add other parameters from ai_profile.capabilities if they exist
        if ai_profile.capabilities:
            if "temperature" in ai_profile.capabilities:
                payload["temperature"] = float(ai_profile.capabilities["temperature"])
            if "max_tokens" in ai_profile.capabilities:
                payload["max_tokens"] = int(ai_profile.capabilities["max_tokens"])

        chat_completions_url = f"{self.api_base.rstrip('/')}/chat/completions"

        try:
            print(f"Sending prompt to OpenAI model: {model_name} at {chat_completions_url}...")
            response = await self.client.post(chat_completions_url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            
            response_data = response.json()
            
            # Extract the content from the first choice's message
            # (OpenAI API can return multiple choices, we typically use the first)
            if response_data.get("choices") and len(response_data["choices"]) > 0:
                message = response_data["choices"][0].get("message")
                if message and "content" in message:
                    ai_content = message["content"]
                    # The AIOutput expects prompt_version_id, which will be set by the agent
                    # when this AIOutput object is persisted.
                    return AIOutput(
                        prompt_version_id=prompt_version.id if prompt_version.id is not None else -1, # Placeholder if id not set yet
                        raw_output_data={"text": ai_content, "full_response": response_data}
                    )
                else:
                    print(f"Error: 'content' not found in OpenAI response message: {message}")
                    return AIOutput(
                        prompt_version_id=prompt_version.id if prompt_version.id is not None else -1,
                        raw_output_data={"error": "Content not found in response", "full_response": response_data}
                    )
            else:
                print(f"Error: 'choices' not found or empty in OpenAI response: {response_data}")
                return AIOutput(
                    prompt_version_id=prompt_version.id if prompt_version.id is not None else -1,
                    raw_output_data={"error": "Choices not found in response", "full_response": response_data}
                )

        except httpx.HTTPStatusError as e:
            print(f"HTTP error calling OpenAI API: {e.response.status_code} - {e.response.text}")
            error_content = {"error": f"HTTP {e.response.status_code}", "details": e.response.text}
            try: # Try to parse JSON error from OpenAI if possible
                error_content["details_json"] = e.response.json()
            except Exception:
                pass
            return AIOutput(prompt_version_id=prompt_version.id if prompt_version.id is not None else -1, raw_output_data=error_content)
        except httpx.RequestError as e:
            print(f"Request error calling OpenAI API: {e}")
            return AIOutput(prompt_version_id=prompt_version.id if prompt_version.id is not None else -1, raw_output_data={"error": "RequestError", "details": str(e)})
        except Exception as e:
            print(f"An unexpected error occurred during OpenAI API call: {e}")
            import traceback
            traceback.print_exc() # For debugging unexpected issues
            return AIOutput(prompt_version_id=prompt_version.id if prompt_version.id is not None else -1, raw_output_data={"error": "UnexpectedError", "details": str(e)})

    async def close(self):
        """Closes the httpx client session."""
        await self.client.aclose()

# Example usage (for manual testing of this file)
# async def main():
#     # IMPORTANT: Set your OPENAI_API_KEY environment variable before running this.
#     # You can create a .env file in the project root with: 
#     # OPENAI_API_KEY="your_actual_api_key"
#     api_key = os.getenv("OPENAI_API_KEY")
#     if not api_key:
#         print("OPENAI_API_KEY not set. Exiting example.")
#         return
#
#     orchestrator = OpenAIDeploymentOrchestrator(api_key=api_key)
#
#     # Create dummy PromptVersion and TargetAIProfile for testing
#     test_prompt_version = PromptVersion(
#         id=1, # Dummy ID
#         original_prompt_id=1,
#         iteration_id=1,
#         version_number=1,
#         prompt_text="What is the capital of France? Answer in one word.",
#         enhancement_rationale="Test prompt"
#     )
#     test_ai_profile = TargetAIProfile(
#         id=1, # Dummy ID
#         name="gpt-3.5-turbo", # Specify a model name
#         capabilities=["text-generation"]
#     )
#
#     print(f"Sending test prompt: '{test_prompt_version.prompt_text}'")
#     ai_output = await orchestrator.deploy_and_collect(test_prompt_version, test_ai_profile)
#
#     if ai_output:
#         print("Received AIOutput:")
#         print(f"  Prompt Version ID (intended): {ai_output.prompt_version_id}")
#         print(f"  Raw Output Data: {ai_output.raw_output_data}")
#     else:
#         print("Failed to get AI output.")
#     
#     await orchestrator.close()
#
# if __name__ == "__main__":
#     # To run this example: 
#     # 1. Ensure httpx and python-dotenv are installed: pip install httpx python-dotenv
#     # 2. Create a .env file in your project root (e.g., mpla_project/.env) with your OpenAI API key:
#     #    OPENAI_API_KEY="sk-yourActualOpenAIapiKeyGoesHere"
#     # 3. Uncomment the asyncio.run(main()) line and run this file directly.
#     load_dotenv()
#     import asyncio
#     # asyncio.run(main()) 