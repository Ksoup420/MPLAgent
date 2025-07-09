from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import re # For potential regex use in format checks

from mpla.knowledge_base.schemas import AIOutput, EvaluationResult, PerformanceMetricDefinition

class EvaluationEngine(ABC):
    """Abstract Base Class for Evaluation Engine modules.
    
    Defines the interface for assessing the quality of an AI's output
    based on defined performance metrics and user feedback.
    """

    @abstractmethod
    async def evaluate(
        self, 
        ai_output: AIOutput,
        performance_metrics: Dict[str, Any], # Could be a list of PerformanceMetricDefinition objects or similar config
        # user_feedback: Optional[UserFeedbackSchema] = None # Placeholder for user feedback structure
    ) -> Optional[EvaluationResult]:
        """Evaluates the given AI output.

        Args:
            ai_output: The AIOutput object to evaluate.
            performance_metrics: Definitions or configurations of metrics to apply.
            # user_feedback: Optional structured user feedback.

        Returns:
            An EvaluationResult object containing the scores and analysis, or None if evaluation fails.
        """
        pass

class BasicEvaluationEngine(EvaluationEngine):
    """
    A basic implementation of the EvaluationEngine that uses a configurable
    set of rules to score AI output.
    """
    DEFAULT_SCORE_SCALE = 5.0

    async def evaluate(
        self, 
        ai_output: AIOutput,
        metrics_config: Dict[str, Any]
    ) -> Optional[EvaluationResult]:
        """
        Evaluates AI output based on rules defined in metrics_config.

        Args:
            ai_output: The AIOutput object. Assumes raw_output_data contains a 'text' field 
                       or is directly a string. If it's a dict with 'error', evaluation is skipped.
            metrics_config: Configuration for evaluation. Example structure:
                {
                    "target_satisfaction": 4.0, // Target overall satisfaction
                    "rules": {
                        "length": {"min": 10, "max": 500, "weight": 0.3, "target_score": 5, "fail_if_outside_strict_bounds": false},
                        "keywords": {"present": ["key", "points"], "absent": ["unable to", "sorry"], "weight": 0.4, "target_score": 5, "case_sensitive": false},
                        "must_contain_phrases": {"phrases": ["In conclusion"], "weight": 0.2, "target_score": 5, "case_sensitive": false},
                        "bullet_points": {"min_bullets": 2, "weight": 0.1, "target_score": 5} // Simple check for '*' or '-'
                    }
                }
        Returns:
            An EvaluationResult object or None if critical errors occur.
        """
        if not ai_output or not ai_output.raw_output_data:
            print("EvaluationEngine: No AI output data to evaluate.")
            return None

        text_to_evaluate = ""
        if isinstance(ai_output.raw_output_data, str):
            text_to_evaluate = ai_output.raw_output_data
        elif isinstance(ai_output.raw_output_data, dict):
            if "error" in ai_output.raw_output_data:
                print(f"EvaluationEngine: AI output contains error: {ai_output.raw_output_data['error']}. Skipping evaluation.")
                # Still return an EvaluationResult, but with error indication
                return EvaluationResult(
                    ai_output_id=ai_output.id if ai_output.id is not None else -1,
                    metric_scores={"error": 1, "overall_satisfaction": 0},
                    qualitative_feedback=f"Evaluation skipped due to AI output error: {ai_output.raw_output_data.get('details', '')}",
                    target_metrics_snapshot=metrics_config
                )
            text_to_evaluate = ai_output.raw_output_data.get("text", "")
        
        if not text_to_evaluate and not isinstance(ai_output.raw_output_data, dict) and "error" not in ai_output.raw_output_data: # check if text_to_evaluate is empty AND not because of an error
            print("EvaluationEngine: No text found in AI output to evaluate.")
            # Create a minimal EvaluationResult indicating no text was found
            return EvaluationResult(
                ai_output_id=ai_output.id if ai_output.id is not None else -1,
                metric_scores={"text_quality": 0, "overall_satisfaction": 0}, # Example low scores
                qualitative_feedback="No evaluable text content found in AI output.",
                target_metrics_snapshot=metrics_config
            )


        rules = metrics_config.get("rules", {})
        metric_scores: Dict[str, float] = {}
        qualitative_feedback_parts: List[str] = []
        
        total_weight = 0.0
        weighted_score_sum = 0.0

        # --- Length Check ---
        if "length" in rules:
            config = rules["length"]
            score = self._score_length(text_to_evaluate, config.get("min"), config.get("max"), config.get("fail_if_outside_strict_bounds", False))
            metric_scores["length"] = score
            weighted_score_sum += score * config.get("weight", 0)
            total_weight += config.get("weight", 0)
            qualitative_feedback_parts.append(f"Length score: {score:.1f}/5.0 (min: {config.get('min')}, max: {config.get('max')})")
            if score == 0 and config.get("fail_if_outside_strict_bounds", False):
                 qualitative_feedback_parts.append("Failed length check (strict bounds).")


        # --- Keyword Check ---
        if "keywords" in rules:
            config = rules["keywords"]
            score, feedback = self._score_keywords(text_to_evaluate, config.get("present", []), config.get("absent", []), config.get("case_sensitive", False))
            metric_scores["keywords"] = score
            weighted_score_sum += score * config.get("weight", 0)
            total_weight += config.get("weight", 0)
            qualitative_feedback_parts.append(f"Keywords score: {score:.1f}/5.0. {feedback}")

        # --- Must Contain Phrases Check ---
        if "must_contain_phrases" in rules:
            config = rules["must_contain_phrases"]
            score, feedback = self._score_must_contain_phrases(text_to_evaluate, config.get("phrases", []), config.get("case_sensitive", False))
            metric_scores["must_contain_phrases"] = score
            weighted_score_sum += score * config.get("weight", 0)
            total_weight += config.get("weight", 0)
            qualitative_feedback_parts.append(f"Must-contain phrases score: {score:.1f}/5.0. {feedback}")
            
        # --- Bullet Points Check ---
        if "bullet_points" in rules:
            config = rules["bullet_points"]
            score, feedback = self._score_bullet_points(text_to_evaluate, config.get("min_bullets", 1))
            metric_scores["bullet_points"] = score
            weighted_score_sum += score * config.get("weight", 0)
            total_weight += config.get("weight", 0)
            qualitative_feedback_parts.append(f"Bullet points score: {score:.1f}/5.0. {feedback}")


        # --- Overall Satisfaction ---
        if total_weight > 0:
            overall_satisfaction = (weighted_score_sum / total_weight)
        elif metric_scores: # If specific scores exist but no weights, average them
            overall_satisfaction = sum(metric_scores.values()) / len(metric_scores) if len(metric_scores) > 0 else 0.0
        else: # No rules applied or no scores generated
             overall_satisfaction = 0.0 # Default if no rules could be applied or all weights are zero

        # Clamp overall_satisfaction to be within 0 and DEFAULT_SCORE_SCALE
        overall_satisfaction = max(0.0, min(self.DEFAULT_SCORE_SCALE, overall_satisfaction))
        metric_scores["overall_satisfaction"] = round(overall_satisfaction, 2)
        
        qualitative_feedback = "; ".join(qualitative_feedback_parts)

        return EvaluationResult(
            ai_output_id=ai_output.id if ai_output.id is not None else -1,
            metric_scores=metric_scores,
            qualitative_feedback=qualitative_feedback,
            target_metrics_snapshot=metrics_config # Store the configuration used for this evaluation
        )

    def _score_length(self, text: str, min_len: Optional[int], max_len: Optional[int], strict_fail: bool = False) -> float:
        length = len(text)
        if min_len is None and max_len is None:
            return self.DEFAULT_SCORE_SCALE # No length constraint

        if min_len is not None and length < min_len:
            return 0.0 if strict_fail else self.DEFAULT_SCORE_SCALE * (length / min_len) * 0.5 # Penalize heavily
        if max_len is not None and length > max_len:
            return 0.0 if strict_fail else self.DEFAULT_SCORE_SCALE * (max_len / length) * 0.5 # Penalize heavily
        
        # If within ideal range (or one bound is not set and other is met)
        # This simple scoring gives full score if within bounds, might need more nuance
        return self.DEFAULT_SCORE_SCALE

    def _score_keywords(self, text: str, present_keywords: List[str], absent_keywords: List[str], case_sensitive: bool) -> tuple[float, str]:
        if not case_sensitive:
            text_to_check = text.lower()
            present_keywords = [k.lower() for k in present_keywords]
            absent_keywords = [k.lower() for k in absent_keywords]
        else:
            text_to_check = text

        found_present = [kw for kw in present_keywords if kw in text_to_check]
        found_absent = [kw for kw in absent_keywords if kw in text_to_check]

        score = self.DEFAULT_SCORE_SCALE
        feedback_parts = []

        if present_keywords:
            presence_ratio = len(found_present) / len(present_keywords)
            score *= presence_ratio # Scale score by ratio of found "present" keywords
            feedback_parts.append(f"Found {len(found_present)}/{len(present_keywords)} required keywords.")
        
        if found_absent:
            score *= 0.2 # Penalize heavily if forbidden keywords are found
            feedback_parts.append(f"Found {len(found_absent)} forbidden keywords: {', '.join(found_absent)}.")
        
        return max(0.0, score), " ".join(feedback_parts)

    def _score_must_contain_phrases(self, text: str, phrases: List[str], case_sensitive: bool) -> tuple[float, str]:
        if not phrases:
            return self.DEFAULT_SCORE_SCALE, "No must-contain phrases specified."

        if not case_sensitive:
            text_to_check = text.lower()
            phrases = [p.lower() for p in phrases]
        else:
            text_to_check = text
            
        missing_phrases = [p for p in phrases if p not in text_to_check]

        if not missing_phrases:
            return self.DEFAULT_SCORE_SCALE, f"All {len(phrases)} required phrases found."
        else:
            # Penalize based on the proportion of missing phrases
            score = self.DEFAULT_SCORE_SCALE * (1 - (len(missing_phrases) / len(phrases)))
            feedback = f"Missing {len(missing_phrases)}/{len(phrases)} required phrases: {', '.join(missing_phrases)}."
            return max(0.0, score), feedback

    def _score_bullet_points(self, text: str, min_bullets: int) -> tuple[float, str]:
        if min_bullets <= 0:
            return self.DEFAULT_SCORE_SCALE, "No bullet point requirement."
        
        # Simple regex for lines starting with common bullet markers (*, -, •) followed by a space
        # This is a basic check and might need refinement for complex cases.
        bullet_pattern = re.compile(r"^\s*[\*\-\•]\s+", re.MULTILINE)
        matches = bullet_pattern.findall(text)
        num_bullets_found = len(matches)

        if num_bullets_found >= min_bullets:
            score = self.DEFAULT_SCORE_SCALE
            feedback = f"Found {num_bullets_found} bullet points (met minimum of {min_bullets})."
        else:
            # Score proportionally if some bullets are found, 0 if none and min_bullets > 0
            score = (num_bullets_found / min_bullets) * self.DEFAULT_SCORE_SCALE if min_bullets > 0 else 0.0
            feedback = f"Found {num_bullets_found} bullet points (expected min {min_bullets})."
        
        return max(0.0, score), feedback 