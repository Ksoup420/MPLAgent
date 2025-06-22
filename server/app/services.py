import asyncio
import json
import os
import sys
from typing import AsyncGenerator, Dict, Any, Optional
from fastapi import HTTPException

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# MPLA imports
from mpla.utils.logging import setup_logging, logger
from mpla.config.loader import load_config, Config
from mpla.agent.mpla_agent import MPLAgent
from mpla.knowledge_base.sqlite_kb import SQLiteKnowledgeBase
from mpla.core.prompt_enhancer import RuleBasedPromptEnhancer
from mpla.core.llm_assisted_prompt_enhancer import LLMAssistedPromptEnhancer
from mpla.external.openai_orchestrator import OpenAIDeploymentOrchestrator
from mpla.external.google_gemini_orchestrator import GoogleGeminiDeploymentOrchestrator
from mpla.core.evaluation_engine import BasicEvaluationEngine
from mpla.core.learning_refinement import RuleBasedLearningRefinementModule
from mpla.core.llm_assisted_learning_refinement import LLMAssistedLearningRefinementModule
from mpla.reporting.database_reporting import DatabaseReportingModule
from mpla.core.exceptions import ConfigurationError, MPLAError
from mpla.enhancers.architect_enhancer import ArchitectPromptEnhancer
from mpla.knowledge_base.schemas import TargetAIProfile, IterationLog, PromptVersion

setup_logging()

# The stream_refinement_cycle is now a native method of MPLAgent,
# so the monkey-patched version is no longer needed here.

# --- Functions moved from CLI ---
def get_default_config_path() -> str:
    """Determines the default config path, making it portable for PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        # Adjusted path for server context
        base_path = os.path.join(project_root, 'mpla_project', 'mpla', 'config')
    return os.path.join(base_path, 'config.yaml')

def build_agent_from_config(config: Config) -> MPLAgent:
    """Builds and returns an MPLAgent based on the provided configuration."""
    if config.agent.knowledge_base.provider == 'sqlite':
        kb = SQLiteKnowledgeBase(db_path=config.agent.knowledge_base.db_path)
    else:
        raise ValueError(f"Unsupported knowledge_base provider: {config.agent.knowledge_base.provider}")

    orchestrator_config = config.agent.deployment_orchestrator
    if orchestrator_config.provider == 'openai':
        deployment_orchestrator = OpenAIDeploymentOrchestrator(api_key=config.api_keys.openai_api_key)
    elif orchestrator_config.provider == 'gemini':
        deployment_orchestrator = GoogleGeminiDeploymentOrchestrator(api_key=config.api_keys.google_api_key)
    else:
        raise ConfigurationError(f"Unsupported or missing deployment_orchestrator provider: {orchestrator_config.provider}")

    if config.agent.prompt_enhancer.provider == 'rule_based':
        prompt_enhancer = RuleBasedPromptEnhancer()
    elif config.agent.prompt_enhancer.provider == 'llm_assisted':
        if not isinstance(deployment_orchestrator, (GoogleGeminiDeploymentOrchestrator, OpenAIDeploymentOrchestrator)):
            raise ConfigurationError("LLM-assisted enhancer requires a real LLM orchestrator (Gemini or OpenAI).")
        prompt_enhancer = LLMAssistedPromptEnhancer(orchestrator=deployment_orchestrator)
    elif config.agent.prompt_enhancer.provider == 'architect':
        if not isinstance(deployment_orchestrator, (GoogleGeminiDeploymentOrchestrator, OpenAIDeploymentOrchestrator)):
            raise ConfigurationError("Architect enhancer requires a real LLM orchestrator (Gemini or OpenAI).")
        prompt_enhancer = ArchitectPromptEnhancer(orchestrator=deployment_orchestrator, kb=kb)
    else:
        raise ConfigurationError(f"Unsupported prompt_enhancer provider: {config.agent.prompt_enhancer.provider}")

    evaluation_engine = BasicEvaluationEngine()

    if config.agent.learning_refinement_module.provider == 'rule_based':
        learning_refinement_module = RuleBasedLearningRefinementModule()
    elif config.agent.learning_refinement_module.provider == 'llm_assisted':
        if not isinstance(deployment_orchestrator, (GoogleGeminiDeploymentOrchestrator, OpenAIDeploymentOrchestrator)):
            raise ConfigurationError("LLM-assisted learning module requires a real LLM orchestrator (Gemini or OpenAI).")
        learning_refinement_module = LLMAssistedLearningRefinementModule(orchestrator=deployment_orchestrator)
    else:
        raise ConfigurationError(f"Unsupported learning_refinement_module provider: {config.agent.learning_refinement_module.provider}")

    if config.agent.reporting_module.provider == 'database':
        reporting_module = DatabaseReportingModule(kb=kb)
    else:
        raise ConfigurationError(f"Unsupported or missing reporting_module provider: {config.agent.reporting_module.provider}")

    return MPLAgent(
        knowledge_base=kb,
        prompt_enhancer=prompt_enhancer,
        deployment_orchestrator=deployment_orchestrator,
        evaluation_engine=evaluation_engine,
        learning_refinement_module=learning_refinement_module,
        reporting_module=reporting_module,
        self_correction_config=config.agent.self_correction,
    )

# --- Main Service Function ---
async def run_mpla_refinement(
    initial_prompt: str,
    settings: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """
    Sets up the MPLA agent from configuration and runs the streaming refinement cycle.
    """
    setup_logging()
    agent = None
    try:
        config_path = get_default_config_path()
        logger.info(f"Loading base configuration from: {config_path}")
        config = load_config(config_path)

        config.agent.deployment_orchestrator.provider = settings["providers"]["orchestrator"]
        config.agent.prompt_enhancer.provider = settings["providers"]["enhancer"]
        
        logger.info(f"Building agent with orchestrator: '{config.agent.deployment_orchestrator.provider}' and enhancer: '{config.agent.prompt_enhancer.provider}'")
        agent = build_agent_from_config(config)

        # Use the specific architect temperature if the architect enhancer is selected
        if settings["providers"]["enhancer"] == 'architect':
            temperature = settings.get("architect_temperature", 0.2)
        else:
            temperature = settings.get("model_temperature", 0.7)

        target_ai_profile_data = {
            "name": "gemini-1.5-flash",
            "capabilities": {
                "temperature": temperature
            }
        }
        
        initial_performance_metrics = {
            "target_satisfaction": 4.0,
            "rules": {
                "length": {"min": 20, "max": 1000, "weight": 0.3, "target_score": 5.0},
                "keywords": {"present": [], "absent": ["sorry", "unable to", "cannot"], "weight": 0.4, "target_score": 5.0, "case_sensitive": False},
            }
        }
        
        yield json.dumps({"event": "message", "data": "Agent initialized. Starting refinement..."})

        async for iteration_result in agent.stream_refinement_cycle(
            original_prompt_text=initial_prompt,
            target_ai_profile_data=target_ai_profile_data,
            initial_performance_metrics=initial_performance_metrics,
            max_iterations=settings.get("max_iterations", 3),
            user_id="web_user",
            self_correction_enabled_by_user=settings.get("enable_self_correction", False),
            self_correction_iterations_by_user=settings.get("self_correction_iterations", 3),
        ):
            yield json.dumps(iteration_result)

    except Exception as e:
        logger.critical(f"An unexpected error occurred during agent setup or execution: {e}", exc_info=True)
        error_payload = json.dumps({
            "event": "error", 
            "data": {
                "message": f"Failed to run refinement: {e}"
            }
        })
        yield error_payload
    finally:
        # This block will run whether there was an error or not.
        final_payload = json.dumps({"event": "complete", "data": "Stream finished."})
        yield final_payload
        
        if agent and agent.kb._conn is not None:
            await agent.kb.disconnect()
            logger.info("Database connection closed.")
        if agent and agent.deployment_orchestrator:
            await agent.deployment_orchestrator.close()
            logger.info("Deployment orchestrator resources released.") 