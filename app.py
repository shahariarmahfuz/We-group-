from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from os import environ
from collections import deque
import eventlet

# Monkey patch to support WebSocket transport
eventlet.monkey_patch()

app = Flask(__name__)
socketio = SocketIO(app)

users = {}
groups = {}
user_groups = {}
group_messages = {}  # Dictionary to store messages for each group

# Keep the last 100 messages for each group
MESSAGE_LIMIT = 100

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/groups')
def groups_page():
    return render_template('groups.html')

@app.route('/chat/<group_id>')
def chat(group_id):
    return render_template('chat.html', group_id=group_id)

@app.route('/get-groups')
def get_groups():
    user_id = request.args.get('user_id')
    my_groups = [group for group in user_groups.get(user_id, [])[:3]]
    all_groups = list(groups.values())
    return jsonify({
        'my_groups': my_groups,
        'all_groups': all_groups
    })

@app.route('/create-group', methods=['POST'])
def create_group():
    user_id = request.form.get('user_id')
    group_name = request.form.get('group_name')
    group_id = request.form.get('group_id')

    if group_id in groups:
        return jsonify({'success': False, 'message': 'Group ID already exists.'})

    groups[group_id] = {'name': group_name, 'members': [user_id]}
    user_groups.setdefault(user_id, []).append(group_id)
    group_messages[group_id] = deque(maxlen=MESSAGE_LIMIT)  # Initialize deque for message storage
    return jsonify({'success': True, 'message': 'Group created successfully.'})

@app.route('/join-group', methods=['POST'])
def join_group():
    user_id = request.form.get('user_id')
    group_id = request.form.get('group_id')

    if group_id not in groups:
        return jsonify({'success': False, 'message': 'Group ID does not exist.'})

    groups[group_id]['members'].append(user_id)
    user_groups.setdefault(user_id, []).append(group_id)
    return jsonify({'success': True, 'message': 'Joined group successfully.'})

@app.route('/get-messages/<group_id>', methods=['GET'])
def get_messages(group_id):
    # Fetch the last 100 messages for a given group
    if group_id in group_messages:
        messages = list(group_messages[group_id])
    else:
        messages = []

    return jsonify(messages)

@socketio.on('message')
def handle_message(data):
    user_id = data['user_id']
    user_name = data['user_name']
    message = data['message']
    profile_picture = data.get('profile_picture', 'default-avatar.png')
    group_id = data['group_id']

    if group_id not in groups:
        return

    # Save the message to the group's message history
    group_messages.setdefault(group_id, deque(maxlen=MESSAGE_LIMIT)).append({
        'user_id': user_id,
        'user_name': user_name,
        'message': message,
        'profile_picture': profile_picture,
        'group_id': group_id
    })

    emit('broadcast message', {'user_id': user_id, 'user_name': user_name, 'message': message, 'profile_picture': profile_picture, 'group_id': group_id}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(environ.get('PORT', 5000)), debug=True)
