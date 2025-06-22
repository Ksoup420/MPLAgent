import os
import google.generativeai as genai
from typing import Optional, List

from mpla.core.deployment_orchestrator import DeploymentOrchestrator
from mpla.knowledge_base.schemas import PromptVersion, TargetAIProfile, AIOutput

class GoogleGeminiDeploymentOrchestrator(DeploymentOrchestrator):
    """
    A deployment orchestrator for interacting with Google's Gemini models.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initializes the orchestrator and configures the Gemini API.

        Args:
            api_key: The Google API key.

        Raises:
            ValueError: If the API key is not provided.
        """
        if not api_key:
            raise ValueError("Google API key must be provided.")
        
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

    async def deploy_and_collect(
        self,
        prompt_version: PromptVersion,
        ai_profile: TargetAIProfile
    ) -> Optional[AIOutput]:
        """
        Sends a prompt to the configured Gemini model and returns the response.

        Args:
            prompt_version: The PromptVersion object containing the prompt text.
            ai_profile: The TargetAIProfile, where `name` is the model name.

        Returns:
            An AIOutput object containing the data from the AI, or None on failure.
            
        Raises:
            Exception: If the API call fails or returns an empty response.
        """
        model_name = ai_profile.name or 'gemini-1.5-flash'
        
        # Extract generation config from capabilities
        capabilities = ai_profile.capabilities or {}
        temperature = capabilities.get("temperature")

        generation_config = None
        if temperature is not None:
            generation_config = genai.types.GenerationConfig(temperature=float(temperature))

        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config
        )
        
        try:
            print(f"Deploying prompt to Gemini model: {model_name} with temp: {temperature}...")
            request_options = {"timeout": 60}
            response: genai.types.GenerateContentResponse = await model.generate_content_async(
                prompt_version.prompt_text,
                request_options=request_options
            )
            
            if response and response.text:
                print("...Response received successfully.")
                return AIOutput(
                    prompt_version_id=prompt_version.id if prompt_version.id is not None else -1,
                    raw_output_data={"text": response.text, "full_response": str(response)}
                )
            else:
                print("API call returned an empty or invalid response.")
                return AIOutput(
                    prompt_version_id=prompt_version.id if prompt_version.id is not None else -1,
                    raw_output_data={"error": "Empty response from API", "full_response": str(response)}
                )

        except Exception as e:
            print(f"An error occurred while communicating with the Google Gemini API: {e}")
            return AIOutput(
                prompt_version_id=prompt_version.id if prompt_version.id is not None else -1,
                raw_output_data={"error": "API communication error", "details": str(e)}
            )

    async def deploy_and_collect_from_history(
        self,
        history: List[str],
        ai_profile: TargetAIProfile
    ) -> Optional[AIOutput]:
        """
        Sends a conversational history to the Gemini model and returns the response.
        The history should be an even-numbered list of strings, representing
        alternating user and model messages.

        Args:
            history: A list of strings representing the alternating user/model conversation.
            ai_profile: The TargetAIProfile, where `name` is the model name.

        Returns:
            An AIOutput object containing the data from the AI, or None on failure.
        """
        model_name = ai_profile.name or 'gemini-1.5-flash'
        
        capabilities = ai_profile.capabilities or {}
        temperature = capabilities.get("temperature")

        generation_config = None
        if temperature is not None:
            generation_config = genai.types.GenerationConfig(temperature=float(temperature))

        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config
        )
        
        # Convert the flat list of strings into the required dict format
        formatted_history = []
        for i, content in enumerate(history[:-1]): # All but the last message
            role = "user" if i % 2 == 0 else "model"
            formatted_history.append({'role': role, 'parts': [content]})

        try:
            print(f"Deploying conversation to Gemini model: {model_name} with temp: {temperature}...")
            
            # Start a chat session with the formatted history
            chat_session = model.start_chat(history=formatted_history)
            
            # Send the final message
            last_prompt = history[-1]
            response: genai.types.GenerateContentResponse = await chat_session.send_message_async(
                last_prompt,
            )
            
            if response and response.text:
                print("...Response received successfully.")
                # We don't have a real PromptVersion, so we use a dummy ID.
                return AIOutput(
                    prompt_version_id=-1, 
                    raw_output_data={"text": response.text, "full_response": str(response)}
                )
            else:
                print("API call returned an empty or invalid response.")
                return AIOutput(
                    prompt_version_id=-1,
                    raw_output_data={"error": "Empty response from API", "full_response": str(response)}
                )

        except Exception as e:
            print(f"An error occurred while communicating with the Google Gemini API: {e}")
            return AIOutput(
                prompt_version_id=-1,
                raw_output_data={"error": "API communication error", "details": str(e)}
            )

    async def generate_text(self, prompt: str, temperature: float) -> Optional[str]:
        """
        Generates text from a single string prompt, for internal use by modules.

        Args:
            prompt: The text prompt to send to the model.
            temperature: The generation temperature.

        Returns:
            The generated text as a string, or None on failure.
        """
        model_name = 'gemini-1.5-flash' # Use a default fast model
        
        generation_config = genai.types.GenerationConfig(temperature=float(temperature))

        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config
        )
        
        try:
            response: genai.types.GenerateContentResponse = await model.generate_content_async(
                prompt
            )
            return response.text if response and response.text else None
        except Exception as e:
            print(f"An error occurred during raw text generation: {e}")
            # Return None to signal failure to the calling module
            return None

    async def close(self):
        """A no-op for the Gemini client, which doesn't need to be closed."""
        pass

    # Architectural Note:
    # The current `MPLAgent` class is designed to use a `deploy_and_collect` method
    # with a more complex signature (taking `PromptVersion` and `TargetAIProfile`
    # objects and returning an `AIOutput` object).
    #
    # This `deploy_and_collect` method is intentionally simpler, as specified for the
    # initial MVP integration. To fully integrate with the existing `MPLAgent`,
    # either the agent will need to be adapted to use this simpler interface,
    # or this class will need to be updated to implement the more complex
    # `deploy_and_collect` method, which would involve handling the richer data
    # objects from the knowledge base. This simpler interface is sufficient for
    # initial functional testing. 