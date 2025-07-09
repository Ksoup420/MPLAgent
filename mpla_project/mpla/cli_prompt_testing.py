#!/usr/bin/env python3
"""
CLI tool for running MPLA prompt testing framework.
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add the project directory to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mpla.core.prompt_testing_framework import PromptTestingFramework
from mpla.knowledge_base.sqlite_kb import SQLiteKnowledgeBase
from mpla.knowledge_base.schemas import TargetAIProfile
from mpla.external.google_gemini_orchestrator import GoogleGeminiOrchestrator
from mpla.utils.logging import logger
import traceback


async def run_prompt_tests(
    prompt_type: str = "architect",
    model: str = "gemini-2.0-flash", 
    prompts_dir: str = "Prompts for MPLA agents",
    output_file: str = None,
    verbose: bool = False
):
    """Run the prompt testing framework."""
    try:
        # Initialize components
        logger.info("Initializing MPLA testing framework...")
        
        # Create knowledge base
        kb = SQLiteKnowledgeBase("mpla_test.db")
        await kb.initialize()
        
        # Create orchestrator
        orchestrator = GoogleGeminiOrchestrator()
        
        # Create AI profile
        ai_profile = TargetAIProfile(
            name=model,
            capabilities={"temperature": 0.2}
        )
        
        # Create testing framework
        testing_framework = PromptTestingFramework(
            deployment_orchestrator=orchestrator,
            knowledge_base=kb,
            prompts_directory=prompts_dir
        )
        
        logger.info(f"Testing {prompt_type} prompts using model {model}")
        
        # Run comprehensive test
        report = await testing_framework.run_comprehensive_test(
            prompt_type=prompt_type,
            ai_profile=ai_profile
        )
        
        # Print summary
        testing_framework.print_summary_report(report)
        
        # Save detailed report
        if output_file:
            filename = await testing_framework.save_report(report, output_file)
        else:
            filename = await testing_framework.save_report(report)
        
        print(f"\n📄 Detailed report saved to: {filename}")
        
        # Close knowledge base
        await kb.close()
        
    except Exception as e:
        logger.error(f"Error running prompt tests: {e}")
        if verbose:
            traceback.print_exc()
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MPLA Prompt Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all architect prompts
  python cli_prompt_testing.py --type architect
  
  # Test analyzer prompts with specific model
  python cli_prompt_testing.py --type analyzer --model gemini-1.5-pro
  
  # Test with custom prompts directory and save to specific file
  python cli_prompt_testing.py --prompts-dir "Custom Prompts" --output results.json
  
  # Verbose output for debugging
  python cli_prompt_testing.py --type architect --verbose
        """
    )
    
    parser.add_argument(
        "--type", 
        choices=["architect", "analyzer", "reviser"],
        default="architect",
        help="Type of prompts to test (default: architect)"
    )
    
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash",
        help="AI model to use for testing (default: gemini-2.0-flash)"
    )
    
    parser.add_argument(
        "--prompts-dir",
        default="Prompts for MPLA agents",
        help="Directory containing prompt variants (default: 'Prompts for MPLA agents')"
    )
    
    parser.add_argument(
        "--output",
        help="Output file for detailed JSON report (auto-generated if not specified)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Check if prompts directory exists
    if not os.path.exists(args.prompts_dir):
        print(f"❌ Error: Prompts directory '{args.prompts_dir}' not found")
        sys.exit(1)
    
    # Run the testing framework
    asyncio.run(run_prompt_tests(
        prompt_type=args.type,
        model=args.model,
        prompts_dir=args.prompts_dir,
        output_file=args.output,
        verbose=args.verbose
    ))


if __name__ == "__main__":
    main() 