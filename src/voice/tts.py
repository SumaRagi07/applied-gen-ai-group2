import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def text_to_speech(
    text: str,
    output_path: str = "response.mp3",
    voice: str = "alloy",
    model: str = "tts-1"
) -> str:
    """
    Convert text to speech using OpenAI TTS API
    
    Args:
        text: Text to convert to speech
        output_path: Where to save audio file (default: response.mp3)
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        model: TTS model (tts-1 for speed, tts-1-hd for quality)
        
    Returns:
        str: Path to generated audio file
        
    Example:
        >>> audio = text_to_speech("Hello, how can I help you?")
        >>> # Now play audio file
    """
    
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        print(f"[TTS] Generating speech... (voice: {voice})")
        
        # Call TTS API
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text
        )
        
        # Save audio to file
        response.stream_to_file(output_path)
        
        print(f"[TTS] Saved audio to {output_path}")
        return output_path
        
    except Exception as e:
        print(f"[TTS] Error: {str(e)}")
        return ""


def get_available_voices():
    """
    Returns list of available TTS voices
    
    Returns:
        list: Available voice names
    """
    return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


# Voice descriptions for choosing
VOICE_INFO = {
    "alloy": "Neutral, clear (recommended for general use)",
    "echo": "Calm, professional",
    "fable": "Expressive, storytelling",
    "onyx": "Deep, authoritative",
    "nova": "Energetic, friendly",
    "shimmer": "Warm, conversational"
}