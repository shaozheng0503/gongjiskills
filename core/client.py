"""共绩算力 API 客户端"""

from __future__ import annotations

import json
from urllib.parse import urlencode

import requests

from .auth import load_config, load_private_key, build_headers


class GongjiClient:
    """共绩算力 Open API 客户端（RSA签名模式）"""

    def __init__(self):
        self.config = load_config()
        self.private_key = load_private_key(self.config)
        self.base_url = self.config["base_url"].rstrip("/")

    def _get(self, path: str, params: dict = None) -> dict:
        """发送GET请求，path中包含query string参与签名"""
        full_path = path
        if params:
            full_path = f"{path}?{urlencode(params)}"
        headers = build_headers(full_path, self.config, self.private_key, body="{}")
        url = f"{self.base_url}{full_path}"
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        """发送POST请求，body的JSON字符串参与签名"""
        body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        headers = build_headers(path, self.config, self.private_key, body=body_str)
        url = f"{self.base_url}{path}"
        resp = requests.post(url, headers=headers, data=body_str, timeout=30)
        resp.raise_for_status()
        return resp.json()

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
