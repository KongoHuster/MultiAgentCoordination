"""
FastAPI 主入口
"""

import sys
import os

# 添加 backend 目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket
import asyncio
import json

from config import get_config
from db import init_db
from api import create_api_router
from websocket.manager import get_ws_manager, WSConnection, EventType, WSEvent
from core.workflow_engine import get_workflow


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    config = get_config()

    app = FastAPI(
        title="Agency Visual API",
        description="可视化多智能体协作平台 API",
        version="1.0.0"
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    api_router = create_api_router()
    app.include_router(api_router)

    # WebSocket 路由
    ws_manager = get_ws_manager()

    @app.websocket("/ws/{conversation_id}")
    async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
        """WebSocket 端点"""
        await websocket.accept()

        connection = WSConnection(
            websocket=websocket,
            conversation_id=conversation_id,
            user_id=websocket.query_params.get("user_id")
        )

        ws_manager.add_connection(connection)

        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()

                try:
                    msg = json.loads(data)

                    # 处理命令
                    if msg.get("type") == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": msg.get("timestamp")
                        }))
                    elif msg.get("type") == "user_message":
                        # 用户消息
                        await ws_manager.emit_user_message(
                            conversation_id,
                            msg.get("user_id", "unknown"),
                            msg.get("content", "")
                        )
                    elif msg.get("type") == "pause":
                        # 暂停
                        workflow = get_workflow(conversation_id)
                        if workflow:
                            workflow.pause()
                        await ws_manager.broadcast(
                            WSEvent(
                                type=EventType.PAUSE.value,
                                conversation_id=conversation_id,
                                data={"status": "paused"}
                            )
                        )
                    elif msg.get("type") == "resume":
                        # 恢复
                        workflow = get_workflow(conversation_id)
                        if workflow:
                            workflow.resume()
                        await ws_manager.broadcast(
                            WSEvent(
                                type=EventType.RESUME.value,
                                conversation_id=conversation_id,
                                data={"status": "running"}
                            )
                        )
                    elif msg.get("type") == "stop":
                        # 停止
                        workflow = get_workflow(conversation_id)
                        if workflow:
                            workflow.stop()
                        await ws_manager.broadcast(
                            WSEvent(
                                type=EventType.STOP.value,
                                conversation_id=conversation_id,
                                data={"status": "stopped"}
                            )
                        )

                except json.JSONDecodeError:
                    pass

        except Exception:
            pass
        finally:
            ws_manager.remove_connection(websocket, conversation_id)

    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_config()

    # 初始化数据库
    init_db()

    uvicorn.run(
        app,
        host=config.app.host,
        port=config.app.port,
        reload=config.app.debug
    )
