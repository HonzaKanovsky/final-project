from flask import Flask, render_template_string
from flask_socketio import SocketIO
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

# Store latest frame per client (by session id)
latest_frames = {}

@app.route('/')
def admin_dashboard():
    # Display all received frames
    images_html = ''.join([
        f'<div style="display:inline-block;margin:10px;"><img src="{frame}" width="320" height="240"/><br>Client: {sid}</div>'
        for sid, frame in latest_frames.items()
    ])
    return render_template_string(f'''
        <h1>Admin Dashboard</h1>
        <div id="streams">{images_html}</div>
        <script>
        setInterval(() => {{ location.reload(); }}, 1000);
        </script>
    ''')

@socketio.on('video_frame')
def handle_video_frame(data):
    sid = threading.get_ident()
    # Use request.sid if you want per-client, but here we use thread id for simplicity
    latest_frames[sid] = data['frame']

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True) 