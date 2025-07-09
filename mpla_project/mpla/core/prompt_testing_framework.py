"""
Prompt Testing Framework for MPLA System

This module provides comprehensive testing capabilities for evaluating different
prompt variants for architect, analyzer, and reviser components.
"""

import asyncio
import json
import os
import statistics
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from mpla.utils.logging import logger
from mpla.knowledge_base.db_connector import KnowledgeBase
from mpla.knowledge_base.schemas import TargetAIProfile
from mpla.core.deployment_orchestrator import DeploymentOrchestrator
from mpla.enhancers.architect_enhancer import ArchitectPromptEnhancer
from mpla.core.output_analyzer import OutputAnalyzer
from mpla.core.prompt_reviser import PromptReviser


@dataclass
class TestCase:
    """Represents a single test case for prompt evaluation."""
    id: str
    name: str
    description: str
    input_prompt: str
    expected_characteristics: List[str]  # What we expect in a good result
    difficulty_level: str  # "easy", "medium", "hard"
    category: str  # "technical", "creative", "analysis", "instruction"


@dataclass
class PromptVariant:
    """Represents a prompt variant to be tested."""
    id: str
    name: str
    description: str
    content: str
    source_file: Optional[str] = None
    prompt_type: str = "architect"  # "architect", "analyzer", "reviser"


@dataclass
class TestResult:
    """Results from testing a single prompt variant on a test case."""
    test_case_id: str
    prompt_variant_id: str
    output: str
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    quality_scores: Dict[str, float] = None  # Custom quality metrics
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.quality_scores is None:
            self.quality_scores = {}


@dataclass
class ComparisonReport:
    """Report comparing multiple prompt variants."""
    test_suite_name: str
    prompt_variants: List[PromptVariant]
    test_cases: List[TestCase]
    results: List[TestResult]
    summary_metrics: Dict[str, Any]
    recommendations: List[str]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PromptTestingFramework:
    """
    Comprehensive framework for testing and comparing different prompt variants.
    """

    def __init__(
        self, 
        deployment_orchestrator: DeploymentOrchestrator,
        knowledge_base: KnowledgeBase,
        prompts_directory: str = "Prompts for MPLA agents"
    ):
        self.orchestrator = deployment_orchestrator
        self.kb = knowledge_base
        self.prompts_directory = prompts_directory
        self.test_cases: List[TestCase] = []
        self.prompt_variants: List[PromptVariant] = []

    async def load_prompt_variants(self) -> List[PromptVariant]:
        """Load all prompt variants from the prompts directory."""
        variants = []
        
        if not os.path.exists(self.prompts_directory):
            logger.warning(f"Prompts directory not found: {self.prompts_directory}")
            return variants

        for filename in os.listdir(self.prompts_directory):
            if filename.endswith(('.txt', '.md')):
                file_path = os.path.join(self.prompts_directory, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Determine prompt type based on filename
                    prompt_type = "architect"  # Default
                    if "analyzer" in filename.lower() or "analysis" in filename.lower():
                        prompt_type = "analyzer"
                    elif "reviser" in filename.lower() or "revision" in filename.lower():
                        prompt_type = "reviser"
                    
                    variant = PromptVariant(
                        id=f"variant_{len(variants)}",
                        name=filename.replace('.txt', '').replace('.md', ''),
                        description=f"Prompt variant from {filename}",
                        content=content,
                        source_file=filename,
                        prompt_type=prompt_type
                    )
                    variants.append(variant)
                    logger.info(f"Loaded prompt variant: {variant.name} (type: {prompt_type})")
                    
                except Exception as e:
                    logger.error(f"Failed to load prompt variant from {filename}: {e}")

        self.prompt_variants = variants
        return variants

    def create_test_cases(self) -> List[TestCase]:
        """Create a comprehensive set of test cases for prompt evaluation."""
        test_cases = [
            # Easy cases - Simple, clear prompts
            TestCase(
                id="easy_01",
                name="Simple Task Request",
                description="Basic task with clear objective",
                input_prompt="Write a summary of the benefits of renewable energy",
                expected_characteristics=["clear structure", "factual content", "good organization"],
                difficulty_level="easy",
                category="instruction"
            ),
            TestCase(
                id="easy_02", 
                name="Basic Technical Question",
                description="Simple technical query",
                input_prompt="Explain how HTTP works",
                expected_characteristics=["technical accuracy", "clear explanation", "appropriate depth"],
                difficulty_level="easy",
                category="technical"
            ),

            # Medium cases - Ambiguous or missing context
            TestCase(
                id="medium_01",
                name="Vague Creative Request",
                description="Creative prompt lacking specifics",
                input_prompt="Write something creative about time",
                expected_characteristics=["clarified format", "defined scope", "creative direction"],
                difficulty_level="medium",
                category="creative"
            ),
            TestCase(
                id="medium_02",
                name="Technical Request Missing Context",
                description="Technical prompt without sufficient detail",
                input_prompt="Debug this code",
                expected_characteristics=["request for code", "specify language", "define problem"],
                difficulty_level="medium",
                category="technical"
            ),
            TestCase(
                id="medium_03",
                name="Analysis Without Subject",
                description="Analysis request missing key information",
                input_prompt="Analyze the effectiveness",
                expected_characteristics=["define subject", "specify criteria", "clarify scope"],
                difficulty_level="medium",
                category="analysis"
            ),

            # Hard cases - Complex, multi-part, or problematic prompts
            TestCase(
                id="hard_01",
                name="Multi-Part Complex Request",
                description="Complex prompt with multiple requirements",
                input_prompt="Create a comprehensive marketing strategy for a startup including market research, competitor analysis, budget planning, timeline, and implementation steps but make it creative and innovative while ensuring it's practical and cost-effective",
                expected_characteristics=["structured breakdown", "prioritized sections", "clear deliverables"],
                difficulty_level="hard",
                category="instruction"
            ),
            TestCase(
                id="hard_02",
                name="Contradictory Requirements",
                description="Prompt with conflicting demands",
                input_prompt="Write a detailed yet brief comprehensive summary of all major historical events in minimal words with extensive coverage",
                expected_characteristics=["resolve contradictions", "clarify priorities", "set realistic scope"],
                difficulty_level="hard",
                category="instruction"
            ),
            TestCase(
                id="hard_03",
                name="Highly Technical Domain-Specific",
                description="Complex technical prompt requiring expertise",
                input_prompt="Implement a distributed consensus algorithm that handles Byzantine failures while maintaining linearizability and partition tolerance",
                expected_characteristics=["break down complexity", "define prerequisites", "structure approach"],
                difficulty_level="hard",
                category="technical"
            ),

            # Edge cases - Test error handling and robustness
            TestCase(
                id="edge_01",
                name="Empty Prompt",
                description="Completely empty input",
                input_prompt="",
                expected_characteristics=["handle gracefully", "request clarification", "provide guidance"],
                difficulty_level="easy",
                category="instruction"
            ),
            TestCase(
                id="edge_02",
                name="Nonsensical Prompt",
                description="Meaningless or incoherent input",
                input_prompt="Purple elephant mathematics flying through tomorrow's wednesday breakfast",
                expected_characteristics=["identify incoherence", "request clarification", "offer alternatives"],
                difficulty_level="medium",
                category="instruction"
            )
        ]

        self.test_cases = test_cases
        logger.info(f"Created {len(test_cases)} test cases")
        return test_cases

    async def test_architect_variant(
        self, 
        variant: PromptVariant, 
        test_case: TestCase,
        ai_profile: TargetAIProfile
    ) -> TestResult:
        """Test a single architect prompt variant on a test case."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Create a temporary architect enhancer with this variant's prompt
            # We'll modify the approach to inject the prompt content
            history = [variant.content.format(user_prompt=test_case.input_prompt), ""]
            
            ai_output = await self.orchestrator.deploy_and_collect_from_history(
                history=history,
                ai_profile=ai_profile
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            if ai_output and isinstance(ai_output.raw_output_data, dict):
                output_text = ai_output.raw_output_data.get("text", "")
            else:
                output_text = ""
            
            # Calculate quality scores
            quality_scores = await self._calculate_quality_scores(
                test_case, output_text, variant.prompt_type
            )
            
            return TestResult(
                test_case_id=test_case.id,
                prompt_variant_id=variant.id,
                output=output_text,
                execution_time=execution_time,
                success=True,
                quality_scores=quality_scores
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Failed to test variant {variant.id} on test case {test_case.id}: {e}")
            
            return TestResult(
                test_case_id=test_case.id,
                prompt_variant_id=variant.id,
                output="",
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )

    async def _calculate_quality_scores(
        self, 
        test_case: TestCase, 
        output: str, 
        prompt_type: str
    ) -> Dict[str, float]:
        """Calculate quality scores for the output."""
        scores = {}
        
        # Basic metrics
        scores['output_length'] = len(output)
        scores['has_content'] = 1.0 if len(output.strip()) > 0 else 0.0
        
        # Check for expected characteristics
        characteristics_found = 0
        for characteristic in test_case.expected_characteristics:
            # Simple keyword-based matching (can be enhanced with NLP)
            if any(keyword in output.lower() for keyword in characteristic.lower().split()):
                characteristics_found += 1
        
        scores['characteristics_coverage'] = (
            characteristics_found / len(test_case.expected_characteristics) 
            if test_case.expected_characteristics else 0.0
        )
        
        # Architect-specific metrics
        if prompt_type == "architect":
            scores['has_enhanced_prompt'] = 1.0 if "enhanced prompt" in output.lower() else 0.0
            scores['has_explanation'] = 1.0 if "explanation" in output.lower() or "rationale" in output.lower() else 0.0
            scores['structure_quality'] = self._assess_structure_quality(output)
        
        # Overall quality (simple heuristic)
        scores['overall_quality'] = statistics.mean([
            scores['has_content'],
            scores['characteristics_coverage'],
            scores.get('structure_quality', 0.5)
        ])
        
        return scores

    def _assess_structure_quality(self, output: str) -> float:
        """Assess the structural quality of the output."""
        score = 0.0
        
        # Check for clear sections
        if "enhanced prompt:" in output.lower():
            score += 0.3
        if any(word in output.lower() for word in ["explanation", "rationale", "analysis"]):
            score += 0.3
        
        # Check for formatting
        if output.count('\n') >= 3:  # Has some structure
            score += 0.2
        if any(marker in output for marker in ['**', '*', '#', '-', '1.', '2.']):
            score += 0.2
        
        return min(score, 1.0)

    async def run_comprehensive_test(
        self, 
        prompt_type: str = "architect",
        ai_profile: Optional[TargetAIProfile] = None
    ) -> ComparisonReport:
        """Run comprehensive testing on all variants of a specific prompt type."""
        if ai_profile is None:
            ai_profile = TargetAIProfile(name="gemini-2.0-flash")
        
        # Load variants and test cases
        await self.load_prompt_variants()
        self.create_test_cases()
        
        # Filter variants by type
        variants_to_test = [v for v in self.prompt_variants if v.prompt_type == prompt_type]
        logger.info(f"Testing {len(variants_to_test)} {prompt_type} variants on {len(self.test_cases)} test cases")
        
        all_results = []
        
        # Test each variant on each test case
        for variant in variants_to_test:
            logger.info(f"Testing variant: {variant.name}")
            for test_case in self.test_cases:
                result = await self.test_architect_variant(variant, test_case, ai_profile)
                all_results.append(result)
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(1)
        
        # Generate summary metrics
        summary_metrics = self._generate_summary_metrics(all_results, variants_to_test)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_results, variants_to_test, self.test_cases)
        
        report = ComparisonReport(
            test_suite_name=f"{prompt_type.title()} Prompt Comparison",
            prompt_variants=variants_to_test,
            test_cases=self.test_cases,
            results=all_results,
            summary_metrics=summary_metrics,
            recommendations=recommendations
        )
        
        return report

    def _generate_summary_metrics(
        self, 
        results: List[TestResult], 
        variants: List[PromptVariant]
    ) -> Dict[str, Any]:
        """Generate summary metrics from test results."""
        metrics = {}
        
        # Overall metrics
        successful_tests = [r for r in results if r.success]
        metrics['total_tests'] = len(results)
        metrics['successful_tests'] = len(successful_tests)
        metrics['success_rate'] = len(successful_tests) / len(results) if results else 0
        
        # Per-variant metrics
        variant_metrics = {}
        for variant in variants:
            variant_results = [r for r in results if r.prompt_variant_id == variant.id]
            variant_successful = [r for r in variant_results if r.success]
            
            if variant_results:
                avg_quality = statistics.mean([
                    r.quality_scores.get('overall_quality', 0) 
                    for r in variant_successful
                ]) if variant_successful else 0
                
                avg_execution_time = statistics.mean([r.execution_time for r in variant_results])
                
                variant_metrics[variant.id] = {
                    'name': variant.name,
                    'success_rate': len(variant_successful) / len(variant_results),
                    'avg_quality_score': avg_quality,
                    'avg_execution_time': avg_execution_time,
                    'total_tests': len(variant_results)
                }
        
        metrics['variant_performance'] = variant_metrics
        
        # Find best performing variant
        if variant_metrics:
            best_variant_id = max(
                variant_metrics.keys(),
                key=lambda vid: variant_metrics[vid]['avg_quality_score']
            )
            metrics['best_variant'] = {
                'id': best_variant_id,
                'name': variant_metrics[best_variant_id]['name'],
                'score': variant_metrics[best_variant_id]['avg_quality_score']
            }
        
        return metrics

    def _generate_recommendations(
        self, 
        results: List[TestResult], 
        variants: List[PromptVariant],
        test_cases: List[TestCase]
    ) -> List[str]:
        """Generate actionable recommendations based on test results."""
        recommendations = []
        
        # Analyze variant performance
        variant_scores = {}
        for variant in variants:
            variant_results = [r for r in results if r.prompt_variant_id == variant.id and r.success]
            if variant_results:
                avg_score = statistics.mean([
                    r.quality_scores.get('overall_quality', 0) for r in variant_results
                ])
                variant_scores[variant.id] = (variant, avg_score)
        
        if variant_scores:
            # Best and worst variants
            best_variant_id = max(variant_scores.keys(), key=lambda vid: variant_scores[vid][1])
            worst_variant_id = min(variant_scores.keys(), key=lambda vid: variant_scores[vid][1])
            
            best_variant, best_score = variant_scores[best_variant_id]
            worst_variant, worst_score = variant_scores[worst_variant_id]
            
            recommendations.append(
                f"🏆 RECOMMENDED: Use '{best_variant.name}' as your primary prompt variant "
                f"(avg quality score: {best_score:.2f})"
            )
            
            if best_score - worst_score > 0.3:
                recommendations.append(
                    f"⚠️  AVOID: '{worst_variant.name}' shows significantly lower performance "
                    f"(avg quality score: {worst_score:.2f})"
                )
        
        # Analyze test case difficulty
        difficulty_performance = {}
        for test_case in test_cases:
            case_results = [r for r in results if r.test_case_id == test_case.id and r.success]
            if case_results:
                avg_score = statistics.mean([
                    r.quality_scores.get('overall_quality', 0) for r in case_results
                ])
                difficulty_performance[test_case.difficulty_level] = avg_score
        
        if len(difficulty_performance) > 1:
            hardest_difficulty = min(difficulty_performance.keys(), 
                                   key=lambda d: difficulty_performance[d])
            recommendations.append(
                f"📈 FOCUS AREA: {hardest_difficulty.title()} prompts need improvement "
                f"(avg score: {difficulty_performance[hardest_difficulty]:.2f})"
            )
        
        # General recommendations
        failed_results = [r for r in results if not r.success]
        if len(failed_results) > len(results) * 0.1:  # More than 10% failure rate
            recommendations.append(
                "🔧 ERROR HANDLING: High failure rate detected. Consider adding error handling "
                "and fallback mechanisms to your prompts."
            )
        
        return recommendations

    async def save_report(self, report: ComparisonReport, filename: Optional[str] = None) -> str:
        """Save the comparison report to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"prompt_testing_report_{timestamp}.json"
        
        # Convert dataclasses to dictionaries for JSON serialization
        report_dict = {
            'test_suite_name': report.test_suite_name,
            'prompt_variants': [asdict(v) for v in report.prompt_variants],
            'test_cases': [asdict(tc) for tc in report.test_cases],
            'results': [asdict(r) for r in report.results],
            'summary_metrics': report.summary_metrics,
            'recommendations': report.recommendations,
            'timestamp': report.timestamp.isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        logger.info(f"Report saved to {filename}")
        return filename

    def print_summary_report(self, report: ComparisonReport):
        """Print a formatted summary of the test results."""
        print("\n" + "="*80)
        print(f"🧪 {report.test_suite_name}")
        print("="*80)
        
        # Summary statistics
        metrics = report.summary_metrics
        print(f"\n📊 SUMMARY STATISTICS")
        print(f"Total Tests: {metrics['total_tests']}")
        print(f"Successful Tests: {metrics['successful_tests']}")
        print(f"Success Rate: {metrics['success_rate']:.1%}")
        
        # Best variant
        if 'best_variant' in metrics:
            best = metrics['best_variant']
            print(f"\n🏆 BEST PERFORMING VARIANT")
            print(f"Name: {best['name']}")
            print(f"Quality Score: {best['score']:.2f}")
        
        # Variant performance table
        print(f"\n📈 VARIANT PERFORMANCE")
        print(f"{'Variant Name':<30} {'Success Rate':<12} {'Avg Quality':<12} {'Avg Time (s)':<12}")
        print("-" * 66)
        
        for variant_id, perf in metrics['variant_performance'].items():
            print(f"{perf['name']:<30} {perf['success_rate']:<12.1%} "
                  f"{perf['avg_quality_score']:<12.2f} {perf['avg_execution_time']:<12.2f}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")
        
        print("\n" + "="*80) 