#!/bin/bash
# filepath: d:\Fileprocess\Fileprocess\start.sh

# Activate virtual environment if applicable
# source venv/bin/activate  # Uncomment and modify if using a virtual environment

# Export environment variables (if needed)
export FLASK_APP=app.py
export FLASK_ENV=production  # Change to 'development' for debugging

# Start the application with Gunicorn
gunicorn --bind 0.0.0.0:8000 app:app