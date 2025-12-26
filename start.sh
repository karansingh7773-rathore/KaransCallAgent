#!/bin/bash
# Start script for Render deployment

echo "Starting Sentinel Connect Voice Agent..."

# Start the LiveKit agent (with health server for Render)
python livekit_agent.py start
