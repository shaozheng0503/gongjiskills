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
  auth.py              # RSA-SHA256 签名
  client.py            # API 客户端
  cli.py               # CLI 实现
tests/                 # 23 个测试
skills/gongji.md       # Claude Code Skill 定义
gongji.py              # 兼容入口
```

## API

- Base URL: `https://openapi.suanli.cn`
- 认证: RSA-SHA256 签名 (PKCS1v15)
- 签名串: `path\nversion\ntimestamp\ntoken\ndata`
- 价格单位: 微元/秒 (10^-6 yuan/s)，转元/h: `raw * 3600 / 1000000`
- 成功码: `"0000"` (不是 `"200"`)
