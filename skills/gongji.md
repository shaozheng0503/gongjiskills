# /gongji — 共绩算力弹性部署

管理共绩算力 GPU 弹性部署任务。Agent 需要 GPU 算力时自动调用。

TRIGGER: 用户提到"部署"、"发布任务"、"GPU"、"算力"、"共绩"、"弹性部署"、"跑模型"、"推理服务"、"vLLM"、"ComfyUI"、"Stable Diffusion"、"Ollama"，或需要创建/管理 GPU 计算任务时触发。

## 命令速查

```bash
gongji init --token <token>                              # 初始化（或 GONGJI_TOKEN=xxx gongji init --force）
gongji resources --json                                  # 查GPU资源（支持 -g/-r 筛选）
gongji resources -g 4090 -r 广东 --json                  # 筛选: 4090 + 广东
gongji images --json                                     # 查内置镜像模板
gongji images add vllm --image <addr> --gpu 4090 -p 8000 # 添加自定义模板
gongji deploy <image> -n <name> -g <gpu> -c <卡数> -p <port> --json  # 部署
gongji deploy --template vllm -n my-llm --json           # 用模板部署（推荐）
gongji deploy <image> -n <name> --ttl 3600 --json        # TTL 自动释放（1小时后）
gongji list --json                                       # 列出任务+URL
gongji status <id> --json                                # 任务详情（含费用）
gongji logs <id>                                         # 容器日志
gongji logs <id> --events                                # 事件（排查失败）
gongji stop <id> -f                                      # 释放单个
gongji stop --all -f --json                              # 批量释放所有任务
```

## 内置镜像模板（开箱即用）

调用 `gongji images --json` 即可获取完整列表。常用：

| 名称 | 用途 | 默认端口 |
|------|------|----------|
| `vllm` | OpenAI 兼容 LLM 推理 | 8000 |
| `ollama` | Ollama 一键 LLM | 11434 |
| `tgi` | HuggingFace TGI | 80 |
| `xinference` | Xorbits 多模型推理 | 9997 |
| `comfyui` | 节点式图像生成 | 8188 |
| `sd-webui` | SD Automatic1111 | 7860 |
| `jupyter` | 数据科学 Notebook | 8888 |
| `pytorch` | PyTorch 训练环境 | 8888 |
| `ffmpeg` | FFmpeg 媒体处理（CPU） | 8080 |

**优先使用模板部署**，Agent 无需记忆镜像地址：
```bash
gongji deploy --template vllm -n my-llm --json
gongji deploy --template comfyui -n sd-svc -g 4090 --json
```

## Agent 调用关键点

1. **必须用 `--json`** 获取结构化输出
2. deploy 成功返回 `{"task_id": N, "status": "Running", "urls": [{"url": "https://...", "port": 8080}]}`
3. 错误也是 JSON: `{"error": "..."}`
4. deploy **自动选最便宜的有库存资源**，用 `-c` 指定卡数，`-r` 指定区域
5. 等待过程会显示实时事件，失败时自动输出原因
6. `gongji images` 无需配置文件，init 前也可使用
7. **强烈建议 `--ttl`**：防止忘记 stop 导致计费烧钱（一次性任务用 `--ttl 3600` 一小时）
8. 任务用完务必 `gongji stop <id> -f`，或 `gongji stop --all -f` 批量释放

## 典型 Agent 工作流

```bash
# A. 快速部署（最推荐：模板 + TTL）
gongji deploy --template vllm -n my-llm --ttl 3600 --json
# → {"task_id": 1926525, "status": "Running", "urls": [{"url": "https://xxx", "port": 8000}], "ttl_seconds": 3600}

# B. 用拿到的 URL 调推理
# curl https://xxx/v1/chat/completions ...

# C. 出问题查事件
gongji logs 1926525 --events

# D. 用完释放
gongji stop 1926525 -f --json
# 或一键释放所有:
gongji stop --all -f --json
```

## deploy 全部参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `<image>` | Docker 镜像地址 | 与 --template 二选一 |
| `-t, --template` | 镜像模板名（见 images） | - |
| `-n, --name` | 任务名 | 必填 |
| `-g, --gpu` | GPU 型号: 4090/H800 | 自动选最便宜 |
| `-c, --gpu-count` | GPU 卡数: 1/2/4/8 | 不限 |
| `-r, --region` | 区域: 广东/河南/河北 | 不限 |
| `-p, --port` | 端口（多个逗号分隔） | 8080 |
| `--points` | 节点数 | 1 |
| `--env` | 环境变量 | - |
| `--start-cmd` | 启动命令 | - |
| `--start-args` | 启动参数（引号包裹） | - |
| `--ttl` | 自动释放（秒） | 不自动释放 |
| `--no-wait` | 不等待就绪 | 等待 |
| `--json` | JSON 输出 | - |

## 错误处理

常见错误已自动映射为带修复建议的中文提示：
- Token 失效 → 提示重新生成 + `gongji init --force`
- 签名错误 → 提示检查公钥上传
- 库存不足 → 提示换区域/型号
- 余额不足 → 提示充值
- 网络超时/5xx → 自动重试 2 次（指数退避）

## 前置条件

配置不存在时：
```bash
gongji init --token <your-token>                         # 交互
GONGJI_TOKEN=xxx gongji init --force                     # 非交互（推荐 CI/Agent）
```

引导用户：https://www.gongjiyun.com → 头像 → API密钥 → RSA模式
