#!/usr/bin/env python3
"""
API测试
"""
import requests
import time
import sys

BASE_URL = "http://localhost:8080"

def wait_for_server(max_wait=30):
    """等待服务启动"""
    for i in range(max_wait):
        try:
            resp = requests.get(f"{BASE_URL}/api/status")
            if resp.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def test_server_running():
    """测试服务是否运行"""
    print("测试: 服务运行状态...")
    try:
        resp = requests.get(f"{BASE_URL}/api/status")
        assert resp.status_code == 200
        data = resp.json()
        print(f"  ✅ 服务运行中: {data}")
        return True
    except Exception as e:
        print(f"  ❌ 服务未运行: {e}")
        return False

def test_conversations_list():
    """测试对话列表API"""
    print("测试: 对话列表API...")
    try:
        resp = requests.get(f"{BASE_URL}/api/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"  ✅ 对话列表: {len(data)} 条记录")
        return True
    except Exception as e:
        print(f"  ❌ 对话列表API失败: {e}")
        return False

def test_conversation_detail():
    """测试对话详情API"""
    print("测试: 对话详情API...")
    try:
        # 获取对话列表
        resp = requests.get(f"{BASE_URL}/api/conversations")
        conversations = resp.json()

        if not conversations:
            print("  ⚠️ 暂无对话记录，跳过")
            return True

        # 获取第一个对话详情
        conv_id = conversations[0]["id"]
        resp = requests.get(f"{BASE_URL}/api/conversations/{conv_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "conversation" in data
        print(f"  ✅ 对话详情: {conv_id}")
        return True
    except Exception as e:
        print(f"  ❌ 对话详情API失败: {e}")
        return False

def test_conversation_tasks():
    """测试对话任务API"""
    print("测试: 对话任务API...")
    try:
        # 获取对话列表
        resp = requests.get(f"{BASE_URL}/api/conversations")
        conversations = resp.json()

        if not conversations:
            print("  ⚠️ 暂无对话记录，跳过")
            return True

        # 获取第一个对话的任务
        conv_id = conversations[0]["id"]
        resp = requests.get(f"{BASE_URL}/api/conversations/{conv_id}/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"  ✅ 任务列表: {len(data)} 条")
        return True
    except Exception as e:
        print(f"  ❌ 任务列表API失败: {e}")
        return False

def test_clear_messages():
    """测试清空消息"""
    print("测试: 清空消息...")
    try:
        resp = requests.post(f"{BASE_URL}/api/clear")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "ok"
        print("  ✅ 清空消息成功")
        return True
    except Exception as e:
        print(f"  ❌ 清空消息失败: {e}")
        return False

def test_start_workflow():
    """测试启动工作流"""
    print("测试: 启动工作流...")
    try:
        resp = requests.post(
            f"{BASE_URL}/api/start",
            json={"task": "测试任务: 简单的打印Hello"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "started"
        print(f"  ✅ 工作流已启动")

        # 等待执行
        time.sleep(5)

        # 获取消息
        resp = requests.get(f"{BASE_URL}/api/messages")
        data = resp.json()
        print(f"  ✅ 消息数: {len(data.get('messages', []))}")
        return True
    except Exception as e:
        print(f"  ❌ 启动工作流失败: {e}")
        return False

def test_pause_resume():
    """测试暂停恢复"""
    print("测试: 暂停恢复...")
    try:
        # 先检查状态
        resp = requests.get(f"{BASE_URL}/api/status")
        data = resp.json()

        if data.get("is_running"):
            # 尝试暂停
            resp = requests.post(f"{BASE_URL}/api/pause")
            if resp.status_code == 200:
                print("  ✅ 暂停请求成功")

            # 尝试恢复
            resp = requests.post(f"{BASE_URL}/api/resume")
            if resp.status_code == 200:
                print("  ✅ 恢复请求成功")
        else:
            print("  ⚠️ 当前无运行中任务，跳过")

        return True
    except Exception as e:
        print(f"  ❌ 暂停恢复失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("API测试")
    print("=" * 60)

    # 等待服务
    if not wait_for_server():
        print("❌ 服务未启动，请先运行: python3 web_server.py")
        return False

    tests = [
        test_server_running,
        test_conversations_list,
        test_conversation_detail,
        test_conversation_tasks,
        test_clear_messages,
        test_pause_resume,
    ]

    results = []
    for test in tests:
        results.append(test())
        print()

    print("=" * 60)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 60)

    return all(results)

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)