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
  ↓ 返回: https://xxx.550w.link:8080
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
gongji init
```

`init` 会自动完成：
1. 生成 RSA 密钥对（私钥权限自动设为 `600`）
2. 显示公钥内容 → 你粘贴到[控制台](https://www.gongjiyun.com)（头像 → API密钥 → RSA模式）
3. 输入获取到的 API Token
4. 验证连通性

**Agent/CI 非交互使用（推荐环境变量，不会泄露到 shell history）：**

```bash
GONGJI_TOKEN=xxx gongji init --force
```

也支持参数传入：`gongji init --token xxx`

> 密钥和配置说明见 [Open API 使用文档](https://www.gongjiyun.com/docs/platform/openapi/zx3iwhbv1i8sxdkeiapcprxhn8d/) 和 [RSA 模式使用指南](https://www.gongjiyun.com/docs/platform/openapi/m3p6whioxidzwaksughc4gfhnro/)。

### 第四步：验证

```bash
gongji resources    # 查看可用GPU和价格
```

---

## CLI 用法

### `resources` — 查看可用 GPU

默认只显示有库存的，按价格从低到高排列：

```bash
gongji resources          # 有库存的（按价格排序）
gongji resources --all    # 全部（含售罄）
gongji resources --json   # JSON 输出
```

**输出：**

```
4090 x1  (显存 24.0G | 16核 | 63G)
  区域           库存     单价(元/h)      折扣价(元/h)
  ----------------------------------------------
  河北六区         21     1.68         1.05
  广东一区         327    1.68         1.05

5090 x1  (显存 31.8G | 48核 | 63G)
  区域           库存     单价(元/h)      折扣价(元/h)
  ----------------------------------------------
  安徽一区         6      2.50         1.60

有库存 14 种（共 44 种，用 --all 查看全部）
```

### `deploy` — 部署任务

自动查找有库存且**最便宜**的 GPU → 创建弹性部署 → 等待就绪 → 返回访问地址。

等待过程中会实时显示事件（拉镜像、启动容器等），失败时自动输出原因。

```bash
gongji deploy <镜像地址> -n <任务名> -g <GPU型号> -p <端口>
```

**示例：**

```bash
# 部署推理服务到 4090 单卡
gongji deploy my-registry/vllm:latest -n my-llm -g 4090 -p 8080

# 指定 4 卡 + 指定广东区域（就近部署，减少延迟）
gongji deploy my-registry/vllm:latest -n my-llm -g 4090 -c 4 -r 广东 -p 8080

# Agent 调用（JSON 输出）
gongji deploy my-registry/vllm:latest -n my-llm -g 4090 -p 8080 --json
```

**输出：**

```
正在查询可用 GPU 资源...
选中资源: 4090 x1 | 广东一区 | 1.05元/h (最低价)
正在创建任务 [my-llm]...
任务已创建, task_id=1926525
等待任务启动...
  [Pulling] Pulling image "my-registry/vllm:latest"
  [Started] Started container istio-proxy
  [Pulled] Successfully pulled image
Running!
访问地址: https://deployment-452-xxx-8080.550w.link (端口 8080)
```

拿到地址后直接调用：

```bash
curl https://deployment-452-xxx-8080.550w.link/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "my-model", "messages": [{"role": "user", "content": "hello"}]}'
```

**全部参数：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `<image>` | Docker 镜像地址（必填） | - |
| `-n, --name` | 任务名称（必填） | - |
| `-g, --gpu` | GPU 型号关键词，如 `4090` / `H800` | 自动选最便宜 |
| `-c, --gpu-count` | GPU 卡数，如 `1` / `4` / `8` | 不限 |
| `-r, --region` | 区域关键词，如 `广东` / `河南` / `河北` | 不限 |
| `-p, --port` | 暴露端口，多个用逗号分隔 | `8080` |
| `--points` | 节点数量 | `1` |
| `--env` | 环境变量 | - |
| `--start-cmd` | 容器启动命令 | - |
| `--start-args` | 启动参数（引号包裹） | - |
| `--no-wait` | 不等待就绪，立即返回 task_id | - |
| `--json` | JSON 格式输出（供 Agent 解析） | - |

### `list` — 查看任务列表

```bash
gongji list                           # 运行中 + 待启动
gongji list -s Running,Pending,Paused # 含暂停的
gongji list --json                    # JSON 输出
```

**输出（含访问地址）：**

```
[1926525] my-llm  Running  节点 1/1  4090 x1
  -> https://deployment-452-xxx-8080.550w.link (:8080)
```

### `status` — 查看任务详情

```bash
gongji status 1926525              # 查看状态、访问地址、费用
gongji status 1926525 --json       # JSON 输出
```

**输出：**

```
任务ID:   1926525
名称:     my-llm
状态:     Running
节点数:   1 / 1
GPU:      4090 x1 (显存 24.0G)
内存:     63G | CPU: 24 核
已花费:   36.44 元
访问地址: https://deployment-452-xxx-8080.550w.link (端口 8080)
```

### `logs` — 查看节点日志

部署失败或运行异常时排查原因：

```bash
gongji logs 1926525                # 查看容器日志
gongji logs 1926525 --events       # 查看事件（镜像拉取失败、OOM 等）
```

**事件输出示例：**

```
=== deployment-452-xxx-74f56c675-pk8hf (Pending) ===
  [Warning] Failed: Error: ImagePullBackOff  (2026-04-13T10:00:00Z)
  [Normal] Pulling: Pulling image "my-image:v1"  (2026-04-13T09:59:55Z)
```

### `stop` — 停止 / 暂停 / 恢复任务

```bash
gongji stop 1926525                # 删除（不可恢复，需确认）
gongji stop 1926525 -f             # 强制删除
gongji stop 1926525 --pause        # 暂停（释放资源，可恢复）
gongji stop 1926525 --resume       # 恢复暂停的任务
gongji stop 1926525 -f --json      # Agent 调用
```

### `--json` — Agent 必须用的输出模式

所有命令都支持 `--json`，**Agent 调用时务必加上**。成功和失败都返回合法 JSON：

```bash
# deploy 成功
gongji deploy my-image:v1 -n svc -g 4090 -p 8080 --json
# {"task_id": 1926525, "status": "Running", "urls": [{"url": "https://xxx", "port": 8080}]}

# 失败
# {"error": "查询资源失败: token expired"}

# list
gongji list --json
# [{"task_id": 1926525, "task_name": "svc", "status": "Running", "urls": [...]}]

# stop
gongji stop 1926525 -f --json
# {"task_id": 1926525, "action": "删除", "ok": true}
```

---

## 在 Agent 代码中使用（Python API）

```python
from gongjiskills import GongjiClient

client = GongjiClient()

# 1. 查可用 GPU
resources = client.search_resources()

# 2. 部署任务
result = client.create_task(
    task_name="my-llm",
    mark="从 search_resources 返回的 mark",
    service_image="my-registry/vllm:latest",
    ports=[8080],
)
task_id = result["data"]["task_id"]

# 3. 获取访问地址
detail = client.task_detail(task_id)
url = detail["data"]["services"][0]["remote_ports"][0]["url"]

# 4. 调用推理 API
# requests.post(f"{url}/v1/chat/completions", json={...})

# 5. 用完释放
client.stop_task(task_id)
```

完整 API 参考见 [Apifox 接口文档](https://s.apifox.cn/6aa360d3-d8f2-471e-b841-3a35c33a7b7c)。

---

## 在 Claude Code 中使用

本项目包含 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill 定义（`skills/gongji.md`），配置后直接对 Agent 说：

- "帮我部署一个 4090 跑推理，镜像是 xxx，开 8080 端口"
- "部署到广东区域，4 卡 4090"
- "看看我有哪些任务在跑"
- "任务 1926525 花了多少钱"
- "把任务停掉"

Agent 会自动调用 CLI 完成操作并返回结果。

---

## 安全

- `~/.gongji/` 目录权限 `700`（仅当前用户可访问）
- `config.json` / `private.key` 权限 `600`（仅当前用户可读写）
- 加载配置时自动检测权限，过宽时输出警告和修复命令
- Token 推荐通过**环境变量** `GONGJI_TOKEN` 传入，避免泄露到 shell history
- RSA 签名模式（PKCS1v15 + SHA256），请求不可伪造

## 项目结构

```
gongjiskills/
├── gongji.py              # CLI 入口（兼容 python3 gongji.py）
├── gongjiskills/           # Python 包（pip install 后 import）
│   ├── __init__.py        # from gongjiskills import GongjiClient
│   ├── auth.py            # RSA-SHA256 签名 + 权限检查
│   ├── client.py          # API 客户端 + 网络错误处理
│   └── cli.py             # CLI 实现（7 个命令）
├── tests/                  # 23 个测试
│   ├── test_cli.py        # CLI 参数解析 + JSON 输出契约
│   └── test_auth.py       # 签名验证 + 配置加载
├── skills/
│   └── gongji.md          # Claude Code Skill 定义
├── setup.py
├── pyproject.toml
├── LICENSE                 # MIT
└── requirements.txt
```

## 常见问题

**Q: 报错 "配置文件不存在"**
A: 运行 `gongji init` 初始化。

**Q: 报错 "token expired"**
A: 登录[控制台](https://www.gongjiyun.com)重新生成 API 密钥，然后 `gongji init --force`。

**Q: 报错 "权限过宽"**
A: 运行提示中的 `chmod` 命令修复，或重新 `gongji init --force`（会自动设置正确权限）。

**Q: 部署后拿不到访问地址**
A: 任务可能还在拉镜像，等待过程会实时显示事件。也可以手动查看：`gongji logs <id> --events`。

**Q: 怎么指定 GPU 卡数和区域**
A: `gongji deploy ... -g 4090 -c 4 -r 广东`（4090 四卡，广东区域）。

**Q: 怎么看已经花了多少钱**
A: `gongji status <id>` 会显示累计花费。

## License

MIT
