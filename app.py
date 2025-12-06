"""
Streamlit UI for Voice-to-Voice Product Discovery Assistant
Beautiful single-page design with live progress and product cards
"""

import streamlit as st
import sys
import os
from pathlib import Path
import time
import json
import pandas as pd
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.voice.asr import transcribe_audio, record_audio, BackgroundRecorder
from src.voice.tts import text_to_speech, VOICE_INFO
from src.agents.graph import invoke_with_logging

# Page config
st.set_page_config(
    page_title="Voice Product Assistant",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
if 'result' not in st.session_state:
    st.session_state.result = None
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None
if 'tts_audio_path' not in st.session_state:
    st.session_state.tts_audio_path = None
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'recorder' not in st.session_state:
    st.session_state.recorder = BackgroundRecorder()
if 'is_recording' not in st.session_state:
    st.session_state.is_recording = False
if 'recording_start_time' not in st.session_state:
    st.session_state.recording_start_time = None

# Custom CSS - Dark theme with beautiful styling
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
    }
    
    /* Headers */
    h1 {
        color: #00d4ff;
        text-align: center;
        font-weight: 700;
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
        margin-bottom: 2rem;
    }
    
    h2, h3 {
        color: #00d4ff;
        font-weight: 600;
    }
    
    /* Product cards */
    .product-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(0, 212, 255, 0.2);
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .product-card:hover {
        border-color: rgba(0, 212, 255, 0.5);
        box-shadow: 0 5px 25px rgba(0, 212, 255, 0.2);
        transform: translateY(-2px);
    }
    
    /* Progress step */
    .step-progress {
        background: rgba(0, 212, 255, 0.1);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #00d4ff;
        animation: slideIn 0.3s ease;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(0, 212, 255, 0.4);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #00d4ff;
        font-size: 1.5rem;
        font-weight: 700;
    }
    
    /* Success/Error messages */
    .stSuccess {
        background: rgba(0, 255, 128, 0.1);
        border-left: 4px solid #00ff80;
    }
    
    .stError {
        background: rgba(255, 0, 0, 0.1);
        border-left: 4px solid #ff0000;
    }
    
    .stWarning {
        background: rgba(255, 165, 0, 0.1);
        border-left: 4px solid #ffa500;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(30, 30, 46, 0.95);
        backdrop-filter: blur(10px);
    }
    
    /* Audio player */
    audio {
        width: 100%;
        border-radius: 10px;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(0, 212, 255, 0.1);
        border-radius: 10px;
        color: #00d4ff;
    }
    
    /* Price badges */
    .price-increase {
        color: #ff4444;
        font-weight: 600;
    }
    
    .price-decrease {
        color: #00ff80;
        font-weight: 600;
    }
    
    /* Citation badge */
    .citation-badge {
        display: inline-block;
        background: rgba(0, 212, 255, 0.2);
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        margin: 0.25rem;
        font-size: 0.85rem;
        font-family: monospace;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
    # Voice selection
    st.markdown("### 🎵 TTS Voice")
    selected_voice = st.selectbox(
        "Choose voice:",
        options=list(VOICE_INFO.keys()),
        index=0,
        help="Select voice for audio responses"
    )
    st.caption(f"*{VOICE_INFO[selected_voice]}*")
    
    st.divider()
    
    # MCP Server status
    st.markdown("### 🔌 Server Status")
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            st.success("✅ MCP Server Online")
        else:
            st.error("❌ Server Error")
    except:
        st.warning("⚠️ MCP Server Offline")
        st.info("Start server:\n```bash\npython src/mcp_server/server.py\n```")
    
    st.divider()
    
    # Quick stats (if result exists)
    if st.session_state.result:
        st.markdown("### 📊 Last Query Stats")
        stats = st.session_state.result.get('_logging', {}).get('execution_stats', {})
        st.metric("Duration", f"{stats.get('total_duration_ms', 0)/1000:.1f}s")
        st.metric("Products", len(st.session_state.result.get('comparison_table', [])))
        st.metric("Citations", len(st.session_state.result.get('citations', [])))
    
    st.divider()
    
    # ✅ Cache Management
    st.markdown("### 🗑️ Cache Management")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        if st.button("Clear Cache", use_container_width=True, type="secondary"):
            try:
                # Clear MCP server cache via API
                import requests
                response = requests.post("http://localhost:8000/clear_cache", timeout=5)
                if response.status_code == 200:
                    st.success("✅ Server cache cleared!")
                else:
                    st.warning("⚠️ Server cache clear failed")
            except:
                st.error("❌ Cannot reach server")
            
            # Clear Streamlit cache
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("✅ UI cache cleared!")
    
    with col_b:
        if st.button("Refresh Stats", use_container_width=True):
            st.rerun()
    
    st.caption("Clear cache if results seem outdated")
    
    
    
# Main header
st.markdown("<h1>🎤 Voice-to-Voice Product Discovery</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888; margin-bottom: 2rem;'>Speak, search, and discover products with AI-powered price comparison</p>", unsafe_allow_html=True)

# Input section
st.markdown("### 🎙️ Your Query")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Option 1: Record**")
    
    if not st.session_state.is_recording:
        if st.button("🎙️ Start Recording", use_container_width=True, type="primary"):
            # Start background recording
            success = st.session_state.recorder.start_recording()
            if success:
                st.session_state.is_recording = True
                st.session_state.recording_start_time = time.time()
                st.rerun()
            else:
                st.error("Failed to start recording. Check microphone permissions.")
    else:
        # Show recording status with live timer
        elapsed = int(time.time() - st.session_state.recording_start_time)
        st.warning(f"🔴 Recording... ({elapsed}s)")
        
        if st.button("⏹️ Stop Recording", use_container_width=True, type="secondary"):
            # Stop background recording and save
            with st.spinner("Saving recording..."):
                audio_path = st.session_state.recorder.stop_recording("user_recording.wav")
                if audio_path:
                    st.session_state.audio_file_path = audio_path
                    st.session_state.is_recording = False
                    st.success(f"✓ Recorded {elapsed}s!")
                else:
                    st.error("Failed to save recording")
                    st.session_state.is_recording = False
            st.rerun()

with col2:
    st.markdown("**Option 2: Upload**")
    uploaded = st.file_uploader("Choose file", type=["wav", "mp3", "m4a"], label_visibility="collapsed")
    if uploaded:
        path = f"uploaded_{uploaded.name}"
        with open(path, "wb") as f:
            f.write(uploaded.getbuffer())
        st.session_state.audio_file_path = path
        st.success("✓ Uploaded!")

with col3:
    st.markdown("**Option 3: Type**")
    text_query = st.text_input("Type query", placeholder="eco puzzles under $20", label_visibility="collapsed")
    if text_query:
        st.session_state.transcript = text_query

# ✅ ADD: Show current audio with clear button
if st.session_state.audio_file_path and os.path.exists(st.session_state.audio_file_path):
    col_audio, col_clear = st.columns([4, 1])
    
    with col_audio:
        st.audio(st.session_state.audio_file_path)
    
    with col_clear:
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Clear", use_container_width=True, type="secondary"):
            # Clear audio file
            st.session_state.audio_file_path = None
            st.session_state.transcript = ""
            st.success("Audio cleared!")
            st.rerun()

# Process button
st.markdown("---")
if st.button("🚀 Search Products", type="primary", use_container_width=True):
    query = None
    
    # Get query
    if st.session_state.audio_file_path:
        with st.spinner("Transcribing..."):
            query = transcribe_audio(st.session_state.audio_file_path)
            st.session_state.transcript = query
    elif text_query:
        query = text_query
    else:
        st.warning("Please provide audio or text query")
        st.stop()
    
    if query:
        st.success(f"📝 **Query:** {query}")
        
        # Live progress
        st.markdown("### ⏳ Processing...")
        progress_bar = st.progress(0)
        status_container = st.empty()
        
        steps = [
            ("🔄", "Router", "Extracting intent"),
            ("🛡️", "Safety", "Checking content"),
            ("📋", "Planner", "Planning search"),
            ("⚡", "Executor", "Searching catalog & web"),
            ("🔀", "Reconciler", "Comparing prices"),
            ("✍️", "Synthesizer", "Generating answer")
        ]
        
        # Show progress animation
        for i, (icon, name, desc) in enumerate(steps):
            progress_bar.progress((i + 1) / len(steps))
            status_container.markdown(
                f'<div class="step-progress">{icon} <strong>{name}</strong> - {desc}...</div>',
                unsafe_allow_html=True
            )
            time.sleep(0.3)
        
        # Actually process
        with st.spinner("Finalizing..."):
            result = invoke_with_logging(query)
            st.session_state.result = result
            
            # Generate TTS
            tts_text = result.get('tts_summary', result.get('final_answer', '')[:500])
            tts_path = text_to_speech(tts_text, "response.mp3", selected_voice)
            st.session_state.tts_audio_path = tts_path
        
        progress_bar.progress(1.0)
        status_container.success("✅ Complete!")
        time.sleep(0.5)
        st.rerun()
# Results section
if st.session_state.result:
    result = st.session_state.result
    
    st.markdown("---")
    st.markdown("## Results")
    
    # Audio response
    if st.session_state.tts_audio_path:
        st.markdown("### 🔊 Audio Summary")
        st.audio(st.session_state.tts_audio_path)
        st.caption("15-second voice summary - Full details below")
    
    st.markdown("---")
    
    # Products with images
    st.markdown("### 🛍️ Product Recommendations")
    
    comparison_table = result.get('comparison_table', [])
    catalog_products = [p for p in comparison_table if p.get('catalog_price')]
    
    if catalog_products:
        for product in catalog_products[:5]:
            st.markdown('<div class="product-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 4])
            
            with col1:
                # Product image - handle multiple images separated by |
                img_url = product.get('image_url')
                if img_url and str(img_url).strip() and img_url != 'N/A':
                    # Handle multiple images (take first one)
                    if '|' in str(img_url):
                        img_url = img_url.split('|')[0].strip()
                    
                    try:
                        st.image(img_url, width=150)
                    except Exception as e:
                        st.markdown("🖼️<br>Image unavailable", unsafe_allow_html=True)
                else:
                    st.markdown("🖼️<br>No image", unsafe_allow_html=True)
            
            with col2:
                # Product title
                st.markdown(f"### {product.get('title', 'Unknown Product')}")
                
                # Price comparison
                col_a, col_b, col_c = st.columns(3)
                
                catalog_price = product.get('catalog_price', 0)
                web_price = product.get('web_price')
                
                with col_a:
                    st.metric("Catalog (2020)", f"${catalog_price:.2f}")
                
                with col_b:
                    if web_price:
                        st.metric(
                            f"Current",
                            f"${web_price:.2f}"
                        )
                
                with col_c:
                    if web_price and catalog_price:
                        diff = ((web_price - catalog_price) / catalog_price) * 100
                        color_class = "price-increase" if diff > 0 else "price-decrease"
                        st.markdown(
                            f'<div class="{color_class}" style="font-size: 1.5rem; margin-top: 1rem;">'
                            f'{"↑" if diff > 0 else "↓"} {abs(diff):.1f}%</div>',
                            unsafe_allow_html=True
                        )
                
                # Tags and info
                tags = []
                if product.get('eco_friendly'):
                    tags.append("♻️ Eco-friendly")
                if product.get('brand'):
                    tags.append(f"🏷️ {product['brand']}")
                if product.get('web_source'):
                    tags.append(f"🛒 {product['web_source']}")
                
                if tags:
                    st.markdown(" · ".join(tags))
                
                # ✅ UPDATED: Links as buttons in columns
                col_link1, col_link2 = st.columns(2)
                
                with col_link1:
                    product_url = product.get('product_url')
                    if product_url and str(product_url).strip() and product_url != 'N/A':
                        st.link_button("🔗 View on Amazon", product_url, use_container_width=True)
                
                with col_link2:
                    web_url = product.get('web_url')
                    if web_url and str(web_url).strip() and web_url != 'N/A':
                        st.link_button("🛒 Current Price", web_url, use_container_width=True, type="secondary")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Web alternatives
    web_only = [p for p in comparison_table if p.get('type') == 'web_only']
    if web_only:
        st.markdown("### 🌐 Alternative Options Online")
        
        for product in web_only[:3]:
            st.markdown('<div class="product-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 4])
            
            with col1:
                # Product image from web thumbnail
                img_url = product.get('image_url')
                
                if img_url and str(img_url).strip() and img_url not in ['N/A', 'None', '']:
                    try:
                        st.image(img_url, width=150)
                    except:
                        st.markdown(
                            '<div style="width: 150px; height: 150px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
                            'border-radius: 10px; display: flex; align-items: center; justify-content: center; '
                            'font-size: 4rem;">🌐</div>',
                            unsafe_allow_html=True
                        )
                else:
                    st.markdown(
                        '<div style="width: 150px; height: 150px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
                        'border-radius: 10px; display: flex; align-items: center; justify-content: center; '
                        'font-size: 4rem;">🌐</div>',
                        unsafe_allow_html=True
                    )
            
            with col2:
                # Full title
                st.markdown(f"### {product.get('title', 'Unknown Product')}")
                
                # Price and source
                col_a, col_b = st.columns(2)
                
                with col_a:
                    price = product.get('web_price', 0)
                    st.metric("Price", f"${price:.2f}" if price else "N/A")
                
                with col_b:
                    source = product.get('web_source', 'Unknown')
                    st.write(f"**Source:** {source}")
                
                # Rating and reviews
                if product.get('rating'):
                    reviews = product.get('reviews', 0)
                    st.write(f"⭐ {product['rating']}/5 ({reviews:,} reviews)" if reviews else f"⭐ {product['rating']}/5")
                
                # ✅ UPDATED: Link as button
                web_url = product.get('web_url') or product.get('product_url')
                if web_url and str(web_url).strip():
                    st.link_button("🔗 View on Google Shopping", web_url, use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Full answer (collapsible)
    with st.expander("📄 Full Detailed Answer"):
        answer_text = result.get('final_answer', '')
        st.code(answer_text, language="markdown")
    
    # Price comparison table (collapsible)
    with st.expander("📊 Price Comparison Table"):
        table_data = []
        for item in comparison_table[:10]:
            cat_price = item.get('catalog_price', 0)
            web_price = item.get('web_price', 0)
            diff = ((web_price - cat_price) / cat_price * 100) if cat_price and web_price else 0
            
            table_data.append({
                "Product": item.get('title', '')[:40],
                "2020": f"${cat_price:.2f}" if cat_price else "—",
                "Now": f"${web_price:.2f}" if web_price else "—",
                "Change": f"{diff:+.1f}%" if diff else "—",
                "Source": (item.get('web_source') or 'Catalog')[:15]
            })
        
        st.dataframe(table_data, width="stretch", hide_index=True)
    
    # Agent execution log (collapsible)
    with st.expander("🤖 Agent Execution Log"):
        logs = result.get('_logging', {})
        steps = logs.get('step_summary', [])
        
        for step in steps:
            st.markdown(
                f"**{step.get('status', '✓')} {step.get('node', 'Unknown').upper()}** "
                f"- {step.get('duration_ms', 0):.0f}ms"
            )
        
        stats = logs.get('execution_stats', {})
        st.metric("Total Duration", f"{stats.get('total_duration_ms', 0)/1000:.2f}s")
    
    # Citations (collapsible)
    with st.expander("📚 Citations & Sources"):
        citations = result.get('citations', [])
        for citation in citations:
            st.markdown(f'<span class="citation-badge">{citation}</span>', unsafe_allow_html=True)
# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #666; padding: 1rem;'>"
    "Powered by LangGraph · OpenAI · SerpAPI · ChromaDB"
    "</p>",
    unsafe_allow_html=True
)