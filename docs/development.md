# 开发与测试

## 本地开发

```bash
git clone https://github.com/shaozheng0503/gongjiskills.git
cd gongjiskills
pip install -e .         # 开发模式，修改代码即时生效
```

依赖：

- Python ≥ 3.9（**运行时零依赖**，仅标准库）
- `cryptography`（可选，`pip install -e ".[crypto]"`，加速签名；缺失时自动退回纯标准库 RSA）
- `openssl` 命令（仅 init 生成密钥对时需要）

## 运行测试

```bash
python3 tests/test_cli.py    # 31 个 CLI 测试（内置无 pytest 的 runner）
python3 tests/test_auth.py   # 13 个签名/解析测试
```

两个 runner 均为纯标准库实现（无 pytest 依赖），直接 `python3` 执行即可。

## Clean-room 失忆测试

每次改动 SKILL.md 后，验证的不是「内容对不对」，而是「一个只看 SKILL.md 的 Agent 能否走对流程」。
方法：**开一个全新会话（无历史上下文）**，只把 SKILL.md 内容给它，让它扮演 Agent 执行以下场景，观察行为是否符合预期：

| 场景 | 预期行为 |
|------|----------|
| "帮我部署个 vLLM" | 先 `images categories --json` → 选 `llm` 分类 → `deploy --template vllm -n xxx --ttl 3600 --json`，而非直接 deploy |
| "有哪些 GPU 可用？" | `resources --json`，按价格排序展示 |
| "任务怎么卡住了？" | `status <id> --json` → `logs <id> --events`，按退出码分支，不盲目重试 |
| "太贵了" | 换便宜模板/单卡配置，或提示改小 `--ttl` |
| "把它删了" | **先二次确认再 `stop`**；批量 `--all` 必须带 `--force` |
| 配置缺失 (exit 3) | 引导用户去 gongjiyun.com 头像 → API 密钥，勿编造 token |
| 模板不存在 (exit 4) | 跑 `images --category <k> --json` 找相近模板，勿重试原模板 |
| 网络失败 (exit 2) | 稍等重试（底层已自动重试 3 次） |

判定标准：

- Agent 没有按 SKILL.md 的「推荐工作流」行动 → 说明速查表/工作流图不够醒目或引导不足
- Agent 编造了 docker hub 镜像地址 → 说明「模板库关键约束」节没起到作用
- Agent 未经确认就 stop → 说明「对话执行约定」第 4 条需要加粗/前置

发现问题后修 SKILL.md，重跑场景验证，形成闭环。测试时建议同时覆盖 JSON 与非 JSON 模式。

## 项目结构

```
gongjiskills/
├── README.md                # 主文档
├── LICENSE                  # MIT
├── setup.py / pyproject.toml  # Python 打包配置
├── requirements.txt
├── install.sh               # 一键安装脚本
├── gongji.py                # 兼容入口（python3 gongji.py xxx）
│
├── gongjiskills/            # Python 包
│   ├── __init__.py          # 导出 GongjiClient
│   ├── __main__.py          # python -m gongjiskills 入口
│   ├── auth.py              # RSA-SHA256 签名（cryptography 优先 + 纯标准库兜底）
│   ├── client.py            # API 客户端（urllib 零依赖）+ 网络错误处理 + 重试
│   ├── cli.py               # CLI 实现（语义化退出码 0/1/2/3/4）
│   ├── templates.py         # 模板加载/校验（数据外置）
│   ├── ttl.py               # TTL 惰性对账（registry + 启动扫描）
│   └── data/templates.json  # 47 个内置模板（数据与逻辑分离）
│
├── tests/                   # 测试（纯标准库 runner，无 pytest 依赖）
│   ├── test_cli.py          # CLI 参数解析 + JSON 契约 + 退出码
│   └── test_auth.py         # 签名 + DER 解析 + 配置加载
│
├── skills/
│   └── gongji.md            # Agent Skill 定义
│
└── docs/                    # 补充文档
    ├── cli-reference.md
    ├── python-api.md
    ├── security.md
    ├── development.md
    └── claude-code.md
```

## 添加新的内置模板

1. 编辑 `gongjiskills/data/templates.json`，在 `templates` 下加新条目：

   ```json
   "my-template": {
       "image": "harbor.suanleme.cn/public-hub/xxx:v1",
       "category": "llm",
       "description": "...",
       "port": "8000",
       "gpu": "4090",
       "env": "KEY=VAL",
       "start_cmd": "/bin/bash",
       "start_args": ["-c", "..."],
       "docs": "https://..."
   }
   ```

2. 校验：

   ```bash
   gongji images validate          # 或
   python3 -c "from gongjiskills.templates import validate_templates; print(validate_templates())"
   ```

   返回 `[]` 即全部通过。校验规则：

   - 所有模板的 `image` 必须以 `harbor.suanleme.cn/` 开头（防止误加上游假镜像）
   - 所有模板必须有合法的 `category`（见 `templates.py` 的 `CATEGORIES`）
   - `port` 为逗号分隔数字；`gpu_count` 为正整数

3. 跑测试：`python3 tests/test_cli.py`

> 模板数据与代码分离：更新模板只改 JSON、发版不涉及逻辑变更，JSON 损坏时回退 3 个最小模板集（vllm / qwen3.5-9b / z-image）。

## 关键设计点

- **API base URL**：`https://openapi.suanli.cn`
- **认证**：RSA-SHA256 签名（PKCS1v15）
- **签名串**：`path\nversion\ntimestamp\ntoken\ndata`
- **成功码**：`"0000"`（不是 `"200"`）
- **价格单位**：微元/秒（10⁻⁶ yuan/s），转元/小时 `raw * 3600 / 1e6`
- **退出码**：0=成功, 1=一般错误, 2=网络, 3=参数/配置, 4=资源未找到
- **TTL 惰性对账**：deploy `--ttl` 写入 `~/.gongji/ttl/registry.json`；后续任意 CLI 调用启动时扫描过期条目自动停止任务，`gongji ttl list/sweep/rm` 手动管理，无常驻进程

## 反馈 / 贡献

- 提 Issue：<https://github.com/shaozheng0503/gongjiskills/issues>
- 想加预制镜像 → 告诉镜像 ID，我补到 `gongjiskills/data/templates.json`（并同步 `docs/预制镜像清单.md`）
- 想扩展 Python API → 看 `client.py`，欢迎 PR
