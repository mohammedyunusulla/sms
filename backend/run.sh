#!/bin/bash
# Script to start the Flask application on Ubuntu/Linux

echo "======================================"
echo "   School Management System"
echo "   Starting Backend Server"
echo "======================================"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated."
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    else
        echo "❌ Error: Virtual environment not found!"
        echo "Please create a virtual environment first:"
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
fi

# Set environment variables
export FLASK_APP=run.py
export FLASK_ENV=development

echo ""
echo "Starting Flask development server..."
echo ""
echo "Server will be available at:"
echo "  http://localhost:5000"
echo "  http://127.0.0.1:5000"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

# Run the Flask application
python3 run.py
