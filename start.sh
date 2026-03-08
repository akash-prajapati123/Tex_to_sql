#!/bin/bash
if [ -z "$NVIDIA_API_KEY" ]; then
    echo "Warning: NVIDIA_API_KEY is not set. You must export it before the chat will work."
    echo "Example: export NVIDIA_API_KEY='nvapi-...'"
fi

# Initialize Database
python setup_db.py

# Start Server
echo "Starting Text-to-SQL server at http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
