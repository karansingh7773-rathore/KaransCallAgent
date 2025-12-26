# 🎙️ Voice Assistant

A low-latency voice assistant with intelligent interrupt handling and conversation memory. Built with Groq AI APIs for fast speech recognition, language understanding, and speech synthesis.

## ✨ Features

- **⚡ Low Latency**: 0.2-0.5 second target response time
- **🛑 Interrupt Handling**: Stop mid-response when you speak
- **🧠 Conversation Memory**: Remembers context when interrupted
- **💬 Natural Resumption**: Asks "Yes, please continue" naturally
- **🎯 Voice Activity Detection**: WebRTC VAD for reliable speech detection

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Audio Input   │────▶│  Speech-to-Text │────▶│   LLM Handler   │
│   (Microphone)  │     │   (Whisper)     │     │   (Llama 3.3)   │
└────────┬────────┘     └─────────────────┘     └────────┬────────┘
         │                                               │
         │ Interrupt Detection                           │
         │                                               ▼
┌────────▼────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Interrupt    │◀────│  Text-to-Speech │◀────│    Response     │
│    Handler      │     │   (PlayAI)      │     │   Generator     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 📋 Requirements

- Python 3.8+
- Windows/Linux/macOS
- Microphone
- Groq API key

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd Voice_Assistant
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Activate on Windows:
.\venv\Scripts\activate

# Activate on Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note for Windows**: If PyAudio fails to install:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

### 4. Configure API Key

Copy the example environment file and add your Groq API key:

```bash
copy .env.example .env
```

Edit `.env` and add your key:
```
GROQ_API_KEY=your_groq_api_key_here
```

Get your API key from: https://console.groq.com/keys

### 5. Run the Assistant

```bash
# Make sure venv is activated first
python main.py
```

## 🎮 Usage

1. **Start Speaking**: Just talk naturally, the assistant will detect your voice
2. **Wait for Response**: The assistant will process and respond
3. **Interrupt Anytime**: If you need to interrupt, just speak - the assistant will stop
4. **Resume or New Topic**: After interrupting, you can:
   - Say something new, or
   - Wait silently and the assistant will ask if you want it to continue

### Exit Commands
Say any of these to quit:
- "exit", "quit", "goodbye", "bye", "stop"

## ⚙️ Configuration

Edit `.env` or `config.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `TTS_VOICE` | Fritz-PlayAI | Voice for speech synthesis |
| `LLM_MODEL` | llama-3.3-70b-versatile | Language model |
| `VAD_AGGRESSIVENESS` | 3 | Voice detection sensitivity (0-3) |
| `DEBUG` | false | Enable debug logging |

### Available Voices
- `Fritz-PlayAI` - Natural male voice
- `Arista-PlayAI` - Natural female voice  
- `Atlas-PlayAI` - Deep male voice
- `Indigo-PlayAI` - Unique voice

## 🔧 Troubleshooting

### "No module named 'pyaudio'"
```bash
# Windows
pip install pipwin
pipwin install pyaudio

# Linux
sudo apt-get install portaudio19-dev
pip install pyaudio

# macOS
brew install portaudio
pip install pyaudio
```

### "GROQ_API_KEY is not set"
Make sure you've created `.env` file with your API key.

### "Audio input failed"
- Check your microphone is connected and set as default
- Try running as administrator (Windows)
- Check system audio permissions

### High Latency
- Ensure stable internet connection
- Try reducing `VAD_AGGRESSIVENESS` to 2
- Enable `DEBUG=true` to see timing info

## 📁 Project Structure

```
Voice_Assistant/
├── main.py              # Entry point
├── config.py            # Configuration
├── requirements.txt     # Dependencies
├── .env.example         # Environment template
├── modules/
│   ├── audio_input.py   # Microphone + VAD
│   ├── speech_to_text.py# Groq Whisper API
│   ├── llm_handler.py   # Groq LLM API
│   ├── text_to_speech.py# Groq PlayAI TTS
│   └── interrupt_handler.py # State machine
└── utils/
    └── audio_utils.py   # Audio helpers
```

## 🔑 API Usage

This assistant uses the following Groq APIs:
- **Speech-to-Text**: `whisper-large-v3-turbo`
- **Language Model**: `llama-3.3-70b-versatile`
- **Text-to-Speech**: `playai-tts`

## 📄 License

MIT License - feel free to use and modify!

## 🤝 Contributing

Contributions welcome! Feel free to submit issues and pull requests.
