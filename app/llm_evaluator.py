"""
LLM Evaluator module for CV evaluation using OpenAI.

This module provides the LlmEvaluator class that uses OpenAI's structured
output parsing to evaluate CVs against a set of predefined rules.
"""

import os
from pathlib import Path
from typing import Optional
import logging

import yaml
from openai import AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RuleResult(BaseModel):
    """Result of evaluating a single CV rule."""
    passed: bool
    details: str


class CvEvaluation(BaseModel):
    """Complete CV evaluation result with all rule checks."""
    passed: bool
    spelling_grammar: RuleResult
    two_pages: RuleResult
    contact_details: RuleResult
    dates: RuleResult
    pronouns: RuleResult
    tense: RuleResult
    buzzwords: RuleResult
    outcomes: RuleResult
    project: RuleResult
    experience: RuleResult
    debug_info: Optional[str] = None


class LlmEvaluator:
    """
    Evaluator class that uses OpenAI to assess CVs.
    
    Uses OpenAI's responses.parse() method with structured output
    to ensure consistent evaluation results.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the LLM evaluator with configuration.
        
        Args:
            config_path: Path to the YAML configuration file.
                        Defaults to llm_evaluator.yml in the same directory.
        """
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent / "llm_evaluator.yml"
        
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # Initialize async OpenAI client
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        # Store configuration for parse calls
        self.model = config.get("model", "gpt-4o")
        self.reasoning = config.get("reasoning", "medium")
        self.max_output_tokens = config.get("max_output_tokens", 4096)
        
        # Store message templates
        self.system_message = config.get("system_message", "")
        self.user_message_template = config.get("user_message", "{cv_text}")
    
    async def eval(self, cv_text: str) -> CvEvaluation:
        """
        Evaluate a CV using OpenAI.
        
        Args:
            cv_text: The text content of the CV to evaluate.
            
        Returns:
            CvEvaluation: Structured evaluation result.
        """
        # Construct the user message with the CV text
        user_message = self.user_message_template.format(cv_text=cv_text)
        
        # Build the messages for the API call
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_message}
        ]

        # Call the OpenAI API with structured output parsing
        try:
            response = await self.client.responses.parse(
                model=self.model,
                input=messages,
                text_format=CvEvaluation,
                max_output_tokens=self.max_output_tokens,
                reasoning={"effort": self.reasoning}
            )
        except Exception as e:
            logger.error("Exception during AI evaluation: %s", str(e))
            raise

        if response is None:
            logger.error("AI evaluation failed: No response received.")
            raise ValueError("AI evaluation failed: No response received.")

        usage = getattr(response, "usage", None)
        logger.info(
            "AI evaluation completed: input_tokens=%s output_tokens=%s total_tokens=%s error=%s",
            getattr(usage, "input_tokens", None),
            getattr(usage, "output_tokens", None),
            getattr(usage, "total_tokens", None),
            getattr(response, "error", None),
        )

        if response.output_parsed is None:
            logger.error("AI evaluation failed: Response could not be parsed.")
            raise ValueError("AI evaluation failed: Response could not be parsed.")
        
        # Return the parsed evaluation result
        return response.output_parsed
