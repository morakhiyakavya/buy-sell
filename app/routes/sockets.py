from flask_login import current_user
from flask_socketio import join_room
from app import socketio


@socketio.on("join")
def on_join(data):
    room = current_user.id
    join_room(room)

