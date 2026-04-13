# 共绩算力 Skills

通过 CLI / Python API 管理共绩算力 GPU 弹性部署，供 Agent 自动调用。

## 快速开始

```bash
# 安装依赖
pip install cryptography requests

# 配置密钥
mkdir -p ~/.gongji
openssl genrsa -out ~/.gongji/private.key 2048
openssl rsa -pubout -in ~/.gongji/private.key -out ~/.gongji/public.pem
# 将 public.pem 内容上传到共绩算力控制台（API密钥 → RSA模式）

# 创建配置
cat > ~/.gongji/config.json << 'EOF'
{
  "token": "your-api-token-here",
  "private_key_path": "~/.gongji/private.key"
}
EOF
```

## CLI 用法

```bash
python gongji.py deploy <image> --name <name> --gpu <gpu> --port <port>
python gongji.py list
python gongji.py status <task_id>
python gongji.py stop <task_id>
```

## 项目结构

```
core/auth.py     — RSA签名
core/client.py   — API客户端
gongji.py        — CLI入口
skills/gongji.md — Claude Code skill定义
```

## 认证方式

RSA-SHA256 签名模式（PKCS1v15），签名串: `path\nversion\ntimestamp\ntoken\ndata`

## API Base URL

`https://openapi.suanli.cn`
