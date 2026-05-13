# 共绩算力 Skills

[![GitHub stars](https://img.shields.io/github/stars/shaozheng0503/gongjiskills?style=social)](https://github.com/shaozheng0503/gongjiskills/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-34%20passed-brightgreen)](./tests)
[![Made for Claude Code](https://img.shields.io/badge/Made%20for-Claude%20Code-orange)](https://docs.anthropic.com/en/docs/claude-code)
[![Templates](https://img.shields.io/badge/Prebuilt-47%20templates-purple)](#5-47-个预制模板完整清单)

> **粘一句话给你的 AI Agent，它自己开 GPU 跑 LLM / 出图 / 转视频，按秒计费、用完自动释放。**

## 30 秒看懂

**你说**：

> 用 z-image 给我画一张赛博朋克东京街头，1 小时后自动关。

**Agent 自动跑**：

```bash
$ gongji deploy --template z-image -n zimg --ttl 3600 --json
{"task_id": 1926601, "status": "Running",
 "urls": [{"url": "https://abc-8188.550c.cloud", "port": 8188}],
 "ttl_seconds": 3600}
```

拿到 URL → 调 ComfyUI 出图 → 1 小时后任务自动停。**全程零控制台、零手动释放、按秒计费**。

---

**适用对象**：Claude Code / Cursor / OpenCode / Codex CLI / Cline / 自研 Agent —— 任何能执行 bash 的 AI Agent。

**核心卖点**：47 个预制镜像 · 11 个分类 · CLI + Python API + Claude Code Skill · TTL 自动释放 · JSON 契约 · 智能选最便宜资源

**相关文档**：
[共绩官网](https://www.gongjiyun.com) ·
[Open API](https://www.gongjiyun.com/docs/platform/openapi/zx3iwhbv1i8sxdkeiapcprxhn8d/) ·
[CLI 参数](./docs/cli-reference.md) ·
[Python API](./docs/python-api.md) ·
[安全](./docs/security.md) ·
[开发](./docs/development.md) ·
[Claude Code](./docs/claude-code.md)

---

## 目录

- [0. 一次性准备](#0-一次性准备仅首次)
- [1. 安装与初始化](#1-安装与初始化agent-第一次听到你说话时做的事)
- [2. Agent 调用协议速览](#2-agent-调用协议速览)
- [3. 典型调用场景](#3-典型调用场景粘给-agent-即可)
  - [A · Z-Image 文生图](#场景-a--z-image-文生图)
  - [B · Qwen3.5-9B LLM 推理](#场景-b--qwen35-9b-llm-推理服务)
  - [C · LLM + Image 组合](#场景-c--llm--image-组合让-llm-写提示词--z-image-生成图)
  - [D · Qwen3-VL 多模态视觉](#场景-d--qwen3-vl-多模态视觉理解)
  - [E · Whisper 语音转文字](#场景-e--whisper-语音转文字)
  - [F · IndexTTS 文本转语音](#场景-f--indextts-文本转语音)
  - [G · MinerU 批量 PDF 解析](#场景-g--mineru-批量-pdf-解析为-markdown)
  - [H · WAN 2.2 文生视频](#场景-h--wan-22-文生视频--图生视频)
  - [I · FLUX.2 高质量出图](#场景-i--flux2-高质量文生图)
  - [J · Ubuntu + Jupyter 开发环境](#场景-j--ubuntu-开发环境--jupyter)
  - [K · LLaMA Factory 模型微调](#场景-k--llama-factory-模型微调)
  - [L · ACE-Step 音乐生成](#场景-l--ace-step-音乐生成)
- [4. 生产模板：PDF-QA 流水线](#4-生产模板pdf-qa-流水线)
- [5. 47 个预制模板完整清单](#5-47-个预制模板完整清单)
- [6. Agent 一行指令参考表](#6-agent-一行指令参考表)
- [7. 任务管理与释放](#7-任务管理与释放)
- [8. 省钱与稳定性建议](#8-省钱与稳定性建议)
- [9. 常见问题](#9-常见问题)
- [附：速查一行命令](#附速查一行命令)

---

## 0. 一次性准备（仅首次）

你只需要做两件事：

1. 在 [共绩算力官网](https://www.gongjiyun.com) 注册账号并充值 ¥10–20（足够体验所有场景）。
2. 打开：头像 → API 密钥 → **RSA 模式** → 新建，拿到一串 token。

把 token 先留着，后面让 Agent 用它初始化。

**你不需要装 Python、不需要装 Docker、不需要开 VPN。** 全部由 Agent 在第一条消息里自动搞定。

---

## 1. 安装与初始化（Agent 第一次听到你说话时做的事）

**粘给 Agent**：

```text
请帮我安装 https://github.com/shaozheng0503/gongjiskills 这个 Skill。

步骤：
1. 用一键安装脚本：
   curl -fsSL https://raw.githubusercontent.com/shaozheng0503/gongjiskills/main/install.sh | bash
2. 用我提供的 token 初始化（非交互模式）：
   GONGJI_TOKEN=<粘这里> gongji init --force
3. 跑 `gongji resources --json` 验证一下，看到 GPU 列表就算成功。
4. 之后所有涉及 GPU / LLM / 生图 / 视频 / 语音 的请求都用 `gongji` CLI 完成，
   并且务必加 `--ttl 3600` 避免忘记释放烧钱。

我的 token 是：<把你的 RSA token 粘在这里>
```

**Agent 实际会跑的命令：**

```bash
curl -fsSL https://raw.githubusercontent.com/shaozheng0503/gongjiskills/main/install.sh | bash
GONGJI_TOKEN="eyJhbGciOi..." gongji init --force
gongji resources --json | head -50
```

看到类似 `{"gpu_name":"4090","regions":[{"region":"广东","price":...}]}` 就是装好了。

---

## 2. Agent 调用协议速览

Agent 和 CLI 之间通过 JSON 契约通信，**所有命令都要加 `--json`**。

| 命令 | 作用 | 返回关键字段 |
|------|------|------------|
| `gongji images categories --json` | 列所有分类 | `{"llm":10,"image-gen":10,...}` |
| `gongji images --category <k> --json` | 列分类下模板 | `{"vllm":{...},"qwen3.5-9b":{...}}` |
| `gongji resources --json` | 查 GPU 库存价格 | `[{"gpu_name":"4090","regions":[...]}]` |
| `gongji deploy --template <t> -n <name> --ttl 3600 --json` | 开一台 GPU 跑服务 | `{"task_id":...,"status":"Running","urls":[...]}` |
| `gongji status <id> --json` | 任务详情（含费用） | `{"status":"Running","billing_value":...}` |
| `gongji logs <id>` | 容器日志 | 纯文本 |
| `gongji logs <id> --events` | 事件（排查失败） | 纯文本 |
| `gongji stop <id> -f --json` | 释放单个任务 | `{"ok":true}` |
| `gongji stop --all -f --json` | 一键释放全部 | `{"stopped":[...],"failed":[]}` |

**Agent 工作三件套：**

1. 开服务 → 拿 `urls[0].url`
2. 用 curl 或 SDK 调用这个 URL
3. 用完 `gongji stop <task_id> -f`

> 失败统一格式：`{"error": "..."}`，exit code 1。完整 CLI 参数见 [docs/cli-reference.md](./docs/cli-reference.md)。

---

## 3. 典型调用场景（粘给 Agent 即可）

下面每个场景都给出：**用户原话** + **Agent 会执行的命令** + **调用示例**。

---

### 场景 A · Z-Image 文生图

**用户原话**：

```text
用 z-image 给我生成一张图："赛博朋克风格的雨夜东京街头，霓虹招牌倒映在积水里，镜头仰角"。
用共绩算力的 gongji CLI 部署，TTL 1 小时，拿到 URL 后直接在 ComfyUI API 上跑一次出图，
把图下载到 ./out/cyberpunk.png，最后停掉任务。
```

**Agent 执行**：

```bash
gongji deploy --template z-image -n zimg --ttl 3600 --json
```

返回：

```json
{
  "task_id": 1926601,
  "status": "Running",
  "urls": [
    {"url": "https://abc-3000.550c.cloud", "port": 3000},
    {"url": "https://abc-8188.550c.cloud", "port": 8188}
  ]
}
```

- **3000 端口**：Web 界面（浏览器直接打开 ComfyUI 可视化）
- **8188 端口**：ComfyUI 的 API 入口

**调用示例**（ComfyUI API）：

```bash
BASE=https://abc-8188.550c.cloud
curl -sS -X POST "$BASE/prompt" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": {
      "3": {"class_type": "KSampler", "inputs": {"seed": 42, "steps": 8, "cfg": 1.0}},
      "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "cyberpunk Tokyo street, rainy night, neon reflections, low angle"}}
    }
  }'
```

更简单：浏览器打开 `https://abc-3000.550c.cloud`，在 ComfyUI 里出图。

**释放**：

```bash
gongji stop 1926601 -f --json
```

> 💡 追求极速（16GB 消费卡也能跑、8 步亚秒级），把模板换成 `z-image-turbo`。

---

### 场景 B · Qwen3.5-9B LLM 推理服务

**用户原话**：

```text
帮我开一个 qwen3.5-9b 的 LLM 推理服务（vLLM，OpenAI 兼容），TTL 1 小时。
拿到 URL 后用 OpenAI Python SDK 跑一个对话："用三句话解释 Transformer 的自注意力"。
最后停掉任务。
```

**Agent 执行**：

```bash
gongji deploy --template qwen3.5-9b -n qwen-llm --ttl 3600 --json
```

返回：

```json
{
  "task_id": 1926602,
  "status": "Running",
  "urls": [{"url": "https://xyz-8000.550c.cloud", "port": 8000}]
}
```

**调用方式 1 · curl**：

```bash
BASE=https://xyz-8000.550c.cloud
curl -sS "$BASE/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3.5-9B",
    "messages": [{"role":"user","content":"用三句话解释 Transformer 的自注意力"}],
    "max_tokens": 256
  }'
```

**调用方式 2 · OpenAI Python SDK**（推荐）：

```python
from openai import OpenAI

client = OpenAI(base_url="https://xyz-8000.550c.cloud/v1", api_key="none")
resp = client.chat.completions.create(
    model="Qwen/Qwen3.5-9B",
    messages=[{"role": "user", "content": "用三句话解释 Transformer 的自注意力"}],
)
print(resp.choices[0].message.content)
```

**调用方式 3 · 配进别的 Agent**（当 OpenAI API 用）：

```bash
export OPENAI_BASE_URL="https://xyz-8000.550c.cloud/v1"
export OPENAI_API_KEY="none"
export OPENAI_MODEL="Qwen/Qwen3.5-9B"
```

之后任何支持 OpenAI 协议的客户端（Cherry Studio / Chatbox / OpenWebUI / LangChain / LlamaIndex）都能直连这台 GPU。

**释放**：

```bash
gongji stop 1926602 -f --json
```

> 💡 更强推理 → `qwen3.5-27b`（4×4090 或 8×4090）；更便宜 → `qwen3.5-0.8b`。

---

### 场景 C · LLM + Image 组合（让 LLM 写提示词 → Z-Image 生成图）

**用户原话**：

```text
我想做一个"一句话出图"的流水线：
1. 用 qwen3.5-9b 把中文描述扩写成高质量英文 SD 提示词；
2. 用 z-image 按这个提示词出 4 张图；
3. 下载到 ./out/ 并打印文件路径；
4. 两个 GPU 任务都 --ttl 1800，结束时 gongji stop --all -f。

我的描述："夏日黄昏的海边小镇，暖色调，胶片质感"
```

**Agent 执行（骨架）**：

```bash
LLM=$(gongji deploy --template qwen3.5-9b -n prompt-llm --ttl 1800 --json)
IMG=$(gongji deploy --template z-image    -n zimg       --ttl 1800 --json)

LLM_URL=$(echo "$LLM" | jq -r '.urls[0].url')
IMG_URL=$(echo "$IMG" | jq -r '.urls[] | select(.port==8188) | .url')

PROMPT_EN=$(curl -sS "$LLM_URL/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{"model":"Qwen/Qwen3.5-9B","messages":[{"role":"user","content":"扩写为英文 SD 提示词：夏日黄昏的海边小镇，暖色调，胶片质感"}]}' \
  | jq -r '.choices[0].message.content')

echo "Prompt: $PROMPT_EN"
# 然后调 ComfyUI API 出图（略）...

gongji stop --all -f --json
```

---

### 场景 D · Qwen3-VL 多模态视觉理解

**用户原话**：

```text
部署 qwen3-8b-vl（Qwen3-VL 视觉语言模型），TTL 1 小时。
拿到 URL 后，给这张图 https://example.com/cat.jpg 生成一段中文描述。结束后停任务。
```

**Agent 执行**：

```bash
gongji deploy --template qwen3-8b-vl -n vlm --ttl 3600 --json
```

**调用**（OpenAI 协议多模态消息）：

```bash
curl -sS "$BASE/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-VL-8B-Instruct-FP8",
    "messages": [{
      "role": "user",
      "content": [
        {"type":"image_url","image_url":{"url":"https://example.com/cat.jpg"}},
        {"type":"text","text":"用中文详细描述这张图片"}
      ]
    }]
  }'
```

---

### 场景 E · Whisper 语音转文字

**用户原话**：

```text
帮我把 ./meeting.mp3 转成文字。用 gongji 部署 whisper，TTL 1 小时，转完停任务。
```

**Agent 执行**：

```bash
gongji deploy --template whisper -n asr --ttl 3600 --json
# → URL 端口 9000

curl -sS -X POST "$BASE/asr?task=transcribe&language=zh&output=txt" \
  -F "audio_file=@./meeting.mp3" \
  -o meeting.txt

gongji stop <task_id> -f --json
```

---

### 场景 F · IndexTTS 文本转语音

**用户原话**：

```text
用 indextts 把 "欢迎使用共绩算力弹性 GPU" 合成为语音，保存 welcome.wav。
```

**Agent 执行**：

```bash
gongji deploy --template indextts -n tts --ttl 1800 --json
# → 端口 7860 的 Gradio / API 界面
```

IndexTTS 默认通过 Gradio WebUI 使用（浏览器打开 URL 直接合成）；如需脚本化：

```python
from gradio_client import Client

c = Client("https://xxx-7860.550c.cloud")
wav_path = c.predict(text="欢迎使用共绩算力弹性 GPU", api_name="/infer")
print(wav_path)
```

---

### 场景 G · MinerU 批量 PDF 解析为 Markdown

**用户原话**：

```text
帮我把 ./papers/ 目录下的 10 个 PDF 全部用 mineru 转成 Markdown，输出到 ./md/，最后停任务。
```

**Agent 执行**：

```bash
gongji deploy --template mineru -n pdf --ttl 3600 --json
# → 端口 8000 的 REST API

for f in ./papers/*.pdf; do
  name=$(basename "$f" .pdf)
  curl -sS -X POST "$BASE/file_parse" \
    -F "files=@$f" -F "return_md=true" \
    | jq -r '.md_content' > "./md/$name.md"
done

gongji stop <task_id> -f --json
```

---

### 场景 H · WAN 2.2 文生视频 / 图生视频

**用户原话**：

```text
用 wan2.2 帮我生成一段 5 秒视频："一只柯基在樱花树下奔跑，慢动作"。
TTL 1 小时，生成完下载到 ./out/corgi.mp4 并停任务。
```

**Agent 执行**：

```bash
gongji deploy --template wan2.2 -n video --ttl 3600 --json
# → 浏览器打开 URL 3000 端口即可使用 ComfyUI
# 或走 8188 API 投递工作流 JSON
```

> 💡 图生视频请改用 `wan2.2-i2v` 模板。

---

### 场景 I · FLUX.2 高质量文生图

**用户原话**：

```text
我要高质量出图，用 flux2-dev，TTL 1 小时。
提示词："a photorealistic portrait of an astronaut on Mars, golden hour"。
```

**Agent 执行**：

```bash
gongji deploy --template flux2-dev -n flux --ttl 3600 --json
# → 端口 3000 / 8188，使用方式同 z-image
```

---

### 场景 J · Ubuntu 开发环境 + Jupyter

**用户原话**：

```text
帮我开一台带 GPU 的 Jupyter 环境，TTL 2 小时。拿到 URL 后打印出来我自己去用。
```

**Agent 执行**：

```bash
gongji deploy --template jupyter -n dev --ttl 7200 --json
# → 8888 是 Jupyter，62661 是 code-server
```

---

### 场景 K · LLaMA Factory 模型微调

**用户原话**：

```text
我想用 LLaMA Factory 在 4090 上跑一次 LoRA 微调实验，TTL 4 小时。
拿到 URL 后我自己进 WebUI 配数据集和参数。
```

**Agent 执行**：

```bash
gongji deploy --template llama-factory -n finetune --ttl 14400 --json
# → 7860 Gradio WebUI，8000 API
```

进 7860 WebUI 即可可视化配训练、推理、合并 LoRA。微调产物挂载到平台共享存储或直接下载。

---

### 场景 L · ACE-Step 音乐生成

**用户原话**：

```text
用 acestep 给我生成一段 30 秒的电子舞曲，120 BPM。TTL 30 分钟。
```

**Agent 执行**：

```bash
gongji deploy --template acestep -n music --ttl 1800 --json
# → 7865 端口 Gradio
```

浏览器打开生成。如需脚本化，用 `gradio_client` 类似场景 F。

---

## 4. 生产模板：PDF-QA 流水线

如果你在构建一个真实产品（比如"PDF 问答机器人"），通常要同时拉起多个服务：

| 需求 | 模板 | 端口 |
|------|------|------|
| PDF 解析 | `mineru` | 8000 |
| 向量化 + LLM 问答 | `qwen3.5-9b` | 8000 |
| 多模态 OCR（含表格公式） | `paddleocr-vl` | 8080 |

**粘给 Agent**：

```text
帮我拉起一条 PDF-QA 流水线：
1. 部署 mineru（--ttl 7200，名字 pdf-parse）
2. 部署 qwen3.5-9b（--ttl 7200，名字 qa-llm）
3. 都成功后把两个 URL 写到 .env：MINERU_URL=xxx  LLM_URL=xxx
4. 写一个 run.py：用户输入问题 → 自动解析 ./docs/ 下 PDF 提取文本 → 作为 context 丢给 LLM → 返回答案
5. 今晚结束后帮我 gongji stop --all -f
```

Agent 会自动处理全部编排。

---

## 5. 47 个预制模板完整清单

**全部来自共绩算力镜像仓库 `harbor.suanleme.cn`，平台内网预缓存**，拉取快、开箱即用。

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

> 完整镜像地址、启动命令、环境变量、文档链接：`gongji images --json`，或查看 [docs/预制镜像清单.md](./docs/预制镜像清单.md)。

---

## 6. Agent 一行指令参考表

| 你想干什么 | 粘给 Agent 的话 |
|----------|--------------|
| 开个 LLM | `gongji 帮我部署 qwen3.5-9b，ttl 一小时，给我 OpenAI 接入地址` |
| 开个生图 | `gongji 帮我开 z-image-turbo，ttl 半小时，浏览器 URL 发我` |
| 开个 VLM | `gongji 部署 qwen3-8b-vl，ttl 一小时` |
| 开个 ASR | `gongji 部署 whisper，ttl 一小时，转 ./a.mp3` |
| 开个 TTS | `gongji 部署 indextts，ttl 一小时` |
| 开个视频 | `gongji 部署 wan2.2，ttl 两小时` |
| 开个 OCR | `gongji 部署 mineru，ttl 一小时，转 ./a.pdf` |
| 开个 Jupyter | `gongji 部署 jupyter，ttl 两小时` |
| 微调一个模型 | `gongji 部署 llama-factory，ttl 四小时` |
| 列所有模板 | `gongji images --json` |
| 查 GPU 库存 | `gongji resources --json` |
| 看花了多少钱 | `gongji status <id> --json` 看 `billing_value` |
| 释放所有 | `gongji stop --all -f --json` |

---

## 7. 任务管理与释放

```bash
gongji list --json                 # 当前在跑的任务
gongji status <id> --json          # 某个任务的详情 + 当前花费
gongji logs <id>                   # 看容器日志
gongji logs <id> --events          # 看调度事件（排查启动失败）
gongji stop <id> -f --json         # 释放单个
gongji stop --all -f --json        # 一键全部释放
```

**强烈建议 Agent 每次 deploy 都带 `--ttl`**，即便忘记 stop，也会到时间自动释放。

完整参数见 [docs/cli-reference.md](./docs/cli-reference.md)。

---

## 8. 省钱与稳定性建议

1. **永远带 `--ttl`**：一次性任务 `--ttl 3600`（1 小时），开发环境 `--ttl 7200`（2 小时）。按秒计费的现实是 4×4090 忘了关一晚上 ≈ ¥96。
2. **优先用 `-turbo` 系列**：同样效果，价格减半。
3. **别指定区域**：deploy 默认选最便宜的有库存节点；强行 `-r 广东` 可能拿不到库存或贵一点。
4. **多卡模型**：`qwen3.5-27b` / `hunyuan-image-3` 这类要 4×/8× GPU，deploy 时平台自动对齐，不要手动改 `-c`。
5. **Agent 批处理完自觉 stop**：让 Agent 把 `gongji stop <id> -f` 放在脚本末尾或 `trap EXIT` 里。
6. **一键回收**：结束一天工作说一句"帮我把共绩算力上所有任务都停了"即可。

---

## 9. 常见问题

**Q: Agent 报 token 失效 / 签名错误？**
让 Agent 执行 `GONGJI_TOKEN=<新 token> gongji init --force`，或去官网 → API 密钥 → 重新生成。

**Q: Agent 报库存不足？**
换模板（比如 `qwen3.5-9b` 改 `qwen3.5-0.8b`），或换区域 `-r 河南`，或稍等 1-2 分钟重试。

**Q: 余额不足？**
去 gongjiyun.com 充值，¥10-20 够跑一整天试验。

**Q: 部署卡在 Pending？**
`gongji logs <id> --events` 看事件；常见是镜像拉取 / 资源等待，一般 30-60 秒内就绪。

**Q: 部署 5 分钟超时但 JSON 仍返回 `status: Pending`？**
任务已在平台创建，没有变成孤儿任务。继续 `gongji status <id>` 等就绪；不需要就 `gongji stop <id> -f`。

**Q: Agent 能不能只用 Python 而不用 CLI？**
可以。`from gongjiskills import GongjiClient` 之后调 `client.create_task(...)`。详见 [docs/python-api.md](./docs/python-api.md)。

**Q: 我想给团队统一接入？**
让 Agent 把 URL 写到你的 `.env` / Vault / 秘密管理器里；或者直接让 LLM URL 配成内部 OpenAI 代理。

**Q: 凭据怎么保护？密钥泄露怎么办？**
私钥默认 600 权限存在 `~/.gongji/`。担心泄露 → 控制台重新生成 token + `gongji init --force` 换密钥对。详见 [docs/security.md](./docs/security.md)。

---

## 附：速查一行命令

```bash
# 安装
curl -fsSL https://raw.githubusercontent.com/shaozheng0503/gongjiskills/main/install.sh | bash

# 配置
GONGJI_TOKEN=xxx gongji init --force

# 开一个 z-image 生图 + qwen3.5-9b LLM（组合）
gongji deploy --template z-image    -n img --ttl 3600 --json
gongji deploy --template qwen3.5-9b -n llm --ttl 3600 --json

# 查看 / 释放
gongji list --json
gongji stop --all -f --json
```

---

祝玩得开心。有任何问题丢回给 Agent，它会带着本手册自动排查。

**License**: MIT — 见 [LICENSE](./LICENSE) · **反馈**: [Issues](https://github.com/shaozheng0503/gongjiskills/issues)
