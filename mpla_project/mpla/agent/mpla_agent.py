from typing import Any, Dict, Optional, AsyncGenerator
import uuid
from datetime import datetime, timezone # Ensure timezone is imported

from mpla.utils.logging import logger
from mpla.knowledge_base.schemas import (
    OriginalPrompt,
    PromptVersion,
    TargetAIProfile,
    EvaluationResult,
    AIOutput,
    IterationLog
)
from mpla.knowledge_base.db_connector import KnowledgeBase
from mpla.core.prompt_enhancer import BasePromptEnhancer
from mpla.core.deployment_orchestrator import DeploymentOrchestrator
from mpla.core.evaluation_engine import EvaluationEngine
from mpla.core.learning_refinement import LearningRefinementModule
from mpla.core.reporting import ReportingModule
from mpla.core.exceptions import KnowledgeBaseError
from mpla.enhancers.architect_enhancer import ArchitectPromptEnhancer
from mpla.config.loader import SelfCorrectionConfig
from mpla.core.output_analyzer import OutputAnalyzer
from mpla.core.prompt_reviser import PromptReviser

class MPLAgent:
    """Manages the overall iterative refinement process for prompts.
    
    This class orchestrates the perceive-decide-act cycle of the MPLA,
    coordinating between various modules like PromptEnhancer, DeploymentOrchestrator,
    EvaluationEngine, LearningRefinementModule, and KnowledgeBase.
    """

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        prompt_enhancer: BasePromptEnhancer,
        deployment_orchestrator: DeploymentOrchestrator,
        evaluation_engine: EvaluationEngine,
        learning_refinement_module: LearningRefinementModule,
        reporting_module: ReportingModule,
        self_correction_config: Optional[SelfCorrectionConfig] = None,
    ):
        self.kb = knowledge_base
        self.prompt_enhancer = prompt_enhancer
        self.deployment_orchestrator = deployment_orchestrator
        self.evaluation_engine = evaluation_engine
        self.learning_refinement_module = learning_refinement_module
        self.reporting_module = reporting_module
        self.current_session_id: Optional[str] = None

        # Initialize self-correction modules if configured
        self.self_correction_enabled = (
            self_correction_config and self_correction_config.enabled
        )
        if self.self_correction_enabled and self_correction_config:
            self.output_analyzer = OutputAnalyzer(
                orchestrator=deployment_orchestrator,
                temperature=self_correction_config.analysis_temperature,
            )
            self.prompt_reviser = PromptReviser(
                orchestrator=deployment_orchestrator,
                temperature=self_correction_config.revision_temperature,
            )
            self.self_correction_max_iterations = self_correction_config.max_iterations
        else:
            self.output_analyzer = None
            self.prompt_reviser = None

    async def _initialize_session(self, original_prompt_text: str, user_id: Optional[str] = None) -> OriginalPrompt:
        """Initializes a new refinement session and saves the original prompt."""
        self.current_session_id = str(uuid.uuid4())
        original_prompt = OriginalPrompt(
            text=original_prompt_text, 
            user_id=user_id,
            # created_at and updated_at are set by BaseMPLAModel or KB during add
        )
        # The kb.add method should handle setting id, created_at, updated_at
        return await self.kb.add(original_prompt)

    async def _self_correct_prompt(
        self,
        prompt_to_correct: str,
        target_ai_profile: TargetAIProfile,
        max_correction_iterations: int,
        result_holder: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Runs an internal self-correction loop on a given prompt.
        Yields events for each step and places the final prompt in the result_holder.
        """
        current_prompt = prompt_to_correct
        result_holder["final_prompt"] = current_prompt # Set a default value

        for i in range(max_correction_iterations):
            yield {
                "event": "self_correction_status",
                "data": {
                    "status": "starting_correction_iteration",
                    "iteration": i + 1,
                    "max_iterations": max_correction_iterations,
                },
            }

            # 1. Test: Get a sample output from the current prompt version
            temp_prompt_version = PromptVersion(prompt_text=current_prompt, version_number=0)
            ai_output = await self.deployment_orchestrator.deploy_and_collect(
                temp_prompt_version, target_ai_profile
            )
            if not ai_output or not ai_output.raw_output_data.get("text"):
                yield {
                    "event": "self_correction_error",
                    "data": {"message": "Failed to generate sample output for analysis."},
                }
                result_holder["final_prompt"] = current_prompt
                return

            sample_output_text = ai_output.raw_output_data["text"]
            yield {
                "event": "self_correction_status",
                "data": {"status": "analyzing_output", "output": sample_output_text},
            }

            # 2. Analyze: Use the OutputAnalyzer to find flaws
            analysis = await self.output_analyzer.analyze(current_prompt, sample_output_text)
            yield {"event": "self_correction_analysis", "data": analysis}

            if not analysis.get("flaws_found"):
                yield {
                    "event": "self_correction_status",
                    "data": {"status": "converged", "message": "No flaws found. Converged."},
                }
                result_holder["final_prompt"] = current_prompt
                return

            # 3. Revise: Use the PromptReviser to fix the flaws
            yield {"event": "self_correction_status", "data": {"status": "revising_prompt"}}
            revised_prompt = await self.prompt_reviser.revise(current_prompt, analysis)

            if revised_prompt == current_prompt:
                yield {
                    "event": "self_correction_status",
                    "data": {"status": "converged", "message": "Reviser made no changes. Converged."},
                }
                result_holder["final_prompt"] = current_prompt
                return

            current_prompt = revised_prompt
            yield {
                "event": "self_correction_revision",
                "data": {"revised_prompt": current_prompt},
            }

        yield {
            "event": "self_correction_status",
            "data": {
                "status": "max_iterations_reached",
                "message": "Max self-correction iterations reached.",
            },
        }
        result_holder["final_prompt"] = current_prompt
        return

    async def run_refinement_cycle(
        self,
        original_prompt_text: str,
        target_ai_profile_data: Dict[str, Any],
        initial_performance_metrics: Dict[str, Any],
        max_iterations: int = 5,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs the full iterative prompt refinement process."""
        await self.kb.connect()

        original_prompt_obj = await self._initialize_session(original_prompt_text, user_id)
        if not original_prompt_obj.id:
            raise KnowledgeBaseError("Failed to save original prompt to the database.")

        target_ai_profile = TargetAIProfile(**target_ai_profile_data)
        
        # This variable will hold the prompt text that serves as input for the next enhancement.
        # It starts with the user's initial prompt.
        prompt_text_for_next_iteration = original_prompt_text
        
        for i in range(max_iterations):
            iteration_count = i + 1
            logger.info(f"--- Starting Iteration {iteration_count} for session {self.current_session_id} ---")

            # 1. Enhance Prompt using the text from the previous step.
            enhanced_prompt_text, rationale = await self.prompt_enhancer.enhance(
                prompt_text_for_next_iteration, target_ai_profile
            )
            
            prompt_version_data = PromptVersion(
                original_prompt_id=original_prompt_obj.id,
                version_number=iteration_count,
                prompt_text=enhanced_prompt_text,
                enhancement_rationale=rationale,
            )
            saved_prompt_version = await self.kb.add(prompt_version_data)
            logger.debug(f"Enhanced Prompt v{saved_prompt_version.version_number}: {saved_prompt_version.prompt_text[:100]}...")

            # 2. Deploy & Collect
            ai_output = await self.deployment_orchestrator.deploy_and_collect(
                saved_prompt_version, target_ai_profile
            )
            
            if not ai_output:
                logger.error("Failed to get AI output. Stopping.")
                break
            
            ai_output.prompt_version_id = saved_prompt_version.id
            saved_ai_output = await self.kb.add(ai_output)
            logger.debug(f"AI Output collected and saved (ID: {saved_ai_output.id}): {str(saved_ai_output.raw_output_data)[:100]}...")

            # 3. Evaluate
            evaluation_result = await self.evaluation_engine.evaluate(
                saved_ai_output, initial_performance_metrics
            )

            if not evaluation_result:
                logger.error("Evaluation failed. Stopping.")
                break

            evaluation_result.ai_output_id = saved_ai_output.id
            saved_evaluation_result = await self.kb.add(evaluation_result)
            logger.info(f"Evaluation complete (ID: {saved_evaluation_result.id}): {saved_evaluation_result.metric_scores}")
            
            # 4. Report Iteration
            iteration_log = IterationLog(
                original_prompt_id=original_prompt_obj.id,
                session_id=self.current_session_id,
                iteration_number=iteration_count,
                active_prompt_version_id=saved_prompt_version.id,
                ai_output_id=saved_ai_output.id,
                evaluation_result_id=saved_evaluation_result.id,
                status="completed"
            )
            await self.reporting_module.report_iteration(iteration_log)

            # 5. Check for completion and prepare for next iteration
            # The early exit for performance has been removed to ensure all generations run.
            if i < max_iterations - 1:
                # For the Architect, the next input is simply the enhanced text from this iteration.
                if isinstance(self.prompt_enhancer, ArchitectPromptEnhancer):
                    prompt_text_for_next_iteration = saved_prompt_version.prompt_text
                else:
                    # For other enhancers, use the learning module to generate the next version.
                    next_prompt_version_obj = await self.learning_refinement_module.learn_and_refine(
                        saved_prompt_version, saved_evaluation_result
                    )
                    if not next_prompt_version_obj:
                        logger.warning("Learning module did not produce a refinement. Ending.")
                        break
                    prompt_text_for_next_iteration = next_prompt_version_obj.prompt_text
            else:
                logger.info("--- Max iterations reached. ---")

        # Generate the final report after all iterations are complete.
        return await self.reporting_module.generate_final_report(self.current_session_id) 

    async def stream_refinement_cycle(
        self,
        original_prompt_text: str,
        target_ai_profile_data: Dict[str, Any],
        initial_performance_metrics: Dict[str, Any],
        max_iterations: int = 5,
        user_id: Optional[str] = None,
        # New params for user control over self-correction
        self_correction_enabled_by_user: bool = False,
        self_correction_iterations_by_user: int = 3,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Runs the iterative prompt refinement process and streams results after each iteration.
        """
        await self.kb.connect()

        original_prompt_obj = await self._initialize_session(original_prompt_text, user_id)
        if not original_prompt_obj.id:
            raise KnowledgeBaseError("Failed to save original prompt to the database.")

        target_ai_profile = TargetAIProfile(**target_ai_profile_data)
        
        prompt_text_for_next_iteration = original_prompt_text
        
        for i in range(max_iterations):
            iteration_count = i + 1
            logger.info(f"--- Starting Stream Iteration {iteration_count} for session {self.current_session_id} ---")

            # 1. Enhance Prompt
            enhanced_prompt_text, rationale = await self.prompt_enhancer.enhance(
                prompt_text_for_next_iteration, target_ai_profile
            )
            
            # --- SELF-CORRECTION HOOK ---
            final_prompt_text = enhanced_prompt_text
            if (
                self.self_correction_enabled
                and self_correction_enabled_by_user
                and self.output_analyzer
                and self.prompt_reviser
            ):
                max_correction_iters = min(
                    self.self_correction_max_iterations, self_correction_iterations_by_user
                )
                
                result_holder = {}
                correction_generator = self._self_correct_prompt(
                    prompt_to_correct=enhanced_prompt_text,
                    target_ai_profile=target_ai_profile,
                    max_correction_iterations=max_correction_iters,
                    result_holder=result_holder,
                )

                # Yield all events from the self-correction process
                async for event in correction_generator:
                    yield event
                
                # Get the final result from the holder
                final_prompt_text = result_holder.get("final_prompt", enhanced_prompt_text)

            prompt_version_data = PromptVersion(
                original_prompt_id=original_prompt_obj.id,
                version_number=iteration_count,
                prompt_text=final_prompt_text, # Use the potentially self-corrected prompt
                enhancement_rationale=rationale,
            )
            saved_prompt_version = await self.kb.add(prompt_version_data)
            logger.debug(f"Stream: Enhanced Prompt v{saved_prompt_version.version_number}: {saved_prompt_version.prompt_text[:100]}...")

            # 2. Deploy & Collect
            ai_output = await self.deployment_orchestrator.deploy_and_collect(
                saved_prompt_version, target_ai_profile
            )
            
            if not ai_output:
                logger.error("Stream: Failed to get AI output. Stopping.")
                break
            
            ai_output.prompt_version_id = saved_prompt_version.id
            saved_ai_output = await self.kb.add(ai_output)
            logger.debug(f"Stream: AI Output collected and saved (ID: {saved_ai_output.id}): {str(saved_ai_output.raw_output_data)[:100]}...")

            # 3. Evaluate
            evaluation_result = await self.evaluation_engine.evaluate(
                saved_ai_output, initial_performance_metrics
            )

            if not evaluation_result:
                logger.error("Stream: Evaluation failed. Stopping.")
                break

            evaluation_result.ai_output_id = saved_ai_output.id
            saved_evaluation_result = await self.kb.add(evaluation_result)
            logger.info(f"Stream: Evaluation complete (ID: {saved_evaluation_result.id}): {saved_evaluation_result.metric_scores}")
            
            # 4. Report Iteration Log
            iteration_log = IterationLog(
                original_prompt_id=original_prompt_obj.id,
                session_id=self.current_session_id,
                iteration_number=iteration_count,
                active_prompt_version_id=saved_prompt_version.id,
                ai_output_id=saved_ai_output.id,
                evaluation_result_id=saved_evaluation_result.id,
                status="completed"
            )
            await self.reporting_module.report_iteration(iteration_log)

            # 5. YIELD THE RESULT FOR THE STREAM
            yield {
                "event": "iteration_result",
                "data": {
                    "iteration": iteration_count,
                    "prompt": saved_prompt_version.prompt_text,
                    "rationale": saved_prompt_version.enhancement_rationale,
                    "evaluation": saved_evaluation_result.metric_scores,
                    "raw_ai_output": saved_ai_output.raw_output_data.get("text", str(saved_ai_output.raw_output_data))
                }
            }

            # 6. Check for completion and prepare for next iteration
            if i < max_iterations - 1:
                if isinstance(self.prompt_enhancer, ArchitectPromptEnhancer):
                    prompt_text_for_next_iteration = saved_prompt_version.prompt_text
                else:
                    next_prompt_version_obj = await self.learning_refinement_module.learn_and_refine(
                        saved_prompt_version, saved_evaluation_result
                    )
                    if not next_prompt_version_obj:
                        logger.warning("Stream: Learning module did not produce a refinement. Ending.")
                        break
                    prompt_text_for_next_iteration = next_prompt_version_obj.prompt_text
            else:
                logger.info("--- Stream: Max iterations reached. ---") 