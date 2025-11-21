import sys
sys.path.append('.')

from src.voice.asr import transcribe_audio, record_audio
from src.voice.tts import text_to_speech, VOICE_INFO
from src.agents.graph import agent_graph

def test_voice_to_voice():
    """
    Test full voice-to-voice pipeline:
    1. Record audio (or use test file)
    2. Transcribe with Whisper
    3. Process with LangGraph
    4. Convert answer to speech
    """
    
   
    print("\nVOICE-TO-VOICE TEST")
 
    
    # Step 1: Get audio input
    print("\n[1/4] AUDIO INPUT")
    choice = input("Record new audio? (y/n): ").lower()
    
    if choice == 'y':
        duration = int(input("Recording duration in seconds (default 5): ") or "5")
        audio_path = record_audio(duration=duration)
    else:
        audio_path = input("Path to audio file (or press Enter for test): ").strip()
        if not audio_path:
            # For testing without audio file
            print("[TEST MODE] Skipping audio, using text query")
            text_query = "Find me eco-friendly puzzles under twenty dollars"
        else:
            text_query = None
    
    # Step 2: Transcribe
    if audio_path and text_query is None:
        print("\n[2/4] TRANSCRIPTION (Whisper)")
        text_query = transcribe_audio(audio_path)
        if not text_query:
            print("Transcription failed. Exiting.")
            return
    
    print(f"\n📝 Query: {text_query}")
    
    # Step 3: Process with LangGraph
    print("\n[3/4] PROCESSING (LangGraph)")
    print("Running agents...")
    
    result = agent_graph.invoke({"user_query": text_query})
    answer = result['final_answer']
    citations = result.get('citations', [])
    
    print("\n Answer generated!")
    print(f"Citations: {len(citations)}")
    
    # Step 4: Convert to speech
    print("\n[4/4] TEXT-TO-SPEECH (OpenAI TTS)")
    
    # Show voice options
    print("\nAvailable voices:")
    for voice, description in VOICE_INFO.items():
        print(f"  - {voice}: {description}")
    
    voice_choice = input("\nChoose voice (default: alloy): ").strip() or "alloy"
    
    audio_output = text_to_speech(
        text=answer,
        output_path="response.mp3",
        voice=voice_choice
    )
    
    if audio_output:
        print(f"\n🔊 Audio saved: {audio_output}")
        print("\n" + "="*70)
        print("ANSWER:")
        print("="*70)
        print(answer)
        print("\n" + "="*70)
        print(f"Citations: {len(citations)}")
        print("="*70)
        for citation in citations:
            print(f"  - {citation}")
        
        print("\n Test complete! Play 'response.mp3' to hear the answer.")
    else:
        print("\n TTS failed")


def test_asr_only():
    """Test ASR module only"""
    print("\n=== ASR TEST ===\n")
    
    choice = input("Record audio? (y/n): ").lower()
    if choice == 'y':
        audio_path = record_audio(duration=5)
    else:
        audio_path = input("Audio file path: ").strip()
    
    if audio_path:
        text = transcribe_audio(audio_path)
        print(f"\n Transcription: {text}")


def test_tts_only():
    """Test TTS module only"""
    print("\n=== TTS TEST ===\n")
    
    text = input("Enter text to speak: ").strip()
    if not text:
        text = "Hello! This is a test of the text to speech system."
    
    voice = input("Voice (alloy/echo/fable/onyx/nova/shimmer, default: alloy): ").strip() or "alloy"
    
    audio_path = text_to_speech(text, voice=voice)
    print(f"\n Audio saved: {audio_path}")


if __name__ == "__main__":
    print("\n🎤 Voice Module Testing\n")
    print("1. Full voice-to-voice test")
    print("2. ASR only (record + transcribe)")
    print("3. TTS only (text to speech)")
    
    choice = input("\nChoose test (1/2/3): ").strip()
    
    if choice == "1":
        test_voice_to_voice()
    elif choice == "2":
        test_asr_only()
    elif choice == "3":
        test_tts_only()
    else:
        print("Invalid choice")