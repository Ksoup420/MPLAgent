import asyncio
import typer
from typing_extensions import Annotated
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any
import sys
from rich.console import Console
from rich.table import Table

# Configuration
from mpla.config.loader import load_config, Config
from mpla.utils.logging import setup_logging, logger

# Agent and Components
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
from mpla.core.reporting import ReportingModule
from mpla.knowledge_base.schemas import IterationLog, MetaPrompt
from mpla.core.exceptions import ConfigurationError, MPLAError
from mpla.enhancers.architect_enhancer import ArchitectPromptEnhancer

# Load .env file for development
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv_path = os.path.join(project_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)

app = typer.Typer(
    name="mpla-cli",
    help="Meta-Prompt Learning Agent CLI - Enhance your prompts iteratively!",
    add_completion=False
)
metaprompt_app = typer.Typer(name="metaprompt", help="Manage the agent's meta-prompts.")
app.add_typer(metaprompt_app, name="metaprompt")

def get_default_config_path() -> str:
    """Determines the default config path, making it portable for PyInstaller."""
    # If the app is frozen (packaged by PyInstaller), the base path is the directory of the executable
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    # Otherwise, it's the project's mpla/config directory
    else:
        base_path = os.path.join(os.path.dirname(__file__), 'config')
    
    return os.path.join(base_path, 'config.yaml')

def build_agent_from_config(config: Config) -> MPLAgent:
    """Builds and returns an MPLAgent based on the provided configuration."""
    
    # Knowledge Base
    if config.agent.knowledge_base.provider == 'sqlite':
        kb = SQLiteKnowledgeBase(db_path=config.agent.knowledge_base.db_path)
    else:
        raise ValueError(f"Unsupported knowledge_base provider: {config.agent.knowledge_base.provider}")

    # Deployment Orchestrator
    orchestrator_config = config.agent.deployment_orchestrator
    if orchestrator_config.provider == 'openai':
        deployment_orchestrator = OpenAIDeploymentOrchestrator(api_key=config.api_keys.openai_api_key)
    elif orchestrator_config.provider == 'gemini':
        deployment_orchestrator = GoogleGeminiDeploymentOrchestrator(api_key=config.api_keys.google_api_key)
    else:
        raise ConfigurationError(f"Unsupported or missing deployment_orchestrator provider: {orchestrator_config.provider}")

    # Prompt Enhancer
    if config.agent.prompt_enhancer.provider == 'rule_based':
        prompt_enhancer = RuleBasedPromptEnhancer()
    elif config.agent.prompt_enhancer.provider == 'llm_assisted':
        # This assumes the main orchestrator is what the enhancer should use.
        # This could be made more flexible in the future.
        if not isinstance(deployment_orchestrator, (GoogleGeminiDeploymentOrchestrator, OpenAIDeploymentOrchestrator)):
            raise ConfigurationError("LLM-assisted enhancer requires a real LLM orchestrator (Gemini or OpenAI).")
        prompt_enhancer = LLMAssistedPromptEnhancer(orchestrator=deployment_orchestrator)
    elif config.agent.prompt_enhancer.provider == 'architect':
        if not isinstance(deployment_orchestrator, (GoogleGeminiDeploymentOrchestrator, OpenAIDeploymentOrchestrator)):
            raise ConfigurationError("Architect enhancer requires a real LLM orchestrator (Gemini or OpenAI).")
        prompt_enhancer = ArchitectPromptEnhancer(orchestrator=deployment_orchestrator, kb=kb)
    else:
        raise ConfigurationError(f"Unsupported prompt_enhancer provider: {config.agent.prompt_enhancer.provider}")

    # Evaluation Engine (assuming basic for now, can be extended)
    evaluation_engine = BasicEvaluationEngine()

    # Learning and Refinement Module
    if config.agent.learning_refinement_module.provider == 'rule_based':
        learning_refinement_module = RuleBasedLearningRefinementModule()
    elif config.agent.learning_refinement_module.provider == 'llm_assisted':
        if not isinstance(deployment_orchestrator, (GoogleGeminiDeploymentOrchestrator, OpenAIDeploymentOrchestrator)):
            raise ConfigurationError("LLM-assisted learning module requires a real LLM orchestrator (Gemini or OpenAI).")
        learning_refinement_module = LLMAssistedLearningRefinementModule(orchestrator=deployment_orchestrator)
    else:
        raise ConfigurationError(f"Unsupported learning_refinement_module provider: {config.agent.learning_refinement_module.provider}")

    # Reporting Module
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
    )

@app.command()
def refine(
    original_prompt: Annotated[str, typer.Argument(help="The initial prompt text to refine.")],
    config_path: Annotated[str, typer.Option(help="Path to the YAML configuration file.")] = get_default_config_path(),
    target_ai_name: Annotated[str, typer.Option(help="Name of the target AI model (e.g., 'gemini-1.5-flash').", rich_help_panel="Overrides")] = "gemini-1.5-flash",
    max_iterations: Annotated[int, typer.Option(help="Maximum number of refinement iterations.", rich_help_panel="Overrides")] = 3,
    user_id: Annotated[str, typer.Option(help="Optional user ID for tracking.", rich_help_panel="Overrides")] = "cli_user",
    metrics_config_json: Annotated[str, typer.Option(help='JSON string defining evaluation metrics. Overrides default metrics.', rich_help_panel="Overrides")] = ''
):
    """Refines a given prompt using the MPLAgent's iterative process, driven by a configuration file."""
    # Setup logging first
    setup_logging()

    logger.info(f"Loading configuration from: {config_path}")
    try:
        config = load_config(config_path)
        logger.info("Configuration loaded successfully.")
        logger.info(f"Using orchestrator: {config.agent.deployment_orchestrator.provider}")
    except FileNotFoundError:
        logger.critical(f"Configuration file not found at: {config_path}", exc_info=True)
        raise typer.Exit(code=1)
    except Exception as e:
        logger.critical(f"Error loading configuration: {e}", exc_info=True)
        raise ConfigurationError(f"Failed to load or parse configuration: {e}")

    typer.echo(f"Starting MPLA refinement for: " + typer.style(f'"{original_prompt[:50]}..."', bold=True))
    
    # 1. Instantiate agent and its components from config
    agent = build_agent_from_config(config)
    
    # 2. Prepare data for the refinement cycle
    target_ai_profile_data = {"name": target_ai_name, "capabilities": ["text-generation"]}
    
    # Allow overriding metrics via CLI
    initial_performance_metrics = {}
    if metrics_config_json:
        try:
            initial_performance_metrics = json.loads(metrics_config_json)
            logger.debug(f"Using custom evaluation metrics from CLI: {json.dumps(initial_performance_metrics, indent=2)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in --metrics-config-json: {e}")
            typer.echo(typer.style(f"Error: Invalid JSON in --metrics-config-json: {e}", fg=typer.colors.RED, bold=True))
            typer.echo("Proceeding with default metrics.")
            initial_performance_metrics = {}

    # Define default metrics if not provided
    if not initial_performance_metrics:
        initial_performance_metrics = {
            "target_satisfaction": 4.0,
            "rules": {
                "length": {"min": 20, "max": 1000, "weight": 0.3, "target_score": 5.0},
                "keywords": {"present": [], "absent": ["sorry", "unable to", "cannot"], "weight": 0.4, "target_score": 5.0, "case_sensitive": False},
            }
        }
        logger.info(f"Using default evaluation metrics.")

    async def main_async():
        try:
            final_report = await agent.run_refinement_cycle(
                original_prompt_text=original_prompt,
                target_ai_profile_data=target_ai_profile_data,
                initial_performance_metrics=initial_performance_metrics,
                max_iterations=max_iterations,
                user_id=user_id
            )
            typer.echo("\n" + typer.style("--- MPLA Refinement Complete ---", fg=typer.colors.GREEN, bold=True))
            typer.echo(typer.style("Final Report:", bold=True))
            # Use default=str to handle non-serializable types like datetime
            typer.echo(json.dumps(final_report, indent=2, default=str))

        except MPLAError as e:
            logger.critical(f"An MPLA-specific error occurred: {e}", exc_info=True)
            typer.echo(typer.style(f"\nA critical agent error occurred: {type(e).__name__} - {e}", fg=typer.colors.RED, bold=True), err=True)
            typer.echo(typer.style("This indicates a problem within the agent's core components. See logs for details.", dim=True), err=True)
        except Exception as e:
            logger.critical(f"An unexpected error occurred during the refinement cycle: {e}", exc_info=True)
            typer.echo(typer.style(f"\nAn unexpected error occurred: {type(e).__name__} - {e}", fg=typer.colors.RED, bold=True), err=True)
        finally:
            if agent.kb and getattr(agent.kb, '_conn', None):
                await agent.kb.disconnect()
            if hasattr(agent.deployment_orchestrator, 'close'):
                await agent.deployment_orchestrator.close()

    asyncio.run(main_async())

@metaprompt_app.command("list")
def list_metaprompts(
    config_path: Annotated[str, typer.Option(help="Path to the YAML configuration file.")] = get_default_config_path(),
):
    """Lists all available meta-prompts in the database."""
    setup_logging() # Keep output clean
    
    try:
        config = load_config(config_path)
        kb = SQLiteKnowledgeBase(db_path=config.agent.knowledge_base.db_path)
    except Exception as e:
        typer.echo(typer.style(f"Error loading configuration or connecting to DB: {e}", fg=typer.colors.RED, bold=True))
        raise typer.Exit(code=1)

    async def main_async():
        await kb.connect()
        try:
            # We need a generic "get_all" method in the KB
            meta_prompts = await kb.get_all(MetaPrompt)
            if not meta_prompts:
                typer.echo("No meta-prompts found in the database.")
                return

            table = Table(title="Available Meta-Prompts")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Is Active", justify="center")
            table.add_column("Created At", style="green")

            for mp in meta_prompts:
                active_str = "✅" if mp.is_active else "❌"
                table.add_row(str(mp.id), mp.name, active_str, str(mp.created_at))
            
            console = Console()
            console.print(table)

        finally:
            if kb._conn:
                await kb.disconnect()

    asyncio.run(main_async())

@app.command()
def show_schema(
    model_name: Annotated[str, typer.Argument(help="Name of the Pydantic model to show schema for (e.g., OriginalPrompt).")]
):
    """Displays the JSON schema for a given Pydantic model in knowledge_base.schemas."""
    try:
        from mpla.knowledge_base import schemas as mpla_schemas
        model_cls = getattr(mpla_schemas, model_name, None)
        if model_cls and hasattr(model_cls, 'model_json_schema'): #Pydantic v2
            typer.echo(typer.style(f"JSON Schema for {model_name}:", bold=True))
            typer.echo(json.dumps(model_cls.model_json_schema(), indent=2))
        elif model_cls and hasattr(model_cls, 'schema_json'): #Pydantic v1
            typer.echo(typer.style(f"JSON Schema for {model_name} (Pydantic v1 format):", bold=True))
            typer.echo(model_cls.schema_json(indent=2))
        else:
            typer.echo(typer.style(f"Error: Model '{model_name}' not found or has no schema method.", fg=typer.colors.RED))
            available_models = [m for m in dir(mpla_schemas) if not m.startswith('__') and isinstance(getattr(mpla_schemas, m), type) and hasattr(getattr(mpla_schemas, m), 'model_fields')]
            typer.echo(f"Available models might include: {available_models}")
    except ImportError:
        typer.echo(typer.style("Error: Could not import schemas.", fg=typer.colors.RED))
    except Exception as e:
        typer.echo(typer.style(f"An error occurred: {e}", fg=typer.colors.RED))

if __name__ == "__main__":
    app() 