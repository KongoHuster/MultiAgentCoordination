"""
共享内存 - 跨 Agent 数据共享
"""

from typing import Any, Optional, Callable
from datetime import datetime
from collections import defaultdict
import threading
import json


class SharedMemory:
    """线程安全的键值存储"""

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._metadata: dict[str, dict] = defaultdict(dict)
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[Callable[[str, Any, Any], None]]] = defaultdict(list)

    def set(self, key: str, value: Any, metadata: Optional[dict] = None):
        """设置值"""
        with self._lock:
            old_value = self._data.get(key)
            self._data[key] = value

            if metadata:
                self._metadata[key].update(metadata)

            # 通知订阅者
            self._notify(key, old_value, value)

    def get(self, key: str, default: Any = None) -> Any:
        """获取值"""
        with self._lock:
            return self._data.get(key, default)

    def delete(self, key: str):
        """删除值"""
        with self._lock:
            if key in self._data:
                del self._data[key]
            if key in self._metadata:
                del self._metadata[key]

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            return key in self._data

    def keys(self, pattern: Optional[str] = None) -> list[str]:
        """获取所有键（可选模式匹配）"""
        with self._lock:
            if pattern is None:
                return list(self._data.keys())

            # 简单的前缀匹配
            return [k for k in self._data.keys() if k.startswith(pattern)]

    def get_metadata(self, key: str) -> dict:
        """获取键的元数据"""
        with self._lock:
            return self._metadata.get(key, {}).copy()

    def update_metadata(self, key: str, metadata: dict):
        """更新键的元数据"""
        with self._lock:
            self._metadata[key].update(metadata)

    def subscribe(self, key_pattern: str, callback: Callable[[str, Any, Any], None]):
        """订阅键变化"""
        with self._lock:
            self._subscribers[key_pattern].append(callback)

    def unsubscribe(self, key_pattern: str, callback: Callable[[str, Any, Any], None]):
        """取消订阅"""
        with self._lock:
            if key_pattern in self._subscribers:
                self._subscribers[key_pattern].remove(callback)

    def _notify(self, key: str, old_value: Any, new_value: Any):
        """通知订阅者"""
        for pattern in self._subscribers:
            if self._matches(key, pattern):
                for callback in self._subscribers[pattern]:
                    try:
                        callback(key, old_value, new_value)
                    except Exception:
                        pass

    def _matches(self, key: str, pattern: str) -> bool:
        """检查键是否匹配模式"""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return key.startswith(pattern[:-1])
        return key == pattern

    def clear(self):
        """清空所有数据"""
        with self._lock:
            self._data.clear()
            self._metadata.clear()

    def get_all(self) -> dict[str, Any]:
        """获取所有数据"""
        with self._lock:
            return self._data.copy()

    def size(self) -> int:
        """获取数据条数"""
        with self._lock:
            return len(self._data)

    # 便捷方法
    def set_json(self, key: str, value: Any):
        """设置 JSON 可序列化的值"""
        self.set(key, json.dumps(value))

    def get_json(self, key: str, default: Any = None) -> Any:
        """获取 JSON 值"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default

    def increment(self, key: str, delta: int = 1) -> int:
        """原子递增"""
        with self._lock:
            current = self._data.get(key, 0)
            new_value = current + delta
            self._data[key] = new_value
            return new_value

    def append(self, key: str, value: Any):
        """追加到列表"""
        with self._lock:
            if key not in self._data:
                self._data[key] = []
            if not isinstance(self._data[key], list):
                self._data[key] = [self._data[key]]
            self._data[key].append(value)


# 全局共享内存
_shared_memory: Optional[SharedMemory] = None


def get_shared_memory() -> SharedMemory:
    """获取全局共享内存"""
    global _shared_memory
    if _shared_memory is None:
        _shared_memory = SharedMemory()
    return _shared_memory


def reset_shared_memory():
    """重置共享内存（用于测试）"""
    global _shared_memory
    _shared_memory = SharedMemory()