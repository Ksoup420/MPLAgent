import asyncio
import json
import os
import sys
from typing import AsyncGenerator, Dict, Any
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException, APIRouter

# Add project root and mpla_project to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
mpla_project_path = os.path.join(project_root, 'mpla_project')

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if mpla_project_path not in sys.path:
    sys.path.insert(0, mpla_project_path)

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

router = APIRouter()

# Knowledge Base - Use absolute path to database file in project root
DATABASE_URL = os.path.join(project_root, "mpla_v2.db")

# Ensure database exists and is initialized
async def initialize_database():
    """Initialize the database if it doesn't exist."""
    try:
        if not os.path.exists(DATABASE_URL):
            logger.info(f"Database not found at {DATABASE_URL}, creating new database...")
            # Create the database file
            open(DATABASE_URL, 'a').close()
        
        # Test connection
        kb = SQLiteKnowledgeBase(db_path=DATABASE_URL)
        await kb.connect()
        logger.info(f"Database initialized successfully at {DATABASE_URL}")
        await kb.disconnect()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

# Initialize database on module load
import asyncio
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If there's already an event loop, schedule the initialization
        asyncio.create_task(initialize_database())
    else:
        # If no event loop is running, run the initialization
        asyncio.run(initialize_database())
except Exception as e:
    logger.error(f"Failed to initialize database during module load: {e}")

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
            "name": settings.get("model", "gemini-2.0-flash"),
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

@router.post("/api/prompt-testing/run")
async def run_prompt_testing(request: dict):
    """Run comprehensive prompt testing framework."""
    try:
        prompt_type = request.get("prompt_type", "architect")
        model = request.get("model", "gemini-2.0-flash")
        
        logger.info(f"Starting prompt testing for {prompt_type} prompts using {model}")
        
        # Initialize components
        kb = SQLiteKnowledgeBase(DB_PATH)
        await kb.initialize()
        
        orchestrator = GoogleGeminiOrchestrator()
        
        ai_profile = TargetAIProfile(
            name=model,
            capabilities={"temperature": 0.2}
        )
        
        # Import here to avoid circular imports
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../mpla_project"))
        
        from mpla.core.prompt_testing_framework import PromptTestingFramework
        
        testing_framework = PromptTestingFramework(
            deployment_orchestrator=orchestrator,
            knowledge_base=kb,
            prompts_directory="Prompts for MPLA agents"
        )
        
        # Run comprehensive test
        report = await testing_framework.run_comprehensive_test(
            prompt_type=prompt_type,
            ai_profile=ai_profile
        )
        
        # Convert report to dictionary for JSON response
        result = {
            "test_suite_name": report.test_suite_name,
            "summary_metrics": report.summary_metrics,
            "recommendations": report.recommendations,
            "results": [
                {
                    "test_case_id": r.test_case_id,
                    "prompt_variant_id": r.prompt_variant_id,
                    "output": r.output[:500] + "..." if len(r.output) > 500 else r.output,  # Truncate long outputs
                    "execution_time": r.execution_time,
                    "success": r.success,
                    "error_message": r.error_message,
                    "quality_scores": r.quality_scores
                }
                for r in report.results
            ],
            "timestamp": report.timestamp.isoformat()
        }
        
        # Save report to file
        await testing_framework.save_report(report)
        
        await kb.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Error running prompt testing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/prompt-variants")
async def get_prompt_variants():
    """Get available prompt variants from the prompts directory."""
    try:
        prompts_dir = "Prompts for MPLA agents"
        variants = []
        
        if os.path.exists(prompts_dir):
            for filename in os.listdir(prompts_dir):
                if filename.endswith(('.txt', '.md')):
                    file_path = os.path.join(prompts_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Determine prompt type
                        prompt_type = "architect"
                        if "analyzer" in filename.lower() or "analysis" in filename.lower():
                            prompt_type = "analyzer"
                        elif "reviser" in filename.lower() or "revision" in filename.lower():
                            prompt_type = "reviser"
                        
                        variants.append({
                            "id": f"variant_{len(variants)}",
                            "name": filename.replace('.txt', '').replace('.md', ''),
                            "description": f"Prompt variant from {filename}",
                            "prompt_type": prompt_type,
                            "source_file": filename,
                            "content_preview": content[:200] + "..." if len(content) > 200 else content
                        })
                    except Exception as e:
                        logger.warning(f"Failed to read prompt file {filename}: {e}")
        
        return {"variants": variants}
        
    except Exception as e:
        logger.error(f"Error getting prompt variants: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/prompt-testing/analyze-prompt")
async def analyze_single_prompt(request: dict):
    """Analyze a single prompt variant for quality and characteristics."""
    try:
        prompt_content = request.get("prompt_content", "")
        prompt_type = request.get("prompt_type", "architect")
        
        if not prompt_content:
            raise HTTPException(status_code=400, detail="Prompt content is required")
        
        # Simple analysis for now - can be enhanced with NLP
        analysis = {
            "length": len(prompt_content),
            "word_count": len(prompt_content.split()),
            "has_structure": bool(any(marker in prompt_content for marker in ['**', '#', '1.', '2.', '-'])),
            "has_examples": "example" in prompt_content.lower(),
            "has_role_definition": any(role in prompt_content.lower() for role in ["you are", "role:", "as a"]),
            "has_output_format": any(fmt in prompt_content.lower() for fmt in ["output:", "format:", "structure:"]),
            "complexity_score": min(len(prompt_content.split()) / 100, 1.0),  # Simple complexity metric
            "estimated_quality": 0.5  # Placeholder - would use ML model in production
        }
        
        # Generate suggestions
        suggestions = []
        if not analysis["has_role_definition"]:
            suggestions.append("Consider adding a clear role definition (e.g., 'You are an expert...')")
        if not analysis["has_structure"]:
            suggestions.append("Add structural elements like headings or numbered steps")
        if not analysis["has_output_format"]:
            suggestions.append("Specify the desired output format explicitly")
        if analysis["word_count"] < 50:
            suggestions.append("Prompt may be too brief - consider adding more context")
        if analysis["word_count"] > 500:
            suggestions.append("Prompt may be too verbose - consider condensing key points")
        
        return {
            "analysis": analysis,
            "suggestions": suggestions,
            "prompt_type": prompt_type
        }
        
    except Exception as e:
        logger.error(f"Error analyzing prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 