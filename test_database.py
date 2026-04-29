#!/usr/bin/env python3
"""
数据库模块测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_session, get_engine, init_db
from models import Conversation, Task, Message, CodeResult, ReviewRecord, TestRecord

def test_connection():
    """测试数据库连接"""
    print("测试: 数据库连接...")
    try:
        session = get_session()
        engine = get_engine()
        print(f"  ✅ 连接成功: {engine.url}")
        session.close()
        return True
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return False

def test_init_db():
    """测试数据库初始化"""
    print("测试: 数据库初始化...")
    try:
        init_db()
        print("  ✅ 数据库表创建成功")
        return True
    except Exception as e:
        print(f"  ❌ 初始化失败: {e}")
        return False

def test_conversation_crud():
    """测试对话CRUD"""
    print("测试: 对话CRUD...")
    session = get_session()
    try:
        # Create
        conv = Conversation(
            id="test_conv_001",
            user_request="测试任务",
            project_name="test_project",
            status="running"
        )
        session.add(conv)
        session.commit()

        # Read
        result = session.query(Conversation).filter_by(id="test_conv_001").first()
        assert result is not None
        assert result.user_request == "测试任务"
        print("  ✅ Create/Read 成功")

        # Update
        result.status = "completed"
        session.commit()
        result = session.query(Conversation).filter_by(id="test_conv_001").first()
        assert result.status == "completed"
        print("  ✅ Update 成功")

        # Delete
        session.delete(result)
        session.commit()
        result = session.query(Conversation).filter_by(id="test_conv_001").first()
        assert result is None
        print("  ✅ Delete 成功")

        session.close()
        return True
    except Exception as e:
        print(f"  ❌ CRUD失败: {e}")
        session.rollback()
        session.close()
        return False

def test_task_crud():
    """测试任务CRUD"""
    print("测试: 任务CRUD...")
    session = get_session()
    try:
        # 先创建对话
        conv = Conversation(id="test_conv_task", user_request="测试", status="running")
        session.add(conv)
        session.commit()

        # 创建任务
        task = Task(
            id="test_task_001",
            conversation_id="test_conv_task",
            description="子任务1",
            status="pending"
        )
        session.add(task)
        session.commit()

        # 验证
        result = session.query(Task).filter_by(id="test_task_001").first()
        assert result is not None
        assert result.conversation_id == "test_conv_task"
        print("  ✅ 任务创建成功")

        # 清理
        session.delete(task)
        session.delete(conv)
        session.commit()
        session.close()
        return True
    except Exception as e:
        print(f"  ❌ 任务CRUD失败: {e}")
        session.rollback()
        session.close()
        return False

def test_message_crud():
    """测试消息CRUD"""
    print("测试: 消息CRUD...")
    session = get_session()
    try:
        # 先创建对话
        conv = Conversation(id="test_conv_msg", user_request="测试", status="running")
        session.add(conv)
        session.commit()

        # 创建消息
        msg = Message(
            id="test_msg_001",
            conversation_id="test_conv_msg",
            agent="coder",
            agent_name="开发者",
            agent_icon="💻",
            message_type="coding_complete",
            content="代码生成完成",
            extra_data={"code_length": 100}
        )
        session.add(msg)
        session.commit()

        # 验证
        result = session.query(Message).filter_by(id="test_msg_001").first()
        assert result is not None
        assert result.agent == "coder"
        print("  ✅ 消息创建成功")

        # 清理
        session.delete(msg)
        session.delete(conv)
        session.commit()
        session.close()
        return True
    except Exception as e:
        print(f"  ❌ 消息CRUD失败: {e}")
        session.rollback()
        session.close()
        return False

def test_code_result_crud():
    """测试代码结果CRUD"""
    print("测试: 代码结果CRUD...")
    session = get_session()
    try:
        # 创建对话和任务
        conv = Conversation(id="test_conv_code", user_request="测试", status="running")
        session.add(conv)
        session.commit()

        task = Task(id="test_task_code", conversation_id="test_conv_code", description="测试", status="pending")
        session.add(task)
        session.commit()

        # 创建代码结果
        code = CodeResult(
            id="test_code_001",
            task_id="test_task_code",
            code="print('Hello')",
            language="python",
            file_path="/test/hello.py"
        )
        session.add(code)
        session.commit()

        # 验证
        result = session.query(CodeResult).filter_by(id="test_code_001").first()
        assert result is not None
        assert result.language == "python"
        print("  ✅ 代码结果创建成功")

        # 清理
        session.delete(code)
        session.delete(task)
        session.delete(conv)
        session.commit()
        session.close()
        return True
    except Exception as e:
        print(f"  ❌ 代码结果CRUD失败: {e}")
        session.rollback()
        session.close()
        return False

def test_review_test_records():
    """测试审查和测试记录"""
    print("测试: 审查和测试记录...")
    session = get_session()
    try:
        # 创建对话和任务
        conv = Conversation(id="test_conv_review", user_request="测试", status="running")
        session.add(conv)
        session.commit()

        task = Task(id="test_task_review", conversation_id="test_conv_review", description="测试", status="pending")
        session.add(task)
        session.commit()

        # 创建审查记录
        review = ReviewRecord(
            id="test_review_001",
            task_id="test_task_review",
            score=8,
            has_blocker=False,
            issues=[{"severity": "WARNING", "description": "建议优化"}],
            review_content="代码审查通过"
        )
        session.add(review)

        # 创建测试记录
        test_record = TestRecord(
            id="test_test_001",
            task_id="test_task_review",
            status="PASS",
            pass_rate=100,
            tests=[{"name": "test_1", "passed": True}],
            test_content="所有测试通过"
        )
        session.add(test_record)
        session.commit()

        print("  ✅ 审查和测试记录创建成功")

        # 清理
        session.delete(review)
        session.delete(test_record)
        session.delete(task)
        session.delete(conv)
        session.commit()
        session.close()
        return True
    except Exception as e:
        print(f"  ❌ 审查和测试记录CRUD失败: {e}")
        session.rollback()
        session.close()
        return False

def test_to_dict():
    """测试 to_dict 方法"""
    print("测试: to_dict 方法...")
    session = get_session()
    try:
        conv = Conversation(
            id="test_to_dict",
            user_request="测试",
            project_name="test",
            status="running"
        )
        session.add(conv)
        session.commit()

        d = conv.to_dict()
        assert d["id"] == "test_to_dict"
        assert d["user_request"] == "测试"
        print("  ✅ to_dict 方法正常")

        session.delete(conv)
        session.commit()
        session.close()
        return True
    except Exception as e:
        print(f"  ❌ to_dict 测试失败: {e}")
        session.rollback()
        session.close()
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("数据库模块测试")
    print("=" * 60)

    # 首先测试连接
    if not test_connection():
        print("\n" + "=" * 60)
        print("⚠️  PostgreSQL 未运行")
        print("=" * 60)
        print("\n请按以下步骤启动 PostgreSQL:")
        print("\n方法1: Homebrew (macOS)")
        print("  $ brew install postgresql")
        print("  $ brew services start postgresql")
        print("  $ createdb multiagent")
        print("\n方法2: Docker")
        print('  $ docker run --name postgres -e POSTGRES_PASSWORD=postgres \\')
        print("           -e POSTGRES_DB=multiagent -p 5432:5432 -d postgres")
        print("\n方法3: 使用环境变量指定其他数据库")
        print('  $ export DATABASE_URL="postgresql://user:pass@host:5432/db"')
        print("=" * 60)
        return False

    tests = [
        test_init_db,
        test_conversation_crud,
        test_task_crud,
        test_message_crud,
        test_code_result_crud,
        test_review_test_records,
        test_to_dict,
    ]

    results = []
    for test in tests:
        results.append(test())
        print()

    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过")
    print("=" * 60)

    if passed == total:
        print("✅ 所有数据库测试通过!")
    else:
        print("❌ 部分测试失败")

    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)