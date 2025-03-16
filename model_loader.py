"""
Model loading and management for the Cartesia State Space Model (SSM) PoC
"""

import mlx.core as mx
import cartesia_mlx as cmx
import time
import traceback
from huggingface_hub import login
from huggingface_hub import snapshot_download, scan_cache_dir

from config import HF_TOKEN, AVAILABLE_MODELS, MODEL_COMPATIBILITY
from utils import log_event, measure_execution_time

# Initialize Hugging Face authentication if token is available
if HF_TOKEN:
    login(token=HF_TOKEN)
else:
    print("Warning: No Hugging Face token found. Some functionality may be limited.")

# Dictionary to store loaded models
loaded_models = {}

def check_model_in_cache(model_id):
    """Check if model is already in the Hugging Face cache."""
    try:
        cache_info = scan_cache_dir()
        for repo in cache_info.repos:
            if repo.repo_id.lower() == model_id.lower():
                return True
        return False
    except:
        return False  # If there's any error with cache inspection, assume not downloaded

@measure_execution_time
def download_model(model_id):
    """Download a model by ID if not already in cache."""
    if check_model_in_cache(model_id):
        log_event("model_cache_hit", {"model_id": model_id})
        return True
    
    log_event("model_download_start", {"model_id": model_id})
    try:
        snapshot_download(model_id, local_files_only=False)
        log_event("model_download_complete", {"model_id": model_id})
        return True
    except Exception as e:
        error_msg = str(e)
        log_event("model_download_error", {"model_id": model_id, "error": error_msg})
        traceback.print_exc()
        raise

@measure_execution_time
def load_model(model_name):
    """Load a model by name and return it."""
    # Check if model is already loaded
    if model_name in loaded_models:
        log_event("model_already_loaded", {"model_name": model_name})
        return loaded_models[model_name]
    
    # Get model ID from name
    model_id = AVAILABLE_MODELS.get(model_name)
    if not model_id:
        raise ValueError(f"Unknown model: {model_name}")
    
    # Download model if needed
    download_model(model_id)
    
    # Load the model
    log_event("model_load_start", {"model_name": model_name, "model_id": model_id})
    try:
        # Try loading with error handling
        model = cmx.from_pretrained(model_id)
        model.set_dtype(mx.float32)  # For best performance on M2
        
        # Cache the loaded model
        loaded_models[model_name] = model
        
        log_event("model_load_success", {"model_name": model_name})
        return model
    except IndexError as e:
        error_msg = str(e)
        log_event("model_load_error", {
            "model_name": model_name,
            "error_type": "IndexError",
            "error": error_msg
        })
        
        # Attempt fallback to a different model if appropriate
        if model_name != "rene":
            log_event("model_load_fallback", {
                "original_model": model_name,
                "fallback_model": "rene"
            })
            return load_model("rene")
        else:
            raise
    except Exception as e:
        error_msg = str(e)
        log_event("model_load_error", {
            "model_name": model_name,
            "error_type": type(e).__name__,
            "error": error_msg
        })
        traceback.print_exc()
        raise

def unload_model(model_name):
    """Unload a model to free resources."""
    if model_name in loaded_models:
        log_event("model_unload", {"model_name": model_name})
        del loaded_models[model_name]
        return True
    return False

def list_loaded_models():
    """Get list of currently loaded models."""
    return list(loaded_models.keys())

def get_model_compatibility(model_name):
    """Check if a model is known to be compatible."""
    return MODEL_COMPATIBILITY.get(model_name, True)  # Default to True if unknown

@measure_execution_time
def generate_text(model, prompt, max_tokens=200, temperature=0.85, top_p=0.99):
    """Generate text using the specified model."""
    log_event("generation_start", {
        "prompt_length": len(prompt),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p
    })
    
    full_output = prompt
    generated_text = ""
    
    try:
        for text in model.generate(
            prompt,
            max_tokens=max_tokens,
            eval_every_n=1,
            verbose=False,
            top_p=top_p,
            temperature=temperature,
        ):
            generated_text += text
            full_output += text
            yield text
        
        log_event("generation_complete", {
            "generated_length": len(generated_text)
        })
        
    except Exception as e:
        error_msg = str(e)
        log_event("generation_error", {"error": error_msg})
        traceback.print_exc()
        yield f"\n\nError during generation: {error_msg}"
