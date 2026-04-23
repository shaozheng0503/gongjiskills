# /gongji — 共绩算力弹性部署

管理共绩算力 GPU 弹性部署任务。Agent 需要 GPU 算力时自动调用。

TRIGGER: 用户提到"部署"、"发布任务"、"GPU"、"算力"、"共绩"、"弹性部署"、"跑模型"、"推理服务"、"vLLM"、"ComfyUI"、"Stable Diffusion"、"Ollama"、"Qwen"、"Flux"、"视频生成"、"TTS"、"语音识别"、"OCR"，或需要创建/管理 GPU 计算任务时触发。

## 命令速查

```bash
gongji init --token <token>                              # 初始化（或 GONGJI_TOKEN=xxx gongji init --force）
gongji resources --json                                  # 查GPU资源
gongji resources -g 4090 -r 广东 --json                  # 筛选: 4090 + 广东
gongji images --json                                     # 列出所有内置模板（按分类分组）
gongji images categories --json                          # 列出所有分类及数量 ★ Agent 先看这个
gongji images --category llm --json                      # 筛选某分类的模板
gongji images add my-vllm --image <addr> --gpu 4090 -p 8000  # 添加自定义模板
gongji deploy --template <name> -n <任务名> --json       # 用模板部署（推荐）
gongji deploy <image> -n <name> -g <gpu> -p <port> --json  # 直接用镜像部署
gongji deploy --template <name> -n <name> --ttl 3600 --json  # TTL 自动释放（1小时）
gongji list --json                                       # 列出任务+URL
gongji status <id> --json                                # 任务详情（含费用）
gongji logs <id>                                         # 容器日志
gongji logs <id> --events                                # 事件（排查失败）
gongji stop <id> -f                                      # 释放单个
gongji stop --all -f --json                              # 批量释放所有任务
```

## 内置模板库（全部来自平台预制镜像）

所有内置模板均指向平台镜像仓库 `harbor.suanleme.cn`，**已在平台内网预缓存**，拉取快、开箱即用。**不要自己编造 docker hub 或 ghcr.io 的镜像地址**，平台拉不到。

### 分类速览

| 分类 key | 中文名 | 常用模板 |
|---------|--------|---------|
| `llm` | 大语言模型推理 | `vllm` · `ollama` · `qwen3.5-9b` · `qwen3.5-27b` · `qwen3.5-0.8b` · `qwen3.5-9b-claude` · `qwen3-30b-webui` · `minicpm-4-8b` · `gpt-oss-20b` |
| `multimodal` | 多模态视觉 | `qwen3-8b-vl` · `minicpm-o-4.5` · `hunyuan-image-3` |
| `image-gen` | 文生图 | `qwen-image` · `qwen-image-2512` · `z-image` · `z-image-turbo` · `flux2-dev` · `flux1-krea` · `flux1-dev-comfyui` · `sd3.5-comfyui` · `sd2.1-webui` · `sd-webui`(SD1.5) |
| `image-edit` | 图像编辑/人像 | `qwen-image-layered` · `qwen-image-edit` · `flux1-kontext` · `facefusion` · `comfyui-facefusion` · `codeformer` · `hunyuan-portrait` · `hivision-idphotos` |
| `video` | 视频生成 | `wan2.2` · `wan2.2-i2v` · `framepack-f1` |
| `3d` | 3D 重建 | `hunyuan-world-mirror` |
| `audio` | 语音合成/识别 | `whisper` · `indextts` · `cosyvoice` · `funasr` |
| `music` | 音乐生成 | `acestep` · `acestep-1.5` |
| `ocr` | 文档解析/OCR | `mineru` · `paddleocr-vl` |
| `dev` | 训练/开发环境 | `ubuntu2404` · `jupyter`(同 ubuntu2404) · `llama-factory` |
| `tools` | 工具类 | `dailyhot` |

**按分类一键部署示例：**

```bash
gongji deploy --template qwen3.5-9b -n my-llm --ttl 3600 --json    # LLM
gongji deploy --template qwen-image -n my-img --json               # 文生图
gongji deploy --template wan2.2 -n my-video --json                 # 视频生成
gongji deploy --template whisper -n asr --json                     # 语音识别
gongji deploy --template mineru -n pdf-parse --json                # PDF 解析
gongji deploy --template ubuntu2404 -n dev --json                  # 开发环境（Jupyter + code-server）
```

模板会自动带上：镜像地址、端口、推荐 GPU、GPU 卡数（如需）、环境变量、启动命令和参数。命令行参数会覆盖模板默认值。

## Agent 推荐工作流

**按需求选镜像的标准流程：**

```
用户说"帮我部署 X"
  ↓
1. gongji images categories --json         # 先看分类大纲
  ↓
2. gongji images --category <匹配的分类> --json  # 在分类里选模板
  ↓
3. gongji deploy --template <name> -n <任务名> --ttl 3600 --json  # 部署
```

**映射关系（Agent 选模板的参考）：**
- "跑 Qwen / 跑 LLM / 推理" → `llm` 分类
- "生成图 / 文生图 / 画图 / SD / Flux" → `image-gen` 分类
- "修图 / 换脸 / 证件照 / 修复" → `image-edit` 分类
- "生成视频 / 图生视频" → `video` 分类
- "3D 建模 / 场景重建" → `3d` 分类
- "语音识别 / ASR / TTS / 语音合成" → `audio` 分类
- "生成音乐 / 作曲" → `music` 分类
- "PDF 解析 / OCR / 文档提取" → `ocr` 分类
- "Jupyter / 训练 / 微调" → `dev` 分类

## Agent 调用关键点

1. **必须用 `--json`** 获取结构化输出
2. deploy 成功返回 `{"task_id": N, "status": "Running", "urls": [{"url": "https://...", "port": 8080}]}`
3. 错误也是 JSON: `{"error": "..."}`
4. deploy **自动选最便宜的有库存资源**，用 `-c` 指定卡数，`-r` 指定区域
5. 等待过程会显示实时事件，失败时自动输出原因
6. `gongji images` 无需配置文件，init 前也可使用
7. **强烈建议 `--ttl`**：防止忘记 stop 导致计费烧钱（一次性任务用 `--ttl 3600` 一小时）
8. 任务用完务必 `gongji stop <id> -f`，或 `gongji stop --all -f` 批量释放
9. **不要使用 docker hub / ghcr.io 的上游镜像地址**，平台内网拉不到 — 只用 `gongji images` 里的模板

## 典型 Agent 工作流

```bash
# A. 最推荐：看分类 → 挑模板 → TTL 部署
gongji images categories --json
gongji images --category llm --json      # 用户要 LLM
gongji deploy --template qwen3.5-9b -n my-llm --ttl 3600 --json
# → {"task_id": 1926525, "status": "Running", "urls": [{"url": "https://xxx", "port": 8000}], "ttl_seconds": 3600}

# B. 用拿到的 URL 调推理
# curl https://xxx/v1/chat/completions -d '{"model":"Qwen/Qwen3.5-9B", ...}'

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
| `-g, --gpu` | GPU 型号: 4090/H800/H20 | 模板值 或 自动选最便宜 |
| `-c, --gpu-count` | GPU 卡数: 1/2/4/8 | 模板值 或 不限 |
| `-r, --region` | 区域: 广东/河南/河北 | 不限 |
| `-p, --port` | 端口（多个逗号分隔） | 模板值 或 8080 |
| `--points` | 节点数 | 1 |
| `--env` | 环境变量 | 模板值 |
| `--start-cmd` | 启动命令 | 模板值 |
| `--start-args` | 启动参数（引号包裹） | 模板值 |
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
