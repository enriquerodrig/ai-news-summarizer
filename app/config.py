"""
Configuration module for AI News Summarizer.

This module instantiates and exports the application configuration,
performing fail-fast validation on import. If required configuration
is missing or invalid, the application will exit with descriptive
error messages.
"""

import sys
from typing import Optional
from pydantic import ValidationError
from app.models.data_models import AppConfig


def load_config() -> Optional[AppConfig]:
    """
    Load and validate application configuration from environment variables.
    
    This function attempts to instantiate the AppConfig model, which reads
    from environment variables. If validation fails, it prints descriptive
    error messages and exits the application.
    
    Returns:
        AppConfig: Validated configuration object
        
    Raises:
        SystemExit: If configuration validation fails
    """
    try:
        config = AppConfig()
        return config
    except ValidationError as e:
        # Format validation errors for user-friendly output
        print("=" * 70, file=sys.stderr)
        print("CONFIGURATION ERROR: Application startup failed", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print("\nThe following configuration issues were detected:\n", file=sys.stderr)
        
        for error in e.errors():
            field = ".".join(str(loc) for loc in error['loc'])
            message = error['msg']
            error_type = error['type']
            
            # Provide helpful context for common errors
            if 'missing' in error_type.lower() or 'required' in message.lower():
                print(f"  ✗ {field.upper()}: Missing required environment variable", file=sys.stderr)
                print(f"    Please set the {field.upper()} environment variable", file=sys.stderr)
            else:
                print(f"  ✗ {field.upper()}: {message}", file=sys.stderr)
            print("", file=sys.stderr)
        
        print("=" * 70, file=sys.stderr)
        print("Configuration Guide:", file=sys.stderr)
        print("  - Set environment variables in your shell or .env file", file=sys.stderr)
        print("  - Required: HUGGINGFACE_TOKEN, MCP_SERVER_URL", file=sys.stderr)
        print("  - Optional: PORT, CACHE_TTL_MINUTES, NEWS_REFRESH_MINUTES, etc.", file=sys.stderr)
        print("  - See .env.example for a complete template", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        
        sys.exit(1)
    except Exception as e:
        # Catch any other unexpected errors during config loading
        print("=" * 70, file=sys.stderr)
        print("UNEXPECTED ERROR: Failed to load configuration", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"\n{type(e).__name__}: {str(e)}\n", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        sys.exit(1)


# Instantiate and export the configuration
# This will validate on import and fail fast if configuration is invalid
config = load_config()


# Export for convenience
__all__ = ['config', 'load_config']
