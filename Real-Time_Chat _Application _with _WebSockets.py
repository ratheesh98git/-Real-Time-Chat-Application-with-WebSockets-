from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room, send
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = '1234567'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class ChatRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())

@app.route('/')
def index():
    if 'username' in session:
        rooms = ChatRoom.query.all()
        return render_template('real_time_chat_index.html', rooms=rooms)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = username
            return redirect(url_for('index'))
        return 'Invalid credentials'
    return render_template('real_time_chat_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('real_time_chat_register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/create_room', methods=['POST'])
def create_room():
    room_name = request.form['room_name']
    if room_name:
        new_room = ChatRoom(name=room_name)
        db.session.add(new_room)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/chat/<room_name>')
def chat(room_name):
    room = ChatRoom.query.filter_by(name=room_name).first_or_404()
    messages = Message.query.filter_by(room_id=room.id).order_by(Message.timestamp).all()
    return render_template('real_time_chat_chat.html', room=room, messages=messages)

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    send(f'{username} has entered the room.', to=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    send(f'{username} has left the room.', to=room)

@socketio.on('message')
def on_message(data):
    room = data['room']
    message = data['message']
    username = data['username']
    room_obj = ChatRoom.query.filter_by(name=room).first()
    new_message = Message(room_id=room_obj.id, username=username, message=message)
    db.session.add(new_message)
    db.session.commit()
    send({'username': username, 'message': message}, to=room)

if __name__ == '__main__':
    db.create_all()
    socketio.run(app, debug=True)
