# MPLA: Meta-Prompt Learning Agent

This project implements the Meta-Prompt Learning Agent (MPLA), an autonomous system designed to iteratively refine and improve prompts for large language models.

## Overview

The MPLA orchestrates a perceive-decide-act cycle to enhance an initial prompt based on performance metrics. It coordinates various modules, including:

-   **Prompt Enhancer**: Improves the prompt based on a set of rules or with the help of another LLM.
-   **Deployment Orchestrator**: Deploys the prompt to a target AI (e.g., Gemini, OpenAI) and collects its output.
-   **Evaluation Engine**: Assesses the quality of the AI's output against defined metrics.
-   **Learning & Refinement Module**: Analyzes evaluation results to suggest the next iteration of the prompt.
-   **Knowledge Base**: Persists all data, including prompts, outputs, and evaluation scores, for analysis and reporting.

## Configuration

The agent's behavior is controlled via a YAML configuration file, typically located at `mpla_project/mpla/config/config.yaml`. This file allows you to specify which providers to use for each component (e.g., `gemini` vs. `openai` for the orchestrator, or `rule_based` vs. `llm_assisted` for the enhancer).

## Secure API Key Management

For the system to interact with external AI services like Google Gemini or OpenAI, you must provide the necessary API keys. **Do not hardcode API keys in the configuration file.**

The recommended approach is to set them as environment variables in your deployment environment. The application is configured to load the following variables:

-   `GOOGLE_API_KEY`: For using the Google Gemini models.
-   `OPENAI_API_KEY`: For using OpenAI models.

### Example (Linux/macOS)

```bash
export GOOGLE_API_KEY="your-google-api-key"
export OPENAI_API_KEY="your-openai-api-key"
python -m mpla.cli refine "My initial prompt"
```

### Example (Windows PowerShell)

```powershell
$env:GOOGLE_API_KEY="your-google-api-key"
$env:OPENAI_API_KEY="your-openai-api-key"
python -m mpla.cli refine "My initial prompt"
```

For development, you can create a `.env` file in the project's root directory and the application will load the variables from there automatically.

```
# .env file
GOOGLE_API_KEY="your-google-api-key"
OPENAI_API_KEY="your-openai-api-key"
```

## Usage

The primary entry point is the command-line interface.

```bash
# Run a refinement cycle with default settings
python -m mpla.cli refine "Tell me about the biggest advancements in AI." --config-path mpla_project/mpla/config/config.yaml

# Override the max number of iterations
python -m mpla.cli refine "Another prompt" --max-iterations 5
``` 
## New Functionalities

*   **Session Summarization:** The system can now generate a `session_summary.json` file, providing a structured overview of the tasks performed, their completion status, and any outstanding issues from a given work session. This aids in project tracking and handoffs.
*   **Prompt History:** The initial, role-defining prompt is now automatically saved in the `Prompt_History/` directory, providing a clear audit trail of the agent's core directives for each project version.

## System Usage Guide

This guide provides instructions on how to use the MPLA system.

### 1. Running the Web Application

The primary way to use the MPLA is through its web interface.

1.  **Start the Backend Server:**
    ```bash
    cd server
    uvicorn app.main:app --reload
    ```
2.  **Start the Frontend Application:**
    In a new terminal:
    ```bash
    cd webapp
    npm run dev
    ```
3.  **Use the Interface:**
    *   Open your web browser to the local address provided by the frontend server (usually `http://localhost:5173`).
    *   Enter a prompt you wish to refine in the main text area.
    *   Adjust settings like iterations, temperature, and AI providers in the Settings panel.
    *   If using the 'Architect' enhancer, you can enable the "Self-Correction" feature for more advanced refinement.
    *   Click "Run Refinement" to see the results stream in real-time.

### 2. Generating a Session Summary

To create a snapshot of the work done in a session:

1.  This feature is currently triggered by the agent at the end of a major project phase.
2.  Execute the finalization script when prompted.
3.  A summary will be created at `Ai_Agents/session_summary.json`.

    *Example `session_summary.json`:*
    ```json
    {
        "session_id": "20231027_103000",
        "tasks": [
            {
                "description": "Implement a self-correction feedback loop.",
                "status": "complete",
                "notes": "Designed and integrated an OutputAnalyzer and a PromptReviser..."
            }
        ],
        "unresolved_issues": [...]
    }
    ```

### 3. Accessing Prompt History

*   The core prompt that defines the agent's mission for this version of the project is stored in `Prompt_History/initial_prompt.txt`. This file is created automatically during the project finalization step.

## Future Improvements

*   Enhanced Evaluation Metrics
*   Proactive Error Recovery in Self-Correction
*   Full-Fledged Knowledge Base UI
*   Configuration Management UI
*   Refined UI for Self-Correction Log
