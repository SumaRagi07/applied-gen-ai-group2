"""
Streamlit UI for Voice-to-Voice Product Discovery Assistant

Features:
- Microphone recording or audio file upload
- Live transcript display
- Agent step-by-step execution log
- Product comparison table (RAG vs Web)
- TTS audio playback
- Citation display
"""

import streamlit as st
import sys
import os
from pathlib import Path
import time
import json
import threading
import pandas as pd
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.voice.asr import transcribe_audio, record_audio
from src.voice.tts import text_to_speech, text_to_speech_with_summary, VOICE_INFO
from src.agents.graph import agent_graph, invoke_with_logging
from src.agents.utils.logger import get_logger

# Page config
st.set_page_config(
    page_title="Voice-to-Voice Product Assistant",
    page_icon="🎤",
    layout="wide"
)

# Initialize session state
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
if 'result' not in st.session_state:
    st.session_state.result = None
if 'agent_steps' not in st.session_state:
    st.session_state.agent_steps = []
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None
if 'tts_audio_path' not in st.session_state:
    st.session_state.tts_audio_path = None

# Custom CSS for better UI
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .step-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .citation {
        background-color: #e8f4f8;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
        font-family: monospace;
        font-size: 0.9rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🎤 Voice-to-Voice Product Discovery Assistant</h1>', unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Voice selection for TTS
    st.subheader("TTS Voice")
    selected_voice = st.selectbox(
        "Choose voice for responses:",
        options=list(VOICE_INFO.keys()),
        index=0,
        help="Select the voice for text-to-speech output"
    )
    st.caption(f"*{VOICE_INFO[selected_voice]}*")
    
    # MCP Server status
    st.subheader("🔌 MCP Server Status")
    mcp_status = st.empty()
    mcp_info = st.empty()
    
    # Check MCP server
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=3)
        if response.status_code == 200:
            mcp_status.success("✅ MCP Server Running")
            mcp_info.empty()
        else:
            mcp_status.error("❌ MCP Server Not Responding")
            mcp_info.error(f"Status Code: {response.status_code}")
    except requests.exceptions.ConnectionError:
        mcp_status.warning("⚠️ MCP Server Not Running")
        mcp_info.info("💡 **Start MCP server in a separate terminal:**\n\n```bash\npython src/mcp_server/server.py\n```")
    except requests.exceptions.Timeout:
        mcp_status.warning("⚠️ MCP Server Timeout")
        mcp_info.info("Server may be starting up. Please wait a few seconds and refresh.")
    except Exception as e:
        mcp_status.error("❌ Connection Error")
        mcp_info.error(f"Error: {str(e)}")
    
    st.divider()
    
    # Instructions
    st.subheader("📖 Instructions")
    st.markdown("""
    1. **Record** audio or **upload** audio file
    2. Click **Process Query** to run agents
    3. View results, comparison table, and citations
    4. Play TTS audio response
    """)

# Main content area
tab1, tab2, tab3 = st.tabs(["🎤 Voice Input", "📊 Results", "📋 Agent Log"])

# Tab 1: Voice Input
with tab1:
    st.header("Audio Input")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Option 1: Record Audio")
        
        # Use Streamlit's audio recorder (simpler and more reliable)
        st.info("💡 **Tip**: For manual stop recording, use the command-line tool: `python test_voice.py`")
        
        # Recording duration selection
        duration_option = st.radio(
            "Recording duration:",
            ["5 seconds", "10 seconds", "30 seconds", "60 seconds", "Custom"],
            horizontal=True,
            help="Select recording duration"
        )
        
        custom_duration = None
        if duration_option == "Custom":
            custom_duration = st.number_input(
                "Enter duration in seconds:",
                min_value=1,
                max_value=300,
                value=10,
                step=1
            )
            duration = custom_duration
        else:
            duration = int(duration_option.split()[0])
        
        record_button = st.button("🎙️ Start Recording", use_container_width=True, type="primary")
        
        if record_button:
            with st.spinner(f"Recording for {duration} seconds... Speak now!"):
                try:
                    audio_path = record_audio(
                        duration=duration,
                        output_path="user_recording.wav"
                    )
                    if audio_path and os.path.exists(audio_path):
                        st.session_state.audio_file_path = audio_path
                        st.success(f"✅ Recording saved: {audio_path}")
                        st.audio(audio_path, format="audio/wav")
                    else:
                        st.error("Recording failed. Please try again.")
                except Exception as e:
                    st.error(f"Recording failed: {str(e)}")
                    st.info("💡 Make sure microphone permissions are granted and try again.")
        
        # Show recorded audio if available
        if st.session_state.get('audio_file_path') and os.path.exists(st.session_state.audio_file_path):
            if not record_button:  # Don't show again if just recorded
                st.audio(st.session_state.audio_file_path, format="audio/wav")
                st.success(f"✅ Recording available: {st.session_state.audio_file_path}")
    
    with col2:
        st.subheader("Option 2: Upload Audio File")
        uploaded_file = st.file_uploader(
            "Choose audio file",
            type=["wav", "mp3", "m4a", "ogg"],
            help="Upload an audio file with your query"
        )
        
        if uploaded_file:
            # Save uploaded file
            upload_path = f"uploaded_{uploaded_file.name}"
            with open(upload_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state.audio_file_path = upload_path
            st.success(f"File uploaded: {uploaded_file.name}")
            st.audio(upload_path)
    
    # Text input fallback
    st.divider()
    st.subheader("Option 3: Type Query")
    text_query = st.text_input(
        "Or type your query directly:",
        placeholder="e.g., Find me eco-friendly wooden puzzles under $20",
        help="Enter your product search query as text"
    )
    
    if text_query:
        st.session_state.transcript = text_query
    
    # Process button
    st.divider()
    process_button = st.button("🚀 Process Query", type="primary", use_container_width=True)
    
    if process_button:
        # Get query from audio or text
        query = None
        
        if st.session_state.audio_file_path:
            # Transcribe audio
            with st.spinner("Transcribing audio..."):
                query = transcribe_audio(st.session_state.audio_file_path)
                if query:
                    st.session_state.transcript = query
                else:
                    st.error("Transcription failed. Please try again.")
                    st.stop()
        elif text_query:
            query = text_query
            st.session_state.transcript = query
        else:
            st.warning("Please record audio, upload a file, or type a query.")
            st.stop()
        
        if query:
            # Display transcript
            st.success(f"📝 Query: **{query}**")
            
            # Process with agents
            with st.spinner("Processing with AI agents..."):
                try:
                    # Run agent graph with logging
                    result = invoke_with_logging(query)
                    
                    # Store results
                    st.session_state.result = result
                    
                    # Get detailed step logs from logger
                    logger = get_logger()
                    step_summary = logger.get_step_summary()
                    execution_stats = logger.get_execution_stats()
                    
                    # Format agent steps for UI
                    st.session_state.agent_steps = step_summary
                    st.session_state.execution_stats = execution_stats
                    st.session_state.log_file = result.get('_logging', {}).get('log_file')
                    
                    st.success("✅ Processing complete!")
                    
                except Exception as e:
                    st.error(f"Error processing query: {str(e)}")
                    st.exception(e)

# Tab 2: Results
with tab2:
    if st.session_state.result:
        result = st.session_state.result
        
        # Final Answer
        st.header("💬 Final Answer")
        st.markdown(f"**Query:** {st.session_state.transcript}")
        st.markdown("---")
        st.markdown(result.get('final_answer', 'No answer generated'))
        
        # TTS Generation
        st.divider()
        st.subheader("🔊 Text-to-Speech")
        
        st.info("💡 **TTS Summary**: Generates a concise ≤15-second voice summary with key recommendations and citations. Full details are shown on screen.")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            tts_button = st.button("🎵 Generate Speech (15s Summary)", use_container_width=True, type="primary")
        
        if tts_button or st.session_state.tts_audio_path:
            if not st.session_state.tts_audio_path:
                with st.spinner("Generating concise speech summary (≤15 seconds)..."):
                    # Use TTS summary from state if available, otherwise generate one
                    tts_text = result.get('tts_summary')
                    if not tts_text:
                        # Generate summary on the fly
                        from src.voice.tts import create_tts_summary
                        tts_text = create_tts_summary(
                            full_answer=result.get('final_answer', ''),
                            citations=result.get('citations', []),
                            max_duration_seconds=15
                        )
                    
                    # Show the summary text
                    with st.expander("📝 View TTS Summary Text"):
                        st.write(tts_text)
                        word_count = len(tts_text.split())
                        st.caption(f"Word count: {word_count} (~{word_count/2.5:.1f} seconds of speech)")
                    
                    # Generate TTS
                    tts_path = text_to_speech(
                        text=tts_text,
                        output_path="response.mp3",
                        voice=selected_voice
                    )
                    if tts_path:
                        st.session_state.tts_audio_path = tts_path
            
            if st.session_state.tts_audio_path and os.path.exists(st.session_state.tts_audio_path):
                st.audio(st.session_state.tts_audio_path, format="audio/mp3")
                st.caption("🎧 **15-second summary** - Full answer and citations shown above")
        
        # Comparison Table
        st.divider()
        st.subheader("📊 Product Comparison Table")
        
        comparison_table = result.get('comparison_table', [])
        if comparison_table:
            # Prepare data for display
            display_data = []
            for item in comparison_table[:10]:  # Limit to top 10
                display_data.append({
                    "Product": item.get('title', 'N/A')[:50] + "..." if len(item.get('title', '')) > 50 else item.get('title', 'N/A'),
                    "Brand": item.get('brand', 'N/A') or 'N/A',
                    "Catalog Price": f"${item.get('catalog_price', 0):.2f}" if item.get('catalog_price') else "N/A",
                    "Web Price": item.get('web_price', 'N/A') or 'N/A',
                    "Sources": ", ".join(item.get('sources', [])),
                    "Conflict": "⚠️" if item.get('has_conflict') else "✓"
                })
            
            st.dataframe(
                display_data,
                use_container_width=True,
                hide_index=True
            )
            
            # Conflicts section
            conflicts = result.get('conflicts', [])
            if conflicts:
                st.warning(f"⚠️ {len(conflicts)} price conflict(s) detected")
                with st.expander("View Conflicts"):
                    for conflict in conflicts:
                        st.markdown(f"**{conflict.get('rag_title', 'Unknown')}**")
                        for c in conflict.get('conflicts', []):
                            st.error(f"  {c.get('message', '')}")
        else:
            st.info("No comparison data available")
        
        # Citations
        st.divider()
        st.subheader("📚 Citations")
        
        citations = result.get('citations', [])
        if citations:
            st.markdown(f"**{len(citations)} citation(s) found:**")
            for citation in citations:
                st.markdown(f'<div class="citation">{citation}</div>', unsafe_allow_html=True)
        else:
            st.info("No citations available")
        
        # Raw Data (expandable)
        with st.expander("🔍 View Raw Data"):
            st.json(result)
    
    else:
        st.info("👆 Process a query in the 'Voice Input' tab to see results here")

# Tab 3: Agent Log
with tab3:
    st.header("🤖 Agent Execution Log")
    
    if st.session_state.agent_steps:
        # Execution Statistics
        if st.session_state.get('execution_stats'):
            stats = st.session_state.execution_stats
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Steps", stats.get('total_steps', 0))
            with col2:
                st.metric("Total Duration", f"{stats.get('total_duration_ms', 0):.0f} ms")
            with col3:
                st.metric("Avg Step Time", f"{stats.get('average_step_time_ms', 0):.1f} ms")
            with col4:
                if st.session_state.get('log_file'):
                    st.caption(f"📄 Log: {Path(st.session_state.log_file).name}")
        
        st.divider()
        
        # Detailed Step Logs
        st.subheader("📋 Step-by-Step Execution")
        for i, step in enumerate(st.session_state.agent_steps, 1):
            with st.expander(f"**{step['status']} Step {i}: {step['node'].upper()}** - {step['duration_ms']:.0f}ms", expanded=(i <= 2)):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Timestamp:**")
                    st.caption(step['timestamp'])
                    
                    st.markdown("**Duration:**")
                    st.caption(f"{step['duration_ms']:.2f} ms")
                
                with col2:
                    st.markdown("**Input Summary:**")
                    st.caption(step.get('input_summary', 'N/A'))
                    
                    st.markdown("**Output Summary:**")
                    st.caption(step.get('output_summary', 'N/A'))
                
                # Tool Calls (if any)
                tool_calls = step.get('tool_calls', [])
                if tool_calls:
                    st.markdown("**🔧 Tool Calls:**")
                    for tool_call in tool_calls:
                        tool_status = "✅" if tool_call.get('success') else "❌"
                        st.markdown(f"{tool_status} **{tool_call['tool']}** ({tool_call['duration_ms']:.0f}ms)")
                        if not tool_call.get('success'):
                            st.error(f"Error: {tool_call.get('error', 'Unknown error')}")
                        with st.expander(f"View {tool_call['tool']} details"):
                            st.json({
                                "params": tool_call.get('params', {}),
                                "result": tool_call.get('result', {}),
                                "success": tool_call.get('success', False)
                            })
                
                # Full Data
                with st.expander("🔍 View Full Step Data"):
                    st.json({
                        "node": step['node'],
                        "timestamp": step['timestamp'],
                        "duration_ms": step['duration_ms'],
                        "input": step.get('input', {}),
                        "output": step.get('output', {})
                    })
        
        # Execution Timeline
        st.divider()
        st.subheader("⏱️ Execution Timeline")
        
        if st.session_state.agent_steps:
            timeline_data = []
            cumulative_time = 0
            for step in st.session_state.agent_steps:
                cumulative_time += step['duration_ms']
                timeline_data.append({
                    "Step": step['node'].upper(),
                    "Duration (ms)": f"{step['duration_ms']:.0f}",
                    "Cumulative (ms)": f"{cumulative_time:.0f}",
                    "Status": step['status']
                })
            
            df = pd.DataFrame(timeline_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Log File Download
        # Log File Download
        if st.session_state.get('log_file') and os.path.exists(st.session_state.log_file):
            st.divider()
            st.subheader("📥 Download Log File")
            with open(st.session_state.log_file, 'r') as f:
                log_content = f.read()
            st.download_button(
                label="📥 Download JSON Log",
                data=log_content,
                file_name=Path(st.session_state.log_file).name,
                mime="application/json"
            )
    else:
        st.info("👆 Process a query to see agent execution steps")
    
    # Agent Flow Diagram
    st.divider()
    st.subheader("🔄 Agent Workflow")
    st.markdown("""
    ```
    User Query
        ↓
    Router → Extract Intent
        ↓
    Safety → Content Check
        ↓
    Planner → Decide Tools
        ↓
    Executor → Call MCP Tools
        ↓
    Reconciler → Match & Compare
        ↓
    Synthesizer → Generate Answer
        ↓
    Final Response
    ```
    """)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>Voice-to-Voice Product Discovery Assistant | Powered by LangGraph, OpenAI, and Brave Search</p>
</div>
""", unsafe_allow_html=True)

