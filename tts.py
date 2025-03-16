"""
Text-to-Speech (TTS) integration for the Cartesia State Space Model (SSM) PoC

This module handles interaction with the Cartesia TTS API.
"""

import os
import json
import datetime
import traceback

# Define log_event here in case utils.py is not available
def log_event(event_type, data=None):
    """Log an event with associated data"""
    try:
        from utils import log_event as utils_log_event
        return utils_log_event(event_type, data)
    except ImportError:
        # Fallback implementation if utils.log_event is not available
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"cartesia_tts_{datetime.datetime.now().strftime('%Y%m%d')}.log")
        
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event_type": event_type,
            "data": data or {}
        }
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Warning: Failed to write to log file: {str(e)}")
            print(f"Log event: {event_type} - {data}")

class CartesiaTTS:
    """Class to handle interaction with the Cartesia TTS API"""
    
    def __init__(self, api_key=None):
        """Initialize with API key"""
        self.api_key = api_key or os.environ.get("CARTESIA_API_KEY")
        if not self.api_key:
            raise ValueError("CARTESIA_API_KEY is not set in environment variables")
        
        self.base_url = "https://api.cartesia.ai"
        self.client = None
        self.available_voices = None
        
        # Initialize the Cartesia client
        try:
            from cartesia import Cartesia
            self.client = Cartesia(api_key=self.api_key)
        except ImportError:
            raise ImportError("The cartesia Python module is not installed. Install with: pip install cartesia")
    
    def get_voices(self, force_refresh=False):
        """Get available voice options from the API"""
        if self.available_voices is not None and not force_refresh:
            return self.available_voices
        
        try:
            log_event("tts_get_voices_start")
            
            # Get voices from the Cartesia API
            voice_objects = self.client.voices.list()
            
            # Convert to a consistent format
            self.available_voices = []
            for voice in voice_objects:
                voice_data = {
                    "voice_id": voice.id,
                    "name": voice.name,
                    "language": getattr(voice, 'language', 'en'),
                    "gender": getattr(voice, 'gender', None),
                    "preview_url": getattr(voice, 'preview_url', None),
                    "description": getattr(voice, 'description', None)
                }
                self.available_voices.append(voice_data)
            
            log_event("tts_get_voices_complete", {"voice_count": len(self.available_voices)})
            return self.available_voices
            
        except Exception as e:
            log_event("tts_get_voices_error", {"error": str(e)})
            traceback.print_exc()
            raise
    
    def generate_audio(self, text, voice_id, model_id="sonic-2", output_format=None):
        """
        Generate audio from text using the Cartesia TTS API
        
        Args:
            text: The text to convert to speech
            voice_id: The ID of the voice to use
            model_id: The ID of the TTS model (default: sonic-2)
            output_format: Dictionary with audio format parameters
            
        Returns:
            Audio data in bytes
        """
        if not text:
            raise ValueError("Text cannot be empty")
        
        if not voice_id:
            raise ValueError("Voice ID cannot be empty")
        
        # Default output format if not specified
        if not output_format:
            output_format = {
                "container": "wav",
                "encoding": "pcm_f32le",
                "sample_rate": 44100,
            }
        
        log_event("tts_generate_start", {
            "text_length": len(text),
            "voice_id": voice_id,
            "model_id": model_id
        })
        
        try:
            # Generate audio using the Cartesia API
            data = self.client.tts.bytes(
                model_id=model_id,
                transcript=text,
                voice_id=voice_id,
                output_format=output_format,
            )
            
            log_event("tts_generate_complete", {
                "data_size_bytes": len(data),
                "output_format": output_format
            })
            
            return data
            
        except Exception as e:
            log_event("tts_generate_error", {"error": str(e)})
            traceback.print_exc()
            raise

# Helper function to initialize TTS client
def get_tts_client():
    """Get an initialized TTS client"""
    try:
        return CartesiaTTS()
    except (ValueError, ImportError) as e:
        log_event("tts_client_init_error", {"error": str(e)})
        return None

# Check if TTS is available
def is_tts_available():
    """Check if TTS functionality is available"""
    try:
        # Check for API key
        api_key = os.environ.get("CARTESIA_API_KEY")
        if not api_key or api_key == "":
            return False
            
        # Check if we can import the cartesia module
        try:
            from cartesia import Cartesia
            return True
        except ImportError:
            return False
    except Exception as e:
        print(f"Error checking TTS availability: {e}")
        return False