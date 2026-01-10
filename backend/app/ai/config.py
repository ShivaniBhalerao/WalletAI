"""
Configuration for AI/LangGraph components

Manages API keys, model settings, and AI-specific configuration
"""

import logging
import os

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIConfig:
    """
    Configuration class for AI/LangGraph components
    
    Manages Gemini API keys, model settings, and generation parameters
    """
    
    # Gemini API Configuration
    GOOGLE_API_KEY: str | None = settings.GOOGLE_API_KEY
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.5
    GEMINI_MAX_TOKENS: int = 4096
    
    # Model Settings
    # Using gemini-2.5-flash for fast responses, can switch to gemini-1.5-pro for better quality
    MODEL_NAME: str = settings.GEMINI_MODEL
    
    # Generation Settings
    TEMPERATURE: float = settings.GEMINI_TEMPERATURE
    MAX_OUTPUT_TOKENS: int = settings.GEMINI_MAX_TOKENS
    TOP_P: float = 0.95  # Default for Gemini
    TOP_K: int = 40  # Default for Gemini
    
    # Agent Settings
    MAX_CONVERSATION_HISTORY: int = 10  # Keep last 10 messages for context
    ENABLE_CLARIFICATION: bool = False #True  # Enable clarifying questions
    
    @classmethod
    def validate_config(cls) -> bool:
        """
        Validate that required configuration is present
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not cls.GOOGLE_API_KEY:
            logger.error(
                "GOOGLE_API_KEY not set. Please set it as an environment variable. "
                "AI features will not be available."
            )
            return False
        
        logger.info(f"AI Config validated: model={cls.MODEL_NAME}, temperature={cls.TEMPERATURE}")
        return True
    
    @classmethod
    def get_model_kwargs(cls) -> dict:
        """
        Get model initialization kwargs
        
        Returns:
            Dictionary of model configuration parameters
        """
        return {
            "model": cls.MODEL_NAME,
            "temperature": cls.TEMPERATURE,
            "max_output_tokens": cls.MAX_OUTPUT_TOKENS,
            "top_p": cls.TOP_P,
            "top_k": cls.TOP_K,
        }


# Check configuration on module load
if AIConfig.GOOGLE_API_KEY:
    logger.info("AI configuration loaded successfully")
else:
    logger.warning("AI configuration incomplete: GOOGLE_API_KEY not set")

