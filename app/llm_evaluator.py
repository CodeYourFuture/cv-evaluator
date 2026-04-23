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
from pydantic import BaseModel, ValidationError
from typing import Any, Dict, Type

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

        # Log the start of the evaluation with relevant configuration details
        logger.info(
            "Starting AI evaluation: model=%s max_output_tokens=%s reasoning_effort=%s",
            self.model,
            self.max_output_tokens,
            self.reasoning
        )

        try:
            # Call create() instead of parse() to have access to the raw response
            response = await self.client.responses.create(
                model=self.model,
                input=messages,
                text={"format": {
                    "type": "json_schema",
                    "strict": True,
                    "name": "CvEvaluation",
                    "schema": self._strict_schema(CvEvaluation.model_json_schema()),
                }},
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

        # Check if output_text is available in the response
        if not hasattr(response, "output_text"):
            logger.error("AI evaluation failed: No output_text in response.")
            raise ValueError("AI evaluation failed: No output_text in response.")

        # Log the raw output before attempting to parse
        raw_output = response.output_text
        logger.info("Raw model output: %s", raw_output)

        # Attempt to parse the raw output into the CvEvaluation model
        try:
            result = CvEvaluation.model_validate_json(raw_output)
        except ValidationError as e:
            logger.error("Failed to parse model output: %s\nRaw output: %s", str(e), raw_output)
            raise
        
        # Return the parsed evaluation result
        return result

    def _strict_schema(self, schema: dict) -> dict:
        """
        Get the JSON schema for the response format.
        OpenAI requires some modifications to the schema.
        When using the parse() method with text_format, this
        is done automatically. However, if we specify the schema
        manually, we need to make these adjustments ourselves.
        """
        if schema.get("type") == "object":
            schema["additionalProperties"] = False
            if "properties" in schema:
                schema["required"] = list(schema["properties"].keys())
        for value in schema.get("properties", {}).values():
            self._strict_schema(value)
        for value in schema.get("$defs", {}).values():
            self._strict_schema(value)
        return schema
