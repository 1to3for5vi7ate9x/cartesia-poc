"""
Testing Framework for the Cartesia State Space Model (SSM) PoC

This module implements the testing framework for real-world testing scenarios
as described in the PoC test plan.
"""

import os
import time
import json
import datetime
import threading
import uuid
from enum import Enum
import pandas as pd

from utils import (
    get_system_info, get_network_info, get_device_resource_state,
    log_event, get_timestamp, calculate_battery_impact
)
from config import PERFORMANCE_TARGETS, TEST_CONFIG
from hybrid_router import ProcessingLocation, select_processing_location

class TestEnvironment(Enum):
    """Enum for test environment types"""
    DOWNTOWN = "downtown"             # Downtown business district
    RESIDENTIAL = "residential"       # Residential neighborhood
    PUBLIC_SPACE = "public_space"     # Park or plaza
    INDOOR_COMMERCIAL = "indoor"      # Mall or office building
    LABORATORY = "laboratory"         # Controlled laboratory environment
    CUSTOM = "custom"                 # Custom environment

class NoiseLevel(Enum):
    """Enum for ambient noise levels"""
    QUIET = "quiet"                   # <30dB ambient
    MODERATE = "moderate"             # 50-60dB ambient
    LOUD = "loud"                     # 70-80dB ambient
    CUSTOM = "custom"                 # Custom noise level

class SpeakerDistance(Enum):
    """Enum for speaker distance from device"""
    CLOSE = "close"                   # 30cm from device
    MEDIUM = "medium"                 # 1m from device
    FAR = "far"                       # 3m from device
    CUSTOM = "custom"                 # Custom distance

class TestType(Enum):
    """Enum for test types"""
    VOICE_PROCESSING = "voice_processing"       # Basic voice command processing
    CONTEXT_RETENTION = "context_retention"     # Context retention capabilities
    RESOURCE_ADAPTATION = "resource_adaptation" # Adaptation to resource constraints
    ENVIRONMENTAL = "environmental"             # Environmental resilience
    EXTENDED_USAGE = "extended_usage"           # Extended usage over time
    NETWORK_PERFORMANCE = "network_performance" # Network performance impact
    LOAD_TESTING = "load_testing"               # Multiple concurrent requests
    CUSTOM = "custom"                           # Custom test type

class TestResult:
    """Object to store test results"""
    def __init__(self, test_id, test_type, success=None, metrics=None):
        self.test_id = test_id
        self.test_type = test_type
        self.success = success  # True/False/None
        self.metrics = metrics or {}
        self.start_time = get_timestamp()
        self.end_time = None
        self.duration_ms = None
    
    def complete(self, success, additional_metrics=None):
        """Mark test as complete with success/failure and additional metrics"""
        self.end_time = get_timestamp()
        self.success = success
        
        if additional_metrics:
            self.metrics.update(additional_metrics)
        
        # Calculate duration
        start_dt = datetime.datetime.fromisoformat(self.start_time)
        end_dt = datetime.datetime.fromisoformat(self.end_time)
        self.duration_ms = (end_dt - start_dt).total_seconds() * 1000
        self.metrics["duration_ms"] = self.duration_ms
        
        return self
    
    def to_dict(self):
        """Convert TestResult to dictionary"""
        return {
            "test_id": self.test_id,
            "test_type": self.test_type.value if isinstance(self.test_type, Enum) else self.test_type,
            "success": self.success,
            "metrics": self.metrics,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms
        }

class TestSession:
    """Manages a test session with multiple tests"""
    def __init__(self, session_name=None, environment=TestEnvironment.LABORATORY, notes=None):
        self.session_id = str(uuid.uuid4())
        self.session_name = session_name or f"Test_Session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.environment = environment
        self.notes = notes or ""
        self.start_time = get_timestamp()
        self.end_time = None
        self.results = []
        self.metrics = {}
        self.context = self._initialize_context()
    
    def _initialize_context(self):
        """Initialize test session context with system and environment information"""
        context = {
            "system_info": get_system_info(),
            "network_info": get_network_info(),
            "resource_state": get_device_resource_state(),
            "environment": self.environment.value if isinstance(self.environment, Enum) else self.environment,
            "timestamp": self.start_time
        }
        return context
    
    def add_result(self, result):
        """Add a test result to the session"""
        self.results.append(result)
        return self
    
    def complete(self, additional_metrics=None):
        """Mark session as complete with additional metrics"""
        self.end_time = get_timestamp()
        
        # Update final metrics
        if additional_metrics:
            self.metrics.update(additional_metrics)
        
        # Calculate aggregate metrics
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success is True)
        failed_tests = sum(1 for r in self.results if r.success is False)
        
        self.metrics.update({
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0
        })
        
        # Calculate duration
        start_dt = datetime.datetime.fromisoformat(self.start_time)
        end_dt = datetime.datetime.fromisoformat(self.end_time)
        self.metrics["duration_s"] = (end_dt - start_dt).total_seconds()
        
        return self
    
    def to_dict(self):
        """Convert TestSession to dictionary"""
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "environment": self.environment.value if isinstance(self.environment, Enum) else self.environment,
            "notes": self.notes,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "metrics": self.metrics,
            "context": self.context,
            "results": [r.to_dict() for r in self.results]
        }
    
    def save(self, output_dir="test_results"):
        """Save test session results to a file"""
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{output_dir}/{self.session_name}_{self.session_id}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        log_event("test_session_saved", {"filename": filename})
        return filename
    
    def to_dataframe(self):
        """Convert test results to pandas DataFrame for analysis"""
        # Flatten the results for easier analysis
        flattened_results = []
        for result in self.results:
            result_dict = result.to_dict()
            base_data = {
                "test_id": result_dict["test_id"],
                "test_type": result_dict["test_type"],
                "success": result_dict["success"],
                "start_time": result_dict["start_time"],
                "end_time": result_dict["end_time"],
                "duration_ms": result_dict["duration_ms"],
                "session_id": self.session_id,
                "environment": self.environment.value if isinstance(self.environment, Enum) else self.environment,
            }
            
            # Add metrics as separate columns
            for metric_key, metric_value in result_dict["metrics"].items():
                if isinstance(metric_value, (int, float, str, bool)) or metric_value is None:
                    base_data[f"metric_{metric_key}"] = metric_value
            
            flattened_results.append(base_data)
        
        return pd.DataFrame(flattened_results)

# Standard test commands for reproducible testing
STANDARD_TEST_COMMANDS = {
    "simple": [
        "What time is it now?",
        "Set an alarm for 7 AM",
        "What's the weather like?",
        "Call Mom",
        "Send a text to John",
        "Play some music",
        "Turn on the lights",
        "Increase the volume",
        "Stop the timer",
        "What's on my calendar today?"
    ],
    "moderate": [
        "What meetings do I have tomorrow after 2 PM?",
        "What's the weather forecast for this weekend in Chicago?",
        "How long will it take to drive to the airport with current traffic?",
        "Find Italian restaurants near me with at least 4-star ratings",
        "What was the score of the Warriors game last night?",
        "Calculate the tip on a $87.50 bill at 18 percent",
        "What's the exchange rate between US dollars and Euros?",
        "Set a reminder to call the dentist when I get home",
        "How many calories are in a medium apple?",
        "When is the next full moon?"
    ],
    "complex": [
        "Compare the weather forecast for San Francisco and New York for the next three days",
        "What meetings do I have with the marketing team next week and who is attending?",
        "Find flights to Boston for next weekend under $500 with no more than one stop",
        "What was the stock performance of Apple compared to Microsoft over the past month?",
        "Give me a summary of the latest news about renewable energy technology",
        "Create a workout plan for the next week focusing on cardio and upper body strength",
        "What restaurants are available for dinner tonight that serve both vegetarian options and sushi?",
        "Find emails from Sarah about the quarterly report that I received last week",
        "Calculate my total expenses in the transportation category for the past three months",
        "What's the best route to the airport at 5 PM next Friday considering typical traffic patterns?"
    ],
    "contextual": [
        # These need to be used in sequence for testing context retention
        ["What's the weather like in New York?", "How about in Los Angeles?", "Will it rain there tomorrow?"],
        ["Find Italian restaurants near me", "Which ones have outdoor seating?", "What are their hours today?"],
        ["Set up a meeting with the marketing team", "Schedule it for tomorrow at 2 PM", "Add John to the invitation"],
        ["What's on my calendar for next week?", "Move my dentist appointment to Friday", "Remind me about it the day before"],
        ["Show me the latest emails from Sarah", "Reply to the one about the project timeline", "Add Tom to the recipients"]
    ]
}

class TestRunner:
    """Runs standardized tests for the Cartesia SSM PoC"""
    def __init__(self, model_loader, generation_function, processing_mode=ProcessingLocation.AUTOMATIC):
        self.model_loader = model_loader
        self.generation_function = generation_function
        self.processing_mode = processing_mode
        self.current_session = None
        self.test_queue = []
        self.is_running = False
    
    def create_session(self, session_name=None, environment=TestEnvironment.LABORATORY, notes=None):
        """Create a new test session"""
        self.current_session = TestSession(session_name, environment, notes)
        log_event("test_session_created", {
            "session_id": self.current_session.session_id,
            "session_name": self.current_session.session_name,
            "environment": self.current_session.environment.value 
                if isinstance(self.current_session.environment, Enum) else self.current_session.environment
        })
        return self.current_session
    
    def queue_voice_processing_test(self, command_set="simple", model_name="rene"):
        """Queue a voice processing test with standard commands"""
        if command_set not in STANDARD_TEST_COMMANDS:
            raise ValueError(f"Invalid command set: {command_set}")
        
        commands = STANDARD_TEST_COMMANDS[command_set]
        
        for cmd in commands:
            test_id = f"voice_{command_set}_{str(uuid.uuid4())[:8]}"
            test_config = {
                "test_id": test_id,
                "test_type": TestType.VOICE_PROCESSING,
                "command": cmd,
                "model_name": model_name,
            }
            self.test_queue.append(test_config)
        
        log_event("tests_queued", {
            "test_type": TestType.VOICE_PROCESSING.value,
            "command_set": command_set,
            "count": len(commands)
        })
        
        return self
    
    def queue_context_retention_test(self, context_set_idx=0, model_name="rene"):
        """Queue a context retention test with sequential commands"""
        if "contextual" not in STANDARD_TEST_COMMANDS:
            raise ValueError("Contextual command set not found")
        
        context_sets = STANDARD_TEST_COMMANDS["contextual"]
        if context_set_idx >= len(context_sets):
            raise ValueError(f"Invalid context set index: {context_set_idx}")
        
        context_commands = context_sets[context_set_idx]
        test_id = f"context_{context_set_idx}_{str(uuid.uuid4())[:8]}"
        
        test_config = {
            "test_id": test_id,
            "test_type": TestType.CONTEXT_RETENTION,
            "command_sequence": context_commands,
            "model_name": model_name,
        }
        self.test_queue.append(test_config)
        
        log_event("test_queued", {
            "test_type": TestType.CONTEXT_RETENTION.value,
            "context_set_idx": context_set_idx,
            "command_count": len(context_commands)
        })
        
        return self
    
    def queue_resource_adaptation_test(self, command, resource_constraints=None, model_name="rene"):
        """Queue a test for adaptation to resource constraints"""
        if not resource_constraints:
            resource_constraints = {
                "memory_pressure": 75,  # Simulate 75% memory usage
                "cpu_pressure": 50,     # Simulate 50% CPU usage
                "battery_low": False    # Normal battery
            }
        
        test_id = f"resource_{str(uuid.uuid4())[:8]}"
        test_config = {
            "test_id": test_id,
            "test_type": TestType.RESOURCE_ADAPTATION,
            "command": command,
            "model_name": model_name,
            "resource_constraints": resource_constraints
        }
        self.test_queue.append(test_config)
        
        log_event("test_queued", {
            "test_type": TestType.RESOURCE_ADAPTATION.value,
            "resource_constraints": resource_constraints
        })
        
        return self
    
    def queue_environmental_test(self, command, noise_level=NoiseLevel.MODERATE, 
                                distance=SpeakerDistance.MEDIUM, model_name="rene"):
        """Queue a test for environmental resilience"""
        test_id = f"env_{str(uuid.uuid4())[:8]}"
        test_config = {
            "test_id": test_id,
            "test_type": TestType.ENVIRONMENTAL,
            "command": command,
            "model_name": model_name,
            "noise_level": noise_level,
            "speaker_distance": distance
        }
        self.test_queue.append(test_config)
        
        log_event("test_queued", {
            "test_type": TestType.ENVIRONMENTAL.value,
            "noise_level": noise_level.value if isinstance(noise_level, Enum) else noise_level,
            "speaker_distance": distance.value if isinstance(distance, Enum) else distance
        })
        
        return self
    
    def queue_extended_usage_test(self, duration_seconds=3600, command_interval_seconds=300, 
                                 command_set="mixed", model_name="rene"):
        """Queue an extended usage test over time"""
        if command_set == "mixed":
            # Create a mix of simple, moderate and complex commands
            commands = (
                STANDARD_TEST_COMMANDS["simple"][:3] + 
                STANDARD_TEST_COMMANDS["moderate"][:3] + 
                STANDARD_TEST_COMMANDS["complex"][:3]
            )
        elif command_set in STANDARD_TEST_COMMANDS:
            commands = STANDARD_TEST_COMMANDS[command_set]
        else:
            raise ValueError(f"Invalid command set: {command_set}")
        
        test_id = f"extended_{str(uuid.uuid4())[:8]}"
        test_config = {
            "test_id": test_id,
            "test_type": TestType.EXTENDED_USAGE,
            "commands": commands,
            "model_name": model_name,
            "duration_seconds": duration_seconds,
            "command_interval_seconds": command_interval_seconds
        }
        self.test_queue.append(test_config)
        
        log_event("test_queued", {
            "test_type": TestType.EXTENDED_USAGE.value,
            "duration_seconds": duration_seconds,
            "command_count": len(commands),
            "interval_seconds": command_interval_seconds
        })
        
        return self
    
    def _run_voice_processing_test(self, test_config):
        """Run a single voice processing test"""
        test_id = test_config["test_id"]
        command = test_config["command"]
        model_name = test_config["model_name"]
        
        result = TestResult(test_id, TestType.VOICE_PROCESSING)
        
        try:
            # Determine processing location
            proc_location, decision_meta = select_processing_location(
                command, forced_location=self.processing_mode.value 
                if isinstance(self.processing_mode, ProcessingLocation) else self.processing_mode
            )
            
            # Record the decision in metrics
            result.metrics.update({
                "command": command,
                "model_name": model_name,
                "processing_location": proc_location.value,
                "decision_metadata": decision_meta
            })
            
            # Load the model
            model_start_time = time.time()
            model = self.model_loader(model_name)
            model_load_time = (time.time() - model_start_time) * 1000
            result.metrics["model_load_time_ms"] = model_load_time
            
            # Generate response
            gen_start_time = time.time()
            full_response = ""
            
            for text_chunk in self.generation_function(model, command):
                full_response += text_chunk
            
            gen_time = (time.time() - gen_start_time) * 1000
            result.metrics.update({
                "generation_time_ms": gen_time,
                "response_length": len(full_response),
                "response": full_response
            })
            
            # Check if meets performance targets
            meets_latency_target = False
            
            if proc_location == ProcessingLocation.LOCAL:
                meets_latency_target = gen_time < PERFORMANCE_TARGETS["local_latency_ms"]
            else:
                meets_latency_target = gen_time < PERFORMANCE_TARGETS["total_roundtrip_ms"]
            
            result.metrics["meets_latency_target"] = meets_latency_target
            
            # Determine success
            success = meets_latency_target and len(full_response) > 0
            
            return result.complete(success)
        
        except Exception as e:
            result.metrics["error"] = str(e)
            return result.complete(False)
    
    def _run_context_retention_test(self, test_config):
        """Run a context retention test with sequential commands"""
        test_id = test_config["test_id"]
        command_sequence = test_config["command_sequence"]
        model_name = test_config["model_name"]
        
        result = TestResult(test_id, TestType.CONTEXT_RETENTION)
        
        try:
            # Load the model
            model_start_time = time.time()
            model = self.model_loader(model_name)
            model_load_time = (time.time() - model_start_time) * 1000
            result.metrics["model_load_time_ms"] = model_load_time
            
            # Build conversation context
            context = ""
            responses = []
            
            for i, command in enumerate(command_sequence):
                log_event("context_test_step", {
                    "step": i + 1,
                    "command": command,
                    "context_length": len(context)
                })
                
                # Generate response for this command
                full_prompt = context + "\nUser: " + command + "\nAssistant: "
                full_response = ""
                
                for text_chunk in self.generation_function(model, full_prompt):
                    full_response += text_chunk
                
                # Record response
                responses.append(full_response)
                
                # Update context for next command
                context += "\nUser: " + command + "\nAssistant: " + full_response
            
            # Record responses in metrics
            for i, response in enumerate(responses):
                result.metrics[f"command_{i+1}"] = command_sequence[i]
                result.metrics[f"response_{i+1}"] = response
            
            # Determine context success (simplified evaluation)
            # A more sophisticated evaluation would parse the responses for actual contextual understanding
            success = all(len(response) > 0 for response in responses)
            
            return result.complete(success, {
                "model_name": model_name,
                "num_turns": len(command_sequence),
                "context_final_length": len(context)
            })
        
        except Exception as e:
            result.metrics["error"] = str(e)
            return result.complete(False)
    
    def _run_extended_usage_test(self, test_config):
        """Run an extended usage test over time"""
        test_id = test_config["test_id"]
        commands = test_config["commands"]
        model_name = test_config["model_name"]
        duration_seconds = test_config["duration_seconds"]
        command_interval_seconds = test_config["command_interval_seconds"]
        
        result = TestResult(test_id, TestType.EXTENDED_USAGE)
        
        try:
            # Record initial resource state
            initial_resources = get_device_resource_state()
            result.metrics["initial_resources"] = initial_resources
            
            # Load the model
            model = self.model_loader(model_name)
            
            # Setup timing
            start_time = time.time()
            end_time = start_time + duration_seconds
            command_index = 0
            next_command_time = start_time
            
            command_results = []
            
            # Run until duration is reached
            while time.time() < end_time:
                current_time = time.time()
                
                # Check if it's time for next command
                if current_time >= next_command_time:
                    # Get command (cycle through the list)
                    command = commands[command_index % len(commands)]
                    command_index += 1
                    
                    # Generate response
                    gen_start_time = time.time()
                    full_response = ""
                    
                    for text_chunk in self.generation_function(model, command):
                        full_response += text_chunk
                    
                    gen_time = (time.time() - gen_start_time) * 1000
                    
                    # Record result
                    command_results.append({
                        "command": command,
                        "time_offset_seconds": current_time - start_time,
                        "generation_time_ms": gen_time,
                        "response_length": len(full_response)
                    })
                    
                    # Schedule next command
                    next_command_time = current_time + command_interval_seconds
                    
                    # Log progress
                    elapsed = current_time - start_time
                    remaining = end_time - current_time
                    log_event("extended_test_progress", {
                        "elapsed_seconds": elapsed,
                        "remaining_seconds": remaining,
                        "commands_executed": command_index,
                        "percent_complete": (elapsed / duration_seconds) * 100
                    })
                
                # Sleep a bit to prevent tight loop
                time.sleep(1)
            
            # Record final resource state
            final_resources = get_device_resource_state()
            result.metrics["final_resources"] = final_resources
            
            # Calculate performance metrics
            cmd_times = [cmd["generation_time_ms"] for cmd in command_results]
            avg_gen_time = sum(cmd_times) / len(cmd_times) if cmd_times else 0
            
            # Calculate resource impacts
            memory_impact = None
            if "memory_percent" in final_resources and "memory_percent" in initial_resources:
                memory_impact = final_resources["memory_percent"] - initial_resources["memory_percent"]
            
            # Calculate battery impact if available
            battery_impact = None
            if ("battery_percent" in final_resources and final_resources["battery_percent"] is not None and
                "battery_percent" in initial_resources and initial_resources["battery_percent"] is not None):
                battery_impact = calculate_battery_impact(
                    initial_resources["battery_percent"],
                    final_resources["battery_percent"],
                    duration_seconds
                )
            
            # Assemble performance metrics
            performance_metrics = {
                "commands_executed": len(command_results),
                "avg_generation_time_ms": avg_gen_time,
                "min_generation_time_ms": min(cmd_times) if cmd_times else None,
                "max_generation_time_ms": max(cmd_times) if cmd_times else None,
                "memory_impact_percent": memory_impact,
                "battery_impact_percent_per_hour": battery_impact,
                "command_results": command_results
            }
            
            # Determine success
            # Success if: average gen time within targets, no excessive resource drain
            success = True
            if avg_gen_time > PERFORMANCE_TARGETS["total_roundtrip_ms"]:
                success = False
            if battery_impact is not None and battery_impact > PERFORMANCE_TARGETS["battery_impact_percent"]:
                success = False
            
            return result.complete(success, performance_metrics)
        
        except Exception as e:
            result.metrics["error"] = str(e)
            return result.complete(False)
    
    def run_tests(self, save_results=True, output_dir="test_results"):
        """Run all queued tests in the current session"""
        if not self.current_session:
            self.create_session()
        
        if not self.test_queue:
            log_event("test_run_error", {"error": "No tests in queue"})
            return None
        
        self.is_running = True
        log_event("test_run_started", {"session_id": self.current_session.session_id, "test_count": len(self.test_queue)})
        
        try:
            for test_config in self.test_queue:
                if not self.is_running:
                    break
                
                test_type = test_config["test_type"]
                log_event("test_started", {
                    "test_id": test_config["test_id"],
                    "test_type": test_type.value if isinstance(test_type, Enum) else test_type
                })
                
                # Run appropriate test based on type
                if test_type == TestType.VOICE_PROCESSING:
                    result = self._run_voice_processing_test(test_config)
                elif test_type == TestType.CONTEXT_RETENTION:
                    result = self._run_context_retention_test(test_config)
                elif test_type == TestType.EXTENDED_USAGE:
                    result = self._run_extended_usage_test(test_config)
                else:
                    log_event("test_not_implemented", {"test_type": test_type})
                    continue
                
                # Add result to session
                self.current_session.add_result(result)
                
                log_event("test_completed", {
                    "test_id": result.test_id,
                    "success": result.success,
                    "duration_ms": result.duration_ms
                })
            
            # Complete the session
            self.current_session.complete()
            
            # Save results if requested
            if save_results:
                result_file = self.current_session.save(output_dir)
                log_event("test_run_completed", {
                    "session_id": self.current_session.session_id,
                    "success_rate": self.current_session.metrics["success_rate"],
                    "result_file": result_file
                })
            else:
                log_event("test_run_completed", {
                    "session_id": self.current_session.session_id,
                    "success_rate": self.current_session.metrics["success_rate"]
                })
            
            # Clear the queue
            self.test_queue = []
            self.is_running = False
            
            return self.current_session
            
        except Exception as e:
            log_event("test_run_error", {"error": str(e)})
            self.is_running = False
            return None
    
    def stop_tests(self):
        """Stop running tests"""
        self.is_running = False
        log_event("test_run_stopped", {"session_id": self.current_session.session_id if self.current_session else None})
        return self
