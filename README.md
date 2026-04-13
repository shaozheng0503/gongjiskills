# 共绩算力 Skills

让 AI Agent 自动调用 [共绩算力](https://www.gongjiyun.com) GPU 资源，一句话部署推理服务、拿到 API 地址、用完释放。

## 它解决什么问题

Agent 开发中经常需要调用 GPU 算力（跑模型推理、图片生成等），但目前只能手动登录控制台操作，或者自己写 API 对接代码。

这个 Skill 让 Agent **自动完成**：查资源 → 部署 → 拿到回调地址 → 用完释放。

## 使用流程

```
1. 你在共绩算力平台准备好账号和余额
2. 配置好 API 密钥
3. Agent 需要 GPU 时，调用 Skill 自动部署
4. 拿到服务地址（如 LLM API endpoint），直接调用
5. 用完释放，按秒计费不浪费
```

**示意：**

```
Agent: "我需要一个 4090 跑 vLLM 推理"
  ↓ 调用 /gongji deploy
  ↓ 自动查找有库存的 4090 → 创建任务 → 等待就绪
  ↓ 返回: https://xxx.suanli.cn:8080
Agent: 拿到地址，开始调用推理 API
  ↓ 推理完成
Agent: "用完了，释放"
  ↓ 调用 /gongji stop
  ↓ 资源释放，停止计费
```

## 前置准备

### 1. 注册共绩算力账号

前往 [www.gongjiyun.com](https://www.gongjiyun.com) 注册账号，并**提前充值余额**（部署任务会按秒计费）。

### 2. 创建 API 密钥（RSA 模式）

登录控制台 → 右上角头像 → **API 密钥** → 新建密钥 → 选择 **RSA 加验签模式**。

### 3. 生成 RSA 密钥对

```bash
mkdir -p ~/.gongji
openssl genrsa -out ~/.gongji/private.key 2048
openssl rsa -pubout -in ~/.gongji/private.key -out ~/.gongji/public.pem
```

将 `public.pem` 的内容粘贴到控制台的公钥输入框，保存后会得到一个 **API Token**。

### 4. 创建配置文件

```bash
cat > ~/.gongji/config.json << 'EOF'
{
  "token": "你的API Token",
  "private_key_path": "~/.gongji/private.key"
}
EOF
```

### 5. 安装依赖

```bash
pip install cryptography requests
```

## CLI 用法

### 部署任务

```bash
# 部署镜像到 4090，暴露 8080 端口
python3 gongji.py deploy my-registry/vllm-server:latest \
  -n my-llm \
  -g 4090 \
  -p 8080

# 部署完成后输出:
# 选中资源: RTX 4090 ×1 | 区域A | ¥1.68/h
# 任务已创建, task_id=388
# 等待任务启动... Running!
# 访问地址: https://xxx.suanli.cn:8080 (端口 8080)
```

拿到访问地址后，Agent 就可以直接调用，比如：

```bash
curl https://xxx.suanli.cn:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "my-model", "messages": [{"role": "user", "content": "hello"}]}'
```

### 查看任务

```bash
python3 gongji.py list                    # 列出所有运行中的任务
python3 gongji.py status 388              # 查看任务详情和访问地址
python3 gongji.py status 388 --json       # 输出完整 JSON
```

### 停止任务

```bash
python3 gongji.py stop 388                # 删除任务（释放资源，不可恢复）
python3 gongji.py stop 388 --pause        # 暂停（释放资源，可恢复）
python3 gongji.py stop 388 --resume       # 恢复暂停的任务
```

## 在 Agent 中使用（Python API）

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

# 4. 调用推理 API
# requests.post(f"{url}/v1/chat/completions", json={...})

# 5. 用完释放
client.stop_task(task_id)
```

## 在 Claude Code 中使用

本项目包含 Claude Code Skill 定义（`skills/gongji.md`），配置后可以直接对 Agent 说：

- "帮我部署一个 4090 跑推理，镜像是 xxx，开 8080 端口"
- "看看我有哪些任务在跑"
- "把任务 388 停掉"

Agent 会自动调用对应的 CLI 命令完成操作。

## 项目结构

```
├── README.md
├── CLAUDE.md            # Claude Code 项目说明
├── gongji.py            # CLI 入口（deploy/list/status/stop）
├── core/
│   ├── auth.py          # RSA-SHA256 签名 + 配置加载
│   └── client.py        # 共绩算力 API 客户端
└── skills/
    └── gongji.md        # Claude Code Skill 定义
```

## 支持的 API

| 模块 | 接口 | 说明 |
|------|------|------|
| 资源 | `GET /api/deployment/resource/search` | 查询 GPU 设备/库存/价格 |
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

## 相关链接

- [共绩算力官网](https://www.gongjiyun.com)
- [Open API 文档](https://www.gongjiyun.com/docs/platform/openapi/zx3iwhbv1i8sxdkeiapcprxhn8d/)
- [API 接口详情 (Apifox)](https://s.apifox.cn/6aa360d3-d8f2-471e-b841-3a35c33a7b7c)
