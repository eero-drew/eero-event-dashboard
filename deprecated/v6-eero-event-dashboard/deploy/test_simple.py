#!/usr/bin/env python3
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>Test Dashboard Working</h1><p>Version: Test</p>'

@app.route('/health')
def health():
    return '{"status": "ok"}'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
