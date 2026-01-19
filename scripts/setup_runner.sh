#!/bin/bash
# Ludi Informatio Self-Hosted Runner Setup
# Run this on your Mac/Local Machine to prep the environment for the runner.

echo "🚀 Setting up Ludi-Bot Runner Environment..."

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 could not be found. Please install it."
    exit 1
fi
echo "✅ Python 3 found"

# 2. Create/Activiate Venv (Optional but recommended for runner)
# Note: The runner usually executes in the workspace directly. 
# We'll install deps to the user's global or user scope if not in venv, 
# OR we rely on the workflow to create a venv.
# BUT to be safe for "shell" executor, let's install deps.

echo "📦 Installing Dependencies..."
pip3 install -r requirements.txt
echo "✅ Dependencies installed"

# 3. Install Playwright Browsers
echo "🎭 Installing Playwright Browsers..."
playwright install chromium
playwright install-deps
echo "✅ Playwright Browsers installed"

echo "🎉 Runner Environment Ready!"
echo "   You can now start the runner with ./run.sh"
