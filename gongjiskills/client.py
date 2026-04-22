"""共绩算力 API 客户端"""

from __future__ import annotations

import json
import time
from urllib.parse import urlencode

import requests

from .auth import load_config, load_private_key, build_headers


class GongjiError(Exception):
    """共绩算力 API 错误"""


# 瞬时错误自动重试的状态码
_RETRY_STATUS = {500, 502, 503, 504}


def _friendly_error(msg: str) -> str:
    """把常见 API 错误映射为带修复建议的中文提示"""
    m = (msg or "").lower()
    if "token" in m and ("expired" in m or "invalid" in m):
        return f"{msg}\n  → Token 已失效，请登录 https://www.gongjiyun.com 重新生成，再运行: gongji init --force"
    if "signature" in m or "sign" in m:
        return f"{msg}\n  → 签名验证失败：公钥可能未上传到控制台，检查 ~/.gongji/public.pem 是否与平台一致"
    if "not found" in m or "不存在" in m:
        return f"{msg}\n  → 资源不存在，用 gongji list 确认 task_id 是否正确"
    if "insufficient" in m or "余额" in m or "欠费" in m:
        return f"{msg}\n  → 账户余额不足，请前往控制台充值后重试"
    if "inventory" in m or "库存" in m or "sold out" in m:
        return f"{msg}\n  → 库存不足，换个区域或 GPU 型号重试（gongji resources 查看库存）"
    return msg


class GongjiClient:
    """共绩算力 Open API 客户端（RSA签名模式）"""

    def __init__(self, max_retries: int = 2, retry_backoff: float = 1.0):
        self.config = load_config()
        self.private_key = load_private_key(self.config)
        self.base_url = self.config["base_url"].rstrip("/")
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def _send(self, method: str, url: str, headers: dict, body_str: str):
        if method == "GET":
            return requests.get(url, headers=headers, timeout=30)
        return requests.post(url, headers=headers, data=body_str, timeout=30)

    def _request(self, method: str, path: str, params: dict = None, body: dict = None) -> dict:
        sign_path = path
        if params:
            sign_path = f"{path}?{urlencode(params)}"
        body_str = "{}"
        if body is not None:
            body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)

        url = f"{self.base_url}{sign_path}"

        last_exc = None
        for attempt in range(self.max_retries + 1):
            # 每次重试都重新签名（timestamp 需要刷新）
            headers = build_headers(sign_path, self.config, self.private_key, body=body_str)
            try:
                resp = self._send(method, url, headers, body_str)
                if resp.status_code in _RETRY_STATUS and attempt < self.max_retries:
                    time.sleep(self.retry_backoff * (2 ** attempt))
                    continue
                resp.raise_for_status()
                return resp.json()
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_exc = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * (2 ** attempt))
                    continue
                if isinstance(e, requests.exceptions.Timeout):
                    raise GongjiError("API 请求超时（已重试），请稍后再试")
                raise GongjiError(f"无法连接到 API 服务器 ({self.base_url})，请检查网络")
            except requests.exceptions.HTTPError as e:
                try:
                    err_data = e.response.json()
                    msg = err_data.get("message") or err_data.get("error") or str(err_data)
                except Exception:
                    msg = f"HTTP {e.response.status_code}"
                raise GongjiError(f"API 返回错误: {_friendly_error(msg)}")
        # 不应到达
        raise GongjiError(str(last_exc) if last_exc else "未知错误")

    def _get(self, path: str, params: dict = None) -> dict:
        return self._request("GET", path, params=params)

    def _post(self, path: str, body: dict) -> dict:
        return self._request("POST", path, body=body)

    # ── 资源 ──

    def search_resources(self, task_type="Deployment", device_type="GpuDevice") -> dict:
        """查询可用GPU资源列表"""
        return self._get("/api/deployment/resource/search", {
            "task_type": task_type,
            "device_type": device_type,
        })

    # ── 任务生命周期 ──

    def create_task(self, task_name: str, mark: str, service_image: str,
                    ports: list[int], gpu_name: str = None, gpu_count: int = None,
                    gpu_memory: int = None, memory: int = None, cpu_cores: int = None,
                    region: str = None, device_name: str = None,
                    points: int = 1, env: str = None,
                    storage_config: list = None,
                    share_storage_config: list = None,
                    command: str = None, args: list[str] = None,
                    repository_username: str = None,
                    repository_password: str = None) -> dict:
        """创建弹性部署任务"""
        resource_obj = {"mark": mark}
        resource_detail = {}
        if device_name:
            resource_detail["device_name"] = device_name
        if region:
            resource_detail["region"] = region
        if gpu_name:
            resource_detail["gpu_name"] = gpu_name
        if gpu_count is not None:
            resource_detail["gpu_count"] = gpu_count
        if gpu_memory is not None:
            resource_detail["gpu_memory"] = gpu_memory
        if memory is not None:
            resource_detail["memory"] = memory
        if cpu_cores is not None:
            resource_detail["cpu_cores"] = cpu_cores
        if resource_detail:
            resource_obj["resource"] = resource_detail

        service = {
            "service_name": task_name,
            "service_image": service_image,
            "remote_ports": [{"service_port": p} for p in ports],
        }
        if env:
            service["env"] = env
        if storage_config:
            service["storage_config"] = storage_config
        if share_storage_config:
            service["share_storage_config"] = share_storage_config
        if command is not None or args is not None:
            service["start_script_v2"] = {
                "command": command,
                "args": args or [],
            }

        body = {
            "task_type": "Deployment",
            "task_name": task_name,
            "points": points,
            "resources": [resource_obj],
            "services": [service],
        }
        if repository_username:
            body["repository_username"] = repository_username
        if repository_password:
            body["repository_password"] = repository_password

        return self._post("/api/deployment/task/create", body)

    def search_tasks(self, status="Running,Pending,Paused", page=1, page_size=20) -> dict:
        """查询任务列表"""
        return self._get("/api/deployment/task/search", {
            "type": "Deployment",
            "status": status,
            "page": page,
            "page_size": page_size,
        })

    def task_detail(self, task_id: int) -> dict:
        """获取任务详情"""
        return self._get("/api/deployment/task/detail", {"task_id": task_id})

    def pause_task(self, task_id: int) -> dict:
        """暂停任务（资源释放，可恢复）"""
        return self._post("/api/deployment/task/pause", {"task_id": task_id})

    def recover_task(self, task_id: int) -> dict:
        """恢复暂停的任务"""
        return self._post("/api/deployment/task/recover", {"task_id": task_id})

    def stop_task(self, task_id: int) -> dict:
        """删除任务（不可恢复）"""
        return self._post("/api/deployment/task/stop", {"task_id": task_id})

    def update_task(self, body: dict) -> dict:
        """更新任务（整体覆盖）"""
        return self._post("/api/deployment/task/update", body)

    # ── 节点 ──

    def list_points(self, task_id: int, status=None, page=1, page_size=20) -> dict:
        """查询任务节点列表"""
        params = {"task_id": task_id, "page": page, "page_size": page_size}
        if status:
            params["status"] = status
        return self._get("/api/deployment/task/points", params)

    def point_log(self, task_id: int, point_id: int, service_id: int) -> dict:
        """查询节点日志"""
        return self._get("/api/deployment/task/point_log", {
            "task_id": task_id,
            "point_id": point_id,
            "service_id": service_id,
        })

    def pod_event(self, point_id: int) -> dict:
        """查询节点事件"""
        return self._get("/api/deployment/task/pod_event", {"point_id": point_id})
