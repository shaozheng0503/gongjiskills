# CLI 命令参考

`gongji` 命令完整参数手册。日常使用查 [README](../README.md) 就够，本文档供需要细调时查阅。

**全局约定**：

- 所有命令都支持 `--json` / `-j`，Agent 调用时务必加
- `--force` / `-f` 跳过确认或覆盖配置
- 成功返回 exit code 0；失败返回 1（JSON 模式下输出 `{"error": "..."}`）
- 参数优先级：命令行参数 > 模板值 > 默认值

---

## `init` — 初始化配置

```bash
gongji init                              # 交互模式
gongji init --force                      # 覆盖已有配置
GONGJI_TOKEN=xxx gongji init --force     # 非交互（Agent / CI）
gongji init --token xxx --force          # 命令行参数（会进 shell history）
```

`init` 会依次完成：

1. 生成 RSA 密钥对（`~/.gongji/private.key` + `public.pem`），私钥权限自动设为 `600`
2. 显示公钥 → 复制到 [控制台](https://www.gongjiyun.com) 头像 → API密钥 → RSA 模式
3. 输入 API Token
4. 验证连通性（查一次 GPU 资源）

**初始化目录结构：**

```
~/.gongji/
├── config.json       # 600 - 包含 token 和密钥路径
├── private.key       # 600 - RSA 私钥
├── public.pem        # 644 - RSA 公钥（供上传控制台）
└── ttl/              # TTL 守护进程的日志 / PID 目录
    ├── <task_id>.log
    └── <task_id>.pid
```

---

## `resources` — 查看 GPU 资源

默认只显示有库存的，按折扣价从低到高排列。

```bash
gongji resources                      # 有库存的（按价格排序）
gongji resources --all                # 全部（含售罄）
gongji resources -g 4090              # 只看 4090
gongji resources -g 4090 -r 广东       # 4090 + 广东区域
gongji resources --json                # JSON 输出
```

| 参数 | 说明 | 默认 |
|------|------|------|
| `--all, -a` | 显示全部（含售罄） | false |
| `--gpu, -g` | GPU 型号关键词（如 4090/H800） | 不限 |
| `--region, -r` | 区域关键词（如 广东/河南） | 不限 |
| `--json, -j` | JSON 输出 | - |

**文本输出示例：**

```
4090 x1  (显存 24.0G | 16核 | 63G)
  区域           库存     单价(元/h)      折扣价(元/h)
  ------------------------------------------------
  河北六区         21     1.68         1.05
  广东一区        327     1.68         1.05

有库存 14 种（共 44 种，用 --all 查看全部）
```

**合并逻辑：** 相同 `(gpu_name, gpu_count, gpu_memory, cpu, memory)` 组合合并成一行，区域作为子行展示。

---

## `images` — 镜像模板管理

**不需要 API 凭据**，`init` 前也能用。

```bash
gongji images                              # 默认：按分类分组列出全部
gongji images categories                   # 11 个分类及模板数
gongji images --category llm               # 按分类筛选
gongji images --category video --json      # JSON 输出
gongji images --json                       # 全部模板 JSON
gongji images add <name> --image <addr>    # 添加自定义模板
gongji images rm <name>                    # 删除自定义（内置不可删）
```

**`add` 参数：**

| 参数 | 说明 |
|------|------|
| `name` | 模板名（必填） |
| `--image, -i` | Docker 镜像地址（必填） |
| `--gpu, -g` | 推荐 GPU 型号 |
| `--port, -p` | 默认暴露端口 |
| `--desc, -d` | 说明 |
| `--start-cmd` | 默认启动命令 |
| `--start-args` | 默认启动参数 |

存储在 `~/.gongji/templates.json`（权限 600）。**与内置重名会覆盖内置同名字段，未覆盖的字段保留**。

**单条 JSON 示例：**

```json
{
  "vllm": {
    "image": "harbor.suanleme.cn/public-hub/vllm-openai:v0.19.0-copy",
    "category": "llm",
    "description": "平台预制 vLLM，默认启动 Qwen3-8B-FP8",
    "port": "8000",
    "gpu": "4090",
    "env": "VLLM_USE_MODELSCOPE=true",
    "start_cmd": "/bin/bash",
    "start_args": ["-c", "vllm serve Qwen/Qwen3-8B-FP8 --max-model-len 16K --max-num-seqs 2"],
    "docs": "https://www.gongjiyun.com/docs/..."
  }
}
```

> ⚠️ 所有内置模板镜像都是 `harbor.suanleme.cn/...`。**不要用 `vllm/vllm-openai:latest`、`ghcr.io/...` 这类上游地址，平台内网可能拉不到。**

---

## `deploy` — 部署任务

自动：查资源 → 选最便宜有库存的 → 创建任务 → 等待就绪 → 返回访问 URL。

```bash
gongji deploy <镜像地址> -n <任务名> [其他参数]
gongji deploy --template <模板名> -n <任务名> [其他参数]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `<image>` | Docker 镜像地址（与 `--template` 二选一） | - |
| `--template, -t` | 镜像模板名 | - |
| `--name, -n` | 任务名称（**必填**） | - |
| `--gpu, -g` | GPU 型号关键词 | 模板值 / 自动选最便宜 |
| `--gpu-count, -c` | GPU 卡数 | 模板值 / 不限 |
| `--region, -r` | 区域关键词 | 不限 |
| `--port, -p` | 暴露端口（逗号分隔） | 模板值 / `8080` |
| `--points` | 节点数量（多副本） | `1` |
| `--env` | 环境变量 | 模板值 |
| `--start-cmd` | 容器启动命令 | 模板值 |
| `--start-args` | 启动参数（引号包裹） | 模板值 |
| `--no-wait` | 不等待就绪，立即返回 | - |
| `--ttl` | TTL 秒数，到期自动释放 | - |
| `--json, -j` | JSON 输出 | - |

**典型用法：**

```bash
# 模板（最简）
gongji deploy --template vllm -n my-llm --ttl 3600 --json

# 模板 + 覆盖 GPU 数量
gongji deploy --template qwen3.5-27b -n big -c 4

# 模板 + 限定区域
gongji deploy --template wan2.2 -n video -r 广东

# 直接指定镜像
gongji deploy harbor.suanleme.cn/public-hub/my-img:v1 \
  -n my-svc -g 4090 -c 1 -p 8080

# 自定义启动命令
gongji deploy harbor.suanleme.cn/public-hub/vllm-openai:v0.19.0-copy \
  -n custom -g 4090 -p 8000 \
  --env "VLLM_USE_MODELSCOPE=true" \
  --start-cmd "/bin/bash" \
  --start-args "-c 'vllm serve Qwen/Qwen3-32B'"

# 不等待立即返回
gongji deploy --template ollama -n bg --no-wait --json

# 多副本
gongji deploy --template whisper -n cluster --points 3 --json
```

**JSON 输出：**

```json
{
  "task_id": 1926525,
  "status": "Running",
  "urls": [{"url": "https://deployment-452-xxx-8000.550w.link", "port": 8000}],
  "ttl_seconds": 3600,
  "auto_release_pid": 12345
}
```

**等待超时**（5 分钟未 Running）不再当作 error，返回：

```json
{
  "task_id": 1926525,
  "status": "Pending",
  "warning": "等待超时 (5分钟)，任务已创建但未就绪",
  "hint": "gongji status 1926525"
}
```

---

## `list` — 列任务

```bash
gongji list                           # 运行中 + 待启动（默认）
gongji list -s Running                # 只看运行中
gongji list -s Running,Pending,Paused # 含暂停的
gongji list --json
```

| 参数 | 说明 | 默认 |
|------|------|------|
| `--status, -s` | 筛选状态（Running/Pending/Paused/End） | `Running,Pending` |
| `--json, -j` | JSON 输出 | - |

**JSON：**

```json
[{
  "task_id": 1926525,
  "task_name": "my-llm",
  "status": "Running",
  "urls": [{"url": "https://...", "port": 8000}]
}]
```

---

## `status` — 任务详情

```bash
gongji status 1926525              # 文本格式
gongji status 1926525 --json       # 完整 JSON（含 resources/services/billing_value）
```

**输出：**

```
任务ID:   1926525
状态:     Running
节点数:   1 / 1
GPU:      4090 x1 (显存 24.0G)
已花费:   36.44 元
访问地址: https://deployment-452-xxx-8000.550w.link (端口 8000)
```

`已花费` 按秒实时更新。

---

## `logs` — 日志 / 事件

```bash
gongji logs 1926525                # 容器日志
gongji logs 1926525 --events       # 事件（排查启动失败）
```

**事件输出示例：**

```
=== deployment-452-xxx-pk8hf (Pending) ===
  [Warning] Failed: Error: ImagePullBackOff
  [Normal] Pulling: Pulling image "my-image:v1"
  [Normal] BackOff: Back-off pulling image
```

常见 reason：

- `Pulling` / `Pulled` — 正常
- `ImagePullBackOff` / `ErrImagePull` — 镜像拉失败（地址错或平台内网拉不到）
- `OOMKilled` — 内存超限
- `CrashLoopBackOff` — 容器启动即崩溃

---

## `stop` — 停止 / 暂停 / 恢复

```bash
# 单个
gongji stop 1926525                # 删除（需确认）
gongji stop 1926525 -f             # 强制删除
gongji stop 1926525 -f --json      # Agent 调用
gongji stop 1926525 --pause        # 暂停（释放资源，可恢复）
gongji stop 1926525 --resume       # 恢复

# 批量
gongji stop --all -f --json        # 删除所有 Running/Pending/Paused 任务
```

| 参数 | 说明 |
|------|------|
| `task_id` | 任务 ID（与 `--all` 二选一） |
| `--all` | 批量删除（**强制要求 `--force`**） |
| `--pause` / `--resume` | 互斥，暂停或恢复 |
| `--force, -f` | 跳过确认 |
| `--json, -j` | JSON 输出 |

**互斥约束**：

- `--all` 不能与 `task_id` 同时使用
- `--all` + JSON 模式必须同时加 `--force`（防止误删）
- `--pause` 与 `--resume` 互斥

**JSON 输出**：

```json
// 单个
{"task_id": 1926525, "action": "删除", "ok": true}

// 批量
{"stopped": [1926525, 1926530], "failed": []}
```

---

## 失败输出统一格式

所有命令失败时输出 `{"error": "..."}`，exit code 1：

```bash
$ gongji deploy --template not-exist -n svc --json
{"error": "模板 [not-exist] 不存在，用 gongji images 查看可用模板"}
$ echo $?
1
```

---

## 自动重试 & 友好错误映射

**瞬时错误自动重试 2 次**（指数退避 1s → 2s）：

- 连接失败（`ConnectionError`）
- 请求超时（`Timeout`，30s）
- HTTP 5xx（500/502/503/504）

**API 错误自动翻译 + 修复建议**：

| 原始 | 翻译 |
|------|------|
| `token expired` / `token invalid` | "Token 已失效，请重新生成，再 `gongji init --force`" |
| `signature invalid` | "签名验证失败：公钥可能未上传到控制台，检查 `~/.gongji/public.pem`" |
| `task not found` / `任务不存在` | "任务不存在，用 `gongji list` 确认 task_id" |
| `insufficient balance` / `余额` | "账户余额不足，请前往控制台充值" |
| `inventory not enough` / `库存` | "库存不足，换个区域或 GPU 型号" |

**注意**：`不存在`/`not found` 只在错误信息中含 `task`/`任务` 时才映射，避免误匹配"配置文件不存在"等错误。
