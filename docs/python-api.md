# Python API

把 `gongjiskills` 当库用，嵌入自研 Agent 或 Python 脚本。

## 安装

```bash
pip install git+https://github.com/shaozheng0503/gongjiskills.git
```

依赖 Python ≥ 3.9。

## 基础用法

```python
from gongjiskills import GongjiClient

client = GongjiClient()  # 自动读取 ~/.gongji/config.json
```

可选参数：

```python
client = GongjiClient(max_retries=2, retry_backoff=1.0)
```

## 查资源

```python
res = client.search_resources()
# 返回 {"code": "0000", "data": {"results": [...]}}

for device in res["data"]["results"]:
    for region in device.get("regions", []):
        if region["inventory"] > 0:
            price_per_hour = region["discount_price"] * 3600 / 1e6
            print(f"{device['gpu_name']} x{device['gpu_count']} "
                  f"| {region['region_name']} "
                  f"| 库存 {region['inventory']} "
                  f"| {price_per_hour:.2f} 元/h")
            break
```

**价格单位**：API 返回的 `price` / `discount_price` 单位是**微元/秒**（10⁻⁶ yuan/s），转元/小时 `raw * 3600 / 1e6`。

## 用模板创建任务（完整业务流）

```python
from gongjiskills import GongjiClient
from gongjiskills.templates import BUILTIN_TEMPLATES
import time

client = GongjiClient()

# 1. 选模板
tmpl = BUILTIN_TEMPLATES["qwen3.5-9b"]

# 2. 挑资源（按价格找有库存的）
res = client.search_resources()
mark = None
for device in res["data"]["results"]:
    if tmpl.get("gpu") and tmpl["gpu"] not in device["gpu_name"]:
        continue
    for region in device.get("regions", []):
        if region["inventory"] > 0:
            mark = region["mark"]["mark"]
            mark_resource = region["mark"]["resource"]
            break
    if mark:
        break

if not mark:
    raise RuntimeError("无可用资源")

# 3. 建任务
ports = [int(p) for p in tmpl["port"].split(",")]
task = client.create_task(
    task_name="my-llm",
    mark=mark,
    service_image=tmpl["image"],
    ports=ports,
    gpu_name=mark_resource.get("gpu_name"),
    gpu_count=mark_resource.get("gpu_count"),
    region=mark_resource.get("region"),
    device_name=mark_resource.get("device_name"),
    env=tmpl.get("env"),
    command=tmpl.get("start_cmd"),
    args=tmpl.get("start_args"),
)
task_id = task["data"]["task_id"]

# 4. 等就绪
while True:
    detail = client.task_detail(task_id)
    status = detail["data"]["status"]
    if status == "Running":
        break
    if status in ("End", "Other"):
        raise RuntimeError(f"任务失败: {status}")
    time.sleep(5)

# 5. 拿 URL
url = detail["data"]["services"][0]["remote_ports"][0]["url"]
print(f"Endpoint: {url}")

# 6. 调用（以 OpenAI 协议为例）
import openai
ai = openai.OpenAI(base_url=f"{url}/v1", api_key="none")
resp = ai.chat.completions.create(
    model="Qwen/Qwen3.5-9B",
    messages=[{"role": "user", "content": "hello"}],
)
print(resp.choices[0].message.content)

# 7. 释放
client.stop_task(task_id)
```

## 异常处理

```python
from gongjiskills.client import GongjiError

try:
    res = client.create_task(...)
except GongjiError as e:
    # 网络错误 / API 错误已被友好化中文化
    print(f"部署失败: {e}")
```

`GongjiError` 包含的场景：

- `API 请求超时（已重试），请稍后再试`
- `无法连接到 API 服务器，请检查网络`
- `API 返回错误: {翻译过的错误信息}`

## 查日志 / 事件

```python
# 节点列表
points = client.list_points(task_id)["data"]["results"]
point_id = points[0]["point_id"]

# 事件（排查启动失败）
events = client.pod_event(point_id)["data"]["events"]
for ev in events:
    print(f"[{ev['type']}] {ev['reason']}: {ev['message']}")

# 容器日志
service_id = detail["data"]["services"][0]["service_id"]
logs = client.point_log(task_id, point_id, service_id)["data"]["logs"]
print(logs)
```

## 持久化存储

CLI 没暴露，需走 Python API：

```python
client.create_task(
    ...,
    storage_config=[{"mount_path": "/data", "size_gb": 50}],
    share_storage_config=[{"mount_path": "/shared", "storage_id": "xxx"}],
)
```

## 私有镜像

```python
client.create_task(
    ...,
    service_image="harbor.my-org.com/private/img:v1",
    repository_username="user",
    repository_password="pass",
)
```

## 完整 API 列表

| 方法 | 说明 |
|------|------|
| `search_resources(task_type, device_type)` | 查所有可用 GPU 资源 |
| `create_task(task_name, mark, service_image, ports, ...)` | 创建任务 |
| `task_detail(task_id)` | 任务详情 |
| `search_tasks(status, page, page_size)` | 任务列表 |
| `pause_task(task_id)` | 暂停任务 |
| `recover_task(task_id)` | 恢复暂停的任务 |
| `stop_task(task_id)` | 删除任务 |
| `update_task(body)` | 更新任务配置 |
| `list_points(task_id, status, page, page_size)` | 节点列表 |
| `point_log(task_id, point_id, service_id)` | 节点日志 |
| `pod_event(point_id)` | 节点事件 |

详见源码 `gongjiskills/client.py`。

## 把 CLI 包成 Python helper

如果只想调用 CLI 而非直接走 SDK，可以这么写：

```python
import json
import subprocess

def gongji(*args):
    """调用 gongji CLI，返回解析后的 JSON 或抛异常"""
    result = subprocess.run(
        ["gongji", *args, "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    if "error" in data:
        raise RuntimeError(data["error"])
    return data

# 发现
categories = gongji("images", "categories")
llm_templates = gongji("images", "--category", "llm")

# 部署
result = gongji("deploy", "--template", "qwen3.5-9b",
                "-n", "agent-task", "--ttl", "3600")
url = result["urls"][0]["url"]

# 用完释放
gongji("stop", str(result["task_id"]), "-f")
```
