"""
Streamlit UI for the voice-to-voice product assistant.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import sounddevice as sd
import streamlit as st
from scipy.io import wavfile

from src.voice.asr import transcribe_audio
from src.voice.tts import text_to_speech, VOICE_INFO, get_available_voices
from src.agents.graph import agent_graph

# ----------------- Page config -----------------
st.set_page_config(
    page_title="Agentic Voice Product Assistant",
    page_icon="🎤",
    layout="wide",
)

# ----------------- Light, high-contrast theme -----------------
st.markdown(
    """
    <style>
    :root {
        --bg: #eef2ff;
        --panel: #ffffff;
        --text: #0f172a;
        --accent: #2563eb;
        --muted: #4b5563;
    }
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 20% 20%, #eef2ff 0, #f8fafc 40%, #e8edf7 100%);
        color: var(--text);
    }
    [data-testid="stAppViewContainer"] * {
        color: var(--text);
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] {
        background: #0f172a;
        color: #f8fafc;
        border-right: 1px solid #111827;
    }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    .stButton > button {
        border-radius: 8px !important;
        padding: 0.6rem 1.4rem;
        font-weight: 600;
        border: none;
        background-color: var(--accent) !important;
        color: #ffffff !important;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
    }
    .stButton > button:hover { filter: brightness(1.05); }
    .card {
        background: var(--panel);
        border-radius: 16px;
        padding: 1.1rem 1.3rem;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
        border: 1px solid #e2e6f0;
    }
    .card h3, .card h4 { margin-top: 0.2rem; margin-bottom: 0.5rem; }
    .small-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted) !important;
        font-weight: 600;
    }
    .stSelectbox div[data-baseweb="select"] {
        background: var(--panel);
        color: var(--text);
        border: 1px solid #d5d9e6;
    }
    .stRadio > label { color: var(--text); }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------- Session state -----------------
def init_state() -> None:
    """Ensure required session state keys exist."""
    defaults = {
        "audio_path": None,
        "transcript": None,
        "result": None,
        "tts_path": None,
        "run_error": None,
        "last_run_ts": None,
        "last_run_ms": None,
        "last_status": "Waiting for running",
        "is_recording": False,
        "rec_buffer": [],
        "stream": None,
        "record_start_ts": None,
        "sample_rate": 16000,
        "target_audio_path": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


# ----------------- Helpers -----------------
def save_uploaded_audio(uploaded_file) -> str:
    """Save uploaded audio to a temp file and return its path."""
    suffix = Path(uploaded_file.name).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name


def run_pipeline(
    text_query: str,
    auto_tts: bool,
    voice: str,
) -> Tuple[Optional[dict], Optional[str], Optional[str], Optional[float]]:
    """
    Run LangGraph on the query and optionally generate TTS.

    Returns: (result_state, tts_path, error_message, duration_ms)
    """
    start = datetime.utcnow()
    try:
        result = agent_graph.invoke({"user_query": text_query})
    except Exception as exc:
        return None, None, f"Agent failed: {exc}", None

    tts_path = None
    if auto_tts and result and result.get("final_answer"):
        try:
            tmp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tmp_audio.close()
            tts_path = text_to_speech(
                text=result["final_answer"],
                output_path=tmp_audio.name,
                voice=voice,
            )
        except Exception as exc:
            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
            return result, None, f"TTS failed: {exc}", duration_ms

    duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
    return result, tts_path, None, duration_ms


def log_run(
    mode: str,
    transcript: str,
    result: Optional[dict],
    tts_path: Optional[str],
    duration_ms: Optional[float],
) -> Optional[str]:
    """Persist a JSON log for grading/traceability."""
    try:
        Path("runs").mkdir(exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        log_path = Path("runs") / f"run-{ts}.json"
        payload = {
            "timestamp_utc": ts,
            "mode": mode,
            "transcript": transcript,
            "result": result,
            "tts_path": tts_path,
            "duration_ms": duration_ms,
        }
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return str(log_path)
    except Exception:
        return None


# ----------------- Local recording helpers -----------------
def start_recording() -> bool:
    """Start open-ended recording with the local mic."""
    if st.session_state.is_recording:
        return False

    buffer = []

    def audio_callback(indata, frames, time, status):  # pragma: no cover - UI path
        if status:
            print(status)
        buffer.append(indata.copy())

    try:
        stream = sd.InputStream(
            samplerate=st.session_state.sample_rate,
            channels=1,
            dtype="int16",
            callback=audio_callback,
        )
        stream.start()
    except Exception as exc:  # pragma: no cover - hardware dependent
        st.session_state.stream = None
        st.session_state.is_recording = False
        st.session_state.rec_buffer = []
        st.session_state.record_start_ts = None
        st.session_state.target_audio_path = None
        st.session_state.run_error = f"Mic error: {exc}"
        return False

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close()

    st.session_state.stream = stream
    st.session_state.is_recording = True
    st.session_state.rec_buffer = buffer
    st.session_state.record_start_ts = datetime.utcnow()
    st.session_state.target_audio_path = tmp.name
    return True


def stop_recording() -> Tuple[Optional[str], Optional[float]]:
    """Stop recording and save to WAV. Returns (path, duration_seconds)."""
    if not st.session_state.is_recording or st.session_state.stream is None:
        return None, None

    try:
        st.session_state.stream.stop()
        st.session_state.stream.close()
    except Exception:
        pass

    st.session_state.is_recording = False
    st.session_state.stream = None

    if not st.session_state.rec_buffer:
        return None, None

    audio = np.concatenate(st.session_state.rec_buffer, axis=0)
    duration = len(audio) / float(st.session_state.sample_rate)

    wavfile.write(st.session_state.target_audio_path, st.session_state.sample_rate, audio)
    st.session_state.audio_path = st.session_state.target_audio_path

    # Reset buffer
    st.session_state.rec_buffer = []
    st.session_state.record_start_ts = None
    st.session_state.target_audio_path = None

    return st.session_state.audio_path, duration


# ----------------- Retrieval results formatting -----------------
def format_rag_dataframe(rag_results: list) -> Optional[pd.DataFrame]:
    """Convert RAG results to a DataFrame for display."""
    if not rag_results:
        return None
    rows = []
    for item in rag_results:
        rows.append(
            {
                "doc_id": item.get("doc_id"),
                "Title": item.get("title", "")[:120],
                "Price($)": item.get("price"),
                "Brand": item.get("brand"),
                "Category": item.get("main_category"),
                "Eco": item.get("eco_friendly"),
                "Rel.": item.get("relevance_score"),
            }
        )
    df = pd.DataFrame(rows)
    return df


def format_web_dataframe(web_results: list) -> Optional[pd.DataFrame]:
    """Convert web search results to a DataFrame for display."""
    if not web_results:
        return None
    rows = []
    for item in web_results:
        rows.append(
            {
                "Title": item.get("title", "")[:120],
                "Price": item.get("price"),
                "Source": item.get("source"),
                "URL": item.get("url"),
            }
        )
    df = pd.DataFrame(rows)
    return df


# ----------------- Main app -----------------
def main():
    init_state()

    # Title block
    st.markdown(
        """
        <div style="margin-bottom: 0.6rem;">
            <div class="small-label">Voice → Whisper → LangGraph agents → RAG + Web search → TTS</div>
            <h1 style="margin: 0.1rem 0 0.2rem 0;">🎤 Agentic Voice Product Assistant</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Status metrics
    status_cols = st.columns(3)
    status_cols[0].metric("Status", st.session_state.last_status)
    status_cols[1].metric(
        "Latest Run (UTC)",
        st.session_state.last_run_ts or "—",
    )
    status_cols[2].metric(
        "Time Spent (ms)",
        f"{st.session_state.last_run_ms:.0f}" if st.session_state.last_run_ms else "—",
    )

    # Sidebar settings
    with st.sidebar:
        st.header("Input & TTS settings")
        auto_tts = st.checkbox("Auto-generate TTS after answer", value=True)
        voice_choice = st.selectbox(
            "Voice",
            get_available_voices(),
            format_func=lambda v: f"{v} — {VOICE_INFO.get(v, '')}",
        )
        st.markdown("---")
        st.markdown(
            "#### Tips\n"
            "- Ensure MCP server is running on **localhost:8000**.\n"
            "- If agents fail, double-check `.env` and API keys."
        )

    # Layout: left = input, right = outputs
    col_input, col_output = st.columns([1.05, 1.95])

    # -------- Left: input card --------
    with col_input:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("User input")

        mode = st.radio(
            "How do you want to ask?",
            ["Computer Recording", "Upload Audio", "Text Input"],
            index=0,
        )

        audio_path: Optional[str] = None
        text_query: Optional[str] = None
        if mode == "Computer Recording":
            st.caption("Use your computer mic. Click **Start**, speak, then **Stop**.")
            start_col, stop_col = st.columns(2)
            with start_col:
                if st.button("Start recording", type="primary", disabled=st.session_state.is_recording):
                    ok = start_recording()
                    if ok:
                        st.toast("Recording started", icon="🎙️")
            with stop_col:
                if st.button("Stop recording", disabled=not st.session_state.is_recording):
                    path, dur = stop_recording()
                    if path:
                        st.success(f"Saved recording ({dur:.1f}s): {path}")
                        st.audio(path, format="audio/wav")
                        audio_path = path
                    else:
                        st.error("Stop failed or no audio captured.")
            if st.session_state.is_recording and st.session_state.record_start_ts:
                elapsed = (datetime.utcnow() - st.session_state.record_start_ts).total_seconds()
                st.info(f"Recording... {elapsed:.1f}s elapsed")

            if st.session_state.audio_path and not st.session_state.is_recording:
                audio_path = st.session_state.audio_path
                st.audio(audio_path, format="audio/wav")

        elif mode == "Upload Audio":
            uploaded = st.file_uploader("Upload wav/mp3/m4a", type=["wav", "mp3", "m4a"])
            if uploaded:
                path = save_uploaded_audio(uploaded)
                st.success(f"Saved upload: {path}")
                st.session_state.audio_path = path
                audio_path = path
                st.audio(path)

        elif mode == "Text Input":
            text_query = st.text_area(
                "Type your request",
                placeholder="e.g., Recommend an eco-friendly stainless-steel cleaner under $15",
            )

        run_clicked = st.button(
            "Transcribe and run" if mode != "Text Input" else "Run agents",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Run pipeline
        if run_clicked:
            st.session_state.run_error = None
            st.session_state.result = None
            st.session_state.tts_path = None
            st.session_state.transcript = None
            st.session_state.last_status = "Running..."

            run_started = datetime.utcnow()

            if mode == "Text Input":
                if not text_query:
                    st.warning("Please enter a query.")
                else:
                    with st.spinner("Running agents..."):
                        result, tts_path, err, duration_ms = run_pipeline(
                            text_query,
                            auto_tts,
                            voice_choice,
                        )
                    st.session_state.transcript = text_query
                    st.session_state.result = result
                    st.session_state.tts_path = tts_path
                    st.session_state.run_error = err
                    st.session_state.last_run_ms = duration_ms
                    st.session_state.last_run_ts = run_started.strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.last_status = "Success" if not err else "Fail"
                    log_run(mode, text_query, result, tts_path, duration_ms)
            else:
                if not audio_path:
                    st.warning("Please record or upload an audio file first.")
                else:
                    with st.spinner("Transcribing audio..."):
                        transcript = transcribe_audio(audio_path)
                    if not transcript:
                        st.session_state.run_error = "Transcription failed."
                        st.session_state.last_status = "Fail"
                    else:
                        st.session_state.transcript = transcript
                        with st.spinner("Running agents..."):
                            result, tts_path, err, duration_ms = run_pipeline(
                                transcript,
                                auto_tts,
                                voice_choice,
                            )
                        st.session_state.result = result
                        st.session_state.tts_path = tts_path
                        st.session_state.run_error = err
                        st.session_state.last_run_ms = duration_ms
                        st.session_state.last_run_ts = run_started.strftime("%Y-%m-%d %H:%M:%S")
                        st.session_state.last_status = "Success" if not err else "Fail"
                        log_run(mode, transcript, result, tts_path, duration_ms)

    # -------- Right: output cards --------
    with col_output:
        # Transcript
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Transcript")
        if st.session_state.transcript:
            st.info(st.session_state.transcript)
        else:
            st.write("Waiting for input...")
        st.markdown("</div>", unsafe_allow_html=True)

        # Answer + citations
        st.markdown('<div class="card" style="margin-top: 0.9rem;">', unsafe_allow_html=True)
        st.subheader("Answer")
        if st.session_state.run_error:
            st.error(st.session_state.run_error)
        elif st.session_state.result and st.session_state.result.get("final_answer"):
            st.write(st.session_state.result["final_answer"])
            citations = st.session_state.result.get("citations", [])
            if citations:
                st.markdown(
                    "**Citations:** "
                    + " ".join(
                        [
                            f"`{c}`" if not (isinstance(c, str) and c.startswith("http")) else f"[{c}]({c})"
                            for c in citations
                        ]
                    )
                )
        else:
            st.write("No answer yet.")
        st.markdown("</div>", unsafe_allow_html=True)

        # TTS audio
        st.markdown('<div class="card" style="margin-top: 0.9rem;">', unsafe_allow_html=True)
        st.subheader("TTS")
        if st.session_state.tts_path:
            st.audio(st.session_state.tts_path, format="audio/mp3")
            st.caption(f"Saved to {st.session_state.tts_path}")
        else:
            st.write("Waiting to generate audio...")
        st.markdown("</div>", unsafe_allow_html=True)

        # Agent trace
        st.markdown('<div class="card" style="margin-top: 0.9rem;">', unsafe_allow_html=True)
        st.subheader("Agent trace")
        result = st.session_state.result or {}
        intent = result.get("intent")
        plan = result.get("plan")
        rag_params = result.get("rag_params")
        if intent:
            st.markdown("**Intent:**")
            st.json(intent, expanded=False)
        if plan:
            st.markdown("**Plan:**")
            st.write(plan)
        if rag_params:
            st.markdown("**RAG params:**")
            st.json(rag_params, expanded=False)
        if not (intent or plan or rag_params):
            st.write("No agent trace yet.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Retrieval results
        st.markdown('<div class="card" style="margin-top: 0.9rem;">', unsafe_allow_html=True)
        st.subheader("Retrieval results")
        rag_results = result.get("rag_results") or []
        web_results = result.get("web_results") or []
        rag_df = format_rag_dataframe(rag_results)
        web_df = format_web_dataframe(web_results)
        if rag_df is not None:
            st.markdown("**Private catalog (rag.search):**")
            st.dataframe(
                rag_df.style.format({"Price($)": "{:.2f}", "Rel.": "{:.3f}"}),
                use_container_width=True,
            )
        if web_df is not None:
            st.markdown("**Web search (web.search):**")
            web_df["URL"] = web_df["URL"].apply(
                lambda u: f"[link]({u})" if isinstance(u, str) else ""
            )
            st.dataframe(web_df, use_container_width=True)
        if rag_df is None and web_df is None:
            st.write("No retrieval results.")
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
