#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set environment variables (load from .env if exists)
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start Flask server
echo "🚀 Starting Flask backend server..."
python flask_app.py