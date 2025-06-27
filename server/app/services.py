import asyncio
import json
import os
import sys
from typing import AsyncGenerator, Dict, Any
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# MPLA imports
from mpla.utils.logging import setup_logging, logger
from mpla.config.loader import load_config
from mpla.agent.mpla_agent import MPLAgent
from mpla.knowledge_base.sqlite_kb import SQLiteKnowledgeBase
from mpla.external.google_gemini_orchestrator import GoogleGeminiOrchestrator
from mpla.enhancers.architect_enhancer import ArchitectPromptEnhancer
from mpla.core.factory import create_evaluation_engine
from mpla.core.learning_refinement import RuleBasedLearningRefinementModule
from mpla.reporting.database_reporting import DatabaseReportingModule
from mpla.core.system_diagnoser import SystemDiagnoser
from mpla.knowledge_base.schemas import MetaPrompt, MetaPromptUpdate

setup_logging()

# --- Service Setup ---
# This setup should be more robust in a production environment (e.g., using dependency injection)
# For now, we instantiate the components directly.

# Knowledge Base
DATABASE_URL = "mpla_v2.db"
kb = SQLiteKnowledgeBase(db_path=DATABASE_URL)

# Load the main application configuration using an absolute path
config_path = os.path.join(project_root, "mpla_project", "mpla", "config", "config.yaml")
try:
    config = load_config(config_path)
except FileNotFoundError:
    logger.error(f"FATAL: Could not find config.yaml at the expected path: {config_path}")
    # In a real app, you might have a default fallback config or a more graceful shutdown.
    config = None 

# --- Meta-Prompt Service Functions ---

async def get_all_meta_prompts() -> list[MetaPrompt]:
    """Service function to retrieve all meta-prompts."""
    await kb.connect()
    prompts = await kb.get_all(MetaPrompt)
    await kb.disconnect()
    return prompts

async def get_meta_prompt_by_name(name: str) -> MetaPrompt:
    """Service function to retrieve a specific meta-prompt by name."""
    await kb.connect()
    prompt = await kb.get_meta_prompt_by_name(name)
    await kb.disconnect()
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Meta-prompt '{name}' not found.")
    return prompt

async def update_meta_prompt(name: str, payload: MetaPromptUpdate) -> MetaPrompt:
    """Service function to update a meta-prompt."""
    await kb.connect()
    updated_prompt = await kb.update_meta_prompt(name, payload)
    await kb.disconnect()
    if not updated_prompt:
        raise HTTPException(status_code=404, detail=f"Meta-prompt '{name}' not found or update failed.")
    return updated_prompt

async def run_mpla_refinement(
    initial_prompt: str,
    settings: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """
    Sets up the MPLA agent dynamically and runs the streaming refinement cycle.
    """
    agent = None
    if not config:
        yield json.dumps({
            "event": "error", 
            "data": {"message": "Server configuration is missing. Cannot start refinement."}
        })
        return
        
    try:
        # --- Dynamic Component Instantiation ---
        
        # 1. Orchestrator
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        orchestrator = GoogleGeminiOrchestrator(api_key=api_key)

        # 2. Evaluation Engine (using the factory)
        evaluation_engine = create_evaluation_engine(settings, orchestrator)
        
        # 3. Prompt Enhancer
        enhancer = ArchitectPromptEnhancer(
            orchestrator=orchestrator,
            kb=kb
        )

        # 4. System Diagnoser (NEW)
        system_diagnoser = SystemDiagnoser(orchestrator=orchestrator)

        # --- Agent Initialization ---
        logger.info(f"Initializing agent with enhancer='Architect', evaluation='{settings.get('evaluation_mode', 'basic')}'")
        agent = MPLAgent(
            knowledge_base=kb,
            prompt_enhancer=enhancer,
            deployment_orchestrator=orchestrator,
            evaluation_engine=evaluation_engine,
            learning_refinement_module=RuleBasedLearningRefinementModule(),
            reporting_module=DatabaseReportingModule(kb=kb),
            system_diagnoser=system_diagnoser,
            self_correction_config=config.agent.self_correction
        )

        target_ai_profile_data = {
            "name": "gemini-1.5-flash",
            "capabilities": {
                "temperature": settings.get("model_temperature", 0.7),
                "architect_temperature": settings.get("architect_temperature", 0.2)
            }
        }
        
        # This structure for metrics will need to adapt for the LLM evaluator
        initial_performance_metrics = {
            # For LLM
            "user_objective": initial_prompt,
            "quality_dimensions": ["clarity", "relevance", "completeness", "adherence_to_constraints"],
            # For Basic
            "target_satisfaction": 4.0,
            "rules": {
                "length": {"min": 20, "max": 2000, "weight": 0.2},
                "keywords": {"absent": ["sorry", "unable", "cannot"], "weight": 0.3},
            }
        }
        
        yield {"event": "message", "data": "Agent initialized. Starting refinement..."}

        async for iteration_result in agent.stream_refinement_cycle(
            original_prompt_text=initial_prompt,
            target_ai_profile_data=target_ai_profile_data,
            initial_performance_metrics=initial_performance_metrics,
            max_iterations=settings.get("max_iterations", 3),
            user_id="web_user",
            self_correction_enabled_by_user=settings.get("enable_self_correction", False),
            self_correction_iterations_by_user=settings.get("self_correction_iterations", 3),
        ):
            yield iteration_result

    except Exception as e:
        logger.critical(f"An unexpected error occurred during agent setup or execution: {e}", exc_info=True)
        error_payload = {
            "event": "error", 
            "data": {
                "message": f"Failed to run refinement: {e}"
            }
        }
        yield error_payload
    finally:
        # This block will run whether there was an error or not.
        final_payload = {"event": "complete", "data": "Stream finished."}
        yield final_payload
        
        if agent and agent.kb._conn is not None:
            await agent.kb.disconnect()
            logger.info("Database connection closed.")
        if agent and agent.deployment_orchestrator:
            await agent.deployment_orchestrator.close()
            logger.info("Deployment orchestrator resources released.") 