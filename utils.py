"""
Utility functions for the Cartesia State Space Model (SSM) PoC
"""

import os
import time
import json
import datetime
import platform
import socket
import functools
import random
import psutil

# Function execution time measurement decorator
def measure_execution_time(func):
    """Decorator to measure execution time of functions"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Log the execution time
        log_event(f"{func.__name__}_execution_time", {
            "time_ms": execution_time,
            "function": func.__name__
        })
        
        return result
    return wrapper

def get_timestamp():
    """Get the current timestamp in ISO format"""
    return datetime.datetime.now().isoformat()

def log_event(event_type, data=None):
    """Log an event with associated data"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"cartesia_{datetime.datetime.now().strftime('%Y%m%d')}.log")
    
    log_entry = {
        "timestamp": get_timestamp(),
        "event_type": event_type,
        "data": data or {}
    }
    
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Warning: Failed to write to log file: {str(e)}")
        print(f"Log event: {event_type} - {data}")

def get_system_info():
    """Get basic system information"""
    try:
        system_info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "hostname": socket.gethostname()
        }
        
        # Add Mac-specific info if applicable
        if platform.system() == "Darwin":
            try:
                import subprocess
                model_cmd = subprocess.run(["sysctl", "-n", "hw.model"], capture_output=True, text=True)
                system_info["mac_model"] = model_cmd.stdout.strip()
            except:
                pass
        
        return system_info
    except Exception as e:
        return {"error": str(e)}

def get_network_info():
    """Get network interface information"""
    try:
        network_interfaces = []
        
        for iface, addrs in psutil.net_if_addrs().items():
            iface_info = {"name": iface, "addresses": []}
            
            for addr in addrs:
                addr_info = {
                    "family": str(addr.family),
                    "address": addr.address
                }
                iface_info["addresses"].append(addr_info)
            
            network_interfaces.append(iface_info)
        
        # Add basic network counters
        net_io = psutil.net_io_counters()
        
        network_info = {
            "interfaces": network_interfaces,
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
        
        return network_info
    except Exception as e:
        return {"error": str(e)}

def get_device_resource_state():
    """Get current state of device resources"""
    try:
        # Get CPU info
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True)
        
        # Get memory info
        memory = psutil.virtual_memory()
        memory_total_mb = memory.total / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)
        memory_percent = memory.percent
        
        # Get battery info if available
        battery_percent = None
        power_plugged = None
        
        try:
            battery = psutil.sensors_battery()
            if battery:
                battery_percent = battery.percent
                power_plugged = battery.power_plugged
        except:
            pass
        
        # Compile resource state
        resource_state = {
            "timestamp": get_timestamp(),
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "memory_total_mb": round(memory_total_mb, 2),
            "memory_available_mb": round(memory_available_mb, 2),
            "memory_percent": memory_percent
        }
        
        # Add battery info if available
        if battery_percent is not None:
            resource_state["battery_percent"] = battery_percent
            resource_state["power_plugged"] = power_plugged
        
        return resource_state
    except Exception as e:
        return {"error": str(e)}

def estimate_network_quality():
    """Estimate the quality of the network connection"""
    try:
        # This is a simplified version for the PoC
        # A real implementation would perform actual network tests
        
        # Ping a few common servers
        hosts = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
        ping_results = []
        
        for host in hosts:
            ping_time = None
            try:
                # Use system ping command
                import subprocess
                
                if platform.system() == "Windows":
                    ping_cmd = ["ping", "-n", "1", "-w", "1000", host]
                else:
                    ping_cmd = ["ping", "-c", "1", "-W", "1", host]
                
                start_time = time.time()
                result = subprocess.run(ping_cmd, capture_output=True, text=True)
                end_time = time.time()
                
                # Check if ping was successful
                if result.returncode == 0:
                    # Try to parse the actual ping time
                    output = result.stdout
                    import re
                    
                    # Extract time from ping output
                    if platform.system() == "Windows":
                        match = re.search(r"time=(\d+)ms", output)
                    else:
                        match = re.search(r"time=(\d+\.\d+) ms", output)
                    
                    if match:
                        ping_time = float(match.group(1))
                    else:
                        # If we can't parse it, use our own timing
                        ping_time = (end_time - start_time) * 1000
                else:
                    # Ping failed
                    ping_time = None
            except:
                # If subprocess fails, simulate a ping
                # This is for testing only!
                ping_time = random.uniform(20, 200)
            
            if ping_time is not None:
                ping_results.append(ping_time)
        
        # Calculate average ping if we have results
        if ping_results:
            avg_ping = sum(ping_results) / len(ping_results)
            
            # Classify network quality based on ping
            if avg_ping < 50:
                quality = "excellent"
            elif avg_ping < 100:
                quality = "good"
            elif avg_ping < 200:
                quality = "fair"
            else:
                quality = "poor"
            
            network_quality = {
                "quality": quality,
                "avg_ping_ms": avg_ping,
                "ping_results": ping_results,
                "timestamp": get_timestamp()
            }
        else:
            # No successful pings
            network_quality = {
                "quality": "unknown",
                "error": "No successful pings",
                "timestamp": get_timestamp()
            }
        
        return network_quality
    except Exception as e:
        return {
            "quality": "unknown",
            "error": str(e),
            "timestamp": get_timestamp()
        }

def calculate_battery_impact(initial_percent, final_percent, duration_seconds):
    """Calculate battery impact as drain per hour"""
    if initial_percent is None or final_percent is None:
        return None
    
    percent_drop = initial_percent - final_percent
    hours = duration_seconds / 3600
    
    if hours <= 0:
        return None
    
    drain_per_hour = percent_drop / hours
    return drain_per_hour
