import pytest
from mpla.agent.mpla_agent import MPLAgent
from .mocks import (
    MockKnowledgeBase,
    MockPromptEnhancer,
    MockDeploymentOrchestrator,
    MockEvaluationEngine,
    MockLearningRefinementModule,
    MockReportingModule,
)
from mpla.knowledge_base.schemas import EvaluationResult, PromptVersion

@pytest.fixture
def mock_agent() -> MPLAgent:
    """Provides a fully mocked MPLAgent for testing."""
    kb = MockKnowledgeBase()
    # The reporting module needs a reference to the KB to build its final report
    reporting_module = MockReportingModule(kb=kb)
    agent = MPLAgent(
        knowledge_base=kb,
        prompt_enhancer=MockPromptEnhancer(),
        deployment_orchestrator=MockDeploymentOrchestrator(),
        evaluation_engine=MockEvaluationEngine(),
        learning_refinement_module=MockLearningRefinementModule(),
        reporting_module=reporting_module,
    )
    return agent

@pytest.mark.asyncio
async def test_run_refinement_cycle_successful_run(mock_agent: MPLAgent):
    """
    Tests a standard, successful run of the refinement cycle for a fixed number of iterations.
    """
    original_prompt = "Make this better."
    target_profile = {"name": "TestAI"}
    initial_metrics = {"target_satisfaction": 4.5}
    max_iterations = 3

    final_report = await mock_agent.run_refinement_cycle(
        original_prompt_text=original_prompt,
        target_ai_profile_data=target_profile,
        initial_performance_metrics=initial_metrics,
        max_iterations=max_iterations,
    )

    # Assertions
    assert final_report is not None
    assert final_report["session_id"] == mock_agent.current_session_id
    # The mock reporting module has its own logic we can test against
    assert "Mock report for session" in final_report["elucidation"]
    
    # Check that the correct number of iterations were reported
    # Note: The mock reporting module is stateful.
    assert len(mock_agent.reporting_module.iterations) == max_iterations
    
    # Verify the last prompt was refined
    last_iteration_log = mock_agent.reporting_module.iterations[-1]
    last_prompt_version = await mock_agent.kb.get(
        PromptVersion, last_iteration_log.active_prompt_version_id
    )
    assert last_prompt_version is not None
    # Based on MockLearningRefinementModule logic
    assert f"Refined v{max_iterations}" in last_prompt_version.prompt_text


@pytest.mark.asyncio
async def test_run_refinement_cycle_meets_criteria_early(mock_agent: MPLAgent):
    """
    Tests that the cycle stops early if the evaluation score meets the target.
    """
    # Override the default mock evaluation engine to return a high score
    class HighScoreEvaluationEngine(MockEvaluationEngine):
        async def evaluate(self, output, metrics):
            # Return a score that meets the target
            return EvaluationResult(
                ai_output_id=output.id or 0,
                metric_scores={"overall_satisfaction": 5.0}
            )

    mock_agent.evaluation_engine = HighScoreEvaluationEngine()

    final_report = await mock_agent.run_refinement_cycle(
        original_prompt_text="This prompt is already perfect.",
        target_ai_profile_data={"name": "TestAI"},
        initial_performance_metrics={"target_satisfaction": 4.5},
        max_iterations=5, # Should not reach this
    )

    # Assert that the loop terminated after the first iteration
    assert len(mock_agent.reporting_module.iterations) == 1
    assert "with 1 iterations" in final_report["elucidation"]


@pytest.mark.asyncio
async def test_run_refinement_cycle_handles_deployment_failure(mock_agent: MPLAgent):
    """
    Tests that the cycle stops gracefully if the orchestrator fails to return an output.
    """
    # Configure the mock orchestrator to fail
    class FailingOrchestrator(MockDeploymentOrchestrator):
        async def deploy_and_collect(self, prompt_version, ai_profile):
            return None # Simulate a failure

    mock_agent.deployment_orchestrator = FailingOrchestrator()

    await mock_agent.run_refinement_cycle(
        original_prompt_text="This will fail.",
        target_ai_profile_data={"name": "TestAI"},
        initial_performance_metrics={"target_satisfaction": 4.0},
        max_iterations=5,
    )

    # The loop should run once, fail, and stop.
    assert len(mock_agent.reporting_module.iterations) == 0 # No iteration is ever successfully reported


@pytest.mark.asyncio
async def test_run_refinement_cycle_handles_evaluation_failure(mock_agent: MPLAgent):
    """
    Tests that the cycle stops gracefully if the evaluation engine fails.
    """
    # Configure the mock evaluation engine to fail
    class FailingEvaluationEngine(MockEvaluationEngine):
        async def evaluate(self, output, metrics):
            return None # Simulate a failure

    mock_agent.evaluation_engine = FailingEvaluationEngine()

    await mock_agent.run_refinement_cycle(
        original_prompt_text="This will fail during evaluation.",
        target_ai_profile_data={"name": "TestAI"},
        initial_performance_metrics={"target_satisfaction": 4.0},
        max_iterations=5,
    )

    # The loop should run once, attempt evaluation, fail, and stop.
    # No full iteration log will be created and reported.
    assert len(mock_agent.reporting_module.iterations) == 0


@pytest.mark.asyncio
async def test_run_refinement_cycle_handles_learning_failure(mock_agent: MPLAgent):
    """
    Tests that the cycle stops if the learning module fails to produce a new prompt.
    """
    # Configure the mock learning module to fail after the first iteration
    class FailingLearningModule(MockLearningRefinementModule):
        async def learn_and_refine(self, current_prompt, eval_result):
            return None # Simulate failure to generate a new version

    mock_agent.learning_refinement_module = FailingLearningModule()

    await mock_agent.run_refinement_cycle(
        original_prompt_text="Learning will fail.",
        target_ai_profile_data={"name": "TestAI"},
        initial_performance_metrics={"target_satisfaction": 4.5},
        max_iterations=5,
    )

    # The loop should run exactly once, then stop when it can't create a v2.
    assert len(mock_agent.reporting_module.iterations) == 1 