import os
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# Handle both old and new OpenAI API versions
try:
    from openai import OpenAI
    OPENAI_NEW_API = True
except ImportError:
    OPENAI_NEW_API = False
    import openai as openai_old

def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribe audio file to text using OpenAI Whisper API
    
    Args:
        audio_file_path: Path to audio file (wav, mp3, m4a, etc.)
        
    Returns:
        str: Transcribed text
        
    Example:
        >>> text = transcribe_audio("recording.wav")
        >>> print(text)
        "Find me eco-friendly puzzles under twenty dollars"
    """
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ASR] Error: OPENAI_API_KEY not set")
        return ""
    
    try:
        if OPENAI_NEW_API:
            # New API (v1.0+)
            client = OpenAI(api_key=api_key)
            with open(audio_file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
        else:
            # Old API (v0.x) - requires upgrade
            raise ImportError(
                "Your openai package is too old (v0.27.8). "
                "Please upgrade: pip install --upgrade 'openai>=1.0.0'"
            )
        
        print(f"[ASR] Transcribed: {transcript}")
        return transcript
        
    except FileNotFoundError:
        print(f"[ASR] Error: Audio file not found at {audio_file_path}")
        return ""
    except Exception as e:
        print(f"[ASR] Error: {str(e)}")
        return ""


def record_audio(duration: int = None, sample_rate: int = 16000, output_path: str = "recording.wav", stop_event=None) -> str:
    """
    Record audio from microphone (optional helper function)
    
    Args:
        duration: Recording duration in seconds (None = record until stopped manually)
        sample_rate: Audio sample rate (16000 Hz works well for speech)
        output_path: Where to save the recording
        stop_event: threading.Event to signal stop (for manual stop)
        
    Returns:
        str: Path to saved audio file
        
    Example:
        >>> audio_path = record_audio(duration=5)  # Fixed duration
        >>> audio_path = record_audio()  # Manual stop (press Enter)
        >>> text = transcribe_audio(audio_path)
    """
    
    try:
        import sounddevice as sd
        import scipy.io.wavfile as wav
        import queue
        import threading
        
        if duration is None:
            print("[ASR] Recording... (Press Enter to stop)")
        else:
            print(f"[ASR] Recording for {duration} seconds...")
        
        # Use queue to collect audio chunks
        q = queue.Queue()
        recording_frames = []
        
        def audio_callback(indata, frames, time, status):
            """Callback function to collect audio data"""
            if status:
                print(f"[ASR] Status: {status}")
            q.put(indata.copy())
        
        # Start recording stream
        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype='int16',
            callback=audio_callback,
            blocksize=int(sample_rate * 0.1)  # 100ms blocks
        )
        
        stream.start()
        
        if duration is None:
            # Manual stop mode - wait for Enter key or stop_event
            if stop_event is None:
                # For command-line use: wait for Enter
                try:
                    input()  # Wait for Enter key
                except (EOFError, KeyboardInterrupt):
                    pass
            else:
                # For Streamlit/threading: wait for stop_event
                stop_event.wait()
        else:
            # Fixed duration mode
            import time
            time.sleep(duration)
        
        # Stop recording
        stream.stop()
        stream.close()
        
        # Collect all audio data
        while not q.empty():
            recording_frames.append(q.get())
        
        if not recording_frames:
            print("[ASR] No audio recorded")
            return ""
        
        # Concatenate all frames
        recording = np.concatenate(recording_frames, axis=0)
        
        # Save as WAV file
        wav.write(output_path, sample_rate, recording)
        
        duration_actual = len(recording) / sample_rate
        print(f"[ASR] Saved recording to {output_path} ({duration_actual:.1f} seconds)")
        return output_path
        
    except ImportError:
        print("[ASR] Error: sounddevice or scipy not installed")
        return ""
    except Exception as e:
        print(f"[ASR] Recording error: {str(e)}")
        return ""