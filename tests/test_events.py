"""活动模块测试——基于 Flask 测试客户端 + 测试数据库。"""
import sys
import os

# 必须在导入 app/config 之前设置环境变量，否则 Config 类会连 MySQL
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from app import create_app
from models import db


@pytest.fixture
def app():
    """创建测试用 Flask 应用（使用 SQLite 内存数据库）。"""
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


def _register_and_login(client):
    client.post('/users/register', json={'username': 'testuser', 'password': 'testpass'})
    return client


def test_create_event(client):
    _register_and_login(client)
    resp = client.post('/events/', json={
        'title': 'Test Event',
        'description': 'A test event.',
        'location': 'Online',
        'tags': 'AI, 测试',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['title'] == 'Test Event'
    assert 'AI' in data['tags']


def test_list_events(client):
    _register_and_login(client)
    client.post('/events/', json={'title': 'Event 1', 'location': 'A'})
    client.post('/events/', json={'title': 'Event 2', 'location': 'B'})
    resp = client.get('/events/')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2


def test_get_event(client):
    _register_and_login(client)
    create_resp = client.post('/events/', json={'title': 'Find Me', 'location': 'Here'})
    event_id = create_resp.get_json()['id']
    resp = client.get(f'/events/{event_id}')
    assert resp.status_code == 200
    assert resp.get_json()['title'] == 'Find Me'


def test_delete_event(client):
    _register_and_login(client)
    create_resp = client.post('/events/', json={'title': 'Delete Me', 'location': 'X'})
    event_id = create_resp.get_json()['id']
    resp = client.delete(f'/events/{event_id}')
    assert resp.status_code == 204
    resp2 = client.get(f'/events/{event_id}')
    assert resp2.status_code == 404


def test_signup_event(client):
    _register_and_login(client)
    create_resp = client.post('/events/', json={'title': 'Signup Test', 'location': 'Y'})
    event_id = create_resp.get_json()['id']
    resp = client.post(f'/events/{event_id}/signup', json={'name': 'Alice'})
    assert resp.status_code == 201