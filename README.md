# 共绩算力 Skills

> 让 AI Agent（或你自己）用一条命令就能在 [共绩算力](https://www.gongjiyun.com) 上开一台 GPU、跑服务、拿到公网地址、用完就释放。
>
> **47 个平台预制镜像模板 · 11 个分类 · CLI + Python API + Claude Code Skill · TTL 自动释放 · JSON 契约**

**相关文档：**
[共绩算力官网](https://www.gongjiyun.com) ·
[Open API 文档](https://www.gongjiyun.com/docs/platform/openapi/zx3iwhbv1i8sxdkeiapcprxhn8d/) ·
[API 接口详情 (Apifox)](https://s.apifox.cn/6aa360d3-d8f2-471e-b841-3a35c33a7b7c) ·
[完整介绍文档](./docs/介绍.md) ·
[预制镜像清单](./docs/预制镜像清单.md)

---

## 目录

- [这是什么](#这是什么)
- [能力速览](#能力速览)
- [快速开始](#快速开始)
  - [安装](#安装)
  - [初始化](#初始化)
  - [验证](#验证)
- [CLI 命令参考](#cli-命令参考)
  - [`resources` — 查看 GPU 资源](#resources--查看-gpu-资源)
  - [`images` — 镜像模板管理](#images--镜像模板管理)
  - [`deploy` — 部署任务](#deploy--部署任务)
  - [`list` — 列任务](#list--列任务)
  - [`status` — 任务详情](#status--任务详情)
  - [`logs` — 日志/事件](#logs--日志事件)
  - [`stop` — 停止/暂停/恢复](#stop--停止暂停恢复)
- [47 个预制模板完整清单](#47-个预制模板完整清单)
- [按分类一键部署手册](#按分类一键部署手册)
- [Python API](#python-api)
- [在 Claude Code 中使用](#在-claude-code-中使用)
- [Agent / JSON 契约](#agent--json-契约)
- [可靠性与错误处理](#可靠性与错误处理)
- [安全](#安全)
- [成本控制](#成本控制)
- [项目结构](#项目结构)
- [开发与测试](#开发与测试)
- [常见问题（FAQ）](#常见问题faq)
- [License](#license)

---

## 这是什么

AI Agent / 开发者在下面场景都可能用到临时 GPU：

- 跑一次 Qwen / Flux / SD 推理或生成
- 批量 OCR 一批 PDF
- 给客户演示一个 ComfyUI 工作流
- CI 里跑一次模型评估
- Agent 执行任务中途需要调用视觉/语音模型

传统做法要手动登控制台选 GPU、配镜像、开端口、等启动、抄 URL、**用完记得回去释放**（容易忘 → 持续烧钱）。

这个 Skill 把全流程压缩成一条命令：

```bash
gongji deploy --template qwen3.5-9b -n my-llm --ttl 3600 --json
# 自动：查最便宜 4090 → 建部署 → 等就绪 → 返回 URL → 1 小时后自动释放
```

它提供三种入口：
- **CLI** `gongji xxx` — 命令行 / 脚本 / CI
- **Python API** `from gongjiskills import GongjiClient` — 嵌入自研 Agent
- **Claude Code Skill** `/gongji` — 自然语言调用

---

## 能力速览

| 能力 | 说明 |
|------|------|
| 🎯 智能选资源 | 自动查所有区域，按折扣价排序选最便宜有库存的 |
| 📦 预制模板库 | 47 个平台镜像（LLM/图像/视频/语音/OCR/训练...） |
| 🗂️ 分类发现 | 11 个分类，`gongji images --category llm` 快速定位 |
| 🚀 一键部署 | 查资源 + 建任务 + 等就绪 + 拿 URL 全自动 |
| ⏰ TTL 自动释放 | `--ttl 3600` 后台守护，到期自动 stop |
| 🔁 自动重试 | 网络超时 / 5xx 自动重试（指数退避 ×2） |
| 💬 友好错误 | Token 失效 / 签名错误 / 库存不足自动附修复建议 |
| 📋 JSON 契约 | 所有命令 `--json` 输出结构化数据，Agent 直接解析 |
| 🔐 安全加固 | 私钥 600、目录 700、权限自动检测、支持 env var |
| 🧩 自定义扩展 | `gongji images add` 添加自定义模板 |
| 📊 实时事件 | 部署过程中显示拉镜像、启容器、失败原因 |
| 🧹 批量管理 | `gongji stop --all` 一键释放所有任务 |

---

## 快速开始

### 安装

**方式 1：一键脚本（推荐）**

自动检测 Python / pip / openssl，支持 `GONGJI_TOKEN` 自动 init：

```bash
curl -fsSL https://raw.githubusercontent.com/shaozheng0503/gongjiskills/main/install.sh | bash

# 带 token 免交互（适合 Agent / CI）
GONGJI_TOKEN=xxx curl -fsSL https://raw.githubusercontent.com/shaozheng0503/gongjiskills/main/install.sh | bash
```

**方式 2：pip 直接安装**

```bash
pip install git+https://github.com/shaozheng0503/gongjiskills.git
```

**方式 3：本地 clone + 安装（适合开发）**

```bash
git clone https://github.com/shaozheng0503/gongjiskills.git
cd gongjiskills
pip install .
# 或开发模式（修改代码即时生效）
pip install -e .
```

安装后可全局调用 `gongji` 命令。也支持 `python3 gongji.py xxx`（仓库根目录的兼容入口）。

**依赖：**
- Python ≥ 3.9
- `requests`（HTTP 客户端）
- `cryptography`（RSA 签名）
- `openssl` 命令（用于 init 生成密钥对）

### 初始化

注册共绩账号并充值（[定价](https://www.gongjiyun.com/pricing/)）后：

```bash
gongji init
```

`init` 会依次完成：

1. 生成 RSA 密钥对（`~/.gongji/private.key` + `public.pem`），私钥权限自动设为 `600`
2. 显示公钥 → 复制到 [控制台](https://www.gongjiyun.com) 头像 → API密钥 → RSA 模式
3. 输入控制台生成的 API Token
4. 验证连通性（查一次 GPU 资源）

**Agent / CI 非交互模式：**

```bash
# 推荐：环境变量传 token（不会进 shell history）
GONGJI_TOKEN=xxx gongji init --force

# 或命令行参数
gongji init --token xxx --force
```

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

> 详细的 RSA 模式说明见 [共绩官方指南](https://www.gongjiyun.com/docs/platform/openapi/m3p6whioxidzwaksughc4gfhnro/)。

### 验证

```bash
gongji resources -g 4090
```

如果能看到 4090 的价格和库存，就说明凭据配好了。

---

## CLI 命令参考

全局参数约定：
- `--json` / `-j` — 所有命令都支持，Agent 调用时务必加
- `--force` / `-f` — 跳过确认或覆盖配置
- 成功返回 exit code 0；失败返回 1（JSON 模式下也输出 `{"error": "..."}`）

### `resources` — 查看 GPU 资源

默认只显示有库存的，按折扣价从低到高排列：

```bash
gongji resources                      # 有库存的（按价格排序）
gongji resources --all                # 全部（含售罄）
gongji resources -g 4090              # 只看 4090
gongji resources -g 4090 -r 广东       # 4090 + 广东区域
gongji resources --json                # JSON 输出
```

**参数：**

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
  广东一区         327    1.68         1.05

5090 x1  (显存 31.8G | 48核 | 63G)
  区域           库存     单价(元/h)      折扣价(元/h)
  ------------------------------------------------
  安徽一区         6      2.50         1.60

有库存 14 种（共 44 种，用 --all 查看全部）
```

**合并逻辑：** 相同 `(gpu_name, gpu_count, gpu_memory, cpu, memory)` 组合会合并成一行，区域作为子行展示，方便比对跨区域价格差异。

---

### `images` — 镜像模板管理

本命令**不需要 API 凭据**，`init` 前也能用（方便 Agent 先看有啥模板再决定装不装）。

#### 默认：按分类分组列出

```bash
gongji images
```

输出（每个分类一个分节，带 GPU × 卡数、端口、说明）：

```
【大语言模型推理】  (llm)
  名称                         GPU      端口             说明
  ---------------------------------------------------------------
   gpt-oss-20b               4090     30000          OpenAI GPT-OSS-20B 开源模型，稀疏激活
   minicpm-4-8b              4090×1   11434          面壁智能 MiniCPM 4-8B 端侧大模型
   ollama                    4090     11434          平台预制 Ollama（需自行 pull 模型）
   qwen3-30b-webui           4090×1   11434          Ollama + Open WebUI + Qwen3-30B
   qwen3.5-0.8b              4090     8000           Qwen3.5-0.8B 超轻量 LLM
   qwen3.5-27b               4090×8   8000           Qwen3.5-27B 阿里 270 亿多模态，26 万上下文
   qwen3.5-27b-claude-gguf   4090×4   -              Qwen3.5-27B 蒸馏 Claude GGUF 量化
   qwen3.5-9b                4090     8000           Qwen3.5-9B vLLM 推理
   qwen3.5-9b-claude         4090×1   8000           Qwen3.5-9B 蒸馏 Claude 融合模型
   vllm                      4090     8000           平台预制 vLLM，默认 Qwen3-8B-FP8
...
```

#### 列分类

```bash
gongji images categories              # 11 个分类及模板数
gongji images categories --json       # JSON
```

输出：

```
【镜像分类】
  分类key          中文名              镜像数
  --------------------------------------------
  llm            大语言模型推理          10
  multimodal     多模态视觉            3
  image-gen      文生图              10
  image-edit     图像编辑/人像          8
  video          视频生成             3
  3d             3D 重建            1
  audio          语音合成/识别          4
  music          音乐生成             2
  ocr            文档解析/OCR         2
  dev            训练/开发环境          3
  tools          工具类              1
```

#### 按分类筛选

```bash
gongji images --category llm              # 只看 LLM 分类
gongji images --category video --json     # JSON 输出
```

#### JSON 格式（Agent 消费）

```bash
gongji images --json                      # 全部模板
gongji images --category llm --json       # LLM 分类
```

每条 JSON 记录包含：

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
    "docs": "https://www.gongjiyun.com/docs/flexible-deployment/pre-fabricated-services/..."
  }
}
```

#### 添加自定义模板

```bash
gongji images add my-vllm \
  --image harbor.suanleme.cn/my-hub/vllm:custom \
  --gpu 4090 --port 8000 \
  --desc "我的定制 vLLM" \
  --start-cmd "/bin/bash" \
  --start-args "-c 'vllm serve my-model --port 8000'"
```

存储在 `~/.gongji/templates.json`（权限 600）。**与内置重名会覆盖内置**。

#### 删除自定义模板

```bash
gongji images rm my-vllm
# 内置模板不可删除（会报错）
```

> ⚠️ **重要：** 所有内置模板的镜像地址都是 `harbor.suanleme.cn/...`（平台镜像仓库）。**不要用 `vllm/vllm-openai:latest`、`ghcr.io/...` 这类上游 docker hub 镜像地址，平台内网可能拉不到。** 一定要用 `gongji images` 里列出的模板，或者自己推镜像到 `harbor.suanleme.cn`。

---

### `deploy` — 部署任务

自动：查资源 → 选最便宜有库存的 → 创建任务 → 等待就绪 → 返回访问 URL。

```bash
gongji deploy <镜像地址> -n <任务名> [其他参数]
gongji deploy --template <模板名> -n <任务名> [其他参数]
```

**参数全表：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `<image>` | Docker 镜像地址（与 `--template` 二选一） | - |
| `--template, -t` | 镜像模板名（见 `gongji images`） | - |
| `--name, -n` | 任务名称（**必填**） | - |
| `--gpu, -g` | GPU 型号关键词，如 `4090` / `H800` | 模板值 或 自动选最便宜 |
| `--gpu-count, -c` | GPU 卡数，如 `1` / `4` / `8` | 模板值 或 不限 |
| `--region, -r` | 区域关键词，如 `广东` / `河南` / `河北` | 不限 |
| `--port, -p` | 暴露端口，多个用逗号分隔 | 模板值 或 `8080` |
| `--points` | 节点数量（多副本） | `1` |
| `--env` | 环境变量（`KEY=val KEY2=val`） | 模板值 |
| `--start-cmd` | 容器启动命令 | 模板值 |
| `--start-args` | 启动参数（引号包裹） | 模板值 |
| `--no-wait` | 不等待就绪，立即返回 task_id | - |
| `--ttl` | TTL 秒数，到期自动释放 | - |
| `--json, -j` | JSON 格式输出 | - |

**参数优先级：** 命令行参数 > 模板值 > 默认值。

**示例：**

```bash
# 1. 用模板（最简，推荐）
gongji deploy --template vllm -n my-llm --json

# 2. 用模板 + TTL 自动释放
gongji deploy --template qwen3.5-9b -n tmp-llm --ttl 3600 --json

# 3. 用模板 + 覆盖 GPU 数量
gongji deploy --template qwen3.5-27b -n big-llm -c 4

# 4. 用模板 + 限定区域
gongji deploy --template wan2.2 -n video -r 广东

# 5. 直接指定镜像（不用模板）
gongji deploy harbor.suanleme.cn/public-hub/my-img:v1 \
  -n my-svc -g 4090 -c 1 -p 8080

# 6. 自定义启动命令
gongji deploy harbor.suanleme.cn/public-hub/vllm-openai:v0.19.0-copy \
  -n custom-llm -g 4090 -p 8000 \
  --env "VLLM_USE_MODELSCOPE=true" \
  --start-cmd "/bin/bash" \
  --start-args "-c 'vllm serve Qwen/Qwen3-32B --max-model-len 32K'"

# 7. 不等待立即返回
gongji deploy --template ollama -n bg --no-wait --json
# → {"task_id": ..., "status": "Pending"}

# 8. 部署多副本
gongji deploy --template whisper -n asr-cluster --points 3 --json
```

**部署过程输出（非 JSON 模式）：**

```
正在查询可用 GPU 资源...
选中资源: 4090 x1 | 广东一区 | 1.05元/h (最低价)
正在创建任务 [my-llm]...
任务已创建, task_id=1926525
已启用自动释放: 3600s (~60.0分钟) 后停止 (pid=12345)
  取消: kill 12345
等待任务启动...
  [Pulling] Pulling image "harbor.suanleme.cn/public-hub/vllm-openai:v0.19.0-copy"
  [Started] Started container istio-proxy
  [Pulled] Successfully pulled image
Running!
访问地址: https://deployment-452-xxx-8000.550w.link (端口 8000)
```

**JSON 输出：**

```json
{
  "task_id": 1926525,
  "status": "Running",
  "urls": [
    {"url": "https://deployment-452-xxx-8000.550w.link", "port": 8000}
  ],
  "ttl_seconds": 3600,
  "auto_release_pid": 12345
}
```

**拿到 URL 后调用：**

```bash
curl https://deployment-452-xxx-8000.550w.link/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-8B-FP8",
    "messages": [{"role": "user", "content": "hello"}]
  }'
```

---

### `list` — 列任务

```bash
gongji list                           # 运行中 + 待启动（默认）
gongji list -s Running                # 只看运行中
gongji list -s Running,Pending,Paused # 含暂停的
gongji list --json
```

**参数：**

| 参数 | 说明 | 默认 |
|------|------|------|
| `--status, -s` | 筛选状态（Running/Pending/Paused/End），逗号分隔 | `Running,Pending` |
| `--json, -j` | JSON 输出 | - |

**输出：**

```
[1926525] my-llm  Running  节点 1/1  4090 x1
  -> https://deployment-452-xxx-8000.550w.link (:8000)
[1926530] sd-svc  Pending  节点 0/1  4090 x1
```

**JSON：**

```json
[
  {
    "task_id": 1926525,
    "task_name": "my-llm",
    "status": "Running",
    "urls": [{"url": "https://...", "port": 8000}]
  }
]
```

---

### `status` — 任务详情

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
访问地址: https://deployment-452-xxx-8000.550w.link (端口 8000)
```

`已花费` 是到目前为止的累计扣费，按秒计算，实时更新。

---

### `logs` — 日志/事件

排查部署失败或运行异常：

```bash
gongji logs 1926525                # 查看容器日志
gongji logs 1926525 --events       # 查看事件（镜像拉取失败、OOM 等）
```

**参数：**

| 参数 | 说明 |
|------|------|
| `task_id` | 任务 ID（必填） |
| `--events, -e` | 查事件而非日志 |

**事件输出示例：**

```
=== deployment-452-xxx-74f56c675-pk8hf (Pending) ===
  [Warning] Failed: Error: ImagePullBackOff  (2026-04-13T10:00:00Z)
  [Normal] Pulling: Pulling image "my-image:v1"  (2026-04-13T09:59:55Z)
  [Normal] BackOff: Back-off pulling image  (2026-04-13T10:00:10Z)
```

事件里常见的 reason：
- `Pulling` / `Pulled` — 正常拉镜像
- `ImagePullBackOff` / `ErrImagePull` — 镜像拉失败（大概率地址错或内网拉不到）
- `OOMKilled` — 容器内存超限
- `CrashLoopBackOff` — 容器启动即崩溃

---

### `stop` — 停止/暂停/恢复

```bash
# 删除单个
gongji stop 1926525                # 删除（不可恢复，需确认）
gongji stop 1926525 -f             # 强制删除
gongji stop 1926525 -f --json      # Agent 调用

# 暂停 / 恢复（不会丢配置）
gongji stop 1926525 --pause        # 暂停（释放资源，可恢复）
gongji stop 1926525 --resume       # 恢复暂停的任务

# 批量
gongji stop --all                  # 批量删除所有任务（需确认）
gongji stop --all -f --json        # Agent 一键释放所有
# → {"stopped": [1, 2, 3], "failed": []}
```

**参数：**

| 参数 | 说明 |
|------|------|
| `task_id` | 任务 ID（与 `--all` 二选一） |
| `--all` | 批量删除所有 Running/Pending/Paused 任务 |
| `--pause` | 暂停（资源释放，配置保留） |
| `--resume` | 恢复暂停的任务 |
| `--force, -f` | 跳过确认 |
| `--json, -j` | JSON 输出 |

**单个 JSON：**

```json
{"task_id": 1926525, "action": "删除", "ok": true}
```

**批量 JSON：**

```json
{"stopped": [1926525, 1926530], "failed": []}
```

---

## 47 个预制模板完整清单

**全部来自共绩算力镜像仓库 `harbor.suanleme.cn`，在平台内网预缓存**，拉取快、开箱即用。

### 大语言模型推理（llm）· 10 个

| 模板名 | 镜像 | 端口 | 推荐硬件 |
|-------|------|------|---------|
| `vllm` | `vllm-openai:v0.19.0-copy` | 8000 | 4090 |
| `ollama` | `ollama:2025-10-30-rc1` | 11434 | 4090 |
| `qwen3.5-0.8b` | `vllm-openai:v2026-3-5-nightly` | 8000 | 4090 |
| `qwen3.5-9b` | `qwen35-9b:v0.17.0-rc1` | 8000 | 4090 |
| `qwen3.5-9b-claude` | `vllm-openai:v2026-3-5-nightly` | 8000 | 单卡 4090 |
| `qwen3.5-27b` | `vllm-openai:v2026-3-5-nightly` | 8000 | 4-8×4090 |
| `qwen3.5-27b-claude-gguf` | `vllm-openai:v2026-3-5-nightly` | - | 4×4090 |
| `qwen3-30b-webui` | `qwen3-32b:20250711` | 11434 | 单卡 4090 |
| `minicpm-4-8b` | `minicpm4-8b:latest` | 11434 | 单卡 4090 |
| `gpt-oss-20b` | `gpt-oss-20b:sglang` | 30000 | 4090 |

### 多模态视觉（multimodal）· 3 个

| 模板名 | 镜像 | 端口 | 推荐硬件 |
|-------|------|------|---------|
| `qwen3-8b-vl` | `vllm-openai:qwen3-8b-vl-...` | 8000 | 4090 |
| `minicpm-o-4.5` | `minicpm-o-4_5:2.0.0` | 8006 | 4090 |
| `hunyuan-image-3` | `hunyuanimage3:v1.0.0` | 30000 | 8×H20 |

### 文生图（image-gen）· 10 个

| 模板名 | 镜像 | 端口 |
|-------|------|------|
| `qwen-image` | `comfyui-qwen-image:8steps-loras-...` | 3000, 8188 |
| `qwen-image-2512` | `qwen-image-2512:v1.2-...` | 8188, 3000 |
| `z-image` | `z-image:0.11.0-...` | 8188, 3000 |
| `z-image-turbo` | `z_image_turbo:1.0.0-...` | 8188, 3000 |
| `flux2-dev` | `flux2:2.0.1-...` | 8188, 3000 |
| `flux1-krea` | `comfyui-krea:0.2` | 3000, 8188 |
| `flux1-dev-comfyui` | `comfyui-flux:0.5` | 3000, 8188 |
| `sd3.5-comfyui` | `comfyui-sd:v3.5-1` | 3000, 8188 |
| `sd2.1-webui` | `lightcloud/sd-webui:hsz...` | 7860 |
| `sd-webui` | `stable-diffusion-webui:v1`（SD 1.5） | 7860 |

### 图像编辑/人像（image-edit）· 8 个

| 模板名 | 镜像 | 端口 |
|-------|------|------|
| `qwen-image-layered` | `qwen-image-layered:1.2` | 7869 |
| `qwen-image-edit` | `comfyui-qwen-image-edit:0.2.2` | 3000, 8188 |
| `flux1-kontext` | `comfyui-kontext:0.3` | 3000, 8188 |
| `comfyui-facefusion` | `comfyui-facefusio-api:...` | 3000, 8188 |
| `facefusion` | `facefusion:0.1.0` | 7860 |
| `codeformer` | `codeformer:070718` | 7860 |
| `hunyuan-portrait` | `hyportrait:070714` | 8089 |
| `hivision-idphotos` | `hivision_idphotos:latest` | 7860, 8080 |

### 视频生成（video）· 3 个

| 模板名 | 镜像 | 端口 |
|-------|------|------|
| `wan2.2` | `wan-2.2:0.2` | 3000, 8188 |
| `wan2.2-i2v` | `wan2.2-14b:4steps-loras-...` | 3000, 8188 |
| `framepack-f1` | `framepack:0.4-f1` | 7860 |

### 3D 重建（3d）· 1 个

| 模板名 | 镜像 | 端口 |
|-------|------|------|
| `hunyuan-world-mirror` | `hunyuanworld-mirror:0.3.8` | 7860 |

### 语音合成/识别（audio）· 4 个

| 模板名 | 镜像 | 端口 |
|-------|------|------|
| `whisper` | `openai-whisper-asr-webservice:v1.8.2-gpu` | 9000 |
| `indextts` | `index-tts:0.3.0` | 7860 |
| `cosyvoice` | `cosyvoice:v2.0.0` | 7860 |
| `funasr` | `funasr-online-server:V070117` | 10095 |

### 音乐生成（music）· 2 个

| 模板名 | 镜像 | 端口 |
|-------|------|------|
| `acestep` | `acestep:1.0` | 7865 |
| `acestep-1.5` | `pytorch271-cuda128-ubuntu2204:acestep1.5-...` | 8888, 62661, 7860, 8001 |

### 文档解析/OCR（ocr）· 2 个

| 模板名 | 镜像 | 端口 |
|-------|------|------|
| `mineru` | `mineru:0.1.3` | 8000, 7860 |
| `paddleocr-vl` | `paddlex-genai-vllm-server:...` | 8080 |

### 开发环境（dev）· 3 个

| 模板名 | 镜像 | 端口 |
|-------|------|------|
| `ubuntu2404` | `ubuntu2404-base:2025-12-11-rc1` | 8888, 62661, 8000-8002 |
| `jupyter` | 同 `ubuntu2404` | 8888, 62661 |
| `llama-factory` | `llama-factory:hsz...` | 7860, 8000 |

### 工具类（tools）· 1 个

| 模板名 | 镜像 | 端口 |
|-------|------|------|
| `dailyhot` | `dailyhot:1.0` | 6688, 80 |

> 想看完整镜像地址、启动命令、环境变量、文档链接：`gongji images --json` 或查看 [docs/预制镜像清单.md](./docs/预制镜像清单.md)。

---

## 按分类一键部署手册

### 跑 LLM 推理

```bash
# 轻量：Qwen3.5-0.8B，边缘/低延时
gongji deploy --template qwen3.5-0.8b -n my-llm --ttl 3600 --json

# 主力：Qwen3.5-9B（最常用，单卡 4090）
gongji deploy --template qwen3.5-9b -n my-llm --ttl 3600 --json

# 大模型：Qwen3.5-27B（4×4090 或 8×4090）
gongji deploy --template qwen3.5-27b -n big-llm -c 8 --ttl 3600 --json

# 通用 vLLM：自己指定 model（覆盖默认启动命令）
gongji deploy --template vllm -n custom-llm \
  --start-args "-c 'vllm serve your-org/your-model --max-model-len 32K'"

# Ollama 服务
gongji deploy --template ollama -n ol --ttl 3600 --json
# 部署后进容器 pull 模型：ollama pull llama3.1
```

拿到 URL 调用：

```bash
URL="https://deployment-xxx.550w.link"
curl $URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-8B-FP8","messages":[{"role":"user","content":"hello"}]}'
```

### 生成图片

```bash
# Qwen-Image（阿里 20B 文生图）
gongji deploy --template qwen-image -n img-svc --json

# Flux.2（多参考图一致性）
gongji deploy --template flux2-dev -n flux --json

# SD 3.5 + ComfyUI
gongji deploy --template sd3.5-comfyui -n sd35 --json

# Flux.1 Krea（更真实，无 AI 味）
gongji deploy --template flux1-krea -n krea --json
```

### 生成视频

```bash
# 阿里 WAN 2.2（270 亿 MoE）
gongji deploy --template wan2.2 -n video --json

# 图生视频
gongji deploy --template wan2.2-i2v -n i2v --json
```

### 语音处理

```bash
# Whisper 语音识别
gongji deploy --template whisper -n asr --ttl 7200 --json

# IndexTTS 中英高质量 TTS
gongji deploy --template indextts -n tts --json

# CosyVoice 近真人合成
gongji deploy --template cosyvoice -n voice --json
```

### 文档解析 / OCR

```bash
# MinerU PDF → Markdown
gongji deploy --template mineru -n pdf-parse --ttl 14400 --json

# PaddleOCR-VL 轻量文档解析
gongji deploy --template paddleocr-vl -n ocr --json
```

### 开发 / 训练

```bash
# Ubuntu 24.04 + Jupyter + code-server
gongji deploy --template ubuntu2404 -n dev --json

# LLaMA Factory 无代码微调
gongji deploy --template llama-factory -n finetune --json
```

### 图像编辑 / 人像

```bash
# Qwen Image Edit
gongji deploy --template qwen-image-edit -n edit --json

# FaceFusion 换脸
gongji deploy --template facefusion -n face --json

# 证件照
gongji deploy --template hivision-idphotos -n idphoto --json

# 肖像动画
gongji deploy --template hunyuan-portrait -n portrait --json
```

### 3D 重建

```bash
gongji deploy --template hunyuan-world-mirror -n 3d --json
```

### 音乐生成

```bash
gongji deploy --template acestep -n music --json
```

---

## Python API

### 基础用法

```python
from gongjiskills import GongjiClient

client = GongjiClient()  # 自动读取 ~/.gongji/config.json
```

### 查资源

```python
res = client.search_resources()
# {"code": "0000", "data": {"results": [...]}}

for device in res["data"]["results"]:
    for region in device.get("regions", []):
        if region["inventory"] > 0:
            print(f"{device['gpu_name']} x{device['gpu_count']} "
                  f"| {region['region_name']} "
                  f"| {region['inventory']} "
                  f"| {region['discount_price'] * 3600 / 1e6:.2f} 元/h")
            break
```

### 用模板创建任务

```python
from gongjiskills.templates import BUILTIN_TEMPLATES
import time

# 1. 选模板
tmpl = BUILTIN_TEMPLATES["qwen3.5-9b"]

# 2. 挑资源
res = client.search_resources()
for device in res["data"]["results"]:
    if tmpl.get("gpu") and tmpl["gpu"] not in device["gpu_name"]:
        continue
    for region in device.get("regions", []):
        if region["inventory"] > 0:
            mark = region["mark"]["mark"]
            break
    else:
        continue
    break

# 3. 建任务
ports = [int(p) for p in tmpl["port"].split(",")]
task = client.create_task(
    task_name="my-llm",
    mark=mark,
    service_image=tmpl["image"],
    ports=ports,
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

# 6. 调用
import openai
ai = openai.OpenAI(base_url=f"{url}/v1", api_key="none")
resp = ai.chat.completions.create(
    model="Qwen/Qwen3.5-9B",
    messages=[{"role": "user", "content": "hello"}]
)

# 7. 释放
client.stop_task(task_id)
```

### 异常处理

```python
from gongjiskills.client import GongjiError

try:
    res = client.create_task(...)
except GongjiError as e:
    # 网络错误 / API 错误已被友好化
    print(f"部署失败: {e}")
```

### 查日志 / 事件

```python
# 节点列表
points = client.list_points(task_id)["data"]["results"]
point_id = points[0]["point_id"]

# 事件（排查失败）
events = client.pod_event(point_id)["data"]["events"]
for ev in events:
    print(f"[{ev['type']}] {ev['reason']}: {ev['message']}")

# 容器日志
service_id = detail["data"]["services"][0]["service_id"]
logs = client.point_log(task_id, point_id, service_id)["data"]["logs"]
print(logs)
```

### 完整 API 列表

| 方法 | 说明 |
|------|------|
| `search_resources()` | 查所有可用 GPU 资源 |
| `create_task(...)` | 创建任务 |
| `task_detail(task_id)` | 任务详情 |
| `search_tasks(status=...)` | 查询任务列表 |
| `pause_task(task_id)` | 暂停任务 |
| `recover_task(task_id)` | 恢复暂停的任务 |
| `stop_task(task_id)` | 删除任务 |
| `update_task(body)` | 更新任务配置 |
| `list_points(task_id)` | 节点列表 |
| `point_log(task_id, point_id, service_id)` | 节点日志 |
| `pod_event(point_id)` | 节点事件 |

详见源码 `gongjiskills/client.py`。

---

## 在 Claude Code 中使用

项目自带 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill 定义（`skills/gongji.md`）。

### 配置方式

把 `skills/gongji.md` 复制到 Claude Code 的 skills 目录，或者在项目根目录保留让 Claude Code 自动发现。

### 自然语言示例

直接对 Claude Code 说：

- "帮我部署一个 4090 跑 Qwen 推理" → `gongji deploy --template qwen3.5-9b -n xxx --ttl 3600 --json`
- "开个 ComfyUI 到广东区域" → `gongji deploy --template flux1-dev-comfyui -n xxx -r 广东 --json`
- "看看我现在有哪些任务在跑" → `gongji list --json`
- "任务 1926525 花了多少钱" → `gongji status 1926525 --json`
- "把任务停掉" → `gongji stop <id> -f --json`
- "跑个 Whisper 语音识别，1 小时后关" → `gongji deploy --template whisper -n xxx --ttl 3600 --json`
- "列出所有 LLM 模板" → `gongji images --category llm --json`

Agent 会自动走：
1. 用户说需求 → Claude 理解意图
2. 必要时 `gongji images categories` / `--category` 找合适模板
3. `gongji deploy --template <name> -n xxx --ttl 3600 --json` 部署
4. 返回 URL 给用户，或直接 `curl` 调用

---

## Agent / JSON 契约

所有命令都支持 `--json`。**Agent 调用时务必加上**。

### 成功输出

```bash
# deploy
gongji deploy --template vllm -n svc --json
# → {"task_id": 1926525, "status": "Running",
#    "urls": [{"url": "https://xxx", "port": 8000}],
#    "ttl_seconds": 3600, "auto_release_pid": 12345}

# list
gongji list --json
# → [{"task_id": 1926525, "task_name": "svc", "status": "Running",
#     "urls": [{"url": "https://xxx", "port": 8000}]}]

# status
gongji status 1926525 --json
# → 完整的任务详情 JSON（包含 resources/services/billing_value 等）

# stop 单个
gongji stop 1926525 -f --json
# → {"task_id": 1926525, "action": "删除", "ok": true}

# stop 批量
gongji stop --all -f --json
# → {"stopped": [1926525, 1926530], "failed": []}

# images
gongji images --json
# → {"vllm": {"image": "...", "category": "llm", ...}, ...}

# categories
gongji images categories --json
# → {"llm": 10, "image-gen": 10, "video": 3, ...}

# resources
gongji resources --json
# → [{"gpu_name": "4090", "gpu_count": 1, "regions": [...]}, ...]
```

### 失败输出

所有失败都是 `{"error": "..."}`，exit code 1：

```bash
gongji deploy --template not-exist -n svc --json
# → {"error": "模板 [not-exist] 不存在，用 gongji images 查看可用模板"}
# exit 1

gongji deploy bad-image -n svc --json
# → {"error": "查询资源失败: token expired"}
# exit 1
```

### Agent 调用模板

```python
import json, subprocess

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
# {"llm": 10, ...}

llm_templates = gongji("images", "--category", "llm")
# {"vllm": {...}, "qwen3.5-9b": {...}, ...}

# 部署
result = gongji("deploy", "--template", "qwen3.5-9b",
                "-n", "agent-task", "--ttl", "3600")
url = result["urls"][0]["url"]

# 用完释放
gongji("stop", str(result["task_id"]), "-f")
```

---

## 可靠性与错误处理

### 自动重试

瞬时错误自动重试 2 次（指数退避 1s → 2s）：

- 连接失败（`ConnectionError`）
- 请求超时（`Timeout`，30s）
- HTTP 5xx（500/502/503/504）

Agent 不需要自己写重试。

### 友好错误映射

底层 API 错误码被翻译成中文 + 修复建议：

| 原始错误 | 翻译 + 建议 |
|---------|-----------|
| `token expired` | "Token 已失效，请登录 https://www.gongjiyun.com 重新生成，再运行: `gongji init --force`" |
| `signature invalid` | "签名验证失败：公钥可能未上传到控制台，检查 `~/.gongji/public.pem` 是否与平台一致" |
| `not found` | "资源不存在，用 `gongji list` 确认 task_id 是否正确" |
| `insufficient balance` | "账户余额不足，请前往控制台充值后重试" |
| `inventory not enough` | "库存不足，换个区域或 GPU 型号重试（`gongji resources` 查看库存）" |

### 部署等待

`deploy` 默认等到 `Running` 才返回（最多 5 分钟，每 5 秒轮询一次）：

- 连续 3 次查询失败才报错（防网络抖动）
- 任务进入 `End` / `Other` 异常状态 → **自动拉取失败原因**并输出
- 超时 → 提示手动用 `gongji status <id>` 检查

### TTL 守护

`--ttl` 启动独立子进程：

```python
# cli.py 内部实现示意
subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(ttl); stop_task(tid)"],
    start_new_session=True,  # 独立进程组
    stdout=log_file, stderr=log_file,
)
```

- CLI 退出不影响
- 日志在 `~/.gongji/ttl/<task_id>.log`
- PID 在 `~/.gongji/ttl/<task_id>.pid`
- 手动取消：`kill <pid>`

---

## 安全

### 凭据保护

| 文件 | 权限 | 说明 |
|------|------|------|
| `~/.gongji/` | `700` | 仅当前用户可访问 |
| `~/.gongji/private.key` | `600` | RSA 私钥 |
| `~/.gongji/config.json` | `600` | 含 token |
| `~/.gongji/public.pem` | `644` | 公钥（不敏感） |

加载配置时**自动检测权限**，过宽时输出警告和修复命令：

```
⚠️  警告：~/.gongji/private.key 权限过宽 (644)，可能被其他用户读取
  修复：chmod 600 ~/.gongji/private.key
```

### Token 传入方式（按安全性）

1. **环境变量**（最推荐）：`GONGJI_TOKEN=xxx gongji init --force`
2. **stdin 管道**：`echo $TOKEN | gongji init --force`
3. **命令行参数**：`gongji init --token xxx`（会进 shell history）
4. **交互输入**：默认情况，终端打星号

### RSA 签名

每次请求都签名：

```
sign_string = f"{path}\n{version}\n{timestamp}\n{token}\n{body}"
signature = RSA_PKCS1v15_SHA256(private_key, sign_string)
```

- `timestamp` 每次不同，防重放
- 请求不可伪造（签名必须由私钥生成，私钥只在客户端本地）

---

## 成本控制

**按秒计费的现实：** 一个 4×4090 任务忘了关一晚上 ≈ ¥96。三道防护：

### 1. `--ttl` 强制到期释放

```bash
# 一次性任务默认加 --ttl 3600（1 小时）
gongji deploy --template vllm -n tmp --ttl 3600 --json
```

### 2. `gongji status <id>` 实时看花费

```
已花费:   36.44 元
```

### 3. `gongji stop --all` 一键全关

```bash
gongji stop --all -f --json
# → {"stopped": [1, 2, 3], "failed": []}
```

### 推荐实践

- **Agent 永远带 `--ttl`**，默认 1 小时
- **shell alias**：`alias gcs="gongji stop --all -f"`
- **CI 场景**：`finally` / `trap` 里一定调 `stop`
- **定时清理**：cron 每天 `gongji list --json` 报警未释放任务

---

## 项目结构

```
gongjiskills/
├── README.md                # 这份文档
├── LICENSE                  # MIT
├── setup.py / pyproject.toml  # Python 打包配置
├── requirements.txt         # 依赖
├── install.sh               # 一键安装脚本
├── gongji.py                # 兼容入口（python3 gongji.py xxx）
│
├── gongjiskills/            # Python 包
│   ├── __init__.py          # 导出 GongjiClient
│   ├── auth.py              # RSA-SHA256 签名 + 权限检查
│   ├── client.py            # API 客户端 + 网络错误处理 + 重试
│   ├── cli.py               # CLI 实现（8 个命令）
│   └── templates.py         # 47 个内置模板 + 分类
│
├── tests/                   # pytest 测试
│   ├── test_cli.py          # CLI 参数解析 + JSON 契约 + 分类
│   └── test_auth.py         # 签名验证 + 配置加载
│
├── skills/
│   └── gongji.md            # Claude Code Skill 定义
│
└── docs/                    # 补充文档
    ├── 介绍.md              # 完整介绍（给别人看）
    └── 预制镜像清单.md      # 46 个平台预制镜像详细清单
```

---

## 开发与测试

```bash
# 本地开发
git clone https://github.com/shaozheng0503/gongjiskills.git
cd gongjiskills
pip install -e .

# 跑测试（34 个）
python3 -m pytest tests/ -v

# 只跑 CLI 测试
python3 -m pytest tests/test_cli.py -v

# 只跑签名测试
python3 -m pytest tests/test_auth.py -v
```

### 添加新的内置模板

1. 编辑 `gongjiskills/templates.py`
2. 在 `BUILTIN_TEMPLATES` 加新条目：
   ```python
   "my-template": {
       "image": "harbor.suanleme.cn/public-hub/xxx",
       "category": "llm",  # 选一个现有分类
       "description": "...",
       "port": "8000",
       "gpu": "4090",
       "env": "KEY=VAL",
       "start_cmd": "/bin/bash",
       "start_args": ["-c", "..."],
       "docs": "https://...",
   },
   ```
3. 跑测试 `python3 -m pytest tests/test_cli.py -v`

测试会自动断言：
- 所有模板的 `image` 必须以 `harbor.suanleme.cn/` 开头（防止误加上游假镜像）
- 所有模板必须有合法的 `category`

---

## 常见问题（FAQ）

<details>
<summary><b>Q: 报错"配置文件不存在"</b></summary>

运行 `gongji init` 初始化。详细步骤见 [快速开始](#快速开始)。
</details>

<details>
<summary><b>Q: 报错"token expired"</b></summary>

登录 [控制台](https://www.gongjiyun.com) 重新生成 API 密钥，然后 `gongji init --force`。
</details>

<details>
<summary><b>Q: 报错"签名验证失败 / signature invalid"</b></summary>

1. 检查 `~/.gongji/public.pem` 内容是否和控制台上传的一致
2. 检查系统时间是否准确（签名包含 timestamp，误差大于几分钟会失败）
3. 最后手段：`gongji init --force` 重新生成密钥对并上传新公钥
</details>

<details>
<summary><b>Q: 报错"权限过宽"</b></summary>

运行提示中的 `chmod` 命令修复，或重新 `gongji init --force`（会自动设置正确权限）。
</details>

<details>
<summary><b>Q: 部署后拿不到访问地址</b></summary>

1. 任务可能还在拉镜像（首次拉镜像可能 1-3 分钟）
2. `deploy` 默认等到 Running 才返回，如果超时了：`gongji status <id>` 看当前状态
3. 排查：`gongji logs <id> --events` 看事件（镜像拉取失败 / OOM / 启动崩溃）
</details>

<details>
<summary><b>Q: 部署失败，报 ImagePullBackOff</b></summary>

平台拉不到镜像。常见原因：
1. **用了上游 docker hub / ghcr 的镜像地址** → 换用 `gongji images` 里的预制模板（只用 `harbor.suanleme.cn/*`）
2. 镜像地址拼错 → 仔细检查
3. 私有镜像没授权 → 用 Python API `create_task(repository_username=..., repository_password=...)`
</details>

<details>
<summary><b>Q: 怎么指定 GPU 卡数和区域</b></summary>

```bash
gongji deploy --template xxx -n svc -g 4090 -c 4 -r 广东
#                              型号      卡数   区域
```
</details>

<details>
<summary><b>Q: 怎么看已经花了多少钱</b></summary>

`gongji status <id>` 会显示累计花费（精确到秒）。
</details>

<details>
<summary><b>Q: 怎么传复杂的启动命令（带引号、环境变量、命令替换）</b></summary>

两种方式：

```bash
# 方式 1：命令行
gongji deploy <image> -n svc \
  --env "FOO=bar BAZ=qux" \
  --start-cmd "/bin/bash" \
  --start-args "-c 'vllm serve model --port 8000'"
```

```python
# 方式 2：自定义模板（推荐，长命令放 JSON 里更稳）
gongji images add my-custom \
  --image harbor.suanleme.cn/xxx \
  --start-cmd /bin/bash \
  --start-args "-c 'vllm serve ...'"
gongji deploy --template my-custom -n svc
```
</details>

<details>
<summary><b>Q: `--ttl` 在什么情况下会失效</b></summary>

守护进程是普通子进程，下面情况会丢：
- 机器关机 / 重启
- 账户注销 / logout
- 进程被 `kill`
- 磁盘写满导致进程 crash

**建议重要任务做二次保险**：cron 里定时 `gongji stop <id>`，或在代码的 `finally` 里兜底。
</details>

<details>
<summary><b>Q: 能挂载持久化存储吗</b></summary>

能。CLI 目前没暴露这个参数，需走 Python API：

```python
client.create_task(
    ...,
    storage_config=[{"mount_path": "/data", "size_gb": 50}],
    share_storage_config=[{"mount_path": "/shared", "storage_id": "xxx"}],
)
```
</details>

<details>
<summary><b>Q: 怎么切换多账号</b></summary>

目前 `~/.gongji/` 是硬编码。一个变通方式是用不同用户跑。需求强烈可以提 Issue，加环境变量 `GONGJI_DIR` 支持。
</details>

<details>
<summary><b>Q: pip install 报 "cryptography 安装失败"</b></summary>

macOS 上常见。先装系统依赖：

```bash
# macOS
brew install openssl rust
export LDFLAGS="-L$(brew --prefix openssl)/lib"
export CPPFLAGS="-I$(brew --prefix openssl)/include"

# Ubuntu/Debian
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
```

然后重试 `pip install`。
</details>

<details>
<summary><b>Q: 能部署多节点（多副本）吗</b></summary>

能：

```bash
gongji deploy --template whisper -n asr-cluster --points 3 --json
```

但要**模板本身支持多节点**（描述里不带"单节点"字样）。平台会自动负载均衡。
</details>

---

## License

MIT — 见 [LICENSE](./LICENSE)

---

## 反馈 / 贡献

- 使用中遇到问题 → [提 Issue](https://github.com/shaozheng0503/gongjiskills/issues)
- 想加预制镜像 → 告诉镜像 ID，我补到 `templates.py`
- 想扩展 Python API → 看 `client.py`，欢迎 PR
- 想做 Web UI / Dashboard → 基于 Python API 开发即可

如果这个工具省了你的时间，欢迎点 Star ⭐
