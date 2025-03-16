#!/usr/bin/env python3
"""
Main entry point for the Cartesia State Space Model (SSM) PoC

This script provides a command-line interface to run different components
of the PoC, including the server, test framework, and hybrid routing tests.
"""

import os
import sys
import argparse
import time

def setup_environment():
    """Ensure all dependencies are available and directories exist"""
    # Create necessary directories
    os.makedirs("test_results", exist_ok=True)
    
    # Check for required modules
    try:
        import mlx.core
        import cartesia_mlx
        import flask
        import pandas
        import psutil
    except ImportError as e:
        print(f"Error: Missing required dependency: {e}")
        print("Please install required dependencies with: pip install -r requirements.txt")
        sys.exit(1)

def run_server(args):
    """Run the web server"""
    from server import run_server
    
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
                    from server import create_self_signed_cert
                    cert_file, key_file = create_self_signed_cert()
                    ssl_context = (cert_file, key_file)
                except ImportError as e:
                    print(f"Error: {str(e)}")
                    print("PyOpenSSL is required for HTTPS support.")
                    print("Please install it with: pip install pyopenssl")
                    sys.exit(1)
        except Exception as e:
            print(f"Error setting up HTTPS: {str(e)}")
            print("Falling back to HTTP")
            ssl_context = None
    
    run_server(args.host, args.port, args.preload, ssl_context)

def run_test(args):
    """Run tests using the test framework"""
    from model_loader import load_model, generate_text
    from test_framework import (
        TestRunner, TestType, TestEnvironment, 
        ProcessingLocation
    )
    
    # Initialize test runner
    test_runner = TestRunner(load_model, generate_text)
    
    # Create session
    try:
        env = TestEnvironment(args.environment)
    except ValueError:
        env = TestEnvironment.LABORATORY
    
    test_runner.create_session(
        session_name=args.session_name,
        environment=env,
        notes=args.notes
    )
    
    # Queue appropriate tests
    if args.test_type == "voice":
        test_runner.queue_voice_processing_test(args.command_set, args.model)
    elif args.test_type == "context":
        test_runner.queue_context_retention_test(int(args.context_set), args.model)
    elif args.test_type == "extended":
        test_runner.queue_extended_usage_test(
            duration_seconds=args.duration,
            command_interval_seconds=args.interval,
            command_set=args.command_set,
            model_name=args.model
        )
    elif args.test_type == "all":
        # Queue all test types
        print("Queuing all test types...")
        test_runner.queue_voice_processing_test("simple", args.model)
        test_runner.queue_voice_processing_test("moderate", args.model)
        test_runner.queue_context_retention_test(0, args.model)
        test_runner.queue_extended_usage_test(
            duration_seconds=300,  # 5 minutes for "all" mode
            command_interval_seconds=30,
            command_set="mixed",
            model_name=args.model
        )
    
    # Run the tests
    print(f"Running {args.test_type} tests...")
    session = test_runner.run_tests(save_results=True, output_dir=args.output_dir)
    
    if session:
        success_rate = session.metrics.get("success_rate", 0) * 100
        print(f"Tests completed with {success_rate:.1f}% success rate")
        print(f"Results saved to {args.output_dir}")
    else:
        print("Tests failed to run properly")

def evaluate_hybrid_routing(args):
    """Evaluate the hybrid routing logic with various inputs"""
    from hybrid_router import (
        select_processing_location, 
        estimate_command_complexity,
        CommandComplexity
    )
    from utils import log_event, get_device_resource_state, estimate_network_quality
    
    print("Evaluating Hybrid Routing Logic")
    print("===============================")
    
    # Get current device state and network conditions
    device_state = get_device_resource_state()
    network_info = estimate_network_quality()
    
    print(f"Current device state: {device_state}")
    print(f"Current network conditions: {network_info}")
    print("\nTesting with various commands:")
    
    # Sample commands of different complexities
    test_commands = [
        # Simple commands
        "What time is it?",
        "Set an alarm for 7 AM",
        # Moderate commands
        "What meetings do I have tomorrow after 2 PM?",
        "How long will it take to drive to the airport?",
        # Complex commands
        "Compare the weather forecast for San Francisco and New York for the next three days",
        "What was the stock performance of Apple compared to Microsoft over the past month?"
    ]
    
    for command in test_commands:
        # Get complexity estimate
        complexity = estimate_command_complexity(command)
        
        # Get routing decision
        location, metadata = select_processing_location(command)
        
        print(f"\nCommand: \"{command}\"")
        print(f"Estimated complexity: {complexity.value}")
        print(f"Selected processing location: {location.value}")
        print(f"Decision reason: {metadata['reason']}")
        print(f"Decision time: {metadata['decision_time_ms']:.2f} ms")
        
        # Log the evaluation
        log_event("hybrid_routing_evaluation", {
            "command": command,
            "complexity": complexity.value,
            "location": location.value,
            "decision_reason": metadata['reason'],
            "decision_time_ms": metadata['decision_time_ms']
        })
        
        # Small delay for readability
        time.sleep(0.5)

def main():
    """Main entry point"""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Cartesia SSM PoC - Test and evaluate State Space Models"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Run the web server")
    server_parser.add_argument("--host", type=str, default="0.0.0.0", 
                            help="Host address to run the server on")
    server_parser.add_argument("--port", type=int, default=8080, 
                            help="Port to run the server on")
    server_parser.add_argument("--preload", type=str, default="rene",
                            help="Preload a specific model on startup")
    server_parser.add_argument("--https", action="store_true",
                            help="Enable HTTPS with a self-signed certificate")
    server_parser.add_argument("--cert", type=str, 
                            help="Path to SSL certificate file (for HTTPS)")
    server_parser.add_argument("--key", type=str, 
                            help="Path to SSL key file (for HTTPS)")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests using the test framework")
    test_parser.add_argument("--test-type", type=str, choices=["voice", "context", "extended", "all"], 
                           default="voice", help="Type of test to run")
    test_parser.add_argument("--model", type=str, default="rene", 
                           help="Model to use for testing")
    test_parser.add_argument("--command-set", type=str, choices=["simple", "moderate", "complex", "mixed"], 
                           default="simple", help="Command set to use for testing")
    test_parser.add_argument("--context-set", type=str, default="0", 
                           help="Context set index to use for context retention tests")
    test_parser.add_argument("--duration", type=int, default=600, 
                           help="Duration in seconds for extended tests")
    test_parser.add_argument("--interval", type=int, default=60, 
                           help="Command interval in seconds for extended tests")
    test_parser.add_argument("--environment", type=str, 
                           choices=["laboratory", "downtown", "residential", "public_space", "indoor"], 
                           default="laboratory", help="Test environment")
    test_parser.add_argument("--session-name", type=str, 
                           help="Custom session name (default: auto-generated)")
    test_parser.add_argument("--notes", type=str, 
                           help="Notes to include with the test session")
    test_parser.add_argument("--output-dir", type=str, default="test_results", 
                           help="Directory to save test results")
    
    # Hybrid router evaluation command
    hybrid_parser = subparsers.add_parser("evaluate-routing", 
                                        help="Evaluate hybrid routing logic")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Ensure environment is set up
    setup_environment()
    
    # Run appropriate command
    if args.command == "server":
        run_server(args)
    elif args.command == "test":
        run_test(args)
    elif args.command == "evaluate-routing":
        evaluate_hybrid_routing(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
