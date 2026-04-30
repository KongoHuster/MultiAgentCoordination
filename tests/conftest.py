"""
pytest 配置文件
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """测试环境设置"""
    # 确保使用测试配置
    os.environ['TESTING'] = 'true'
    yield
    # 清理
    os.environ.pop('TESTING', None)


@pytest.fixture(scope='function')
def clean_state():
    """每个测试前清理状态"""
    from web_server import state
    # 保留测试数据但记录初始状态
    original_projects = state.projects.copy()
    yield state
    # 测试后不清理，保留测试创建的数据用于后续测试


def pytest_configure(config):
    """pytest 配置"""
    config.addinivalue_line(
        "markers", "integration: 集成测试"
    )
    config.addinivalue_line(
        "markers", "ui: UI测试"
    )
    config.addinivalue_line(
        "markers", "api: API测试"
    )
