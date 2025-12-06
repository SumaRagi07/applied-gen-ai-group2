import sys
sys.path.append('.')

from src.voice.asr import transcribe_audio, record_audio
from src.voice.tts import text_to_speech, VOICE_INFO
from src.agents.graph import agent_graph, invoke_with_logging

def test_voice_to_voice():
    """
    Test full voice-to-voice pipeline:
    1. Record audio (or use test file)
    2. Transcribe with Whisper
    3. Process with LangGraph
    4. Convert answer to speech
    """
    
   
    print("\nVOICE-TO-VOICE TEST")
 
    # Initialize variables
    audio_path = None
    text_query = None
    
    # Step 1: Get audio input
    print("\n[1/4] AUDIO INPUT")
    choice = input("Record new audio? (y/n): ").lower()
    
    if choice == 'y':
        duration_input = input("Recording duration in seconds (or press Enter for manual stop): ").strip()
        if duration_input:
            try:
                duration = int(duration_input)
                audio_path = record_audio(duration=duration)
            except ValueError:
                print("Invalid duration, using manual stop mode")
                audio_path = record_audio(duration=None)
        else:
            print("Manual stop mode: Press Enter to stop recording")
            audio_path = record_audio(duration=None)  # Manual stop
    else:
        audio_path = input("Path to audio file (or press Enter for test): ").strip()
        if not audio_path:
            # For testing without audio file
            print("[TEST MODE] Skipping audio, using text query")
            text_query = "Find me eco-friendly puzzles under twenty dollars"
    
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
    
    result = invoke_with_logging(text_query)
    answer = result['final_answer']
    citations = result.get('citations', [])
    tts_summary = result.get('tts_summary', answer)  # ✅ GET TTS SUMMARY
    
    # Show execution stats
    logging_data = result.get('_logging', {})
    if logging_data:
        stats = logging_data.get('execution_stats', {})
        print(f"\n📊 Execution: {stats.get('total_steps', 0)} steps in {stats.get('total_duration_ms', 0):.0f}ms")
        print(f"   Log file: {logging_data.get('log_file', 'N/A')}")
    
    print("\n✅ Answer generated!")
    print(f"Citations: {len(citations)}")
    
    # Step 4: Convert to speech
    print("\n[4/4] TEXT-TO-SPEECH (OpenAI TTS)")
    
    # Show voice options
    print("\nAvailable voices:")
    for voice, description in VOICE_INFO.items():
        print(f"  - {voice}: {description}")
    
    voice_choice = input("\nChoose voice (default: alloy): ").strip() or "alloy"
    
    # ✅ USE TTS SUMMARY (NOT FULL ANSWER)
    audio_output = text_to_speech(
        text=tts_summary,  # ✅ CHANGED: Use tts_summary instead of answer
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
        
        print("\n✅ Test complete! Play 'response.mp3' to hear the answer.")
    else:
        print("\n❌ TTS failed")


def test_asr_only():
    """Test ASR module only"""
    print("\n=== ASR TEST ===\n")
    
    choice = input("Record audio? (y/n): ").lower()
    if choice == 'y':
        duration_choice = input("Recording duration in seconds (or press Enter for manual stop): ").strip()
        if duration_choice:
            try:
                duration = int(duration_choice)
                audio_path = record_audio(duration=duration)
            except ValueError:
                print("Invalid duration, using manual stop mode")
                audio_path = record_audio(duration=None)  # Manual stop
        else:
            print("Manual stop mode: Press Enter to stop recording")
            audio_path = record_audio(duration=None)  # Manual stop
    else:
        audio_path = input("Audio file path: ").strip()
    
    if audio_path:
        text = transcribe_audio(audio_path)
        print(f"\n✅ Transcription: {text}")


def test_tts_only():
    """Test TTS module only"""
    print("\n=== TTS TEST ===\n")
    
    text = input("Enter text to speak: ").strip()
    if not text:
        text = "Hello! This is a test of the text to speech system."
    
    voice = input("Voice (alloy/echo/fable/onyx/nova/shimmer, default: alloy): ").strip() or "alloy"
    
    audio_path = text_to_speech(text, voice=voice)
    print(f"\n✅ Audio saved: {audio_path}")


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