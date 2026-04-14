"""
Flask Web Application for LLM Chatbot
Runs on port 3000
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from src.config import Config, ConfigurationError
from src.chatbot import Chatbot
import sys

app = Flask(__name__)
CORS(app)

# Initialize chatbot
try:
    config = Config.from_env()
    chatbot = Chatbot(config)
except ConfigurationError as e:
    print(f"Configuration error: {str(e)}")
    sys.exit(1)


@app.route('/')
def index():
    """Render the main chat interface"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Please provide a valid message'
            }), 400
        
        # Process the query through the chatbot
        response = chatbot.process_query(user_message)
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/clear', methods=['POST'])
def clear_history():
    """Clear conversation history"""
    try:
        chatbot.conversation_store.clear_history()
        return jsonify({
            'success': True,
            'message': 'Conversation history cleared'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
