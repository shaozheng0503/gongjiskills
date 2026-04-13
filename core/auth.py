"""共绩算力 RSA 签名模块"""

import base64
import json
import time
import os
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def load_config() -> dict:
    """加载 ~/.gongji/config.json 配置"""
    config_path = Path.home() / ".gongji" / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}\n"
            "请先创建配置文件，格式:\n"
            '{"token": "your-token", "private_key_path": "~/.gongji/private.key"}'
        )
    with open(config_path) as f:
        config = json.load(f)
    for key in ("token", "private_key_path"):
        if key not in config:
            raise KeyError(f"配置缺少必填字段: {key}")
    config.setdefault("base_url", "https://openapi.suanli.cn")
    config.setdefault("version", "1.0.0")
    return config


def load_private_key(config: dict):
    """加载RSA私钥"""
    key_path = Path(os.path.expanduser(config["private_key_path"]))
    if not key_path.exists():
        raise FileNotFoundError(f"私钥文件不存在: {key_path}")
    with open(key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    return private_key


def sign_request(
    path: str,
    version: str,
    timestamp: int,
    token: str,
    body: str,
    private_key,
) -> str:
    """
    RSA-SHA256 签名

    签名串格式: path\nversion\ntimestamp\ntoken\ndata
    GET请求: path包含query string, body为'{}'
    POST请求: path不含query, body为JSON字符串
    """
    sign_str = f"{path}\n{version}\n{timestamp}\n{token}\n{body}"
    signature = private_key.sign(
        sign_str.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def build_headers(
    path: str,
    config: dict,
    private_key,
    body: str = "{}",
) -> dict:
    """构建带签名的请求头"""
    timestamp = int(time.time() * 1000)
    sign_str = sign_request(
        path=path,
        version=config["version"],
        timestamp=timestamp,
        token=config["token"],
        body=body,
        private_key=private_key,
    )
    return {
        "token": config["token"],
        "timestamp": str(timestamp),
        "version": config["version"],
        "sign_str": sign_str,
        "Content-Type": "application/json",
    }
