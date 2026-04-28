"""
多Agent协作系统 - GUI入口
使用PyWebView创建跨平台桌面应用
"""
import os
import sys

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class JavaScriptAPI:
    """JavaScript API 类 - 用于与前端通信"""

    def __init__(self):
        self.workflow_engine = None

    def start_workflow(self, task_description: str):
        """启动工作流"""
        import threading
        from ui_bridge import get_ui_emitter, EventTypes
        from workflow_engine import WorkflowEngine
        from config import get_config

        def run_workflow():
            try:
                config = get_config()
                self.workflow_engine = WorkflowEngine(config.anthropic_api_key)
                result = self.workflow_engine.run(task_description)
                return result
            except Exception as e:
                ui = get_ui_emitter()
                ui.emit(EventTypes.ERROR, {
                    "message": f"工作流执行出错: {str(e)}"
                }, agent="system")
                return {"status": "error", "message": str(e)}

        thread = threading.Thread(target=run_workflow, daemon=True)
        thread.start()
        return {"status": "started"}

    def get_status(self):
        """获取当前状态"""
        return {
            "status": "running" if self.workflow_engine else "idle",
            "ready": True
        }


def start_gui():
    """启动GUI应用"""
    try:
        import webview
    except ImportError:
        print("错误: pywebview 未安装")
        print("请运行: pip install pywebview")
        return

    from ui_bridge import get_ui_emitter

    # 设置HTML路径
    web_dir = os.path.join(os.path.dirname(__file__), 'web')
    index_path = os.path.join(web_dir, 'index.html')

    # 使用绝对路径
    import urllib.parse
    file_url = 'file://' + urllib.parse.quote(os.path.abspath(index_path))

    # 创建 JavaScript API 实例
    js_api = JavaScriptAPI()

    # 创建窗口，传递 js_api
    window = webview.create_window(
        "多Agent协作系统",
        file_url,
        width=1100,
        height=800,
        resizable=True,
        min_size=(800, 600),
        js_api=js_api
    )

    # 设置事件发射器窗口引用
    get_ui_emitter().set_window(window)

    print("启动多Agent协作系统 GUI...")
    print(f"界面文件: {index_path}")
    webview.start(debug=True, http_server=False)


def main():
    """主入口"""
    print("=" * 60)
    print("多Agent协作系统 - GUI模式")
    print("=" * 60)

    # 检查依赖
    try:
        import webview
        print("✓ pywebview 已安装")
    except ImportError:
        print("✗ pywebview 未安装")
        print("安装命令: pip install pywebview")
        return

    # 检查web目录
    web_dir = os.path.join(os.path.dirname(__file__), 'web')
    index_path = os.path.join(web_dir, 'index.html')

    if not os.path.exists(index_path):
        print(f"✗ 文件不存在: {index_path}")
        return

    print(f"✓ 界面文件: {index_path}")
    print()
    start_gui()


if __name__ == "__main__":
    main()
