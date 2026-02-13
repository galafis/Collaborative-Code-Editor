#!/usr/bin/env python3
"""
Collaborative Code Editor
Real-time collaborative code editor with syntax highlighting, live collaboration,
and integrated chat functionality using WebSockets.
"""

import os
import uuid
from datetime import datetime

from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
socketio = SocketIO(app, cors_allowed_origins=os.environ.get('CORS_ORIGINS', '*'))

# In-memory storage for demo
documents = {}
active_users = {}
chat_messages = {}

# Sample documents
documents['demo-js'] = {
    'id': 'demo-js',
    'title': 'JavaScript Demo',
    'language': 'javascript',
    'content': '''// Welcome to the Collaborative Code Editor!
// This is a real-time collaborative editor with syntax highlighting

function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

// Calculate and display fibonacci sequence
for (let i = 0; i < 10; i++) {
    console.log(`Fibonacci(${i}) = ${fibonacci(i)}`);
}

// Object-oriented example
class Calculator {
    constructor() {
        this.history = [];
    }
    
    add(a, b) {
        const result = a + b;
        this.history.push(`${a} + ${b} = ${result}`);
        return result;
    }
    
    getHistory() {
        return this.history;
    }
}

const calc = new Calculator();
console.log(calc.add(5, 3));
console.log(calc.getHistory());''',
    'created_at': datetime.now().isoformat(),
    'last_modified': datetime.now().isoformat()
}

documents['demo-python'] = {
    'id': 'demo-python',
    'title': 'Python Demo',
    'language': 'python',
    'content': '''# Welcome to the Collaborative Code Editor!
# Real-time collaboration with syntax highlighting

import math
from datetime import datetime

def calculate_prime_numbers(limit):
    """Generate prime numbers up to the given limit using Sieve of Eratosthenes"""
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    
    for i in range(2, int(math.sqrt(limit)) + 1):
        if sieve[i]:
            for j in range(i * i, limit + 1, i):
                sieve[j] = False
    
    return [i for i in range(2, limit + 1) if sieve[i]]

# Data analysis example
class DataAnalyzer:
    def __init__(self, data):
        self.data = data
        self.timestamp = datetime.now()
    
    def calculate_statistics(self):
        if not self.data:
            return None
        
        return {
            'mean': sum(self.data) / len(self.data),
            'min': min(self.data),
            'max': max(self.data),
            'count': len(self.data)
        }
    
    def filter_outliers(self, threshold=2):
        if len(self.data) < 2:
            return self.data
        
        mean = sum(self.data) / len(self.data)
        std_dev = (sum((x - mean) ** 2 for x in self.data) / len(self.data)) ** 0.5
        
        return [x for x in self.data if abs(x - mean) <= threshold * std_dev]

# Example usage
sample_data = [1, 2, 3, 4, 5, 100, 6, 7, 8, 9, 10]
analyzer = DataAnalyzer(sample_data)

print("Original data:", sample_data)
print("Statistics:", analyzer.calculate_statistics())
print("Without outliers:", analyzer.filter_outliers())
print("Prime numbers up to 50:", calculate_prime_numbers(50))''',
    'created_at': datetime.now().isoformat(),
    'last_modified': datetime.now().isoformat()
}

@app.route('/')
def index():
    return jsonify({
        'name': 'Collaborative Code Editor',
        'description': 'Real-time collaborative code editor backend using Flask-SocketIO',
        'endpoints': {
            'GET /api/documents': 'List all documents',
            'GET /api/documents/<doc_id>': 'Get a specific document',
            'GET /api/stats': 'Get server statistics'
        },
        'websocket_events': [
            'join_document', 'leave_document', 'code_change',
            'cursor_change', 'send_message', 'get_chat_history',
            'create_document', 'save_document'
        ]
    })

@app.route('/api/documents')
def get_documents():
    return jsonify(list(documents.values()))

@app.route('/api/documents/<doc_id>')
def get_document(doc_id):
    if doc_id in documents:
        return jsonify(documents[doc_id])
    return jsonify({'error': 'Document not found'}), 404

@socketio.on('connect')
def on_connect():
    print(f'User connected: {request.sid}')
    emit('connected', {'user_id': request.sid})

@socketio.on('disconnect')
def on_disconnect():
    print(f'User disconnected: {request.sid}')
    # Remove user from all rooms and active users
    for doc_id in list(active_users.keys()):
        if request.sid in active_users[doc_id]:
            active_users[doc_id].pop(request.sid, None)
            if not active_users[doc_id]:
                del active_users[doc_id]
            else:
                emit('user_left', {
                    'user_id': request.sid,
                    'active_users': list(active_users[doc_id].values())
                }, room=doc_id)

@socketio.on('join_document')
def on_join_document(data):
    doc_id = data.get('document_id')
    if not doc_id:
        return
    username = data.get('username', f'User_{request.sid[:8]}')
    
    join_room(doc_id)
    
    # Add user to active users
    if doc_id not in active_users:
        active_users[doc_id] = {}
    
    active_users[doc_id][request.sid] = {
        'id': request.sid,
        'username': username,
        'cursor_position': 0,
        'selection': None
    }
    
    # Send document content and active users to the joining user
    if doc_id in documents:
        emit('document_content', {
            'document': documents[doc_id],
            'active_users': list(active_users[doc_id].values())
        })
    
    # Notify other users in the room
    emit('user_joined', {
        'user': active_users[doc_id][request.sid],
        'active_users': list(active_users[doc_id].values())
    }, room=doc_id, include_self=False)

@socketio.on('leave_document')
def on_leave_document(data):
    doc_id = data.get('document_id')
    if not doc_id:
        return
    leave_room(doc_id)
    
    # Remove user from active users
    if doc_id in active_users and request.sid in active_users[doc_id]:
        active_users[doc_id].pop(request.sid, None)
        
        if not active_users[doc_id]:
            del active_users[doc_id]
        else:
            emit('user_left', {
                'user_id': request.sid,
                'active_users': list(active_users[doc_id].values())
            }, room=doc_id)

@socketio.on('code_change')
def on_code_change(data):
    doc_id = data.get('document_id')
    content = data.get('content')
    if not doc_id or content is None:
        return
    change_data = data.get('change', {})
    
    # Update document content
    if doc_id in documents:
        documents[doc_id]['content'] = content
        documents[doc_id]['last_modified'] = datetime.now().isoformat()
    
    # Broadcast change to other users in the room
    emit('code_changed', {
        'content': content,
        'change': change_data,
        'user_id': request.sid
    }, room=doc_id, include_self=False)

@socketio.on('cursor_change')
def on_cursor_change(data):
    doc_id = data.get('document_id')
    cursor_position = data.get('cursor_position')
    if not doc_id or cursor_position is None:
        return
    selection = data.get('selection')
    
    # Update user's cursor position
    if doc_id in active_users and request.sid in active_users[doc_id]:
        active_users[doc_id][request.sid]['cursor_position'] = cursor_position
        active_users[doc_id][request.sid]['selection'] = selection
    
    # Broadcast cursor position to other users
    emit('cursor_changed', {
        'user_id': request.sid,
        'cursor_position': cursor_position,
        'selection': selection
    }, room=doc_id, include_self=False)

@socketio.on('send_message')
def on_send_message(data):
    doc_id = data.get('document_id')
    message = data.get('message')
    if not doc_id or not message:
        return
    username = data.get('username', f'User_{request.sid[:8]}')
    
    # Store message
    if doc_id not in chat_messages:
        chat_messages[doc_id] = []
    
    message_data = {
        'id': str(uuid.uuid4()),
        'user_id': request.sid,
        'username': username,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    
    chat_messages[doc_id].append(message_data)
    
    # Keep only last 100 messages
    if len(chat_messages[doc_id]) > 100:
        chat_messages[doc_id] = chat_messages[doc_id][-100:]
    
    # Broadcast message to all users in the room
    emit('new_message', message_data, room=doc_id)

@socketio.on('get_chat_history')
def on_get_chat_history(data):
    doc_id = data.get('document_id')
    if not doc_id:
        return
    messages = chat_messages.get(doc_id, [])
    emit('chat_history', {'messages': messages})

@socketio.on('create_document')
def on_create_document(data):
    doc_id = str(uuid.uuid4())
    title = data.get('title', 'Untitled Document')
    language = data.get('language', 'javascript')
    
    new_document = {
        'id': doc_id,
        'title': title,
        'language': language,
        'content': f'// Welcome to {title}\n// Start coding here...\n\n',
        'created_at': datetime.now().isoformat(),
        'last_modified': datetime.now().isoformat()
    }
    
    documents[doc_id] = new_document
    emit('document_created', new_document)

@socketio.on('save_document')
def on_save_document(data):
    doc_id = data.get('document_id')
    if not doc_id:
        return
    
    if doc_id in documents:
        documents[doc_id]['last_modified'] = datetime.now().isoformat()
        emit('document_saved', {
            'document_id': doc_id,
            'last_modified': documents[doc_id]['last_modified']
        })

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

