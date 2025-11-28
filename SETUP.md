# Setup Guide

## Prerequisites

- Python 3.9+ (3.10+ recommended)
- Git
- VSCode (recommended for editing .env files)

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/SumaRagi07/applied-gen-ai-group2
cd applied-gen-ai-group2
```

### 2. Set Up Environment Variables

**Important**: The `.env.example` file is usually hidden. Open the cloned folder in VSCode to see it.

1. Open the cloned folder in VSCode
2. Open the `.env.example` file
3. Rename it to `.env` (remove `.example`)
4. Replace the placeholder values with your actual API keys and paths:

```bash
OPENAI_API_KEY=sk-proj-your-actual-key-here
BRAVE_API_KEY=BSA-your-actual-key-here
CHROMA_PATH=/full/path/to/applied-gen-ai-group2/vectordb/chroma
```

**Note**: Replace `CHROMA_PATH` with the absolute path to the `vectordb/chroma` folder on your laptop.

### 3. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Test the Setup

#### Test 1: MCP Server

In **Terminal 1** (with venv activated):

```bash
python src/mcp_server/server.py
```

You should see:
```
Starting MCP Server...
✓ RAG Search tool initialized
✓ Web Search tool initialized
Server ready on http://0.0.0.0:8000
```

#### Test 2: Voice Module

In **Terminal 2** (new terminal, activate venv, cd to repo):

```bash
cd applied-gen-ai-group2
source venv/bin/activate  # or venv\Scripts\activate on Windows
python test_voice.py
```

Choose option **3** (TTS only) for quick testing. This verifies your API keys are working.

### 6. Run Streamlit App

Once both tests pass, you can run the Streamlit UI:

```bash
# Make sure MCP server is running in Terminal 1
# Then in Terminal 2:
streamlit run app.py
```

## Troubleshooting

### Error: "OPENAI_API_KEY environment variable not set"
- Make sure you created `.env` file (not `.env.example`)
- Check that `.env` contains `OPENAI_API_KEY=sk-...`
- Verify the file is in the project root directory
- Restart your terminal/IDE after creating `.env`

### Error: "404 Not Found" when testing MCP server
- Make sure MCP server is running: `python src/mcp_server/server.py`
- Check it's running on `http://localhost:8000`
- Wait a few seconds after starting the server before testing

### Error: "Connection refused" or "Connection error"
- Start the MCP server first in Terminal 1
- Check if port 8000 is already in use: `lsof -i :8000` (macOS/Linux)
- Make sure you're using the correct CHROMA_PATH (absolute path)

### Error: Module not found
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

## Getting API Keys

### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign in or create account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

### Brave Search API Key
1. Go to https://api.search.brave.com/
2. Sign up for free tier (2000 queries/month)
3. Get your API key from dashboard
4. Copy the key (starts with `BSA_`)

## Project Structure

See `README.md` for complete project structure and architecture details.

