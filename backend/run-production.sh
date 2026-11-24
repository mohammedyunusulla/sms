#!/bin/bash
# Production deployment script using Gunicorn on Ubuntu/Linux

echo "======================================"
echo "   Institution Management System"
echo "   Starting Production Server"
echo "======================================"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated."
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    else
        echo "❌ Error: Virtual environment not found!"
        exit 1
    fi
fi

# Set environment variables for production
export FLASK_ENV=production
export FLASK_APP=run.py

echo ""
echo "Starting Gunicorn production server..."
echo ""
echo "Server configuration:"
echo "  Workers: 4"
echo "  Bind: 0.0.0.0:5000"
echo "  Timeout: 120s"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

# Run Gunicorn
gunicorn --workers 4 \
         --bind 0.0.0.0:5000 \
         --timeout 120 \
         --access-logfile logs/access.log \
         --error-logfile logs/error.log \
         --log-level info \
         "app:create_app()"
