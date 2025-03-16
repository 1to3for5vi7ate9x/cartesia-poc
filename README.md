# Cartesia SSM Edge Technology PoC

This repository contains the implementation of the Proof of Concept (PoC) for evaluating Cartesia's State Space Model (SSM) technology in distributed deployment scenarios.

## Overview

The PoC demonstrates how Cartesia's SSM technology operates across a distributed architecture that includes:

1. Edge device processing (on-device inference)
2. Data center processing (simulating future cell tower deployments)
3. Hybrid intelligent routing between processing locations

## Key Components

- **Server**: Web interface for interacting with models and running tests
- **Model Management**: Loading and running various Cartesia models
- **Hybrid Router**: Intelligent decision-making for optimal processing location
- **Test Framework**: Comprehensive testing suite for real-world performance evaluation

## Project Structure

```
cartesia-poc/
├── config.py            # Configuration settings and constants
├── model_loader.py      # Model loading and management logic
├── server.py            # Flask server implementation
├── hybrid_router.py     # Intelligent processing selection logic
├── test_framework.py    # Testing framework for real-world tests 
├── utils.py             # Shared utility functions
├── main.py              # Main entry point CLI
├── requirements.txt     # Project dependencies
├── .env                 # Environment variables (create from .env.example)
└── templates/           # HTML templates for the web interface
    └── index.html       # Main web interface template
```

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv cartesia-env
   source cartesia-env/bin/activate  # On Windows: cartesia-env\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your Hugging Face token
   ```

## Environment Configuration

The application uses environment variables for configuration. Create a `.env` file based on the provided `.env.example`:

```
# Hugging Face API token - replace with your own token
HF_TOKEN=your_huggingface_token_here

# Server configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8080

# Default model to preload
DEFAULT_MODEL=rene
```

You'll need a Hugging Face token with read access to download models from the Hugging Face Hub.

## Usage

### Running the Web Server

```bash
# Run with HTTP (default)
python main.py server --port 8080 --preload rene

# Run with HTTPS (self-signed certificate)
python main.py server --https --port 8443 --preload rene

# Run with HTTPS using custom certificates
python main.py server --https --cert /path/to/cert.pem --key /path/to/key.pem --port 8443
```

This starts the web server on the specified port and preloads the 'rene' model. Using HTTPS makes it easier to share with others for testing, as the server will be accessible at https://your-ip-address:port.

### Running Tests

```bash
# Run voice processing tests with the simple command set
python main.py test --test-type voice --command-set simple --model rene

# Run context retention tests
python main.py test --test-type context --model rene

# Run extended usage tests
python main.py test --test-type extended --duration 3600 --interval 60 --model rene

# Run all test types
python main.py test --test-type all --model rene
```

### Evaluating Hybrid Routing

```bash
python main.py evaluate-routing
```

This runs an evaluation of the hybrid routing logic with a set of sample commands.

## Web Interface

The web interface provides:

1. **Text Generation**: Interactive testing of Cartesia models
2. **Testing Framework**: Interface to run standardized tests
3. **System Information**: Details about the current system state

Access the web interface at http://localhost:8080 when the server is running.

## Performance Metrics

The PoC tracks the following key performance metrics:

- **Latency**: Processing time for commands in both on-device and server modes
- **Accuracy**: Word error rate and command success rate
- **Resource Utilization**: CPU, memory, and battery impact
- **Network Impact**: Data transmission requirements
- **Scalability**: Performance under various loads

## Test Scenarios

1. **On-Device Edge Intelligence**: Performance of on-device processing
2. **Data Center Processing**: Performance when using server-side processing
3. **Intelligent Hybrid Processing**: Effectiveness of processing location selection
4. **Real-World Environment Testing**: Performance in various real-world conditions

## Security Notes

When using HTTPS:

1. Self-signed certificates will cause a browser warning. Users can click "Advanced" and then "Proceed anyway" to access the site.
2. For production use, you should obtain a proper SSL certificate from a certificate authority.
3. Running on `0.0.0.0` makes the server accessible to anyone on your network - be aware of what resources you're exposing.

## Required Packages

Make sure to install additional dependencies for HTTPS support:

```bash
pip install python-dotenv pyopenssl
```

## License

This software is provided for evaluation purposes only. All rights reserved.
