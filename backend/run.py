#!/usr/bin/env python3
"""
Flask Institution Management System
Main application runner
"""

import os
from app import create_app, socketio

# Create Flask application
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    print(f"Starting Institution Management System...")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Debug mode: {debug}")
    print(f"Running on: http://{host}:{port}")

    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
