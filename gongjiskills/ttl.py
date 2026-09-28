"""TTL 惰性对账模块

设计：registry.json 记录 {task_id: {"expire_at": <epoch秒>, "name": <任务名>}}，
不再依赖客户端常驻 sleep 进程（进程会因机器重启/休眠而消失，导致任务永不释放）。

对账时机：
1. 每次 CLI 启动（list / status / deploy 等命令入口）惰性扫描
2. gongji ttl sweep 手动触发

扫描时对已过期条目补发 stop_task；stop 成功（或任务已 End）即从 registry 移除。
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def _ttl_dir() -> Path:
    return Path.home() / ".gongji" / "ttl"


def _registry_path() -> Path:
    return _ttl_dir() / "registry.json"


def _now() -> float:
    return time.time()


def load_registry() -> dict:
    """加载 TTL 注册表；损坏时视为空（自动丢弃脏数据）"""
    path = _registry_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            # 只保留结构合法的条目
            clean = {}
            for tid, entry in data.items():
                if isinstance(entry, dict) and isinstance(entry.get("expire_at"), (int, float)):
                    clean[tid] = entry
            return clean
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_registry(registry: dict):
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def register(task_id: int, ttl_seconds: int, task_name: str = ""):
    """登记一个 TTL 条目（deploy --ttl 时调用）"""
    registry = load_registry()
    registry[str(task_id)] = {
        "expire_at": _now() + ttl_seconds,
        "ttl_seconds": ttl_seconds,
        "name": task_name,
    }
    save_registry(registry)


def unregister(task_id: int):
    """移除条目（手动 stop 任务时调用）"""
    registry = load_registry()
    if str(task_id) in registry:
        del registry[str(task_id)]
        save_registry(registry)


def list_expiring(registry: dict | None = None) -> list[dict]:
    """列出全部登记中的条目（含未到期的），按到期时间升序"""
    reg = registry if registry is not None else load_registry()
    items = []
    for tid, entry in reg.items():
        items.append({
            "task_id": int(tid),
            "expire_at": entry["expire_at"],
            "expires_in": round(entry["expire_at"] - _now(), 1),
            "name": entry.get("name", ""),
            "expired": entry["expire_at"] <= _now(),
        })
    items.sort(key=lambda x: x["expire_at"])
    return items


def _try_stop(client, task_id: int) -> str:
    """尝试停止任务；返回 'stopped' / 'ended' / 'failed'"""
    try:
        # 先查状态：已 End 的直接移除，不再发 stop
        detail = client.task_detail(task_id)
        data = detail.get("data") or {}
        status = data.get("status", "")
        if status in ("End", "Other"):
            return "ended"
        res = client.stop_task(task_id)
        code = str(res.get("code", ""))
        if code in ("200", "0000"):
            return "stopped"
        msg = res.get("message", "")
        # 任务已不存在的错误也视为已结束
        low = msg.lower()
        if ("not found" in low or "不存在" in msg) and ("task" in low or "任务" in msg):
            return "ended"
        return "failed"
    except Exception:
        return "failed"


def sweep(client, quiet: bool = True) -> dict:
    """扫描过期条目并补发 stop。返回统计。

    只处理已过期条目；未到期的保留。网络失败时条目保留，下次再试。
    """
    registry = load_registry()
    now = _now()
    expired = {tid: e for tid, e in registry.items() if e["expire_at"] <= now}
    if not expired:
        return {"checked": len(registry), "expired": 0, "stopped": 0, "ended": 0, "failed": 0}

    stopped, ended, failed = 0, 0, 0
    for tid in list(expired.keys()):
        result = _try_stop(client, int(tid))
        if result == "stopped":
            stopped += 1
            del registry[tid]
        elif result == "ended":
            ended += 1
            del registry[tid]
        else:
            failed += 1
        if not quiet:
            print(f"  TTL 到期 task {tid}: {result}")

    save_registry(registry)
    return {
        "checked": len(registry) + len(expired),
        "expired": len(expired),
        "stopped": stopped,
        "ended": ended,
        "failed": failed,
    }


def lazy_sweep(client):
    """CLI 命令入口的惰性钩子：有登记才扫，且静默吞掉一切异常（不打断主命令）"""
    try:
        registry = load_registry()
        if not registry:
            return None
        now = _now()
        # 有已到期条目才真正发请求
        if any(e["expire_at"] <= now for e in registry.values()):
            return sweep(client, quiet=True)
        return None
    except Exception:
        return None
