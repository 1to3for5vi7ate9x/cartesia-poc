"""
Flask server implementation for the Cartesia State Space Model (SSM) PoC
"""

import socket
import traceback
import os
from flask import Flask, request, jsonify, render_template

from config import SERVER_CONFIG, PERFORMANCE_TARGETS
from model_loader import load_model, get_model_compatibility, generate_text
from hybrid_router import ProcessingLocation, select_processing_location
from utils import log_event, get_system_info, get_network_info, get_device_resource_state

# Initialize Flask app
app = Flask(__name__, template_folder='templates')

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
