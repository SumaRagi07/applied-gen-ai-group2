import os
import numpy as np
from dotenv import load_dotenv
import threading
import time

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


class BackgroundRecorder:
    """Records audio in background using sounddevice"""
    
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.recording = []
        self.is_recording = False
        self.stream = None
        self.thread = None
        
    def start_recording(self):
        """Start recording in background thread"""
        try:
            import sounddevice as sd
            
            self.recording = []
            self.is_recording = True
            
            print("[ASR] Starting background recording...")
            
            # Define callback to collect audio
            def audio_callback(indata, frames, time_info, status):
                if status:
                    print(f"[ASR] Status: {status}")
                if self.is_recording:
                    self.recording.append(indata.copy())
            
            # Start audio stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16',
                callback=audio_callback,
                blocksize=int(self.sample_rate * 0.1)  # 100ms blocks
            )
            
            self.stream.start()
            print("[ASR] ✓ Recording started")
            
        except ImportError:
            print("[ASR] Error: sounddevice not installed. Install with: pip install sounddevice")
            return False
        except Exception as e:
            print(f"[ASR] Error starting recording: {e}")
            return False
        
        return True
    
    def stop_recording(self, output_path="recording.wav"):
        """Stop recording and save to file"""
        try:
            import sounddevice as sd
            import scipy.io.wavfile as wav
            
            print("[ASR] Stopping recording...")
            self.is_recording = False
            
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            if not self.recording:
                print("[ASR] No audio recorded")
                return ""
            
            # Concatenate all recorded chunks
            audio_data = np.concatenate(self.recording, axis=0)
            
            # Save to WAV file
            wav.write(output_path, self.sample_rate, audio_data)
            
            duration = len(audio_data) / self.sample_rate
            print(f"[ASR] ✓ Saved {duration:.1f}s recording to {output_path}")
            
            return output_path
            
        except ImportError:
            print("[ASR] Error: scipy not installed. Install with: pip install scipy")
            return ""
        except Exception as e:
            print(f"[ASR] Error saving recording: {e}")
            return ""


def record_audio(duration: int = None, sample_rate: int = 16000, output_path: str = "recording.wav", stop_event=None) -> str:
    """
    Record audio from microphone (legacy fixed-duration function)
    
    Args:
        duration: Recording duration in seconds (None = record until stopped manually)
        sample_rate: Audio sample rate (16000 Hz works well for speech)
        output_path: Where to save the recording
        stop_event: threading.Event to signal stop (for manual stop)
        
    Returns:
        str: Path to saved audio file
        
    Example:
        >>> audio_path = record_audio(duration=5)  # Fixed duration
        >>> text = transcribe_audio(audio_path)
    """
    
    try:
        import sounddevice as sd
        import scipy.io.wavfile as wav
        import queue
        
        if duration is None:
            print("[ASR] Recording... (Press Enter to stop)")
        else:
            print(f"[ASR] Recording for {duration} seconds...")
        
        # Use queue to collect audio chunks
        q = queue.Queue()
        recording_frames = []
        
        def audio_callback(indata, frames, time_info, status):
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
        print("[ASR] Install with: pip install sounddevice scipy")
        return ""
    except Exception as e:
        print(f"[ASR] Recording error: {str(e)}")
        return ""