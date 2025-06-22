from pydantic import BaseModel, Field
from typing import Literal, Optional
import yaml
import os

class ApiKeys(BaseModel):
    google_api_key: Optional[str] = Field(None)
    openai_api_key: Optional[str] = Field(None)

class DeploymentOrchestratorConfig(BaseModel):
    provider: Literal['gemini', 'openai', 'mock']

class KnowledgeBaseConfig(BaseModel):
    provider: Literal['sqlite']
    db_path: str

class PromptEnhancerConfig(BaseModel):
    provider: Literal['rule_based', 'llm_assisted', 'architect']

class EvaluationEngineConfig(BaseModel):
    provider: Literal['basic']

class LearningRefinementModuleConfig(BaseModel):
    provider: Literal['rule_based', 'llm_assisted']

class ReportingModuleConfig(BaseModel):
    provider: Literal['mock', 'database']

class SelfCorrectionConfig(BaseModel):
    enabled: bool
    max_iterations: int
    analysis_temperature: float
    revision_temperature: float

class AgentConfig(BaseModel):
    deployment_orchestrator: DeploymentOrchestratorConfig
    knowledge_base: KnowledgeBaseConfig
    prompt_enhancer: PromptEnhancerConfig
    evaluation_engine: EvaluationEngineConfig
    learning_refinement_module: LearningRefinementModuleConfig
    reporting_module: ReportingModuleConfig
    self_correction: Optional[SelfCorrectionConfig] = None

class Config(BaseModel):
    agent: AgentConfig
    api_keys: ApiKeys


def load_config(path: str = "mpla/config/config.yaml") -> Config:
    with open(path, 'r') as f:
        config_data = yaml.safe_load(f)

    # Substitute environment variables
    for key, value in config_data.get('api_keys', {}).items():
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            config_data['api_keys'][key] = os.getenv(env_var)

    return Config(**config_data) 