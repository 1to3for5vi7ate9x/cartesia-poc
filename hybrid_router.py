"""
Hybrid Processing Router for the Cartesia State Space Model (SSM) PoC

This module implements the intelligent routing logic that decides whether to process
requests locally (on-device) or remotely (data center/server), simulating the edge-to-cell-tower
architecture described in the PoC test plan.
"""

import time
import re
import json
from enum import Enum
from utils import get_device_resource_state, estimate_network_quality, log_event

class ProcessingLocation(Enum):
    """Enum for possible processing locations"""
    LOCAL = "local"           # Process on the current device
    SERVER = "server"         # Process on the server/data center
    HYBRID = "hybrid"         # Use both in complementary ways
    AUTOMATIC = "automatic"   # Let the system decide

class CommandComplexity(Enum):
    """Enum for command complexity categories"""
    SIMPLE = "simple"         # Basic commands, e.g., "What time is it?"
    MODERATE = "moderate"     # More complex queries, e.g., "What meetings do I have tomorrow?"
    COMPLEX = "complex"       # Very complex queries requiring context or extensive processing
    UNKNOWN = "unknown"       # Unknown complexity

class NetworkCondition(Enum):
    """Enum for network condition categories"""
    EXCELLENT = "excellent"   # Low latency, high bandwidth
    GOOD = "good"             # Moderate latency, good bandwidth
    FAIR = "fair"             # Higher latency, adequate bandwidth
    POOR = "poor"             # High latency, low bandwidth
    OFFLINE = "offline"       # No connectivity
    UNKNOWN = "unknown"       # Unknown network condition

class DeviceResourceState(Enum):
    """Enum for device resource state categories"""
    OPTIMAL = "optimal"       # High available memory, low CPU usage, good battery
    ADEQUATE = "adequate"     # Moderate resource availability
    CONSTRAINED = "constrained" # Limited resources available
    CRITICAL = "critical"     # Very limited resources, need to conserve
    UNKNOWN = "unknown"       # Unknown resource state

# Command complexity patterns - simple regex patterns to estimate command complexity
COMMAND_COMPLEXITY_PATTERNS = {
    CommandComplexity.SIMPLE: [
        r"^what time is it",
        r"^how are you",
        r"^hello|^hi\b",
        r"^thank you",
        r"^stop|^cancel|^exit",
        r"^yes|^no\b",
        r"^turn (on|off)",
        r"^play|^pause|^next|^previous",
        r"^volume (up|down)"
    ],
    CommandComplexity.MODERATE: [
        r"what.*weather",
        r"what.*meeting",
        r"how.*get to",
        r"find.*near me",
        r"set.*reminder|set.*alarm",
        r"send.*message|send.*email",
        r"search for",
        r"calculate|convert",
        r"who is|what is|how (do|does|did)"
    ],
    CommandComplexity.COMPLEX: [
        r"compare|difference between",
        r"explain|elaborate on",
        r"analyze|predict|forecast",
        r"summarize|synopsis|summary of",
        r"relationship between",
        r"what would happen if",
        r"history of|evolution of",
        r"that|this|it|one|them|those",  # Potential contextual references
        r"like I mentioned|as I said|earlier|before"  # More contextual references
    ]
}

def estimate_command_complexity(command_text):
    """Estimate the complexity of a command based on patterns"""
    command_text = command_text.lower()
    
    # Check patterns from complex to simple (more specific to more general)
    for complexity in [CommandComplexity.COMPLEX, CommandComplexity.MODERATE, CommandComplexity.SIMPLE]:
        for pattern in COMMAND_COMPLEXITY_PATTERNS[complexity]:
            if re.search(pattern, command_text):
                return complexity
    
    # Default to moderate if no patterns match
    return CommandComplexity.MODERATE

def classify_network_condition(network_info):
    """Classify network condition based on ping data"""
    quality = network_info.get("quality", "unknown")
    
    if quality == "excellent":
        return NetworkCondition.EXCELLENT
    elif quality == "good":
        return NetworkCondition.GOOD
    elif quality == "fair":
        return NetworkCondition.FAIR
    elif quality == "poor":
        return NetworkCondition.POOR
    elif quality == "offline":
        return NetworkCondition.OFFLINE
    else:
        return NetworkCondition.UNKNOWN

def classify_device_resource_state(resource_state):
    """Classify device resource state based on memory, CPU, and battery"""
    if "error" in resource_state:
        return DeviceResourceState.UNKNOWN
    
    # Extract metrics
    cpu_percent = resource_state.get("cpu_percent", 50)  # Default to 50% if unknown
    memory_percent = resource_state.get("memory_percent", 50)  # Default to 50% if unknown
    memory_available_mb = resource_state.get("memory_available_mb", 2000)  # Default to 2GB if unknown
    battery_percent = resource_state.get("battery_percent", 50)  # Default to 50% if unknown
    
    # First check for critical conditions
    if (battery_percent is not None and battery_percent < 15) or memory_available_mb < 500:
        return DeviceResourceState.CRITICAL
    
    # Check for constrained resources
    if (cpu_percent > 80) or (memory_percent > 80) or (memory_available_mb < 1000) or \
       (battery_percent is not None and battery_percent < 30):
        return DeviceResourceState.CONSTRAINED
    
    # Check for optimal resources
    if (cpu_percent < 30) and (memory_percent < 50) and (memory_available_mb > 4000) and \
       (battery_percent is None or battery_percent > 70):
        return DeviceResourceState.OPTIMAL
    
    # Default to adequate
    return DeviceResourceState.ADEQUATE

# Placeholder functions for client-side metric classification (to be implemented)
def classify_network_condition_from_client(client_network_metrics):
    # TODO: Implement logic based on client_network_metrics (effectiveType, rtt, downlink)
    print(f"DEBUG: Classifying network from client: {client_network_metrics}") # Debug print
    if not client_network_metrics or client_network_metrics.get('effectiveType') == 'unknown':
        return NetworkCondition.UNKNOWN
    effective_type = client_network_metrics.get('effectiveType')
    if effective_type == 'offline': return NetworkCondition.OFFLINE
    if effective_type == 'slow-2g' or effective_type == '2g': return NetworkCondition.POOR
    if effective_type == '3g': return NetworkCondition.FAIR
    if effective_type == '4g': return NetworkCondition.GOOD # Treat 4g as good/excellent base
    # Could add checks for rtt/downlink if available for finer classification
    return NetworkCondition.GOOD # Default assumption if type is known but not matched

def classify_device_resource_state_from_client(client_metrics):
    # TODO: Implement logic based on client_metrics (memoryGB, battery.level)
    print(f"DEBUG: Classifying device state from client: {client_metrics}") # Debug print
    if not client_metrics:
        return DeviceResourceState.UNKNOWN
        
    memory_gb = client_metrics.get('memory', {}).get('memoryGB')
    battery_info = client_metrics.get('battery', {})
    battery_level = battery_info.get('level')
    # cpu_load = client_metrics.get('cpu', {}).get('load') # Currently always 'unknown'

    # Critical check (low battery or very low memory)
    if (battery_level is not None and battery_level < 15) or \
       (memory_gb is not None and memory_gb < 0.5): # Less than 512MB
        return DeviceResourceState.CRITICAL
        
    # Constrained check (medium battery or low memory)
    if (battery_level is not None and battery_level < 30) or \
       (memory_gb is not None and memory_gb < 1): # Less than 1GB
        return DeviceResourceState.CONSTRAINED
        
    # Optimal check (high battery and high memory)
    if (battery_level is None or battery_level > 70) and \
       (memory_gb is None or memory_gb >= 4): # 4GB+ memory
        return DeviceResourceState.OPTIMAL
        
    return DeviceResourceState.ADEQUATE # Default

def select_processing_location(command_text, context=None, forced_location=None, client_metrics=None): # Added client_metrics
    """
    Intelligently select the optimal processing location based on:
    - Command complexity
    - Device resource state
    - Network conditions
    - Context requirements
    
    Args:
        command_text: The text command to process
        context: Optional context information
        forced_location: Force a specific processing location
        
    Returns:
        ProcessingLocation enum value and decision metadata
    """
    decision_time_start = time.time()
    
    # If location is forced, respect that setting
    if forced_location:
        try:
            forced_loc = ProcessingLocation(forced_location)
            decision_metadata = {
                "decision": forced_loc.value,
                "reason": "Forced by user setting",
                "decision_time_ms": 0
            }
            return forced_loc, decision_metadata
        except ValueError:
            # Invalid forced location, continue with automatic selection
            pass
    
    metrics_source = "server" # Track where metrics came from
    
    # --- Use Client Metrics if available ---
    if client_metrics:
        metrics_source = "client"
        print("DEBUG: Using client metrics for routing decision") # Debug print
        network_condition = classify_network_condition_from_client(client_metrics.get('network'))
        device_state = classify_device_resource_state_from_client(client_metrics)
    else:
        # --- Fallback to Server Metrics ---
        print("DEBUG: Using server metrics for routing decision") # Debug print
        resource_state = get_device_resource_state()
        network_info = estimate_network_quality()
        network_condition = classify_network_condition(network_info)
        device_state = classify_device_resource_state(resource_state)
        
    # Estimate command complexity (always done on server)
    command_complexity = estimate_command_complexity(command_text)
    
    # Log the context of the decision
    log_event("processing_location_context", {
        "metrics_source": metrics_source, # Added source
        "command_complexity": command_complexity.value,
        "network_condition": network_condition.value,
        "device_state": device_state.value,
        "has_context": context is not None
    })
    
    # Step 1: Check for offline condition - must use local
    if network_condition == NetworkCondition.OFFLINE:
        decision_time = (time.time() - decision_time_start) * 1000  # Convert to milliseconds
        decision_metadata = {
            "decision": ProcessingLocation.LOCAL.value,
            "reason": "No network connectivity available",
            "command_complexity": command_complexity.value,
            "network_condition": network_condition.value,
            "device_state": device_state.value,
            "decision_time_ms": decision_time
        }
        return ProcessingLocation.LOCAL, decision_metadata
    
    # Step 2: Check for critical device state with good network - prefer server
    if device_state == DeviceResourceState.CRITICAL and \
       network_condition in [NetworkCondition.EXCELLENT, NetworkCondition.GOOD]:
        decision_time = (time.time() - decision_time_start) * 1000
        decision_metadata = {
            "decision": ProcessingLocation.SERVER.value,
            "reason": "Device resources critically low, good network available",
            "command_complexity": command_complexity.value,
            "network_condition": network_condition.value,
            "device_state": device_state.value,
            "decision_time_ms": decision_time
        }
        return ProcessingLocation.SERVER, decision_metadata
    
    # Step 3: Consider command complexity
    if command_complexity == CommandComplexity.COMPLEX:
        # Complex commands go to server if network is decent
        if network_condition in [NetworkCondition.EXCELLENT, NetworkCondition.GOOD, NetworkCondition.FAIR]:
            decision_time = (time.time() - decision_time_start) * 1000
            decision_metadata = {
                "decision": ProcessingLocation.SERVER.value,
                "reason": "Complex command with adequate network",
                "command_complexity": command_complexity.value,
                "network_condition": network_condition.value,
                "device_state": device_state.value,
                "decision_time_ms": decision_time
            }
            return ProcessingLocation.SERVER, decision_metadata
    
    # Step 4: Consider simple commands with good device state
    if command_complexity == CommandComplexity.SIMPLE and \
       device_state in [DeviceResourceState.OPTIMAL, DeviceResourceState.ADEQUATE]:
        decision_time = (time.time() - decision_time_start) * 1000
        decision_metadata = {
            "decision": ProcessingLocation.LOCAL.value,
            "reason": "Simple command with adequate device resources",
            "command_complexity": command_complexity.value,
            "network_condition": network_condition.value,
            "device_state": device_state.value,
            "decision_time_ms": decision_time
        }
        return ProcessingLocation.LOCAL, decision_metadata
    
    # Step 5: Consider network quality for everything else
    if network_condition in [NetworkCondition.EXCELLENT, NetworkCondition.GOOD]:
        decision_time = (time.time() - decision_time_start) * 1000
        decision_metadata = {
            "decision": ProcessingLocation.SERVER.value,
            "reason": "Good network conditions favor server processing",
            "command_complexity": command_complexity.value,
            "network_condition": network_condition.value,
            "device_state": device_state.value,
            "decision_time_ms": decision_time
        }
        return ProcessingLocation.SERVER, decision_metadata
    
    # Default fallback to local processing for reliability
    decision_time = (time.time() - decision_time_start) * 1000
    decision_metadata = {
        "decision": ProcessingLocation.LOCAL.value,
        "reason": "Default fallback to local for reliability",
        "command_complexity": command_complexity.value,
        "network_condition": network_condition.value,
        "device_state": device_state.value,
        "decision_time_ms": decision_time
    }
    return ProcessingLocation.LOCAL, decision_metadata

def transition_processing_context(from_location, to_location, conversation_context):
    """
    Handle transitions between processing locations while preserving context
    
    Args:
        from_location: The current processing location
        to_location: The new processing location
        conversation_context: Context data to preserve
        
    Returns:
        Updated context data and transition metadata
    """
    transition_start = time.time()
    
    if not conversation_context:
        conversation_context = {"history": []}
    
    # Add transition event to context
    transition_event = {
        "timestamp": time.time(),
        "from_location": from_location.value if isinstance(from_location, ProcessingLocation) else from_location,
        "to_location": to_location.value if isinstance(to_location, ProcessingLocation) else to_location
    }
    
    if "transitions" not in conversation_context:
        conversation_context["transitions"] = []
    conversation_context["transitions"].append(transition_event)
    
    # Log the transition
    log_event("processing_location_transition", transition_event)
    
    # Return updated context and transition metadata
    transition_time = (time.time() - transition_start) * 1000  # Convert to milliseconds
    transition_metadata = {
        "transition_time_ms": transition_time
    }
    
    return conversation_context, transition_metadata
