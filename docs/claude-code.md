# 在 Claude Code 中使用

项目自带 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill 定义（`skills/gongji.md`）。

## 配置方式

把 `skills/gongji.md` 复制到 Claude Code 的 skills 目录，或者在项目根目录保留让 Claude Code 自动发现。

## 自然语言示例

直接对 Claude Code 说：

| 你说 | Claude 会跑 |
|------|------------|
| 帮我部署一个 4090 跑 Qwen 推理 | `gongji deploy --template qwen3.5-9b -n xxx --ttl 3600 --json` |
| 开个 ComfyUI 到广东区域 | `gongji deploy --template flux1-dev-comfyui -n xxx -r 广东 --json` |
| 看看我现在有哪些任务在跑 | `gongji list --json` |
| 任务 1926525 花了多少钱 | `gongji status 1926525 --json` |
| 把任务停掉 | `gongji stop <id> -f --json` |
| 跑个 Whisper 语音识别，1 小时后关 | `gongji deploy --template whisper -n xxx --ttl 3600 --json` |
| 列出所有 LLM 模板 | `gongji images --category llm --json` |
| 全部停掉 | `gongji stop --all -f --json` |

## Agent 工作链路

1. 用户说需求 → Claude 理解意图
2. 必要时 `gongji images categories` / `--category` 找合适模板
3. `gongji deploy --template <name> -n xxx --ttl 3600 --json` 部署
4. 返回 URL 给用户，或直接 `curl` 调用
5. 用完 `gongji stop <id> -f`

## 给其他 Agent 用

不是 Claude Code 专属。任何能执行 bash 的 AI Agent（Cursor / Cline / Codex CLI / OpenCode / 自研）按 [README](../README.md) 的"安装 & 初始化"那一段粘给它，就能直接用。

Skill 的本质就是一份给 LLM 看的说明书 + 一个 CLI 工具，**不强制依赖 Claude Code**。
