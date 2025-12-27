#!/bin/bash
# Start script for Render deployment

echo "Starting Sentinel Connect Voice Agent..."

# Start the LiveKit agent in the background
python livekit_agent.py start &

# Start the FastAPI server (this is what Render's load balancer will hit)
# Port 10000 is Render's default for web services
uvicorn server:app --host 0.0.0.0 --port ${PORT:-10000}
