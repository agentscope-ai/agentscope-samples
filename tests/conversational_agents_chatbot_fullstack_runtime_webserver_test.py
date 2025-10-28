# -*- coding: utf-8 -*-
# tests/chatbot_fullstack_runtime/test_webserver.py
from datetime import datetime
import pytest
from unittest.mock import MagicMock, patch
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from agentscope.message import Msg

# 本地模块导入
from conversational_agents.chatbot_fullstack_runtime.backend.web_server import (
    User,
    Conversation,
    Message,
)


# 创建全新的测试 Flask 应用
@pytest.fixture
def app():
    """创建全新的 Flask 应用实例"""
    app = Flask(__name__)
    app.config.update(
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "TESTING": True,
        }
    )

    # 创建新的 SQLAlchemy 实例
    db = SQLAlchemy(app)

    # 重新定义模型类
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        password_hash = db.Column(db.String(120), nullable=False)
        name = db.Column(db.String(100), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        conversations = db.relationship(
            "Conversation", backref="user", lazy=True
        )

    class Conversation(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(200), nullable=False)
        user_id = db.Column(
            db.Integer, db.ForeignKey("user.id"), nullable=False
        )
        messages = db.relationship(
            "Message", backref="conversation", lazy=True
        )

    class Message(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        text = db.Column(db.Text, nullable=False)
        sender = db.Column(db.String(20), nullable=False)
        conversation_id = db.Column(
            db.Integer, db.ForeignKey("conversation.id"), nullable=False
        )

    # 初始化数据库
    with app.app_context():
        db.create_all()

    # 将模型类附加到 app 供测试使用
    app.db = db
    app.User = User
    app.Conversation = Conversation
    app.Message = Message

    yield app

    # 清理数据库
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()


# 模拟 call_runner 函数
def mock_call_runner(query, session_id, user_id):
    """Mock function for call_runner"""
    yield "Test response part 1"
    yield " Test response part 2"


def test_login_success(app, client):
    """Test successful user login"""
    with app.app_context():
        # 创建测试用户
        user = app.User(username="test", name="Test User")
        user.set_password = lambda p: setattr(user, "password_hash", p)
        app.db.session.add(user)
        app.db.session.commit()

    response = client.post(
        "/api/login",
        json={
            "username": "test",
            "password": "testpass",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["username"] == "test"


def test_login_invalid_credentials(app, client):
    """Test login with invalid credentials"""
    response = client.post(
        "/api/login",
        json={
            "username": "test",
            "password": "wrongpass",
        },
    )

    assert response.status_code == 401


def test_conversation_crud_operations(app, client):
    """Test conversation creation and retrieval"""
    with app.app_context():
        # 创建测试用户
        user = app.User(username="test", name="Test User")
        user.set_password = lambda p: setattr(user, "password_hash", p)
        app.db.session.add(user)
        app.db.session.commit()

        # 创建对话
        create_response = client.post(
            "/api/users/1/conversations",
            json={"title": "Test Conversation"},
        )

        assert create_response.status_code == 201
        conversation_id = create_response.get_json()["id"]

        # 获取对话
        get_response = client.get(f"/api/conversations/{conversation_id}")
        assert get_response.status_code == 200
        assert "Test Conversation" in get_response.get_json()["title"]


@patch(
    "conversational_agents.chatbot_fullstack_runtime.backend.web_server.call_runner",
    new=MagicMock(side_effect=mock_call_runner),
)
def test_send_message(app, client):
    """Test message sending and AI response"""
    with app.app_context():
        # 创建测试用户和对话
        user = app.User(username="test", name="Test User")
        user.set_password = lambda p: setattr(user, "password_hash", p)
        conversation = app.Conversation(title="Test", user_id=1)
        app.db.session.add_all([user, conversation])
        app.db.session.commit()

        # 发送消息
        response = client.post(
            "/api/conversations/1/messages",
            json={"text": "Hello", "sender": "user"},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert "id" in data
        assert "Hello" in data["text"]

        # 验证 AI 回复
        messages = app.Message.query.filter_by(conversation_id=1).all()
        assert len(messages) == 2  # 用户 + AI 回复
