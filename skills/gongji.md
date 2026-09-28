---
name: gongji
description: >-
  共绩算力（gongjiyun.com / suanli.cn）GPU 弹性部署 CLI：一句话开 GPU 跑 LLM 推理（vLLM/Qwen/Ollama）、
  文生图（ComfyUI/Z-Image/FLUX/SD）、视频生成（WAN2.2）、语音（Whisper/IndexTTS/CosyVoice）、
  音乐（ACE-Step）、OCR/文档解析（MinerU/PaddleOCR）、开发环境（Jupyter/LLaMA-Factory）。
  按 GPU 秒计费、TTL 到期自动释放。在用户提到部署 GPU、开显卡、跑模型、推理服务、弹性部署、
  共绩、算力平台、gongji、gongjiyun.com、suanli、openapi.suanli.cn、ComfyUI、vLLM、
  Stable Diffusion、Flux、视频生成、TTS、ASR、语音识别、OCR、微调时启用。
---

# /gongji — 共绩算力弹性部署

管理共绩算力 GPU 弹性部署任务。Agent 需要 GPU 算力时自动调用。

## 命令速查

| 命令 | 一句话 |
|------|--------|
| `gongji init` | 初始化（`GONGJI_TOKEN=xxx gongji init --force` 非交互） |
| `gongji resources --json` | 查 GPU 库存价格（`-g 4090 -r 广东` 筛选） |
| `gongji images categories --json` | 看分类大纲 ★ Agent 先看这个 |
| `gongji images --category <k> --json` | 看分类下模板 |
| `gongji images validate` | 校验模板数据（维护后用） |
| `gongji deploy --template <t> -n <名> --ttl 3600 --json` | 部署（推荐，务必带 `--ttl`） |
| `gongji list --json` | 列任务+URL |
| `gongji status <id> --json` | 任务详情（含费用） |
| `gongji logs <id> [--events]` | 日志 / 事件（排查失败） |
| `gongji stop <id> -f --json` | 释放单个 |
| `gongji stop --all -f --json` | 批量释放 |
| `gongji ttl list` / `sweep` / `rm <id>` | TTL 登记管理 / 立即对账 / 移除登记 |

完整参数（deploy 全字段、images add 等）见 [docs/cli-reference.md](../docs/cli-reference.md)，**仅在构造复杂命令时读取，勿整篇加载**。

## 退出码

| code | 含义 | Agent 动作 |
|------|------|------------|
| 0 | 成功 | — |
| 1 | 一般错误 | 读 `error` 字段 |
| 2 | 网络失败 | 稍等重试（已自动重试 3 次） |
| 3 | 参数/配置错误 | 检查参数或引导用户 `gongji init` |
| 4 | 资源未找到 | 换模板/确认 task_id，勿盲目重试 |

JSON 错误格式：`{"error": "...", "exit_code": N}`。

## Agent 推荐工作流

```
用户说"帮我部署 X"
  ↓
1. gongji images categories --json          # 看分类
2. gongji images --category <匹配分类> --json # 选模板
3. gongji deploy --template <name> -n <名> --ttl 3600 --json  # 部署
4. 拿 urls[].url 调用服务（curl / SDK）
5. 用完 gongji stop <id> -f --json
```

**意图映射**：跑 LLM/推理→`llm` · 看图/多模态→`multimodal` · 文生图→`image-gen` · 修图/换脸/证件照→`image-edit` · 视频→`video` · 3D→`3d` · 语音→`audio` · 音乐→`music` · PDF/OCR→`ocr` · Jupyter/微调→`dev`

**模板库关键约束**：所有镜像来自平台 registry `harbor.suanleme.cn`（内网预缓存）。**不要编造 docker hub / ghcr.io 上游地址**，平台拉不到。模板数据在 `gongjiskills/data/templates.json`，平台暂无公开清单 API，人工维护后跑 `gongji images validate`。

## deploy 关键点

1. **必须 `--json`**；成功返回 `{"task_id", "status", "urls": [{"url", "port"}]}`
2. deploy 自动选最便宜有库存资源；`-c` 卡数、`-r` 区域可覆盖
3. **强烈建议 `--ttl`**（如 3600 秒）防忘删烧钱；TTL 为惰性对账：登记 `~/.gongji/ttl/registry.json`，任意 gongji 命令启动时自动补发 stop，也可 `gongji ttl sweep` 手动触发
4. 等待超时（5 分钟）不报 error，返回 `status: "Pending"` + hint——任务已创建，继续 `gongji status <id>`
5. 模板分类速览表见 [README.md](../README.md) 第 5 节，或 `gongji images --json` 拿全量

## 对话执行约定

1. 缺 token / 配置不存在时，引导用户去 https://www.gongjiyun.com → 头像 → API 密钥（RSA 模式）获取，勿猜测、勿编造。
2. deploy 前确认：模板名、任务名、TTL；大模型（27B+/多卡）确认用户接受价格。
3. 创建成功后回报 `task_id` + 访问 URL，询问是否轮询就绪。
4. **删除/批量删除前必须二次确认**；`stop --all` 强制要求 `--force`。
5. 错误时输出完整 `error` + `exit_code`，按退出码分支处理，勿吞错误。
6. 任务用完自觉 `stop`；长任务建议同时提醒用户设置日历提醒（TTL 惰性对账依赖客户端后续有命令执行）。
7. 镜像只用 `gongji images` 列出的平台 registry 地址；用户给上游地址时提示平台内网拉不到。
