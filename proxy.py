#!/usr/bin/env python3
"""
Local proxy server for OpenAI API calls
Solves CORS issue when calling OpenAI from browser
"""
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Configure your OpenAI-compatible API key here
API_KEY = os.environ.get('OPENAI_API_KEY', 'sk-cp-QGn3Ig1iuD0anJwkEZglYUwFS_lEgQHhHcbHE0QYIBV0qBCZc2j1o44z5v_VX5jBtfnqtxqDSTNzw0tzqoJBLs0GspfyaX9WrxsDCvUM_dbN2KrfTZg_cTk')
API_BASE = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com/v1')

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    try:
        data = request.get_json()

        # Forward to OpenAI-compatible API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }

        response = requests.post(
            f'{API_BASE}/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )

        return jsonify(response.json()), response.status_code

    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("Starting proxy server on http://localhost:3000")
    print("Update main.js CONFIG.proxyUrl to 'http://localhost:3000'")
    app.run(host='0.0.0.0', port=3000, debug=False)
