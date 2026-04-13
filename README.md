# 共绩算力 Skills

让 AI Agent 自动调用 [共绩算力](https://www.gongjiyun.com) GPU 资源 — 一句话部署推理服务、拿到 API 地址、用完释放。

> **相关文档：** [共绩算力官网](https://www.gongjiyun.com) | [Open API 使用文档](https://www.gongjiyun.com/docs/platform/openapi/zx3iwhbv1i8sxdkeiapcprxhn8d/) | [API 接口详情 (Apifox)](https://s.apifox.cn/6aa360d3-d8f2-471e-b841-3a35c33a7b7c)

---

## 它解决什么问题

Agent 开发中经常需要 GPU 算力（跑模型推理、图片生成等），但目前只能手动去[控制台](https://www.gongjiyun.com)操作，或者自己对着 [API 文档](https://www.gongjiyun.com/docs/platform/openapi/zx3iwhbv1i8sxdkeiapcprxhn8d/)写对接代码。

**这个 Skill 让 Agent 自动完成整个流程：**

```
Agent: "我需要一个 4090 跑 vLLM 推理"
  ↓ 自动查找有库存的 4090 → 创建部署 → 等待就绪
  ↓ 返回: https://xxx.suanli.cn:8080
Agent: 拿到地址，直接调用推理 API
  ↓ 任务完成
Agent: "用完了，释放"
  ↓ 资源释放，停止计费
```

---

## 快速开始

### 第一步：注册 & 充值

前往 [共绩算力官网](https://www.gongjiyun.com) 注册账号，**提前充值余额**（部署按秒计费，[查看定价](https://www.gongjiyun.com/pricing/)）。

### 第二步：安装

```bash
pip install git+https://github.com/shaozheng0503/gongjiskills.git
```

安装后全局可用 `gongji` 命令。也可以 clone 后本地安装：

```bash
git clone https://github.com/shaozheng0503/gongjiskills.git
cd gongjiskills
pip install .
```

### 第三步：初始化配置

```bash
python3 gongji.py init
```

`init` 会自动完成：
1. 生成 RSA 密钥对
2. 显示公钥内容 → 你粘贴到[控制台](https://www.gongjiyun.com)（头像 → API密钥 → RSA模式）
3. 输入获取到的 API Token
4. 验证连通性

> 也可以手动配置，见 [Open API 使用文档](https://www.gongjiyun.com/docs/platform/openapi/zx3iwhbv1i8sxdkeiapcprxhn8d/) 和 [RSA 模式使用指南](https://www.gongjiyun.com/docs/platform/openapi/m3p6whioxidzwaksughc4gfhnro/)。

### 第四步：验证

```bash
python3 gongji.py resources    # 查看可用GPU和价格
```

---

## CLI 用法

### `resources` — 查看可用 GPU

部署前先看看有什么资源、什么价格：

```bash
python3 gongji.py resources
```

**输出：**

```
RTX 4090 x1  (显存 24G | 8核 | 32G 内存)
  区域           库存   原价       折扣价
  ------------------------------------------
  华东A          12     1.98       1.68
  华北B          3      1.98       1.68

H800 x8  (显存 640G | 128核 | 1024G 内存)
  区域           库存   原价       折扣价
  ------------------------------------------
  华东A          1      88.00      78.00

共 5 种规格
```

### `deploy` — 部署任务

自动查找有库存的 GPU → 创建弹性部署 → 等待就绪 → 返回访问地址。

```bash
python3 gongji.py deploy <镜像地址> -n <任务名> -g <GPU型号> -p <端口>
```

**示例：**

```bash
# 部署一个 vLLM 推理服务到 4090
python3 gongji.py deploy my-registry/vllm-server:latest -n my-llm -g 4090 -p 8080
```

**输出：**

```
正在查询可用 GPU 资源...
选中资源: RTX 4090 x1 | 区域A | 1.68/h (最低价)
正在创建任务 [my-llm]...
任务已创建, task_id=388
等待任务启动........ Running!
访问地址: https://xxx.suanli.cn:8080 (端口 8080)
```

拿到地址后直接调用：

```bash
curl https://xxx.suanli.cn:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "my-model", "messages": [{"role": "user", "content": "hello"}]}'
```

**全部参数：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `<image>` | Docker 镜像地址（必填） | - |
| `-n, --name` | 任务名称（必填） | - |
| `-g, --gpu` | GPU 型号关键词，如 `4090` / `H800` | 自动选择 |
| `-p, --port` | 暴露端口，多个用逗号分隔 | `8080` |
| `--points` | 节点数量 | `1` |
| `--env` | 环境变量 | - |
| `--start-cmd` | 容器启动命令 | - |
| `--start-args` | 启动参数（引号包裹） | - |
| `--no-wait` | 不等待就绪，立即返回 task_id | - |
| `--json` | JSON 格式输出（供 Agent 解析） | - |

**更多示例：**

```bash
# 多端口 + 2 节点
python3 gongji.py deploy my-image:latest -n my-svc -g 4090 -p 8080,8443 --points 2

# 带启动命令
python3 gongji.py deploy my-image:latest -n my-svc -g 4090 -p 8080 \
  --start-cmd "python" --start-args "serve.py --host 0.0.0.0"

# 不等待，后台部署
python3 gongji.py deploy my-image:latest -n my-svc -g 4090 --no-wait
```

### `list` — 查看任务列表

```bash
python3 gongji.py list                    # 运行中 + 待启动 + 已暂停
python3 gongji.py list -s Running         # 只看运行中的
python3 gongji.py list -s End             # 查看已结束的
```

**输出（含访问地址）：**

```
[388] my-llm  Running  节点 1/1  RTX 4090 x1
  -> https://xxx.suanli.cn:8080 (:8080)
[392] sd-server  Pending  节点 0/2  RTX 4090 x2
```

### `status` — 查看任务详情

```bash
python3 gongji.py status 388              # 查看状态和访问地址
python3 gongji.py status 388 --json       # 输出完整 JSON（调试用）
```

**输出：**

```
任务ID:   388
名称:     my-llm
状态:     Running
节点数:   1 / 1
GPU:      RTX 4090 x1
内存:     32768 MB | CPU: 8 核
访问地址: https://xxx.suanli.cn:8080 (端口 8080)
```

### `stop` — 停止 / 暂停 / 恢复任务

```bash
python3 gongji.py stop 388                # 删除（释放资源，不可恢复，需确认）
python3 gongji.py stop 388 -f             # 强制删除，跳过确认
python3 gongji.py stop 388 --pause        # 暂停（释放资源，可恢复）
python3 gongji.py stop 388 --resume       # 恢复暂停的任务
```

> `--pause` 和 `--resume` 互斥，不能同时使用。删除操作不可恢复，请确认后再执行。

### `logs` — 查看节点日志

部署失败或运行异常时，用 logs 排查原因：

```bash
python3 gongji.py logs 388                # 查看容器日志
python3 gongji.py logs 388 --events       # 查看事件（镜像拉取失败、OOM 等）
```

**事件输出示例：**

```
=== point-1 (Failed) ===
  [Warning] Failed: Error: ImagePullBackOff  (2026-04-13T10:00:00Z)
  [Warning] BackOff: Back-off pulling image "bad-image:latest"  (2026-04-13T10:00:05Z)
```

### `--json` — Agent 可解析的输出

所有查询命令都支持 `--json`，Agent 调用时**务必加上**，不要解析人类可读文本：

```bash
# deploy 返回
python3 gongji.py deploy my-image:v1 -n svc -g 4090 -p 8080 --json
# {"task_id": 388, "status": "Running", "urls": [{"url": "https://xxx:8080", "port": 8080}]}

# list 返回
python3 gongji.py list --json
# [{"task_id": 388, "task_name": "svc", "status": "Running", "urls": [{"url": "https://xxx:8080", "port": 8080}]}]

# status 返回完整任务详情 JSON
python3 gongji.py status 388 --json
```

---

## 在 Agent 代码中使用（Python API）

除了 CLI，也可以在 Python 代码中直接调用：

```python
from core.client import GongjiClient

client = GongjiClient()

# 1. 查可用 GPU
resources = client.search_resources()

# 2. 部署任务
result = client.create_task(
    task_name="my-llm",
    mark="从 search_resources 返回的 mark",
    service_image="my-registry/vllm-server:latest",
    ports=[8080],
)
task_id = result["data"]["task_id"]

# 3. 等待就绪，获取访问地址
detail = client.task_detail(task_id)
url = detail["data"]["services"][0]["remote_ports"][0]["url"]
# url = "https://xxx.suanli.cn:8080"

# 4. 调用你的推理 API
# requests.post(f"{url}/v1/chat/completions", json={...})

# 5. 用完释放
client.stop_task(task_id)
```

完整 API 参考见 [Apifox 接口文档](https://s.apifox.cn/6aa360d3-d8f2-471e-b841-3a35c33a7b7c)。

---

## 在 Claude Code 中使用

本项目包含 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill 定义（`skills/gongji.md`），配置后直接对 Agent 说：

- "帮我部署一个 4090 跑推理，镜像是 xxx，开 8080 端口"
- "看看我有哪些任务在跑"
- "把任务 388 停掉"

Agent 会自动调用 CLI 完成操作并返回结果。

---

## 项目结构

```
gongjiskills/
├── gongji.py              # CLI 入口（兼容 python3 gongji.py）
├── gongjiskills/           # Python 包（pip install 后 import）
│   ├── __init__.py        # from gongjiskills import GongjiClient
│   ├── auth.py            # RSA-SHA256 签名 + 配置加载
│   ├── client.py          # 共绩算力 API 客户端
│   └── cli.py             # CLI 实现
├── tests/                  # 20 个测试
│   ├── test_cli.py        # CLI 参数解析 + JSON 输出
│   └── test_auth.py       # 签名逻辑 + 配置加载
├── skills/
│   └── gongji.md          # Claude Code Skill 定义
├── setup.py
├── pyproject.toml
└── requirements.txt
```

## 支持的 API

基于[共绩算力 Open API](https://www.gongjiyun.com/docs/platform/openapi/zx3iwhbv1i8sxdkeiapcprxhn8d/) 封装，已对接以下接口（[完整接口文档](https://s.apifox.cn/6aa360d3-d8f2-471e-b841-3a35c33a7b7c)）：

| 模块 | 接口 | 说明 |
|------|------|------|
| 资源 | `GET /api/deployment/resource/search` | 查询 GPU 设备 / 库存 / 价格 |
| 任务 | `POST /api/deployment/task/create` | 创建弹性部署任务 |
| | `GET /api/deployment/task/search` | 查询任务列表 |
| | `GET /api/deployment/task/detail` | 获取任务详情 |
| | `POST /api/deployment/task/update` | 更新任务 |
| | `POST /api/deployment/task/pause` | 暂停任务 |
| | `POST /api/deployment/task/recover` | 恢复任务 |
| | `POST /api/deployment/task/stop` | 删除任务 |
| 节点 | `GET /api/deployment/task/points` | 查询节点列表 |
| | `POST /api/deployment/task/change_points` | 扩缩容 |
| | `POST /api/deployment/task/delete_pod` | 删除节点 |
| | `GET /api/deployment/task/point_log` | 节点日志 |
| | `GET /api/deployment/task/pod_event` | 节点事件 |
| 账单 | `GET /api/billing/get_billing_record` | 总账单 |
| | `GET /api/billing/get_task_billing_record` | 任务账单 |
| 存储 | `GET /api/storage/get_storage` | 存储资源列表 |

## 常见问题

**Q: 配置报错 "配置文件不存在"**
A: 按[快速开始](#第三步生成-rsa-密钥对--配置)创建 `~/.gongji/config.json`。

**Q: 报错 "token expired"**
A: Token 已过期，登录[控制台](https://www.gongjiyun.com)重新生成 API 密钥。

**Q: 部署后拿不到访问地址**
A: 任务可能还在启动中，用 `python3 gongji.py status <task_id>` 查看状态。状态为 `Running` 后才有访问地址。

**Q: 如何查看支出费用**
A: 登录[控制台](https://www.gongjiyun.com)查看账单，或使用 Python API 调用 `client` 的账单接口。
