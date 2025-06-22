"""
Centralized Mock Components for Testing

This module contains mock implementations of the core abstract classes
(e.g., DeploymentOrchestrator, KnowledgeBase) for use in unit and
integration tests. This prevents test code from cluttering production modules.
"""

from typing import Any, Dict, Optional, List

# Core abstractions to be mocked
from mpla.core.deployment_orchestrator import DeploymentOrchestrator
from mpla.core.evaluation_engine import EvaluationEngine
from mpla.core.learning_refinement import LearningRefinementModule
from mpla.core.prompt_enhancer import BasePromptEnhancer
from mpla.core.reporting import ReportingModule
from mpla.knowledge_base.db_connector import KnowledgeBase
from mpla.knowledge_base.schemas import (
    AIOutput,
    BaseMPLAModel,
    EvaluationResult,
    IterationLog,
    PromptVersion,
    TargetAIProfile,
)

# --- Mock Implementations ---

class MockPromptEnhancer(BasePromptEnhancer):
    async def enhance(self, original_prompt_text: str, ai_profile: Optional[TargetAIProfile] = None) -> tuple[str, str]:
        return f"Enhanced: {original_prompt_text}", "Applied basic mock enhancement rule."

class MockDeploymentOrchestrator(DeploymentOrchestrator):
    async def deploy_and_collect(self, prompt_version: PromptVersion, ai_profile: TargetAIProfile) -> Optional[AIOutput]:
        return AIOutput(
            prompt_version_id=prompt_version.id if prompt_version.id else 0,
            raw_output_data=f"Mock output for: {prompt_version.prompt_text}"
        )

class MockEvaluationEngine(EvaluationEngine):
    async def evaluate(self, output: AIOutput, metrics: Dict[str, Any]) -> Optional[EvaluationResult]:
        # score = len(str(output.raw_output_data)) % 5 + 1 # Avoid 0 score
        return EvaluationResult(
            ai_output_id=output.id if output.id else 0,
            metric_scores={"clarity": 3, "overall_satisfaction": 3}
        )

class MockLearningRefinementModule(LearningRefinementModule):
    async def learn_and_refine(self, current_prompt: PromptVersion, eval_result: EvaluationResult) -> Optional[PromptVersion]:
        satisfaction = eval_result.metric_scores.get("overall_satisfaction", 0)
        if satisfaction < 4.5:
            return PromptVersion(
                original_prompt_id=current_prompt.original_prompt_id,
                version_number=current_prompt.version_number + 1,
                prompt_text=f"Refined v{current_prompt.version_number + 1} from score {satisfaction}",
                enhancement_rationale=f"Attempting to improve score from {satisfaction}",
                target_ai_profile_id=current_prompt.target_ai_profile_id
            )
        return None

class MockReportingModule(ReportingModule):
    def __init__(self, kb: Optional[KnowledgeBase] = None):
        self.kb = kb
        self.iterations = []

    async def report_iteration(self, iteration_log: IterationLog) -> None:
        self.iterations.append(iteration_log)

    async def generate_final_report(self, session_id: str) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "final_prompt": "Final mock prompt",
            "elucidation": f"Mock report for session {session_id} with {len(self.iterations)} iterations.",
            "iterations_summary": [{"iter": it.iteration_number, "status": it.status} for it in self.iterations]
        }

class MockKnowledgeBase(KnowledgeBase):
    def __init__(self):
        self._store: Dict[str, Dict[int, Any]] = {}
        self._id_counter: int = 0

    async def connect(self):
        pass # No-op

    async def disconnect(self):
        pass # No-op

    async def add(self, record: BaseMPLAModel) -> BaseMPLAModel:
        self._id_counter += 1
        record.id = self._id_counter
        # Timestamps would be set here in a real scenario
        model_name = record.__class__.__name__
        if model_name not in self._store:
            self._store[model_name] = {}
        self._store[model_name][record.id] = record
        return record

    async def get(self, model_cls: type | str, record_id: int) -> Optional[Any]:
        model_name = model_cls if isinstance(model_cls, str) else model_cls.__name__
        return self._store.get(model_name, {}).get(record_id)

    async def get_iterations_for_session(self, session_id: str) -> List[IterationLog]:
        return [
            log for log in self._store.get("IterationLog", {}).values()
            if log.session_id == session_id
        ]

    async def get_prompt_versions_for_original(self, original_prompt_id: int) -> List[PromptVersion]:
        return [
            pv for pv in self._store.get("PromptVersion", {}).values()
            if pv.original_prompt_id == original_prompt_id
        ]

    async def get_evaluations_for_prompt_version(self, prompt_version_id: int) -> List[EvaluationResult]:
        # This is a bit more complex as EvaluationResult is linked to AIOutput,
        # which is linked to PromptVersion.
        # This simplified mock will just look for direct links if we add them.
        return []

    async def get_iteration_log(self, iteration_id: int) -> Optional[IterationLog]:
        return await self.get(IterationLog, iteration_id)

    async def update(self, record_id: int, update_data: BaseMPLAModel) -> Optional[BaseMPLAModel]:
        model_name = update_data.__class__.__name__
        if model_name in self._store and record_id in self._store[model_name]:
            # In a real DB, you wouldn't pass the full model, but for a mock, this is fine.
            self._store[model_name][record_id] = update_data
            return update_data
        return None

    # Add other required abstract methods if any, with simple mock implementations
    async def log_iteration(self, iteration_log: IterationLog) -> IterationLog:
        return await self.add(iteration_log) 