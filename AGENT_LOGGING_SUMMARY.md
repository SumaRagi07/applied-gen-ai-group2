# Agent Step Logging & Transparency - Implementation Summary

## ✅ Completed Features

### 1. Structured Logging System
- **Location**: `src/agents/utils/logger.py`
- **Features**:
  - JSON log files saved to `logs/session_*.json`
  - Timestamps for each node execution
  - Duration tracking (milliseconds)
  - Input/output state logging
  - Tool call logging with parameters and results

### 2. Node-Level Logging
All agent nodes now log their execution:
- ✅ **Router**: Intent extraction with timing
- ✅ **Safety**: Safety check results
- ✅ **Planner**: Planning strategy and tool selection
- ✅ **Executor**: Tool calls (RAG & Web search) with I/O
- ✅ **Reconciler**: Product matching and conflict detection
- ✅ **Synthesizer**: Answer generation with citation extraction

### 3. Tool Call Logging
- **RAG Search**: Parameters, results count, execution time
- **Web Search**: Parameters, results count, cache status, execution time
- **Error Tracking**: Failed tool calls with error messages
- **Success/Failure**: Status for each tool call

### 4. Streamlit UI Integration
Enhanced "Agent Log" tab with:
- **Execution Statistics**: Total steps, duration, average time
- **Step-by-Step Log**: Expandable details for each node
- **Tool Call Details**: Expandable tool call information
- **Execution Timeline**: Table showing step durations
- **Log File Download**: Download JSON log file

### 5. Data Sanitization
- API keys and tokens automatically redacted
- Large data structures truncated
- Sensitive information removed

## Log File Example

```json
{
  "session_id": "session_1764360812638",
  "query": "Find wooden puzzles under 20 dollars",
  "start_time": "2024-11-28T14:13:32.638123",
  "end_time": "2024-11-28T14:13:42.204123",
  "total_duration_ms": 9566.0,
  "steps": [
    {
      "node": "router",
      "timestamp": "2024-11-28T14:13:32.640123",
      "duration_ms": 1234.56,
      "input": {"user_query": "..."},
      "output": {"intent": {...}},
      "metadata": {"model": "gpt-4o", "prompt_length": 250}
    },
    {
      "node": "executor",
      "timestamp": "2024-11-28T14:13:35.123456",
      "duration_ms": 2345.67,
      "input": {...},
      "output": {...},
      "metadata": {
        "tool_calls": [
          {
            "tool": "rag.search",
            "timestamp": "2024-11-28T14:13:35.200000",
            "duration_ms": 1234.56,
            "params": {"query": "wooden puzzles", "price_max": 20.0},
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

### In Code
```python
from src.agents.graph import invoke_with_logging

result = invoke_with_logging("User query")
logging_data = result.get('_logging', {})
```

### In Streamlit
1. Process a query
2. Go to "Agent Log" tab
3. View detailed execution log
4. Download JSON log file

## Benefits

1. **Transparency**: See exactly what each agent does
2. **Debugging**: Identify bottlenecks and errors
3. **Auditing**: Track all tool calls and decisions
4. **Performance**: Monitor execution times
5. **Reproducibility**: Replay execution from logs

## Files Modified

- `src/agents/utils/logger.py` - New logging system
- `src/agents/nodes/*.py` - All nodes updated with logging
- `src/agents/graph.py` - Added `invoke_with_logging()` function
- `app.py` - Enhanced UI with detailed logs
- `test_agents.py` - Updated to use logging
- `test_voice.py` - Updated to use logging

## Log Files

- **Location**: `logs/` directory
- **Format**: `session_<timestamp>.json`
- **Auto-created**: Directory created automatically
- **Retention**: Logs persist until manually deleted

