"""共绩算力 RSA 签名模块

签名实现双轨：
1. cryptography 库（若已安装，优先）
2. 纯标准库 PKCS#1 v1.5 + SHA-256（兜底，零依赖场景）

密钥生成仍依赖 openssl 命令行（init 阶段一次性操作）。
"""

import base64
import hashlib
import json
import time
import os
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    _HAS_CRYPTOGRAPHY = False


# ── 纯标准库 PKCS#1 v1.5 RSA 签名（兜底实现） ──

def _pem_decode(pem_text: str) -> bytes:
    """从 PEM 文本提取 DER 字节"""
    lines = [
        l for l in pem_text.strip().splitlines()
        if l and not l.startswith("-----")
    ]
    return base64.b64decode("".join(lines))


def _parse_pkcs1_or_pkcs8_private_der(der: bytes):
    """极简 DER 解析，返回 (n, e, d)。

    支持 PKCS#1 (RSA PRIVATE KEY) 与 PKCS#8 (PRIVATE KEY, 内嵌 PKCS#1) 两种格式。
    只取我们需要的三个大整数，忽略其余字段。
    """
    def _read_tlv(data: bytes, offset: int):
        """读一个完整 TLV；返回 (tag, value_bytes, next_offset)"""
        tag = data[offset]
        # 长度在 tag 之后的字节
        first = data[offset + 1]
        if first & 0x80 == 0:
            length = first
            pos = offset + 2
        else:
            num_bytes = first & 0x7F
            length = int.from_bytes(data[offset + 2: offset + 2 + num_bytes], "big")
            pos = offset + 2 + num_bytes
        return tag, data[pos: pos + length], pos + length

    def _find_pkcs1_sequence(der: bytes) -> bytes | None:
        """定位 PKCS#1 RSAPrivateKey 的 SEQUENCE 内容（PKCS#8 外层或直接 PKCS#1）"""
        oid_marker = bytes.fromhex("06092A864886F70D010101")
        idx = der.find(oid_marker)
        if idx >= 0:
            rest = der[idx + len(oid_marker):]
            # 跳过 0500 (NULL)
            if rest[:2] == b"\x05\x00":
                rest = rest[2:]
            # 04 <len> <PKCS#1 SEQUENCE>
            if rest[0:1] == b"\x04":
                _, pkcs1_der, _ = _read_tlv(rest, 0)
                # pkcs1_der 是完整 PKCS#1 SEQUENCE TLV（含 30 xx 头），再剥一层取内容
                if pkcs1_der[0:1] == b"\x30":
                    _, value, _ = _read_tlv(pkcs1_der, 0)
                    return value
        # 直接 PKCS#1：第一个 SEQUENCE 的内容
        if der[0:1] == b"\x30":
            _, value, _ = _read_tlv(der, 0)
            return value
        return None

    seq = _find_pkcs1_sequence(der)
    if seq is None:
        raise ValueError("无法解析私钥 DER 结构")
    # seq 现在是 RSAPrivateKey SEQUENCE 的 **内容**（去掉了 30 xx 头）
    # 依次读 version, n, e, d
    pos = 0
    _, version, pos = _read_tlv(seq, pos)
    _, n_bytes, pos = _read_tlv(seq, pos)
    _, e_bytes, pos = _read_tlv(seq, pos)
    _, d_bytes, pos = _read_tlv(seq, pos)
    n = int.from_bytes(n_bytes, "big")
    e = int.from_bytes(e_bytes, "big")
    d = int.from_bytes(d_bytes, "big")
    return n, e, d


def _sign_pkcs1v15_sha256_pure(message: bytes, n: int, e: int, d: int, key_size_bytes: int) -> bytes:
    """纯 Python PKCS#1 v1.5 签名"""
    digest = hashlib.sha256(message).digest()
    # DigestInfo for SHA-256
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + digest
    ps_len = key_size_bytes - len(digest_info) - 3
    em = b"\x00\x01" + b"\xff" * ps_len + b"\x00" + digest_info
    m = int.from_bytes(em, "big")
    s = pow(m, d, n)
    return s.to_bytes(key_size_bytes, "big")


class _PureRSAPrivateKey:
    """cryptography 缺失时的私钥替身：只实现 sign(PKCS1v15+SHA256)"""

    def __init__(self, n: int, e: int, d: int):
        self.n, self.e, self.d = n, e, d
        self.key_size_bytes = (n.bit_length() + 7) // 8

    def sign(self, data: bytes, padding_obj, hash_obj) -> bytes:
        # 忽略 padding_obj/hash_obj 参数（本实现固定 PKCS1v15+SHA256）
        return _sign_pkcs1v15_sha256_pure(data, self.n, self.e, self.d, self.key_size_bytes)


def load_config() -> dict:
    """加载 ~/.gongji/config.json 配置"""
    config_path = Path.home() / ".gongji" / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}\n"
            "请先创建配置文件，格式:\n"
            '{"token": "your-token", "private_key_path": "~/.gongji/private.key"}'
        )
    # 检查文件权限，过于宽松时警告
    try:
        mode = config_path.stat().st_mode & 0o777
        if mode & 0o077:  # 其他用户/组可读
            import sys
            print(
                f"警告: {config_path} 权限过宽 ({oct(mode)})，"
                f"建议运行: chmod 600 {config_path}",
                file=sys.stderr,
            )
    except OSError:
        pass
    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError:
        raise ValueError(
            f"配置文件格式错误: {config_path}\n"
            "请检查 JSON 格式是否正确，示例:\n"
            '{"token": "your-token", "private_key_path": "~/.gongji/private.key"}'
        )
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
    try:
        mode = key_path.stat().st_mode & 0o777
        if mode & 0o077:
            import sys
            print(
                f"警告: 私钥 {key_path} 权限过宽 ({oct(mode)})，"
                f"建议运行: chmod 600 {key_path}",
                file=sys.stderr,
            )
    except OSError:
        pass
    with open(key_path, "rb") as f:
        key_data = f.read()
    if _HAS_CRYPTOGRAPHY:
        private_key = serialization.load_pem_private_key(key_data, password=None)
        return private_key
    # 兜底：纯标准库解析 PEM → DER → (n, e, d)
    pem_text = key_data.decode("utf-8", errors="strict")
    der = _pem_decode(pem_text)
    n, e, d = _parse_pkcs1_or_pkcs8_private_der(der)
    return _PureRSAPrivateKey(n, e, d)


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
    if _HAS_CRYPTOGRAPHY and not isinstance(private_key, _PureRSAPrivateKey):
        signature = private_key.sign(
            sign_str.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    else:
        # 纯标准库兜底
        signature = private_key.sign(
            sign_str.encode("utf-8"), None, None,
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
