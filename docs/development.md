# 开发与测试

## 本地开发

```bash
git clone https://github.com/shaozheng0503/gongjiskills.git
cd gongjiskills
pip install -e .         # 开发模式，修改代码即时生效
```

依赖：

- Python ≥ 3.9
- `requests`、`cryptography`
- `openssl` 命令（用于 init 生成密钥对）

## 运行测试

```bash
python3 -m pytest tests/ -v             # 全部 34 个
python3 -m pytest tests/test_cli.py -v  # 只跑 CLI 测试
python3 -m pytest tests/test_auth.py -v # 只跑签名测试
```

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
│   ├── auth.py              # RSA-SHA256 签名 + 权限检查
│   ├── client.py            # API 客户端 + 网络错误处理 + 重试
│   ├── cli.py               # CLI 实现
│   └── templates.py         # 内置模板 + 分类
│
├── tests/                   # pytest 测试
│   ├── test_cli.py          # CLI 参数解析 + JSON 契约
│   └── test_auth.py         # 签名 + 配置加载
│
├── skills/
│   └── gongji.md            # Claude Code Skill 定义
│
└── docs/                    # 补充文档
    ├── cli-reference.md
    ├── python-api.md
    ├── security.md
    ├── development.md
    └── claude-code.md
```

## 添加新的内置模板

1. 编辑 `gongjiskills/templates.py`，在 `BUILTIN_TEMPLATES` 加新条目：

   ```python
   "my-template": {
       "image": "harbor.suanleme.cn/public-hub/xxx:v1",
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

2. 跑测试：

   ```bash
   python3 -m pytest tests/test_cli.py -v
   ```

测试会自动断言：

- 所有模板的 `image` 必须以 `harbor.suanleme.cn/` 开头（防止误加上游假镜像）
- 所有模板必须有合法的 `category`

## 关键设计点

- **API base URL**：`https://openapi.suanli.cn`
- **认证**：RSA-SHA256 签名（PKCS1v15）
- **签名串**：`path\nversion\ntimestamp\ntoken\ndata`
- **成功码**：`"0000"`（不是 `"200"`）
- **价格单位**：微元/秒（10⁻⁶ yuan/s），转元/小时 `raw * 3600 / 1e6`
- **TTL 守护**：`subprocess.Popen(start_new_session=True)` 启独立进程组

## 反馈 / 贡献

- 提 Issue：<https://github.com/shaozheng0503/gongjiskills/issues>
- 想加预制镜像 → 告诉镜像 ID，我补到 `templates.py`
- 想扩展 Python API → 看 `client.py`，欢迎 PR
