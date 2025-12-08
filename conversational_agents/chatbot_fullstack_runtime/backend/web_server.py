# -*- coding: utf-8 -*-
import json
import logging
import os
from datetime import datetime

import requests

from openai import OpenAI
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
# Configure database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    basedir,
    "ai_assistant.db",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db: SQLAlchemy = SQLAlchemy(app)


# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    conversations = db.relationship(
        "Conversation",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    messages = db.relationship(
        "Message",
        backref="conversation",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    sender = db.Column(db.String(20), nullable=False)  # 'user' or 'ai'
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("conversation.id"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Create database tables


def create_tables():
    db.create_all()

    # Create sample users (if none exist)
    if not User.query.first():
        user1 = User(username="user1", name="Bruce")
        user1.set_password("password123")
        user2 = User(username="user2", name="John")
        user2.set_password("password456")
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()


# functions
def parse_sse_line(line):
    line = line.decode("utf-8").strip()
    if line.startswith("data: "):
        return "data", line[6:]
    elif line.startswith("event:"):
        return "event", line[7:]
    elif line.startswith("id: "):
        return "id", line[4:]
    elif line.startswith("retry:"):
        return "retry", int(line[7:])
    return None, None


def sse_client(url, data=None):
    headers = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
    }
    if data is not None:
        response = requests.post(
            url,
            stream=True,
            headers=headers,
            json=data,
        )
    else:
        response = requests.get(
            url,
            stream=True,
            headers=headers,
        )
    for line in response.iter_lines():
        if line:
            field, value = parse_sse_line(line)
            if field == "data":
                try:
                    data = json.loads(value)
                    if (
                        data["object"] == "content"
                        and data["delta"] is True
                        and data["type"] == "text"
                    ):
                        yield data["text"]

                except json.JSONDecodeError:
                    pass


def call_runner(query):
    server_port = int(os.environ.get("SERVER_PORT", "8090"))
    server_host = os.environ.get("SERVER_HOST", "localhost")

    client = OpenAI(
        base_url=f"http://{server_host}:{server_port}/compatible-mode/v1",
    )

    stream = client.responses.create(
        model="any_name",
        input=query,
        stream=True,
    )

    for chunk in stream:
        if hasattr(chunk, "delta"):
            yield chunk.delta
        else:
            yield ""


# API routes


# User login
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password cannot be empty"}), 400

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        return (
            jsonify(
                {
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                    "created_at": user.created_at.isoformat(),
                },
            ),
            200,
        )
    else:
        return jsonify({"error": "Invalid username or password"}), 401


# Get all user conversations
@app.route("/api/users/<int:user_id>/conversations", methods=["GET"])
def get_user_conversations(user_id):
    User.query.get_or_404(user_id)
    conversations = (
        Conversation.query.filter_by(user_id=user_id)
        .order_by(
            Conversation.updated_at.desc(),
        )
        .all()
    )

    result = []
    for conv in conversations:
        # Get the last message as preview
        last_message = (
            Message.query.filter_by(
                conversation_id=conv.id,
            )
            .order_by(
                Message.created_at.desc(),
            )
            .first()
        )
        preview = last_message.text if last_message else ""

        result.append(
            {
                "id": conv.id,
                "title": conv.title,
                "user_id": conv.user_id,
                "preview": preview,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
            },
        )

    return jsonify(result), 200


# Create new conversation
@app.route("/api/users/<int:user_id>/conversations", methods=["POST"])
def create_conversation(user_id):
    User.query.get_or_404(user_id)
    data = request.get_json()

    title = data.get(
        "title",
        f'Conversation {datetime.now().strftime("%Y-%m-%d %H:%M")}',
    )

    conversation = Conversation(title=title, user_id=user_id)
    db.session.add(conversation)
    db.session.commit()

    # Create welcome message
    welcome_message = Message(
        text="Hello! I am your AI assistant. How can I help you today?",
        sender="ai",
        conversation_id=conversation.id,
    )
    db.session.add(welcome_message)
    db.session.commit()

    return (
        jsonify(
            {
                "id": conversation.id,
                "title": conversation.title,
                "user_id": conversation.user_id,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
            },
        ),
        201,
    )


# Get conversation details and messages
@app.route("/api/conversations/<int:conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    messages = (
        Message.query.filter_by(
            conversation_id=conversation_id,
        )
        .order_by(
            Message.created_at.asc(),
        )
        .all()
    )

    messages_data = []
    for msg in messages:
        messages_data.append(
            {
                "id": msg.id,
                "text": msg.text,
                "sender": msg.sender,
                "created_at": msg.created_at.isoformat(),
            },
        )

    return (
        jsonify(
            {
                "id": conversation.id,
                "title": conversation.title,
                "user_id": conversation.user_id,
                "messages": messages_data,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
            },
        ),
        200,
    )


# Send message
@app.route(
    "/api/conversations/<int:conversation_id>/messages",
    methods=["POST"],
)
def send_message(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    data = request.get_json()

    text = data.get("text")
    sender = data.get("sender", "user")

    if not text:
        return jsonify({"error": "Message content cannot be empty"}), 400

    # Create user message
    user_message = Message(
        text=text,
        sender=sender,
        conversation_id=conversation_id,
    )
    db.session.add(user_message)

    # Update conversation title (if it's the first user message)
    if sender == "user" and len(conversation.messages) <= 1:
        conversation.title = text[:20] + ("..." if len(text) > 20 else "")

    db.session.commit()

    if sender == "user":
        ai_response_text = ""

        question = text

        for item in call_runner(
            question,
        ):
            ai_response_text += item

        ai_message = Message(
            text=ai_response_text,
            sender="ai",
            conversation_id=conversation_id,
        )
        db.session.add(ai_message)
        db.session.commit()

    return (
        jsonify(
            {
                "id": user_message.id,
                "text": user_message.text,
                "sender": user_message.sender,
                "created_at": user_message.created_at.isoformat(),
            },
        ),
        201,
    )


# Delete conversation
@app.route("/api/conversations/<int:conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({"message": "Conversation deleted successfully"}), 200


# Update conversation title
@app.route("/api/conversations/<int:conversation_id>", methods=["PUT"])
def update_conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    data = request.get_json()

    if "title" in data:
        conversation.title = data["title"]

    db.session.commit()

    return (
        jsonify(
            {
                "id": conversation.id,
                "title": conversation.title,
                "user_id": conversation.user_id,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
            },
        ),
        200,
    )


# Get user information
@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return (
        jsonify(
            {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "created_at": user.created_at.isoformat(),
            },
        ),
        200,
    )


# Error handling
@app.errorhandler(404)
def not_found(error):
    logger.error(error)
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(error)
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5100)
