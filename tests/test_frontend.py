"""
MultiAgent协作系统 - 前端文件独立测试
不依赖后端模块，直接测试HTML/CSS/JS文件
"""

import pytest
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


# ========== 用例1: 项目管理测试 (文件级别) ==========

class TestFileExistence:
    """文件存在性测试"""

    def test_index_html_exists(self):
        """测试 index.html 存在"""
        path = PROJECT_ROOT / "web" / "index.html"
        assert path.exists(), f"文件不存在: {path}"

    def test_styles_css_exists(self):
        """测试 styles.css 存在"""
        path = PROJECT_ROOT / "web" / "styles.css"
        assert path.exists(), f"文件不存在: {path}"

    def test_app_js_exists(self):
        """测试 app.js 存在"""
        path = PROJECT_ROOT / "web" / "app.js"
        assert path.exists(), f"文件不存在: {path}"


# ========== 用例2: HTML结构测试 ==========

class TestHTMLStructure:
    """HTML结构测试"""

    def test_html_contains_sidebar(self):
        """测试HTML包含侧边栏"""
        html_path = PROJECT_ROOT / "web" / "index.html"
        content = html_path.read_text()
        assert 'id="sidebar"' in content, "缺少侧边栏"

    def test_html_contains_project_list(self):
        """测试HTML包含项目列表"""
        html_path = PROJECT_ROOT / "web" / "index.html"
        content = html_path.read_text()
        assert 'id="projectList"' in content, "缺少项目列表"

    def test_html_contains_message_container(self):
        """测试HTML包含消息容器"""
        html_path = PROJECT_ROOT / "web" / "index.html"
        content = html_path.read_text()
        assert 'id="messageContainer"' in content, "缺少消息容器"

    def test_html_contains_message_input(self):
        """测试HTML包含输入框"""
        html_path = PROJECT_ROOT / "web" / "index.html"
        content = html_path.read_text()
        assert 'id="messageInput"' in content, "缺少输入框"

    def test_html_contains_new_project_button(self):
        """测试HTML包含新建项目按钮"""
        html_path = PROJECT_ROOT / "web" / "index.html"
        content = html_path.read_text()
        assert 'id="newProjectBtn"' in content, "缺少新建项目按钮"

    def test_html_contains_chat_panel(self):
        """测试HTML包含聊天面板"""
        html_path = PROJECT_ROOT / "web" / "index.html"
        content = html_path.read_text()
        assert 'id="chatPanel"' in content, "缺少聊天面板"

    def test_html_contains_agent_status_bar(self):
        """测试HTML包含Agent状态栏"""
        html_path = PROJECT_ROOT / "web" / "index.html"
        content = html_path.read_text()
        assert 'id="agentStatusBar"' in content, "缺少Agent状态栏"

    def test_html_contains_new_project_modal(self):
        """测试HTML包含新建项目弹窗"""
        html_path = PROJECT_ROOT / "web" / "index.html"
        content = html_path.read_text()
        assert 'id="newProjectModal"' in content, "缺少新建项目弹窗"


# ========== 用例3: CSS样式测试 ==========

class TestCSSStyles:
    """CSS样式测试"""

    def test_css_contains_qq_blue_variable(self):
        """测试CSS包含QQ蓝色变量"""
        css_path = PROJECT_ROOT / "web" / "styles.css"
        content = css_path.read_text()
        assert '--qq-blue:' in content, "缺少QQ蓝色变量"

    def test_css_contains_sidebar_styles(self):
        """测试CSS包含侧边栏样式"""
        css_path = PROJECT_ROOT / "web" / "styles.css"
        content = css_path.read_text()
        assert '#sidebar' in content, "缺少侧边栏样式"

    def test_css_contains_project_item_styles(self):
        """测试CSS包含项目项样式"""
        css_path = PROJECT_ROOT / "web" / "styles.css"
        content = css_path.read_text()
        assert '.project-item' in content, "缺少项目项样式"

    def test_css_contains_message_bubble_styles(self):
        """测试CSS包含消息气泡样式"""
        css_path = PROJECT_ROOT / "web" / "styles.css"
        content = css_path.read_text()
        assert '.message-bubble' in content, "缺少消息气泡样式"

    def test_css_contains_agent_status_card(self):
        """测试CSS包含Agent状态卡片样式"""
        css_path = PROJECT_ROOT / "web" / "styles.css"
        content = css_path.read_text()
        assert '.agent-status-card' in content, "缺少Agent状态卡片样式"

    def test_css_contains_progress_bar(self):
        """测试CSS包含进度条样式"""
        css_path = PROJECT_ROOT / "web" / "styles.css"
        content = css_path.read_text()
        assert '.progress-bar' in content or 'progress' in content.lower(), "缺少进度条样式"

    def test_css_contains_dark_mode_support(self):
        """测试CSS包含深色模式支持"""
        css_path = PROJECT_ROOT / "web" / "styles.css"
        content = css_path.read_text()
        assert 'prefers-color-scheme: dark' in content, "缺少深色模式支持"

    def test_css_contains_message_animation(self):
        """测试CSS包含消息动画"""
        css_path = PROJECT_ROOT / "web" / "styles.css"
        content = css_path.read_text()
        assert '@keyframes messageIn' in content or 'animation' in content.lower(), "缺少消息动画"


# ========== 用例4: JavaScript功能测试 ==========

class TestJavaScriptFunctionality:
    """JavaScript功能测试"""

    def test_js_contains_state_object(self):
        """测试JS包含状态管理对象"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'const state' in content or 'let state' in content, "缺少状态对象"
        assert 'projects' in content, "状态对象缺少projects属性"

    def test_js_contains_projects_array(self):
        """测试JS包含项目数组"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'projects:' in content, "状态缺少projects属性"

    def test_js_contains_agents_array(self):
        """测试JS包含Agent数组"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'agents' in content, "状态缺少agents属性"

    def test_js_contains_messages_array(self):
        """测试JS包含消息数组"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'messages' in content, "状态缺少messages属性"

    def test_js_contains_renderProjectList_function(self):
        """测试JS包含渲染项目列表函数"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'renderProjectList' in content, "缺少renderProjectList函数"

    def test_js_contains_sendMessage_function(self):
        """测试JS包含发送消息函数"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'sendMessage' in content, "缺少sendMessage函数"

    def test_js_contains_createProject_function(self):
        """测试JS包含创建项目函数"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'createProject' in content, "缺少createProject函数"

    def test_js_contains_switchProject_function(self):
        """测试JS包含切换项目函数"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'switchProject' in content, "缺少switchProject函数"

    def test_js_contains_renderMessages_function(self):
        """测试JS包含渲染消息函数"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'renderMessages' in content or 'appendMessage' in content, "缺少消息渲染函数"

    def test_js_contains_interrupt_handling(self):
        """测试JS包含打断处理"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'interrupt' in content.lower(), "缺少打断功能"

    def test_js_contains_sse_connection(self):
        """测试JS包含SSE连接"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'EventSource' in content or 'SSE' in content or 'stream' in content.lower(), "缺少SSE连接"

    def test_js_contains_notification_system(self):
        """测试JS包含通知系统"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'notification' in content.lower(), "缺少通知系统"

    def test_js_contains_agent_status_update(self):
        """测试JS包含Agent状态更新"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert 'renderAgentStatusBar' in content, "缺少Agent状态渲染函数"


# ========== 用例5: 界面UI验证测试 ==========

class TestUIValidation:
    """UI验证测试"""

    def test_html_has_proper_structure(self):
        """测试HTML有正确的文档结构"""
        html_path = PROJECT_ROOT / "web" / "index.html"
        content = html_path.read_text()
        assert '<!DOCTYPE html>' in content, "缺少DOCTYPE声明"
        assert '<html' in content, "缺少html标签"
        assert '</html>' in content, "html标签未闭合"
        assert '<head>' in content, "缺少head标签"
        assert '</head>' in content, "head标签未闭合"
        assert '<body>' in content, "缺少body标签"
        assert '</body>' in content, "body标签未闭合"

    def test_html_loads_css(self):
        """测试HTML加载CSS文件"""
        html_path = PROJECT_ROOT / "web" / "index.html"
        content = html_path.read_text()
        assert 'styles.css' in content, "未加载styles.css"

    def test_html_loads_js(self):
        """测试HTML加载JS文件"""
        html_path = PROJECT_ROOT / "web" / "index.html"
        content = html_path.read_text()
        assert 'app.js' in content, "未加载app.js"

    def test_css_file_not_empty(self):
        """测试CSS文件不为空"""
        css_path = PROJECT_ROOT / "web" / "styles.css"
        content = css_path.read_text()
        assert len(content) > 100, "CSS文件过小，可能未正确写入"

    def test_js_file_not_empty(self):
        """测试JS文件不为空"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        assert len(content) > 1000, "JS文件过小，可能未正确写入"

    def test_css_uses_variables(self):
        """测试CSS使用CSS变量"""
        css_path = PROJECT_ROOT / "web" / "styles.css"
        content = css_path.read_text()
        assert 'var(--' in content, "CSS未使用变量"

    def test_css_has_responsive_design(self):
        """测试CSS包含响应式设计"""
        css_path = PROJECT_ROOT / "web" / "styles.css"
        content = css_path.read_text()
        assert '@media' in content, "CSS缺少响应式设计"


# ========== 用例6: 功能完整性测试 ==========

class TestFeatureCompleteness:
    """功能完整性测试"""

    def test_multi_project_support(self):
        """测试支持多项目"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        # 检查是否有项目列表相关的代码
        assert 'projectList' in content or 'projects' in content, "缺少多项目支持"

    def test_multi_agent_support(self):
        """测试支持多Agent"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        # 检查是否有Agent相关的代码
        assert 'agent' in content.lower(), "缺少多Agent支持"

    def test_progress_tracking(self):
        """测试进度追踪"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        # 检查是否有进度相关的代码
        assert 'progress' in content.lower(), "缺少进度追踪"

    def test_user_interrupt_support(self):
        """测试用户打断支持"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        # 检查是否有打断相关的代码
        assert 'interrupt' in content.lower(), "缺少用户打断支持"

    def test_notification_support(self):
        """测试通知支持"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        # 检查是否有通知相关的代码
        assert 'showNotification' in content, "缺少通知支持"

    def test_test_api_exposed(self):
        """测试测试API已暴露"""
        js_path = PROJECT_ROOT / "web" / "app.js"
        content = js_path.read_text()
        # 检查是否暴露了测试接口
        assert 'window.testAPI' in content or 'testAPI' in content, "未暴露测试API"


# ========== 运行器 ==========

def run_frontend_tests():
    """运行前端文件测试"""
    import subprocess
    result = subprocess.run(
        ['python', '-m', 'pytest', __file__, '-v', '--tb=short'],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0


if __name__ == '__main__':
    success = run_frontend_tests()
    exit(0 if success else 1)