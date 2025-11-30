import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

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
    
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        # Open audio file
        with open(audio_file_path, "rb") as audio_file:
            # Call Whisper API
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        print(f"[ASR] Transcribed: {transcript}")
        return transcript
        
    except FileNotFoundError:
        print(f"[ASR] Error: Audio file not found at {audio_file_path}")
        return ""
    except Exception as e:
        print(f"[ASR] Error: {str(e)}")
        return ""


def record_audio(duration: int = 30, sample_rate: int = 16000, output_path: str = "recording.wav") -> str:
    """
    Record audio from microphone (optional helper function)
    
    Args:
        duration: Recording duration in seconds
        sample_rate: Audio sample rate (16000 Hz works well for speech)
        output_path: Where to save the recording
        
    Returns:
        str: Path to saved audio file
        
    Example:
        >>> audio_path = record_audio(duration=30)
        >>> text = transcribe_audio(audio_path)
    """
    
    try:
        import sounddevice as sd
        import scipy.io.wavfile as wav
        
        print(f"[ASR] Recording for {duration} seconds...")
        
        # Record audio
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='int16'
        )
        sd.wait()  # Wait until recording is finished
        
        # Save as WAV file
        wav.write(output_path, sample_rate, recording)
        
        print(f"[ASR] Saved recording to {output_path}")
        return output_path
        
    except Exception as e:
        print(f"[ASR] Recording error: {str(e)}")
        return ""
