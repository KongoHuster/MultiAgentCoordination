"""
API 路由 - Git 操作
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from git.manager import create_git_manager
from core.workflow_engine import get_workflow


router = APIRouter(prefix="/conversations/{conversation_id}/git", tags=["git"])


@router.get("/status")
async def get_git_status(conversation_id: str):
    """获取 Git 状态"""
    git_manager = create_git_manager(conversation_id)

    try:
        status = git_manager.status()
        return {
            "branch": status.branch,
            "is_clean": status.is_clean,
            "staged": status.staged,
            "modified": status.modified,
            "untracked": status.untracked
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/log")
async def get_git_log(conversation_id: str, limit: int = 50):
    """获取提交历史"""
    git_manager = create_git_manager(conversation_id)

    try:
        commits = git_manager.get_log(limit)
        return [
            {
                "hash": c.hash,
                "short_hash": c.short_hash,
                "message": c.message,
                "author": c.author,
                "date": c.date.isoformat(),
                "files": c.files
            }
            for c in commits
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CommitRequest(BaseModel):
    message: str


@router.post("/commit")
async def git_commit(conversation_id: str, request: CommitRequest):
    """手动提交"""
    git_manager = create_git_manager(conversation_id)

    try:
        commit_hash = git_manager.commit(request.message)
        return {
            "status": "success",
            "commit_hash": commit_hash
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def list_files(conversation_id: str, ref: Optional[str] = None):
    """列出项目文件"""
    git_manager = create_git_manager(conversation_id)

    try:
        files = git_manager.list_files(ref)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_path:path}")
async def get_file_content(conversation_id: str, file_path: str, ref: Optional[str] = None):
    """获取文件内容"""
    git_manager = create_git_manager(conversation_id)

    try:
        content = git_manager.get_file_content(file_path, ref)
        return {"file_path": file_path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/diff")
async def get_diff(conversation_id: str, ref: Optional[str] = None):
    """获取变更"""
    git_manager = create_git_manager(conversation_id)

    try:
        diff = git_manager.get_diff(ref)
        return {"diff": diff}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))