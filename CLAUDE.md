# 共绩算力 Skills

通过 CLI / Python API 管理共绩算力 GPU 弹性部署，供 Agent 自动调用。

## 快速开始

```bash
pip install .
gongji init           # 首次配置
gongji resources      # 查看GPU
gongji deploy <image> -n <name> -g 4090 -p 8080  # 部署
gongji list           # 查看任务
gongji stop <id> -f   # 释放
```

## 项目结构

```
gongjiskills/          # Python 包
  auth.py              # RSA-SHA256 签名（cryptography 优先，纯标准库兜底）
  client.py            # API 客户端（urllib，零依赖）
  cli.py               # CLI 实现（语义化退出码）
  templates.py         # 模板加载/校验（数据在 data/templates.json）
  ttl.py               # TTL 惰性对账（registry + 启动扫描）
  data/templates.json  # 47 个内置模板（数据与逻辑分离）
tests/                 # 44 个测试（CLI 31 + auth 13，纯标准库 runner）
skills/gongji.md       # Agent Skill 定义
gongji.py              # 兼容入口
```

## 依赖

- **运行时零依赖**：仅 Python ≥ 3.9 标准库。
- `cryptography` 为可选加速（`pip install .[crypto]`）；未安装时自动退回纯标准库 RSA 签名。
- `openssl` 命令仅 init 生成密钥时需要。

## API

- Base URL: `https://openapi.suanli.cn`
- 认证: RSA-SHA256 签名 (PKCS1v15)
- 签名串: `path\nversion\ntimestamp\ntoken\ndata`
- 价格单位: 微元/秒 (10^-6 yuan/s)，转元/h: `raw * 3600 / 1000000`
- 成功码: `"0000"` (不是 `"200"`)

## 关键设计

- **退出码**: 0=成功, 1=一般错误, 2=网络, 3=参数/配置, 4=资源未找到
- **TTL**: deploy `--ttl` 写入 `~/.gongji/ttl/registry.json`，后续任意 CLI 调用时惰性对账（`gongji ttl sweep` 可手动触发），无常驻进程。
- **模板数据**: 新增模板改 `gongjiskills/data/templates.json`，跑 `gongji images validate` 校验，无需动代码。
- **降级路径**: `templates.json` 缺失/损坏时回退 3 个最小模板集（vllm / qwen3.5-9b / z-image）。

开发细节见 [docs/development.md](./docs/development.md)。
