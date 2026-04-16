"""用户模块测试——基于 Flask 测试客户端 + 测试数据库。"""
import sys
import os

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from app import create_app
from models import db


@pytest.fixture
def app():
    application = create_app()
    application.config['TESTING'] = True
    application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with application.app_context():
        db.create_all()
        yield application
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_register(client):
    resp = client.post('/users/register', json={'username': 'alice', 'password': 'pass123'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['user']['username'] == 'alice'


def test_register_duplicate(client):
    client.post('/users/register', json={'username': 'bob', 'password': 'pass123'})
    resp = client.post('/users/register', json={'username': 'bob', 'password': 'pass456'})
    assert resp.status_code == 400


def test_login(client):
    client.post('/users/register', json={'username': 'carol', 'password': 'pass123'})
    resp = client.post('/users/login', json={'username': 'carol', 'password': 'pass123'})
    assert resp.status_code == 200
    assert resp.get_json()['user']['username'] == 'carol'


def test_login_wrong_password(client):
    client.post('/users/register', json={'username': 'dave', 'password': 'pass123'})
    resp = client.post('/users/login', json={'username': 'dave', 'password': 'wrong'})
    assert resp.status_code == 401


def test_get_me(client):
    client.post('/users/register', json={'username': 'eve', 'password': 'pass123'})
    resp = client.get('/users/me')
    assert resp.status_code == 200
    assert resp.get_json()['username'] == 'eve'


def test_logout(client):
    client.post('/users/register', json={'username': 'frank', 'password': 'pass123'})
    resp = client.post('/users/logout')
    assert resp.status_code == 200
    resp2 = client.get('/users/me')
    assert resp2.status_code == 401