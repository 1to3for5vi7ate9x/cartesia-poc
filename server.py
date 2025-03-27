"""
Flask server implementation for the Cartesia State Space Model (SSM) PoC
"""
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS # Import CORS
import io
import os
import socket
import traceback
import datetime
import os
from flask import Flask, request, jsonify, render_template

from config import SERVER_CONFIG, PERFORMANCE_TARGETS
from model_loader import load_model, get_model_compatibility, generate_text
# Updated import for hybrid router
from hybrid_router import ProcessingLocation, select_processing_location
from utils import log_event, get_system_info, get_network_info, get_device_resource_state

# Initialize Flask app
app = Flask(__name__, template_folder='templates')
CORS(app) # Enable CORS for all routes

@app.route('/')
def home():
    """Render the web interface"""
    from config import AVAILABLE_MODELS
    return render_template("index.html", models=AVAILABLE_MODELS)

@app.route('/check_model', methods=['POST'])
def check_model():
    """Check if a model is compatible"""
    data = request.json
    model_name = data.get('model', 'rene')
    
    compatible = get_model_compatibility(model_name)
    
    return jsonify({
        'compatible': compatible,
        'message': f"Model {model_name} {'is' if compatible else 'may not be'} compatible with current system"
    })

@app.route('/system_info', methods=['GET'])
def system_info():
    """Get system and status information"""
    from model_loader import list_loaded_models
    
    info = {
        'system': get_system_info(),
        'network': get_network_info(),
        'resources': get_device_resource_state(),
        'loaded_models': list_loaded_models(),
        'performance_targets': PERFORMANCE_TARGETS
    }
    
    return jsonify(info)

@app.route('/api/process-request', methods=['POST'])
def process_request():
    """Handle requests from the PWA"""
    data = request.json
    query = data.get('query', '')
    client_metrics = data.get('client_metrics', None) # Extract client metrics
    
    if not query:
        log_event("pwa_request_error", {"error": "No query provided"})
        return jsonify({'error': 'No query provided'}), 400
        
    log_event("pwa_request_received", {
        "query": query,
        "has_client_metrics": client_metrics is not None
    })

    # --- Hybrid Routing Logic ---
    # Determine the ideal processing location
    # Note: For now, we still process on the server regardless of the decision.
    #       We just report the decision back to the client.
    try:
        # Pass client_metrics to the routing function
        ideal_location, decision_meta = select_processing_location(
            query,
            client_metrics=client_metrics
        )
        log_event("pwa_routing_decision", decision_meta)
    except Exception as e:
        log_event("pwa_routing_error", {"error": str(e)})
        traceback.print_exc()
        # Default to server if routing fails
        ideal_location = ProcessingLocation.SERVER
        decision_meta = {
            "decision": ProcessingLocation.SERVER.value,
            "reason": f"Error during routing decision: {str(e)}",
            "decision_time_ms": 0
        }
    # --- End Hybrid Routing Logic ---

    # Simulate processing delay (replace with actual processing later)
    import time
    time.sleep(0.5)
    
    # Placeholder response - include routing decision
    response_text = f"Server received: '{query}'. Ideal location: {ideal_location.value}. (Reason: {decision_meta.get('reason', 'N/A')})"
    
    log_event("pwa_response_sent", {
        "response_length": len(response_text),
        "ideal_location": ideal_location.value,
        "actual_location": ProcessingLocation.SERVER.value # Hardcoded for now
    })
    
    return jsonify({
        'result': response_text,
        'ideal_processing_location': ideal_location.value,
        'actual_processing_location': ProcessingLocation.SERVER.value, # Hardcoded for now
        'routing_metadata': decision_meta
    })

@app.route('/generate', methods=['POST'])
def generate():
    """Generate text from a prompt using the specified model"""
    data = request.json
    model_name = data.get('model', 'rene')
    prompt = data.get('prompt', 'Rene Descartes was')
    max_tokens = int(data.get('max_tokens', 200))
    temperature = float(data.get('temperature', 0.85))
    top_p = float(data.get('top_p', 0.99))
    processing_location = data.get('processing_location', 'automatic')
    
    try:
        # Log request
        log_event("generate_request", {
            "model_name": model_name,
            "prompt_length": len(prompt),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "processing_location": processing_location
        })
        
        # Determine processing location if set to automatic
        if processing_location == 'automatic':
            proc_location, decision_meta = select_processing_location(prompt)
            log_event("processing_decision", decision_meta)
        else:
            try:
                proc_location = ProcessingLocation(processing_location)
            except ValueError:
                proc_location = ProcessingLocation.SERVER
        
        # For PoC, we're always using server-side processing in this endpoint
        # In a real implementation, we would route to on-device processing if selected
        
        # Load the model
        model = load_model(model_name)
        
        # Set up streaming response
        def generate_stream():
            try:
                for text in generate_text(
                    model,
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p
                ):
                    yield text
            except Exception as e:
                error_msg = str(e)
                log_event("generation_error", {"error": error_msg})
                traceback.print_exc()
                yield f"\n\nError during generation: {error_msg}"
        
        return generate_stream(), {'Content-Type': 'text/plain'}
    
    except Exception as e:
        error_msg = str(e)
        log_event("generate_route_error", {"error": error_msg})
        traceback.print_exc()
        
        # Add context to error message
        if "index out of range" in error_msg and model_name == "llamba-1b":
            error_msg += " - This model may be incompatible with the current version of cartesia_mlx. Try using the 'rene' model instead."
        
        return jsonify({'error': error_msg}), 500

@app.route('/run_test', methods=['POST'])
def run_test():
    """Run a test using the test framework"""
    data = request.json
    test_type = data.get('test_type', 'voice_processing')
    test_params = data.get('test_params', {})
    
    try:
        # Import TestRunner here to avoid circular imports
        from test_framework import TestRunner, TestType, TestEnvironment
        from model_loader import load_model, generate_text
        
        # Initialize test runner
        test_runner = TestRunner(load_model, generate_text)
        
        # Create test session
        environment = test_params.get('environment', 'laboratory')
        try:
            env = TestEnvironment(environment)
        except ValueError:
            env = TestEnvironment.LABORATORY
        
        session_name = test_params.get('session_name', f"API_Test_{test_type}")
        test_runner.create_session(session_name=session_name, environment=env)
        
        # Queue appropriate test based on type
        if test_type == 'voice_processing':
            command_set = test_params.get('command_set', 'simple')
            model_name = test_params.get('model_name', 'rene')
            test_runner.queue_voice_processing_test(command_set, model_name)
        
        elif test_type == 'context_retention':
            context_set_idx = int(test_params.get('context_set_idx', 0))
            model_name = test_params.get('model_name', 'rene')
            test_runner.queue_context_retention_test(context_set_idx, model_name)
        
        elif test_type == 'extended_usage':
            duration_seconds = int(test_params.get('duration_seconds', 600))  # Default to 10 minutes
            command_interval = int(test_params.get('command_interval_seconds', 60))
            model_name = test_params.get('model_name', 'rene')
            test_runner.queue_extended_usage_test(duration_seconds, command_interval, "mixed", model_name)
        
        else:
            return jsonify({'error': f"Unsupported test type: {test_type}"}), 400
        
        # Run tests in a background thread to avoid blocking the response
        import threading
        
        def run_tests_async():
            test_session = test_runner.run_tests()
            log_event("async_test_completed", {
                "session_id": test_session.session_id if test_session else None
            })
        
        thread = threading.Thread(target=run_tests_async)
        thread.start()
        
        return jsonify({
            'status': 'Test started',
            'session_id': test_runner.current_session.session_id,
            'test_type': test_type
        })
    
    except Exception as e:
        error_msg = str(e)
        log_event("run_test_error", {"error": error_msg})
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500

# IMPROVED TTS ROUTES
@app.route('/tts/available', methods=['GET'])
def tts_check_available():
    """Check if TTS functionality is available with improved error reporting"""
    try:
        from tts import is_tts_available
        available = is_tts_available()
        
        if available:
            return jsonify({
                'available': True,
                'message': 'TTS service is available'
            })
        else:
            # Check environment for API key
            api_key = os.environ.get("CARTESIA_API_KEY")
            if not api_key:
                error_msg = "TTS API key (CARTESIA_API_KEY) not found in environment"
            else:
                error_msg = "TTS initialization failed. Check server logs for details."
            
            return jsonify({
                'available': False,
                'error': error_msg
            }), 503
    except Exception as e:
        log_event("tts_available_route_error", {"error": str(e)})
        return jsonify({
            'available': False,
            'error': f'Error checking TTS availability: {str(e)}'
        }), 500

@app.route('/tts/voices', methods=['GET'])
def tts_get_voices():
    """Get available TTS voices with improved error handling"""
    try:
        from tts import get_tts_client
        tts_client = get_tts_client()
        
        if not tts_client:
            return jsonify({
                'error': 'TTS client initialization failed. Check server logs for details.'
            }), 503
        
        try:
            voices = tts_client.get_voices(force_refresh=True)  # Force refresh to ensure latest data
            
            # Group voices by language for better UI organization
            voices_by_language = {}
            for voice in voices:
                lang = voice.get('language', 'unknown')
                if lang not in voices_by_language:
                    voices_by_language[lang] = []
                voices_by_language[lang].append(voice)
            
            return jsonify({
                'voices': voices,
                'voices_by_language': voices_by_language,
                'count': len(voices)
            })
        except Exception as e:
            log_event("tts_voices_error", {"error": str(e)})
            return jsonify({
                'error': f'Failed to get voices: {str(e)}'
            }), 500
    except ImportError as e:
        return jsonify({
            'error': f'TTS module not available: {str(e)}'
        }), 503

@app.route('/tts/generate', methods=['POST'])
def tts_generate():
    """Generate TTS audio from text with robust error handling"""
    try:
        from tts import get_tts_client, is_tts_available
        
        # First check if TTS is available
        if not is_tts_available():
            return jsonify({
                'error': 'TTS service is not available. Check server logs for details.'
            }), 503
        
        tts_client = get_tts_client()
        if not tts_client:
            return jsonify({
                'error': 'Failed to initialize TTS client. Check server logs for details.'
            }), 503
        
        # Get request parameters
        data = request.json
        text = data.get('text', '')
        voice_id = data.get('voice_id', '')
        model_id = data.get('model_id', 'sonic-2')
        
        # Validate input
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        if not voice_id:
            return jsonify({'error': 'Voice ID is required'}), 400
        
        try:
            # Define output format
            output_format = {
                "container": "wav",
                "encoding": "pcm_f32le",
                "sample_rate": 44100,
            }
            
            # Generate audio
            log_event("tts_generate_request", {
                "text_length": len(text),
                "voice_id": voice_id,
                "model_id": model_id
            })
            
            audio_data = tts_client.generate_audio(text, voice_id, model_id, output_format)
            
            # Create an in-memory file
            audio_file = io.BytesIO(audio_data)
            audio_file.seek(0)
            
            log_event("tts_generate_success", {
                "audio_size_bytes": len(audio_data)
            })
            
            # Return the audio file
            return send_file(
                audio_file,
                mimetype='audio/wav',
                as_attachment=True,
                download_name='tts_output.wav'
            )
        except Exception as e:
            log_event("tts_generate_error", {"error": str(e)})
            return jsonify({
                'error': f'Failed to generate audio: {str(e)}'
            }), 500
    except ImportError as e:
        return jsonify({
            'error': f'TTS module not available: {str(e)}'
        }), 503

@app.route('/tts/test', methods=['GET'])
def tts_test():
    """Test endpoint to verify TTS functionality"""
    try:
        from tts import test_tts
        
        results = {
            "test_ran": True,
            "test_time": datetime.datetime.now().isoformat()
        }
        
        try:
            test_success = test_tts()
            results["success"] = test_success
            
            if test_success:
                results["message"] = "TTS functionality verified successfully"
                return jsonify(results)
            else:
                results["error"] = "TTS test failed. Check server logs for details."
                return jsonify(results), 500
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            return jsonify(results), 500
    except ImportError as e:
        return jsonify({
            "test_ran": False,
            "error": f"Failed to import TTS module: {str(e)}"
        }), 503

def run_server(host=None, port=None, preload=None, ssl_context=None):
    """Run the Flask server"""
    host = host or SERVER_CONFIG['default_host']
    port = port or SERVER_CONFIG['default_port']
    
    # Preload model if specified
    if preload:
        try:
            print(f"Preloading model: {preload}")
            load_model(preload)
            print(f"Successfully preloaded {preload}")
        except Exception as e:
            print(f"Failed to preload {preload}: {str(e)}")
            if preload != "rene":
                print("Trying to preload 'rene' instead...")
                try:
                    load_model("rene")
                    print("Successfully preloaded 'rene'")
                except Exception as e2:
                    print(f"Failed to preload 'rene': {str(e2)}")
    
    # Print the URL to access the web interface
    protocol = "https" if ssl_context else "http"
    try:
        ip = socket.gethostbyname(socket.gethostname())
        print(f"\nWeb interface will be available at:")
        print(f"Local: {protocol}://localhost:{port}")
        print(f"Network: {protocol}://{ip}:{port}")
    except:
        print(f"\nWeb interface will be available at: {protocol}://localhost:{port}")
    
    # Run the web server
    app.run(host=host, port=port, debug=False, threaded=True, ssl_context=ssl_context)

def create_self_signed_cert(cert_dir='certs'):
    """Create a self-signed certificate for HTTPS support"""
    from OpenSSL import crypto
    
    # Create cert directory if it doesn't exist
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)
    
    cert_file = os.path.join(cert_dir, 'cert.pem')
    key_file = os.path.join(cert_dir, 'key.pem')
    
    # Check if the certificate already exists
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"Using existing certificates from {cert_dir}")
        return cert_file, key_file
    
    # Create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)
    
    # Create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "California"
    cert.get_subject().L = "San Francisco"
    cert.get_subject().O = "Cartesia PoC"
    cert.get_subject().OU = "SSM Edge Technology"
    cert.get_subject().CN = socket.gethostname()
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365*24*60*60)  # 1 year
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')
    
    # Write certificate and key to files
    with open(cert_file, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    with open(key_file, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    
    print(f"Created self-signed certificate in {cert_dir}")
    return cert_file, key_file

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Run Cartesia models as a web service")
    parser.add_argument("--host", type=str, default=SERVER_CONFIG['default_host'], 
                        help="Host address to run the server on")
    parser.add_argument("--port", type=int, default=SERVER_CONFIG['default_port'], 
                        help="Port to run the server on")
    parser.add_argument("--preload", type=str, default="rene",
                        help="Preload a specific model on startup")
    parser.add_argument("--https", action="store_true",
                        help="Enable HTTPS with a self-signed certificate")
    parser.add_argument("--cert", type=str, 
                        help="Path to SSL certificate file (for HTTPS)")
    parser.add_argument("--key", type=str, 
                        help="Path to SSL key file (for HTTPS)")
    
    args = parser.parse_args()
    
    # Setup SSL context if HTTPS is enabled
    ssl_context = None
    if args.https:
        try:
            if args.cert and args.key:
                # Use provided certificate and key
                ssl_context = (args.cert, args.key)
                print(f"Using provided SSL certificate: {args.cert}")
            else:
                # Generate self-signed certificate
                try:
                    from OpenSSL import crypto
                    cert_file, key_file = create_self_signed_cert()
                    ssl_context = (cert_file, key_file)
                except ImportError:
                    print("Error: PyOpenSSL is required for HTTPS support.")
                    print("Please install it with: pip install pyopenssl")
                    sys.exit(1)
        except Exception as e:
            print(f"Error setting up HTTPS: {str(e)}")
            print("Falling back to HTTP")
            ssl_context = None
    
    run_server(args.host, args.port, args.preload, ssl_context)