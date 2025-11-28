"""
Agent Step Logging System

Provides structured logging for agent execution:
- Timestamps for each node
- Input/output tracking
- Tool call logging
- JSON log files
- Real-time step tracking
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import defaultdict

class AgentLogger:
    """Structured logger for agent execution steps"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Current execution log
        self.current_execution = {
            "session_id": None,
            "query": None,
            "start_time": None,
            "end_time": None,
            "total_duration_ms": None,
            "steps": []
        }
        
        # Step tracking
        self.step_logs = []
        self.step_timings = {}
    
    def start_session(self, query: str) -> str:
        """Start a new logging session"""
        # Reset previous session
        self.step_logs = []
        self.step_timings = {}
        
        session_id = f"session_{int(time.time() * 1000)}"
        self.current_execution = {
            "session_id": session_id,
            "query": query,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "total_duration_ms": None,
            "steps": []
        }
        return session_id
    
    def log_step(
        self,
        node_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a single agent step"""
        step_log = {
            "node": node_name,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": round(duration_ms, 2),
            "input": self._sanitize_data(input_data),
            "output": self._sanitize_data(output_data),
            "metadata": metadata or {}
        }
        
        self.step_logs.append(step_log)
        self.current_execution["steps"].append(step_log)
        self.step_timings[node_name] = duration_ms
        
        return step_log
    
    def log_tool_call(
        self,
        tool_name: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log a tool call (MCP server call)"""
        tool_log = {
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": round(duration_ms, 2),
            "params": self._sanitize_data(params),
            "result": self._sanitize_data(result),
            "success": success,
            "error": error
        }
        
        # Add to current step if available
        if self.step_logs:
            last_step = self.step_logs[-1]
            if "tool_calls" not in last_step["metadata"]:
                last_step["metadata"]["tool_calls"] = []
            last_step["metadata"]["tool_calls"].append(tool_log)
        
        return tool_log
    
    def end_session(self):
        """End the current session and save log"""
        self.current_execution["end_time"] = datetime.now().isoformat()
        
        if self.current_execution["start_time"]:
            start = datetime.fromisoformat(self.current_execution["start_time"])
            end = datetime.fromisoformat(self.current_execution["end_time"])
            duration = (end - start).total_seconds() * 1000
            self.current_execution["total_duration_ms"] = round(duration, 2)
        
        # Save to file
        log_file = self.log_dir / f"{self.current_execution['session_id']}.json"
        with open(log_file, 'w') as f:
            json.dump(self.current_execution, f, indent=2)
        
        return log_file
    
    def get_step_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all steps for UI display"""
        summary = []
        for step in self.step_logs:
            summary.append({
                "step": step["node"].capitalize(),  # For backward compatibility
                "node": step["node"],
                "timestamp": step["timestamp"],
                "duration_ms": step["duration_ms"],
                "status": "✓",
                "input": step["input"],  # Full input for expandable view
                "output": step["output"],  # Full output for expandable view
                "input_summary": self._summarize_data(step["input"]),
                "output_summary": self._summarize_data(step["output"]),
                "data": step["output"],  # For backward compatibility
                "tool_calls": step["metadata"].get("tool_calls", [])
            })
        return summary
    
    def _sanitize_data(self, data: Any) -> Any:
        """Remove sensitive data and limit size"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if "api_key" in key.lower() or "token" in key.lower():
                    sanitized[key] = "***REDACTED***"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                elif isinstance(value, str) and len(value) > 1000:
                    sanitized[key] = value[:1000] + "... (truncated)"
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data[:50]]  # Limit to 50 items
        elif isinstance(data, str) and len(data) > 1000:
            return data[:1000] + "... (truncated)"
        else:
            return data
    
    def _summarize_data(self, data: Any) -> str:
        """Create a brief summary of data for display"""
        if isinstance(data, dict):
            keys = list(data.keys())[:5]
            return f"Keys: {', '.join(keys)}" + ("..." if len(data) > 5 else "")
        elif isinstance(data, list):
            return f"List with {len(data)} items"
        elif isinstance(data, str):
            return data[:100] + "..." if len(data) > 100 else data
        else:
            return str(data)[:100]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        total_time = sum(self.step_timings.values())
        return {
            "total_steps": len(self.step_logs),
            "total_duration_ms": round(total_time, 2),
            "step_timings": self.step_timings,
            "average_step_time_ms": round(total_time / len(self.step_logs), 2) if self.step_logs else 0
        }


# Global logger instance
_global_logger = None

def get_logger() -> AgentLogger:
    """Get or create global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = AgentLogger()
    return _global_logger

def reset_logger():
    """Reset global logger (for testing)"""
    global _global_logger
    _global_logger = None

