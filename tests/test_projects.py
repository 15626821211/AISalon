"""项目知识库模块测试——基于 Flask 测试客户端 + 测试数据库。"""
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


def _register_and_login(client):
    client.post('/users/register', json={'username': 'projuser', 'password': 'pass123'})
    return client


def test_create_project(client):
    _register_and_login(client)
    resp = client.post('/projects/', json={
        'name': 'Test Project',
        'github_url': 'https://github.com/test/repo',
        'team': 'Alice, Bob',
        'tags': 'AI, NLP',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Test Project'
    assert data['status'] == 'draft'


def test_list_projects(client):
    _register_and_login(client)
    client.post('/projects/', json={'name': 'P1', 'github_url': 'https://github.com/a/b'})
    client.post('/projects/', json={'name': 'P2', 'github_url': 'https://github.com/c/d'})
    resp = client.get('/projects/')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_get_project(client):
    _register_and_login(client)
    create_resp = client.post('/projects/', json={'name': 'Find', 'github_url': 'https://github.com/x/y'})
    pid = create_resp.get_json()['id']
    resp = client.get(f'/projects/{pid}')
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Find'


def test_delete_project(client):
    _register_and_login(client)
    create_resp = client.post('/projects/', json={'name': 'Del', 'github_url': 'https://github.com/x/y'})
    pid = create_resp.get_json()['id']
    resp = client.delete(f'/projects/{pid}')
    assert resp.status_code == 204


def test_project_comment(client):
    _register_and_login(client)
    create_resp = client.post('/projects/', json={'name': 'Comment', 'github_url': 'https://github.com/x/y'})
    pid = create_resp.get_json()['id']
    resp = client.post(f'/projects/{pid}/comments', json={'content': 'Nice project!'})
    assert resp.status_code == 201
    resp2 = client.get(f'/projects/{pid}/comments')
    assert len(resp2.get_json()) == 1


def test_unauthorized_create(client):
    resp = client.post('/projects/', json={'name': 'No Auth', 'github_url': 'https://github.com/x/y'})
    assert resp.status_code == 401
