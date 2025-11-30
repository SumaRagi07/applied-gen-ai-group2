"""
Streamlit UI for the voice-to-voice product assistant.
Refactored to use native st.audio_input for reliable browser-based recording.
Matches the "CommercialGPT" HTML design structure.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import pandas as pd
import streamlit as st

# --- Import your actual backend functions here ---
from src.voice.asr import transcribe_audio
from src.voice.tts import text_to_speech, VOICE_INFO, get_available_voices
from src.agents.graph import agent_graph

# ----------------- Page config -----------------
st.set_page_config(
    page_title="CommercialGPT - Voice Product Assistant",
    page_icon="🛍️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ----------------- "CommercialGPT" Theme CSS -----------------
st.markdown(
    """
    <style>
    :root {
        --primary-color: #2E7D32; /* Eco Green */
        --bg-light: #F5F7F5;
        --text-dark: #333;
        --shadow: 0 4px 6px rgba(0,0,0,0.1);
        --card-radius: 15px;
    }

    [data-testid="stAppViewContainer"] {
        background-color: var(--bg-light);
        color: var(--text-dark);
    }
    [data-testid="stHeader"] { background: transparent; }

    h1, h2, h3 { color: var(--primary-color) !important; }

    /* Generic Card Container */
    .eco-card {
        background: white;
        padding: 30px;
        border-radius: var(--card-radius);
        box-shadow: var(--shadow);
        margin-bottom: 25px;
    }

    .eco-card.centered {
        text-align: center;
    }

    /* Comparison Table */
    .comparison-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
        font-size: 0.95rem;
    }
    .comparison-table th {
        background-color: var(--primary-color);
        color: white;
        text-align: left;
        padding: 12px 15px;
        font-weight: 500;
    }
    .comparison-table td {
        text-align: left;
        padding: 12px 15px;
        border-bottom: 1px solid #eee;
        vertical-align: top;
    }

    /* Citation Badges */
    .citation-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-top: 5px;
        margin-right: 5px;
    }
    .citation-private {
        background-color: #E0F2F1;
        color: #00695C;
        border: 1px solid #00695C;
    }
    .citation-live {
        background-color: #FFF3E0;
        color: #E65100;
        border: 1px solid #E65100;
    }

    /* Center the audio input widget */
    [data-testid="stAudioInput"] {
        margin: 0 auto;
        max-width: 400px;
    }

    /* Conversation bubbles (chat_message) */
    [data-testid="stChatMessage"] {
        background: #ffffff;
        border-radius: 14px;
        padding: 10px 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.04);
        margin-bottom: 10px;
    }

    [data-testid="stChatMessageContent"],
    [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessageContent"] li {
        color: #111827 !important;
        opacity: 1 !important;
    }

    [data-testid="stChatMessageAvatarIcon"] {
        background-color: var(--primary-color);
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------- Session state init -----------------
def init_state() -> None:
    """Ensure required session state keys exist."""
    defaults = {
        "transcript": None,
        "result": None,
        "tts_path": None,
        "run_error": None,
        "last_audio_id": None,  # To track if audio is new
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


# ----------------- Backend Pipeline -----------------
def run_pipeline(
    input_query: str,
    is_audio_input: bool,
    auto_tts: bool,
    voice: str,
) -> Tuple[Optional[str], Optional[dict], Optional[str], Optional[str]]:
    """
    Orchestrates ASR (if needed), LangGraph agent execution, and TTS.
    Returns: (transcript, result_dict, tts_path, error_msg)
    """
    transcript = input_query

    # 1. ASR Stage (if input is an audio path)
    if is_audio_input:
        try:
            transcript = transcribe_audio(input_query)
            if not transcript:
                return None, None, None, "Transcription returned empty text."
        except Exception as e:
            return None, None, None, f"ASR Failed: {e}"

    # 2. Agent/LangGraph Stage
    try:
        result = agent_graph.invoke({"user_query": transcript})
    except Exception as exc:
        return transcript, None, None, f"Agent Graph Failed: {exc}"

    # 3. TTS Stage
    tts_path = None
    final_answer = result.get("final_answer")
    if auto_tts and final_answer:
        try:
            tmp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tmp_audio.close()
            tts_text = final_answer[:500] if len(final_answer) > 800 else final_answer

            tts_path = text_to_speech(
                text=tts_text,
                output_path=tmp_audio.name,
                voice=voice,
            )
        except Exception as exc:
            print(f"TTS Failed: {exc}")

    return transcript, result, tts_path, None


# ----------------- HTML Table Generation Helper -----------------
def generate_html_table(rag_results: List[Dict[str, Any]], web_results: List[Dict[str, Any]]) -> str:
    """Generates the HTML string for the Comparison Table with citation badges."""
    if not rag_results and not web_results:
        return "<p>No specific products found to compare.</p>"

    rows_html = ""

    # Private Catalog Results (RAG)
    for item in rag_results:
        title = item.get("title", "N/A")[:100]
        price = f"${item.get('price'):.2f}" if item.get("price") else "N/A"
        rating = f"{item.get('rating')} ★" if item.get("rating") else "N/A"
        features = f"Brand: {item.get('brand')}. {item.get('features', '')[:80]}..."

        doc_id = item.get("doc_id", "unknown")
        citation_html = (
            f'<span class="citation-badge citation-private">'
            f'Private Catalog (ID: {doc_id})</span>'
        )

        rows_html += (
            f"<tr><td><strong>{title}</strong></td>"
            f"<td>{price}</td><td>{rating}</td><td>{features}</td>"
            f"<td>{citation_html}</td></tr>"
        )

    # Live Web Results
    for item in web_results:
        title = item.get("title", "Web Result")[:100]
        price = item.get("price", "Check link")
        rating = "Live check"
        snippet = item.get("snippet", "")[:100] + "..."
        url = item.get("url", "#")
        source = item.get("source", "Web")

        citation_html = (
            f'<a href="{url}" target="_blank" style="text-decoration:none;">'
            f'<span class="citation-badge citation-live">Live: {source} ↗</span>'
            f"</a>"
        )

        rows_html += (
            f"<tr><td><strong>{title}</strong></td>"
            f"<td>{price}</td><td>{rating}</td><td>{snippet}</td>"
            f"<td>{citation_html}</td></tr>"
        )

    table_html = f"""
    <div style="overflow-x: auto;">
        <table class="comparison-table">
            <thead>
                <tr>
                    <th style="width: 25%;">Product Name</th>
                    <th style="width: 10%;">Price</th>
                    <th style="width: 10%;">Rating</th>
                    <th style="width: 35%;">Key Features / Snippet</th>
                    <th style="width: 20%;">Data Source (Citation)</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """
    return table_html


# ----------------- Main App Layout -----------------
def main():
    init_state()

    # --- Sidebar ---
    with st.sidebar:
        st.header("Settings")
        voice_choice = st.selectbox(
            "TTS Voice",
            get_available_voices(),
            index=0,
            format_func=lambda v: f"{v} - {VOICE_INFO.get(v, '')}",
        )
        auto_tts_on = st.checkbox("Auto-play Response", value=True)
        st.markdown("---")
        input_mode = st.radio(
            "Input Mode",
            ["Voice (Live)", "Text Debug"],
            horizontal=True,
        )

    # --- Header ---
    st.markdown(
        "<div style='text-align: center; margin-bottom: 20px;'>",
        unsafe_allow_html=True,
    )
    st.title("🛍️ CommercialGPT Voice Assistant")
    st.caption("Agentic product discovery with private catalog + live web tools")
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Section 1: Hero Interaction Area ---
    st.markdown('<div class="eco-card centered">', unsafe_allow_html=True)

    # 1. Input Handling
    audio_value = None
    user_text = None

    if input_mode == "Voice (Live)":
        st.subheader("Click the mic to start asking...")
        audio_value = st.audio_input("Record your query")
    else:
        user_text = st.text_input("Type your query here...")
        st.write("")  # spacer
        run_text = st.button("Run Agent")

    # 2. Processing Logic
    should_run_audio = False
    should_run_text = False

    if audio_value is not None:
        should_run_audio = True
    if input_mode == "Text Debug" and user_text and run_text:
        should_run_text = True

    if should_run_audio or should_run_text:
        with st.spinner("🧠 CommercialGPT is thinking..."):
            if should_run_audio:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                    tmp_wav.write(audio_value.read())
                    query_input = tmp_wav.name
                is_audio = True
            else:
                query_input = user_text
                is_audio = False

            transcript, result, tts_path, err = run_pipeline(
                input_query=query_input,
                is_audio_input=is_audio,
                auto_tts=auto_tts_on,
                voice=voice_choice,
            )

            st.session_state.run_error = err
            st.session_state.transcript = transcript
            st.session_state.result = result
            st.session_state.tts_path = tts_path

    # 3. Output TTS Player (in Hero section)
    if st.session_state.tts_path:
        st.success("Analysis Complete!")
        st.audio(
            st.session_state.tts_path,
            format="audio/mp3",
            autoplay=auto_tts_on,
        )

    st.markdown("</div>", unsafe_allow_html=True)  # end eco-card

    # --- Section 2: Conversation Card (like your Figure 2) ---
    if st.session_state.transcript:
        st.markdown('<div class="eco-card">', unsafe_allow_html=True)
        st.subheader("Conversation")

        with st.chat_message("user", avatar="👤"):
            st.write(st.session_state.transcript)

        with st.chat_message("assistant", avatar="🌿"):
            if st.session_state.run_error:
                st.error(st.session_state.run_error)
            elif st.session_state.result:
                st.write(
                    st.session_state.result.get(
                        "final_answer", "No answer generated."
                    )
                )
            else:
                st.write("No answer generated.")

        st.markdown("</div>", unsafe_allow_html=True)

    # --- Section 3: Reasoning Trace ---
    if st.session_state.result:
        with st.expander("🧠 View Agent Reasoning & Tool Calls", expanded=False):
            res = st.session_state.result
            if res.get("intent"):
                st.markdown("**Intent:**")
                st.json(res["intent"])
            if res.get("plan"):
                st.markdown("**Plan:**")
                st.write(res["plan"])
            if res.get("rag_params"):
                st.markdown("**Tool Params:**")
                st.json(res["rag_params"])

    # --- Section 4: Comparison Table ---
    if st.session_state.result:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Recommended Products")

        rag_data = st.session_state.result.get("rag_results", [])
        web_data = st.session_state.result.get("web_results", [])

        table_html = generate_html_table(rag_data, web_data)

        st.markdown('<div class="eco-card" style="padding: 15px;">', unsafe_allow_html=True)
        st.markdown(table_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
