# Changelog

本文件记录 gongjiskills 的版本变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [0.2.0] — 2026-09-28

按 Agent Skills 设计规范（渐进披露 / 自包含分发 / 数据与逻辑分离 / 降级路径 / 语义化退出码 / clean-room 验证）全量改造。

### 新增

- **数据与逻辑分离**：47 个模板从 `templates.py` 硬编码外置到 `gongjiskills/data/templates.json`；JSON 损坏时自动回退 3 个最小模板集（vllm / qwen3.5-9b / z-image），保证 CLI 永不因数据文件挂掉。
- **TTL 惰性对账**（`ttl.py`）：移除常驻 `subprocess` 守护（机器重启即失效的隐患），改为 `~/.gongji/ttl/registry.json` 登记 + 任意 CLI 命令启动时自动扫描补发 stop + 新增 `gongji ttl list / sweep / rm` 手动管理。
- **纯标准库 RSA 签名兜底**（`auth.py`）：`cryptography` 缺失时自动退回纯 Python PKCS#1 v1.5 + SHA-256 实现（含极简 DER 解析器，支持 PKCS#1 / PKCS#8 双格式），实现运行时零依赖。
- **语义化退出码**：0=成功 / 1=一般错误 / 2=网络失败 / 3=参数或配置错误 / 4=资源未找到；JSON 错误输出统一携带 `exit_code` 字段，供 Agent 分支处理。
- **`python -m gongjiskills` 入口**（`__main__.py`）：免安装直接从仓库根运行。
- **`gongji images validate`**：校验模板数据（镜像前缀 `harbor.suanleme.cn/`、category 合法性、port/gpu_count 格式），人工维护模板后自检。
- **测试扩充至 44 个**（CLI 31 + auth 13），runner 纯标准库实现，无 pytest 依赖亦可执行。
- **Clean-room 失忆测试流程**写入 `docs/development.md`。

### 变更

- `client.py`：`requests` → 标准库 `urllib`；重试升级为 3 次（覆盖 429/5xx，指数退避）；`GongjiError` 携带 `exit_code`；新增「模板不存在」等友好错误提示。
- `skills/gongji.md`（SKILL.md）规范化：补 YAML frontmatter（含触发词）、命令速查表、退出码表、Agent 推荐工作流、对话执行约定（删前二次确认、勿编造 token/镜像）等渐进披露结构。
- `pyproject.toml`：`dependencies` 置空，`cryptography` 移入可选 extra `pip install gongjiskills[crypto]`；打包包含 `data/*.json`。
- README / CLAUDE.md / docs 与零依赖架构对账更新；预制镜像清单 46 vs 47 差异说明（jupyter 为 ubuntu2404 派生）；修复 `Qwen-lmage-2512` OCR 错别字。

### 移除

- `setup.py`、`requirements.txt`（信息合并进 `pyproject.toml`，避免双源漂移）。
- 常驻 TTL 守护进程方案。

## [0.1.0] — 2026-04

首个公开版本：单 skill（`skills/gongji.md`）+ Python 包（init / resources / deploy / list / status / logs / stop）+ 47 个预制模板 + docs + install.sh。

[0.2.0]: https://github.com/shaozheng0503/gongjiskills/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/shaozheng0503/gongjiskills/releases/tag/v0.1.0
