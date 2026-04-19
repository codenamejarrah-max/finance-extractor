#!/bin/bash

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# --- Auto-Minimize Logic ---
# Minimize this window immediately
osascript -e 'tell application "Terminal" to set miniaturized of window 1 to true'

# Background task to catch the second window (python/streamlit) that often pops up
(
    sleep 3
    osascript -e 'tell application "Terminal" to set miniaturized of (every window whose name contains "python" or name contains "streamlit") to true'
) &
# ---------------------------

echo "🚀 Starting Finance Record Extractor..."
echo "📍 Project Directory: $DIR"

# Check if venv exists
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment (venv) not found. Please ensure it exists in $DIR"
    read -p "Press enter to exit..."
    exit 1
fi

# Run Streamlit
streamlit run app.py

# Keep the window open if it crashes
echo ""
echo "Streamlit process ended."
read -p "Press enter to close this window..."
