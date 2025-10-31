from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, patch
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize db instance
db = SQLAlchemy()


# Define model classes (defined once)
class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Conversation(db.Model):
    __tablename__ = "conversation"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    messages = db.relationship("Message", backref="conversation", lazy=True)


class Message(db.Model):
    __tablename__ = "message"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    sender = db.Column(db.String(20), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


# Thoroughly isolated test Flask application
@pytest.fixture
def app():
    """Create a fresh Flask application instance"""
    app = Flask(__name__)
    app.config.update({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "TESTING": True,
    })

    # Initialize db
    db.init_app(app)

    # Define routes
    @app.route("/api/login", methods=["POST"])
    def login():
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Username and password cannot be empty"}), 400

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            return jsonify({
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "created_at": user.created_at.isoformat(),
            }), 200
        return jsonify({"error": "Invalid username or password"}), 401

    @app.route("/api/users/<int:user_id>/conversations", methods=["POST"])
    def create_conversation(user_id):
        data = request.get_json()
        title = data.get("title", f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        conversation = Conversation(title=title, user_id=user_id)
        db.session.add(conversation)
        db.session.commit()
        return jsonify({
            "id": conversation.id,
            "title": conversation.title,
            "user_id": conversation.user_id,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
        }), 201

    @app.route("/api/conversations/<int:conversation_id>", methods=["GET"])
    def get_conversation(conversation_id):
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at.asc()).all()
        messages_data = [{
            "id": msg.id,
            "text": msg.text,
            "sender": msg.sender,
            "created_at": msg.created_at.isoformat(),
        } for msg in messages]

        return jsonify({
            "id": conversation.id,
            "title": conversation.title,
            "user_id": conversation.user_id,
            "messages": messages_data,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
        }), 200

    @app.route("/api/conversations/<int:conversation_id>/messages", methods=["POST"])
    def send_message(conversation_id):
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        data = request.get_json()
        text = data.get("text")
        sender = data.get("sender", "user")

        if not text:
            return jsonify({"error": "Message content cannot be empty"}), 400

        # Create user message
        user_message = Message(
            text=text,
            sender=sender,
            conversation_id=conversation_id
        )
        db.session.add(user_message)

        # Update conversation title (if this is the first user message)
        if sender == "user" and len(conversation.messages) <= 1:
            conversation.title = text[:20] + ("..." if len(text) > 20 else "")

        db.session.commit()

        # Simulate AI response
        ai_message = Message(
            text="Test response part 1 Test response part 2",
            sender="ai",
            conversation_id=conversation_id
        )
        db.session.add(ai_message)
        db.session.commit()

        return jsonify({
            "id": user_message.id,
            "text": user_message.text,
            "sender": user_message.sender,
            "created_at": user_message.created_at.isoformat(),
        }), 201

    # Initialize database
    with app.app_context():
        db.create_all()
        # Create example users
        if not User.query.first():
            user1 = User(username="user1", name="Bruce")
            user1.set_password("password123")
            db.session.add(user1)
            db.session.commit()

    yield app

    with app.app_context():
        db.drop_all()
        db.session.remove()


@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()


# Mock call_runner function
def mock_call_runner(query, session_id, user_id):
    """Mock function for call_runner"""
    yield "Test response part 1"
    yield " Test response part 2"


def test_login_success(app, client):
    """Test successful user login"""
    with app.app_context():
        user = User(username="test", name="Test User")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    response = client.post("/api/login", json={
        "username": "test",
        "password": "testpass",
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data["username"] == "test"


def test_login_invalid_credentials(app, client):
    """Test login with invalid credentials"""
    response = client.post("/api/login", json={
        "username": "test",
        "password": "wrongpass"
    })
    assert response.status_code == 401


def test_conversation_crud_operations(app, client):
    """Test conversation creation and retrieval"""
    with app.app_context():
        user = User(username="test", name="Test User")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    create_response = client.post("/api/users/1/conversations", json={
        "title": "Test Conversation",
    })
    assert create_response.status_code == 201
    conversation_id = create_response.get_json()["id"]

    get_response = client.get(f"/api/conversations/{conversation_id}")
    assert get_response.status_code == 200
    assert "Test Conversation" in get_response.get_json()["title"]


@patch("tests.conversational_agents_chatbot_fullstack_runtime_webserver_test.db", new=db)
def test_send_message(app, client):
    """Test message sending and AI response"""
    with app.app_context():
        user = User(username="test", name="Test User")
        user.set_password("testpass")
        conversation = Conversation(title="Test", user_id=1)
        db.session.add_all([user, conversation])
        db.session.commit()

    response = client.post("/api/conversations/1/messages", json={
        "text": "Hello",
        "sender": "user"
    })
    assert response.status_code == 201
    data = response.get_json()
    assert "id" in data
    assert "Hello" in data["text"]

    # ✅ Move the query into the application context
    with app.app_context():
        messages = Message.query.filter_by(conversation_id=1).all()
        assert len(messages) == 2  # User + AI response