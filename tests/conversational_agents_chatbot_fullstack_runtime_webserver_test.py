# -*- coding: utf-8 -*-
import os
import time
import tempfile
import pytest
import conversational_agents.chatbot_fullstack_runtime.backend.web_server as ws


app = ws.app
_db = ws.db
User = ws.User


def generate_unique_username():
    return f"testuser_{int(time.time())}"


@pytest.fixture
def client_and_username():
    """Create an Isolated Test Client and Username"""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["TESTING"] = True
    client = app.test_client()

    with app.app_context():
        _db.drop_all()
        _db.create_all()

        # Generate Unique Username
        username = generate_unique_username()
        password = "testpass"
        user = User(username=username, name="Test User")
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()

    yield client, username, password

    os.close(db_fd)
    os.unlink(db_path)


def test_user_login_success(
    # pylint: disable=redefined-outer-name
    client_and_username,
):
    """Test Successful User Login"""
    client, username, password = client_and_username

    response = client.post(
        "/api/login",
        json={
            "username": username,
            "password": password,
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "id" in data
    assert data["username"] == username
