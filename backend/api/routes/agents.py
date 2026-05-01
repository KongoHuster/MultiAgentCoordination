"""
API 路由 - Agent 控制
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio

from core.workflow_engine import create_workflow, get_workflow, WorkflowConfig, WorkflowState
from db import get_db, Conversation
from websocket.manager import get_ws_manager


router = APIRouter(prefix="/conversations/{conversation_id}", tags=["agent"])


class StartRequest(BaseModel):
    task: str
    agent_configs: Optional[dict] = None


@router.post("/start")
async def start_workflow(conversation_id: str, request: StartRequest):
    """启动任务执行"""
    with get_db() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if conversation.status == "running":
            raise HTTPException(status_code=400, detail="Workflow already running")

        # 更新状态
        conversation.status = "running"
        db.commit()

    # 创建工作流
    config = WorkflowConfig()
    workflow = create_workflow(conversation_id, config)

    # 如果有 agent 配置，设置配置
    if request.agent_configs:
        for agent_type, llm_config in request.agent_configs.items():
            if llm_config:
                from llm.base import LLMConfig, LLMBackend
                config_dict = llm_config if isinstance(llm_config, dict) else {}
                backend = LLMBackend(config_dict.get("backend", "ollama"))
                workflow.set_agent_config(
                    agent_type,
                    LLMConfig(
                        backend=backend,
                        model=config_dict.get("model", "gemma2:9b"),
                        api_key=config_dict.get("api_key"),
                        base_url=config_dict.get("base_url")
                    )
                )

    # 后台运行工作流
    asyncio.create_task(_run_workflow(workflow, request.task, conversation_id))

    return {"status": "started", "conversation_id": conversation_id}


async def _run_workflow(workflow, task: str, conversation_id: str):
    """后台运行工作流"""
    try:
        await workflow.run(task)
    except Exception as e:
        with get_db() as db:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if conversation:
                conversation.status = "failed"
                db.commit()

        ws_manager = get_ws_manager()
        await ws_manager.emit_workflow_complete(conversation_id, {
            "status": "error",
            "error": str(e)
        })


@router.post("/pause")
async def pause_workflow(conversation_id: str):
    """暂停执行"""
    workflow = get_workflow(conversation_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow.pause()

    with get_db() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if conversation:
            conversation.status = "paused"
            db.commit()

    ws_manager = get_ws_manager()
    await ws_manager.broadcast(
        type="pause",
        conversation_id=conversation_id,
        data={"status": "paused"}
    )

    return {"status": "paused"}


@router.post("/resume")
async def resume_workflow(conversation_id: str):
    """恢复执行"""
    workflow = get_workflow(conversation_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow.resume()

    with get_db() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if conversation:
            conversation.status = "running"
            db.commit()

    ws_manager = get_ws_manager()
    await ws_manager.broadcast(
        type="resume",
        conversation_id=conversation_id,
        data={"status": "running"}
    )

    return {"status": "running"}


@router.post("/stop")
async def stop_workflow(conversation_id: str):
    """停止执行"""
    workflow = get_workflow(conversation_id)

    if workflow:
        workflow.stop()

    with get_db() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if conversation:
            conversation.status = "idle"
            db.commit()

    ws_manager = get_ws_manager()
    await ws_manager.broadcast(
        type="stop",
        conversation_id=conversation_id,
        data={"status": "stopped"}
    )

    return {"status": "stopped"}


@router.get("/status")
async def get_workflow_status(conversation_id: str):
    """获取工作流状态"""
    workflow = get_workflow(conversation_id)

    with get_db() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        status = {
            "conversation_id": conversation_id,
            "status": conversation.status,
            "user_messages": []
        }

    if workflow:
        status["user_messages"] = workflow.get_user_messages()
        status["state"] = workflow.get_state()

    return status