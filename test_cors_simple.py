#!/usr/bin/env python3
"""Test simple pour voir si after_request fonctionne"""

from flask import Flask, jsonify, request

app = Flask(__name__)

@app.after_request  
def add_cors(response):
    print(f"🔧 APRÈS REQUÊTE pour: {request.path}")
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    print(f"🔧 En-têtes CORS ajoutés")
    return response

@app.route('/test')
def test():
    return jsonify({"message": "test"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8001, debug=True)