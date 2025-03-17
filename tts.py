"""
Improved Text-to-Speech (TTS) implementation for the Cartesia SSM PoC

This file contains enhanced versions of the TTS functionality to ensure
proper integration with the Cartesia API.
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
            # Test connection by listing voices
            _ = self.client.voices.list()
        except ImportError as e:
            print(f"CartesiaTTS init error: {e}")
            raise ImportError(f"The cartesia Python module is not installed or has missing dependencies: {str(e)}")
        except Exception as e:
            print(f"CartesiaTTS init error: {e}")
            raise Exception(f"Failed to initialize Cartesia client: {str(e)}")
    
    def get_voices(self, force_refresh=False):
        """Get available voice options from the API"""
        if self.available_voices is not None and not force_refresh:
            return self.available_voices
        
        try:
            log_event("tts_get_voices_start")
            print("TTS get_voices: Fetching voices from API")
            
            # Get voices from the Cartesia API
            voice_objects = self.client.voices.list()
            
            # Convert to a consistent format
            self.available_voices = []
            for voice in voice_objects:
                # Check if voice is a dictionary or an object
                if isinstance(voice, dict):
                    voice_data = {
                        "voice_id": voice.get("id"),
                        "name": voice.get("name"),
                        "language": voice.get("language", "en"),
                        "gender": voice.get("gender"),
                        "preview_url": voice.get("preview_url"),
                        "description": voice.get("description")
                    }
                else:
                    # Original object-based approach
                    voice_data = {
                        "voice_id": getattr(voice, "id", None),
                        "name": getattr(voice, "name", None),
                        "language": getattr(voice, "language", "en"),
                        "gender": getattr(voice, "gender", None),
                        "preview_url": getattr(voice, "preview_url", None),
                        "description": getattr(voice, "description", None)
                    }
                
                # Only add voices with valid IDs
                if voice_data["voice_id"]:
                    self.available_voices.append(voice_data)
            
            print(f"TTS get_voices: Found {len(self.available_voices)} voices")
            log_event("tts_get_voices_complete", {"voice_count": len(self.available_voices)})
            return self.available_voices
            
        except Exception as e:
            print(f"TTS get_voices error: {e}")
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
        
        print(f"TTS generate_audio: Generating audio for text of length {len(text)}")
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
            
            print(f"TTS generate_audio: Generated {len(data)} bytes of audio data")
            log_event("tts_generate_complete", {
                "data_size_bytes": len(data),
                "output_format": output_format
            })
            
            return data
            
        except Exception as e:
            print(f"TTS generate_audio error: {e}")
            log_event("tts_generate_error", {"error": str(e)})
            traceback.print_exc()
            raise

# Improved helper function to initialize TTS client
def get_tts_client():
    """Get an initialized TTS client"""
    try:
        print("Initializing TTS client...")
        client = CartesiaTTS()
        print("TTS client initialized successfully")
        return client
    except (ValueError, ImportError, Exception) as e:
        print(f"TTS client init error: {e}")
        log_event("tts_client_init_error", {"error": str(e)})
        return None

# Improved TTS availability check
def is_tts_available():
    """Check if TTS functionality is available with better error reporting"""
    try:
        # Check for API key
        api_key = os.environ.get("CARTESIA_API_KEY")
        if not api_key or api_key == "":
            print("TTS check: API key not found")
            return False
            
        print(f"TTS check: API key found (starts with: {api_key[:4] if len(api_key) > 4 else '****'}...)")
        
        # Check if we can import the cartesia module and its dependencies
        try:
            print("TTS check: Importing cartesia module")
            from cartesia import Cartesia
            
            # Try to initialize client
            print("TTS check: Creating client instance")
            client = Cartesia(api_key=api_key)
            
            # Test with a simple API call
            print("TTS check: Testing API connection")
            voices = client.voices.list()
            print(f"TTS check: API connection successful, found {len(voices)} voices")
            
            return True
            
        except ImportError as e:
            print(f"TTS check: Import error: {e}")
            
            # Check for specific dependency issues
            if "audioop" in str(e) or "pyaudioop" in str(e):
                print("TTS check: Missing audioop/pyaudioop dependencies. Install them with pip install pyaudioop")
            elif "pydub" in str(e):
                print("TTS check: Missing pydub dependency. Install with pip install pydub")
            elif "ffmpeg" in str(e):
                print("TTS check: Missing ffmpeg. Install with brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)")
                
            return False
            
        except Exception as e:
            print(f"TTS check: Error creating client: {e}")
            return False
            
    except Exception as e:
        print(f"TTS check: Unexpected error: {e}")
        return False

# Simple test function to verify TTS functionality
def test_tts():
    """Test TTS functionality and report results"""
    print("Testing TTS functionality...")
    
    if not is_tts_available():
        print("TTS is not available. Check the logs for details.")
        return False
    
    try:
        client = get_tts_client()
        if not client:
            print("Failed to initialize TTS client.")
            return False
        
        voices = client.get_voices()
        print(f"Found {len(voices)} voices.")
        
        if voices:
            print(f"First voice: {voices[0]['name']} (ID: {voices[0]['voice_id']})")
        
        return True
    except Exception as e:
        print(f"TTS test error: {e}")
        return False

# Run test if executed directly
if __name__ == "__main__":
    test_tts()