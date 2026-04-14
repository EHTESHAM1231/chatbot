"""
Main entry point for LLM Chatbot Flask Web Application.
Run with: python app.py
Access at: http://localhost:3000
"""

import sys
from app import app

if __name__ == "__main__":
    print("="*60)
    print("  LLM Chatbot Web Application")
    print("="*60)
    print("\n🚀 Starting server on http://localhost:3000")
    print("📝 Press Ctrl+C to stop the server\n")
    
    try:
        app.run(host='0.0.0.0', port=3000, debug=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
        sys.exit(0)
