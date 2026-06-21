#!/usr/bin/env python3
"""
Local proxy server for MiniMax API calls
Solves CORS issue when calling AI APIs from browser
"""
from flask import Flask, request, jsonify, make_response
import requests

app = Flask(__name__)

# MiniMax API configuration
API_KEY = 'sk-cp-QGn3Ig1iuD0anJwkEZglYUwFS_lEgQHhHcbHE0QYIBV0qBCZc2j1o44z5v_VX5jBtfnqtxqDSTNzw0tzqoJBLs0GspfyaX9WrxsDCvUM_dbN2KrfTZg_cTk'
API_BASE = 'https://api.minimax.chat/v1'

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
def chat_completions():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return ''

    try:
        data = request.get_json()

        # Always use MiniMax-M3 model (exact case required)
        data['model'] = 'MiniMax-M3'

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }

        response = requests.post(
            f'{API_BASE}/chat/completions',
            headers=headers,
            json=data,
            timeout=60
        )

        return jsonify(response.json()), response.status_code

    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'provider': 'MiniMax'})

if __name__ == '__main__':
    print("Starting MiniMax proxy server on http://localhost:3000")
    app.run(host='0.0.0.0', port=3000, debug=False)
