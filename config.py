"""
Configuration settings for the Cartesia State Space Model (SSM) PoC
"""

import os
import dotenv

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Hugging Face token for accessing models
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# List of available models
AVAILABLE_MODELS = {
    "rene": "cartesia-ai/Rene-v0.1-1.3b-4bit-mlx",
    "llamba-1b": "cartesia-ai/Llamba-1B",
    "llamba-3b": "cartesia-ai/Llamba-3B-4bit-mlx",
    "llamba-8b": "cartesia-ai/Llamba-8B"
}

# Model compatibility ratings based on testing
MODEL_COMPATIBILITY = {
    "rene": True,        # Known to work well
    "llamba-1b": False,  # Known issues with current version
    "llamba-3b": True,   # Assumed compatible
    "llamba-8b": True    # Assumed compatible
}

# Default generation parameters
DEFAULT_GENERATION_PARAMS = {
    "max_tokens": 200,
    "temperature": 0.85,
    "top_p": 0.99
}

# Performance targets (based on PoC requirements)
PERFORMANCE_TARGETS = {
    "local_latency_ms": 100,           # Target <100ms for on-device processing
    "network_latency_ms": 50,          # Target <50ms for network transmission
    "server_processing_ms": 50,        # Target <50ms for server processing
    "total_roundtrip_ms": 200,         # Target <200ms for total processing
    "word_error_rate_optimal": 5,      # Target <5% in optimal conditions
    "word_error_rate_challenging": 15, # Target <15% in challenging conditions
    "command_success_rate": 95,        # Target >95% for standard commands
    "context_retention": 90,           # Target >90% for contextual follow-ups
    "battery_impact_percent": 3,       # Target <3% additional drain per hour
    "max_concurrent_users": 50         # Target 50+ per server node
}

# Server configuration
SERVER_CONFIG = {
    "default_host": os.environ.get("SERVER_HOST", "0.0.0.0"),
    "default_port": int(os.environ.get("SERVER_PORT", 8080)),
}

# Test configuration
TEST_CONFIG = {
    "default_test_duration_seconds": 3600,  # 1 hour default test duration
    "standard_commands_count": 25,          # Number of commands in standard test set
    "noise_levels_db": {
        "quiet": 30,     # <30dB ambient
        "moderate": 60,  # 50-60dB ambient
        "loud": 80       # 70-80dB ambient
    },
    "speaker_distances_cm": {
        "close": 30,     # 30cm from device
        "medium": 100,   # 1m from device
        "far": 300       # 3m from device
    }
}
