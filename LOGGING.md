# Agent Step Logging and Transparency

## Overview

Comprehensive logging system that tracks all agent execution steps with timestamps, tool I/O, and structured JSON logs for transparency and debugging.

## Features

### 1. Structured Logging
- **JSON Log Files**: Each execution session saved to `logs/session_*.json`
- **Timestamps**: ISO format timestamps for each node execution
- **Duration Tracking**: Execution time in milliseconds for each step
- **Input/Output Logging**: Full state tracking at each node

### 2. Tool Call Logging
- **MCP Tool Calls**: Logs all `rag.search` and `web.search` calls
- **Parameters**: Records all tool parameters
- **Results**: Captures tool responses (sanitized)
- **Error Tracking**: Logs failures with error messages
- **Performance**: Tracks tool execution times

### 3. Real-Time Step Tracking
- **Step-by-Step Display**: Live updates in Streamlit UI
- **Execution Timeline**: Visual timeline of all steps
- **Statistics**: Total duration, average step time, etc.
- **Tool Call Details**: Expandable tool call information

### 4. Data Sanitization
- **Security**: Automatically redacts API keys and tokens
- **Size Limits**: Truncates large data structures
- **Sensitive Data**: Removes credentials from logs

## Log File Structure

```json
{
  "session_id": "session_1234567890",
  "query": "Find me eco-friendly puzzles under $20",
  "start_time": "2024-01-15T10:30:00",
  "end_time": "2024-01-15T10:30:05",
  "total_duration_ms": 5234.56,
  "steps": [
    {
      "node": "router",
      "timestamp": "2024-01-15T10:30:00.123",
      "duration_ms": 1234.56,
      "input": {"user_query": "..."},
      "output": {"intent": {...}},
      "metadata": {
        "model": "gpt-4o",
        "prompt_length": 250
      }
    },
    {
      "node": "executor",
      "timestamp": "2024-01-15T10:30:02.456",
      "duration_ms": 2345.67,
      "input": {...},
      "output": {...},
      "metadata": {
        "tool_calls": [
          {
            "tool": "rag.search",
            "timestamp": "2024-01-15T10:30:02.500",
            "duration_ms": 1234.56,
            "params": {"query": "...", "price_max": 20.0},
            "result": {"count": 5, "execution_time_ms": 1234.56},
            "success": true
          }
        ]
      }
    }
  ]
}
```

## Usage

### In Streamlit App

1. Process a query
2. Go to "Agent Log" tab
3. View:
   - Execution statistics (total steps, duration, avg time)
   - Step-by-step execution log
   - Tool call details
   - Execution timeline
   - Download JSON log file

### Programmatic Usage

```python
from src.agents.graph import invoke_with_logging
from src.agents.utils.logger import get_logger

# Run with logging
result = invoke_with_logging("Find eco-friendly toys under $15")

# Access logging data
logging_data = result.get('_logging', {})
session_id = logging_data.get('session_id')
log_file = logging_data.get('log_file')
step_summary = logging_data.get('step_summary')
execution_stats = logging_data.get('execution_stats')

# Get logger stats
logger = get_logger()
stats = logger.get_execution_stats()
```

### Direct Logger Usage

```python
from src.agents.utils.logger import get_logger

logger = get_logger()

# Start session
session_id = logger.start_session("User query")

# Log a step
logger.log_step(
    node_name="router",
    input_data={"user_query": "..."},
    output_data={"intent": {...}},
    duration_ms=1234.56,
    metadata={"model": "gpt-4o"}
)

# Log a tool call
logger.log_tool_call(
    tool_name="rag.search",
    params={"query": "...", "price_max": 20.0},
    result={"count": 5},
    duration_ms=1234.56,
    success=True
)

# End session and save
log_file = logger.end_session()
```

## Log File Location

- **Directory**: `logs/` (created automatically)
- **Format**: `logs/session_<timestamp>.json`
- **Retention**: Logs persist until manually deleted

## Logged Information

### Per Node:
- Node name
- Timestamp
- Duration (ms)
- Input state
- Output state
- Metadata (model, prompt length, etc.)

### Per Tool Call:
- Tool name
- Parameters
- Result summary
- Success/failure status
- Error messages (if failed)
- Execution time

## Benefits

1. **Transparency**: See exactly what each agent does
2. **Debugging**: Identify bottlenecks and errors
3. **Auditing**: Track all tool calls and decisions
4. **Performance**: Monitor execution times
5. **Reproducibility**: Replay execution from logs

## Example Log Output

```
📊 Execution Stats:
   Total Steps: 6
   Total Duration: 5234.56 ms
   Average Step Time: 872.43 ms
   Log File: logs/session_1234567890.json
```

## Integration

- **All Nodes**: Router, Safety, Planner, Executor, Reconciler, Synthesizer
- **Tool Calls**: RAG search, Web search
- **Streamlit UI**: Real-time display in "Agent Log" tab
- **Test Files**: Automatic logging in test scripts

