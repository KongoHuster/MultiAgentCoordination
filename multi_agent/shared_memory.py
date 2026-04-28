"""
Shared Memory - 跨 Agent 共享数据存储
"""
import json
from datetime import datetime
from typing import Any, Optional
from threading import Lock


class SharedMemory:
    """线程安全的共享内存"""

    def __init__(self):
        self._storage: dict[str, dict] = {}
        self._lock = Lock()

    def write(self, key: str, value: Any, tags: list[str] = None) -> None:
        """写入数据"""
        with self._lock:
            self._storage[key] = {
                "data": value,
                "timestamp": datetime.utcnow().isoformat(),
                "version": self._get_version(key) + 1,
                "tags": tags or []
            }

    def read(self, key: str) -> Optional[Any]:
        """读取数据"""
        with self._lock:
            entry = self._storage.get(key)
            return entry["data"] if entry else None

    def get_entry(self, key: str) -> Optional[dict]:
        """获取完整条目（含元数据）"""
        with self._lock:
            return self._storage.get(key)

    def read_by_tag(self, tag: str) -> dict[str, Any]:
        """按标签批量读取"""
        with self._lock:
            return {
                k: v["data"]
                for k, v in self._storage.items()
                if tag in v.get("tags", [])
            }

    def read_all_by_prefix(self, prefix: str) -> dict[str, Any]:
        """按前缀批量读取"""
        with self._lock:
            return {
                k: v["data"]
                for k, v in self._storage.items()
                if k.startswith(prefix)
            }

    def delete(self, key: str) -> bool:
        """删除数据"""
        with self._lock:
            if key in self._storage:
                del self._storage[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            return key in self._storage

    def _get_version(self, key: str) -> int:
        """获取版本号"""
        entry = self._storage.get(key)
        return entry["version"] if entry else 0

    def get_history(self, key: str) -> list[dict]:
        """获取键的历史记录（保留最后10个版本）"""
        with self._lock:
            # 简化实现：只返回当前值
            entry = self._storage.get(key)
            if entry:
                return [entry]
            return []

    def clear(self) -> None:
        """清空所有数据"""
        with self._lock:
            self._storage.clear()

    def keys(self) -> list[str]:
        """获取所有键"""
        with self._lock:
            return list(self._storage.keys())

    def to_dict(self) -> dict:
        """导出为字典"""
        with self._lock:
            return dict(self._storage)


# 全局共享内存实例
memory = SharedMemory()
