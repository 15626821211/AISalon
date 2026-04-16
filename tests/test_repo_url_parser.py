"""仓库 URL 解析测试。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from integrations.github_client import parse_repo_url


def test_parse_github_repo_url():
    repo_info = parse_repo_url('https://github.com/pallets/flask')

    assert repo_info['provider'] == 'github'
    assert repo_info['owner'] == 'pallets'
    assert repo_info['repo'] == 'flask'
    assert repo_info['project_path'] == 'pallets/flask'


def test_parse_gitlab_repo_url():
    repo_info = parse_repo_url('http://dev-gitlab.aeonbuy.com/dataplatform/monitor-cn-wecom')

    assert repo_info['provider'] == 'gitlab'
    assert repo_info['owner'] == 'dataplatform'
    assert repo_info['repo'] == 'monitor-cn-wecom'
    assert repo_info['project_path'] == 'dataplatform/monitor-cn-wecom'


def test_parse_gitlab_nested_group_url():
    repo_info = parse_repo_url('https://gitlab.example.com/group/subgroup/project.git')

    assert repo_info['provider'] == 'gitlab'
    assert repo_info['repo'] == 'project'
    assert repo_info['project_path'] == 'group/subgroup/project'


def test_parse_invalid_repo_url_raises():
    with pytest.raises(ValueError, match='仓库 URL'):
        parse_repo_url('not-a-valid-url')