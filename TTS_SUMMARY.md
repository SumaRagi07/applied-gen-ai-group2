# TTS Summary Implementation

## Overview

Implemented fragment-based TTS synthesis with ≤15-second summaries that align with on-screen citations.

## Features

### 1. Automatic Summary Generation
- **Function**: `create_tts_summary()` in `src/voice/tts.py`
- **Method**: Uses GPT-4o to create concise summaries
- **Target**: ≤15 seconds of speech (~37-40 words at 2.5 words/second)
- **Preserves**: Key product recommendations, prices, and citations

### 2. Fragment-Based Synthesis
- **Technology**: OpenAI TTS API (non-streaming)
- **Format**: Full WAV/MP3 file generation
- **Voices**: 6 options (alloy, echo, fable, onyx, nova, shimmer)
- **Model**: `tts-1` (fast) or `tts-1-hd` (high quality)

### 3. Citation Alignment
- Summaries include citation references (e.g., `[doc_12345]`, `[amazon.com]`)
- Top 1-3 citations preserved in summary
- Full citations displayed on screen alongside audio

## Implementation Details

### Summary Generation Process

1. **Input**: Full answer text + citations list
2. **LLM Processing**: GPT-4o creates concise summary with:
   - Top 1-2 product recommendations
   - Prices when available
   - Key features/benefits
   - Citation references
   - Note to check full details on screen
3. **Output**: ~30-40 word summary (≤15 seconds)

### Fallback Mechanism

If LLM summary generation fails:
- Simple truncation method
- Preserves first sentences
- Adds citation note
- Ensures ≤15 seconds

### Integration Points

1. **Synthesizer Node**: Generates `tts_summary` in state
2. **Streamlit UI**: Uses `text_to_speech_with_summary()` function
3. **State Management**: `tts_summary` stored in agent state

## Usage

### In Streamlit App

1. Process a query
2. View full answer with citations
3. Click "🎵 Generate Speech (15s Summary)"
4. Summary text is shown in expandable section
5. Audio file generated and ready to play

### Programmatic Usage

```python
from src.voice.tts import text_to_speech_with_summary

audio_path = text_to_speech_with_summary(
    full_answer="Full answer text...",
    citations=["doc_12345", "amazon.com"],
    output_path="response.mp3",
    voice="alloy",
    max_duration_seconds=15
)
```

### Direct Summary Creation

```python
from src.voice.tts import create_tts_summary

summary = create_tts_summary(
    full_answer="Full answer...",
    citations=["doc_12345"],
    max_duration_seconds=15
)
```

## Example Output

**Full Answer:**
> Here are some eco-friendly wooden puzzle options:
> - **Melissa & Doug Wooden Jigsaw Puzzle** [doc_00123] - Catalog: $12.99, Current: $15.99 [amazon.com]
> - **Green Toys Building Blocks** [doc_00456] - $18.50
> - **Plan Toys Puzzle Set** [doc_00789] - $15.00

**TTS Summary (15 seconds):**
> "Check out the Melissa & Doug Wooden Jigsaw Puzzle for $15.99 on amazon.com, perfect for kids. Also, consider Green Toys Building Blocks, eco-friendly at $18.50. See full details on screen."

## Technical Specifications

- **Speech Rate**: ~2.5 words/second (150 words/minute)
- **Target Duration**: ≤15 seconds
- **Word Limit**: ~37-40 words
- **Citation Format**: Preserved in summary (e.g., `[doc_12345]`, `[amazon.com]`)
- **Audio Format**: MP3 (default) or WAV
- **Quality**: High-quality neural TTS (OpenAI)

## Benefits

1. **Concise**: Users get key information quickly
2. **Natural**: LLM-generated summaries sound conversational
3. **Aligned**: Citations match on-screen references
4. **Efficient**: Fragment-based (no streaming complexity)
5. **Reliable**: Fallback mechanism ensures it always works

## Future Enhancements

Potential improvements:
- Multiple summary styles (brief, detailed, conversational)
- Language support (multilingual summaries)
- Voice cloning (custom voices)
- Streaming TTS (for real-time applications)
- Emotion/prosody control

