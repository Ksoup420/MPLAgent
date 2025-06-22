from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship, JSON, Column

class BaseMPLAModel(SQLModel):
    """Base model for all MPLA data entities, providing common fields."""
    id: Optional[int] = Field(default=None, primary_key=True, description="Unique identifier, typically database-generated.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False, description="Timestamp of creation.")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False, sa_column_kwargs={"onupdate": datetime.now}, description="Timestamp of last update.")

    class Config:
        orm_mode = True # Allows easy mapping from SQLAlchemy models if used later
        validate_assignment = True # Re-validate on attribute assignment

class MetaPrompt(BaseMPLAModel, table=True):
    """Stores meta-prompts used by the LLM-assisted enhancer."""
    name: str = Field(unique=True, description="A unique, human-readable name for the meta-prompt.")
    template: str = Field(description="The template text of the meta-prompt.")
    description: Optional[str] = Field(default=None, description="Detailed description of the meta-prompt.")
    version: int = Field(default=1, description="Version number of the meta-prompt.")
    is_active: bool = Field(default=True, description="Indicates if this is the currently active meta-prompt for its role.")

class OriginalPrompt(BaseMPLAModel, table=True):
    """Represents the initial prompt provided by the user."""
    text: str = Field(..., description="The raw text of the original prompt.")
    user_id: Optional[str] = Field(default=None, index=True, description="Identifier for the user who submitted the prompt.")

    prompt_versions: List["PromptVersion"] = Relationship(back_populates="original_prompt")
    iteration_logs: List["IterationLog"] = Relationship(back_populates="original_prompt")

class TargetAIProfile(BaseMPLAModel, table=True):
    """Defines the profile of the target AI system for which a prompt is being optimized."""
    name: str = Field(index=True, description="Descriptive name of the AI system (e.g., 'GPT-4 Turbo').")
    api_endpoint: Optional[str] = Field(default=None, description="API endpoint for the AI system.")
    capabilities: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict, description="List of known capabilities (e.g., 'text-generation').")
    # Potentially add fields for API keys (managed securely), rate limits, specific model names/versions

    # Relationships
    ai_outputs: List["AIOutput"] = Relationship(back_populates="target_ai_profile")

class PromptVersion(BaseMPLAModel, table=True):
    """Represents a specific version of a prompt during the refinement lifecycle."""
    original_prompt_id: int = Field(foreign_key="originalprompt.id", description="Foreign key to the OriginalPrompt.")
    iteration_id: Optional[int] = Field(default=None, description="Foreign key to an IterationLog, linking it to a specific cycle.")
    version_number: int = Field(..., description="Sequential version number of this prompt.")
    prompt_text: str = Field(..., description="The actual text of this prompt version.")
    enhancement_rationale: Optional[str] = Field(default=None, description="Explanation of how this version was improved over the previous one.")
    target_ai_profile_id: Optional[int] = Field(default=None, description="Foreign key to the TargetAIProfile used for this version.")

    original_prompt: OriginalPrompt = Relationship(back_populates="prompt_versions")
    ai_outputs: List["AIOutput"] = Relationship(back_populates="prompt_version")
    iteration_logs: List["IterationLog"] = Relationship(back_populates="active_prompt_version")

class AIOutput(BaseMPLAModel, table=True):
    """Stores the output received from a target AI system for a given PromptVersion."""
    prompt_version_id: int = Field(foreign_key="promptversion.id", description="Foreign key to the PromptVersion that generated this output.")
    raw_output_data: Union[str, Dict[str, Any], List[Any]] = Field(sa_column=Column(JSON), description="The raw output from the AI (text, JSON, etc.).")
    target_ai_profile_id: int = Field(foreign_key="targetaiprofile.id", description="Foreign key to the TargetAIProfile used for this output.")
    # error_message: Optional[str] = Field(default=None, description="Any error message if the AI call failed.")

    prompt_version: PromptVersion = Relationship(back_populates="ai_outputs")
    target_ai_profile: TargetAIProfile = Relationship(back_populates="ai_outputs")
    evaluation_result: Optional["EvaluationResult"] = Relationship(back_populates="ai_output")

class PerformanceMetricDefinition(BaseMPLAModel):
    """Defines a type of metric used for evaluating AI outputs."""
    name: str = Field(..., description="Name of the performance metric (e.g., 'Clarity Score').")
    description: Optional[str] = Field(default=None, description="Detailed description of the metric.")
    metric_type: str = Field(..., description="Type of metric (e.g., 'automated_nlp', 'user_rating', 'code_linter').")
    # config: Optional[Dict[str, Any]] = Field(default=None, description="Configuration for the metric (e.g., keywords).")

class EvaluationResult(BaseMPLAModel, table=True):
    """Stores the evaluation results for a specific AIOutput."""
    ai_output_id: int = Field(foreign_key="aioutput.id")
    metric_scores: Dict[str, Any] = Field(sa_column=Column(JSON))
    target_metrics_snapshot: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    qualitative_feedback: Optional[str] = Field(default=None)
    user_rating: Optional[int] = Field(default=None, ge=1, le=5)
    overall_score: Optional[float] = None
    notes: Optional[str] = None

    ai_output: AIOutput = Relationship(back_populates="evaluation_result")
    iteration_logs: List["IterationLog"] = Relationship(back_populates="evaluation_result")

class IterationLog(BaseMPLAModel, table=True):
    """Logs a single iteration within a prompt refinement session."""
    original_prompt_id: int = Field(foreign_key="originalprompt.id", description="Foreign key to the OriginalPrompt that started this session.")
    session_id: str = Field(..., description="Unique identifier for the entire refinement session.")
    iteration_number: int = Field(..., description="The sequence number of this iteration within the session.")
    active_prompt_version_id: int = Field(foreign_key="promptversion.id", description="Foreign key to the PromptVersion used in this iteration.")
    ai_output_id: int = Field(foreign_key="aioutput.id", description="Foreign key to the AIOutput from this iteration.")
    evaluation_result_id: int = Field(foreign_key="evaluationresult.id", description="Foreign key to the EvaluationResult for this iteration.")
    status: str = Field(default="pending", description="Current status of the iteration (e.g., 'pending', 'evaluated').")

    original_prompt: OriginalPrompt = Relationship(back_populates="iteration_logs")
    active_prompt_version: PromptVersion = Relationship(back_populates="iteration_logs")
    ai_output: AIOutput = Relationship()
    evaluation_result: EvaluationResult = Relationship(back_populates="iteration_logs")

# Add other schemas like RefinementLog, LearnedStrategy as needed based on the full plan.

# Example usage (not part of the file, just for illustration)
if __name__ == "__main__":
    original_prompt = OriginalPrompt(text="Describe quantum computing.", user_id="user123")
    print(original_prompt.model_dump_json(indent=2))

    prompt_v1 = PromptVersion(
        original_prompt_id=original_prompt.id, # Assuming ID is set after DB save
        iteration_id=1,
        version_number=1,
        prompt_text="Explain quantum computing in simple terms for a beginner.",
        enhancement_rationale="Added target audience and simplicity constraint."
    )
    print(prompt_v1.model_dump_json(indent=2))

# Resolve forward references after all models are defined
AIOutput.model_rebuild()
EvaluationResult.model_rebuild()
IterationLog.model_rebuild()
OriginalPrompt.model_rebuild()
PromptVersion.model_rebuild()
TargetAIProfile.model_rebuild()
MetaPrompt.model_rebuild() 