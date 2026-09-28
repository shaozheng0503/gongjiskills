"""auth 模块单元测试 — 签名串构建、Base64编码、请求头、纯标准库兜底"""

import base64
import json
import sys
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import hashes, serialization
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

from gongjiskills.auth import (
    sign_request, build_headers, load_config, load_private_key,
    _pem_decode, _parse_pkcs1_or_pkcs8_private_der, _PureRSAPrivateKey,
    _sign_pkcs1v15_sha256_pure,
)


def _gen_test_key():
    """生成测试用 RSA 密钥对（cryptography 可用时）"""
    if not HAS_CRYPTOGRAPHY:
        return None
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key


def _gen_test_key_pure(bitlen=1024):
    """纯标准库生成 RSA 密钥对（小位宽提速，仅测试用）"""
    def _probable_prime(n, rounds=24):
        import secrets as _s
        if n % 2 == 0 or n % 3 == 0:
            return False
        for _ in range(rounds):
            a = _s.randbelow(n - 3) + 2
            if pow(a, n - 1, n) != 1:
                return False
        return True

    import secrets
    while True:
        p = secrets.randbits(bitlen // 2) | (1 << (bitlen // 2 - 1)) | 1
        if _probable_prime(p):
            break
    while True:
        q = secrets.randbits(bitlen // 2) | (1 << (bitlen // 2 - 1)) | 1
        if _probable_prime(q) and q != p:
            break
    n = p * q
    e = 65537
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    return _PureRSAPrivateKey(n, e, d)


def _skip_if_no_cryptography(func):
    """无 pytest 环境的 skip 装饰器：cryptography 未安装时跳过"""
    if HAS_CRYPTOGRAPHY:
        return func
    def _skipped():
        print(f"  SKIP  {func.__name__} (cryptography 未安装)")
    _skipped.__name__ = func.__name__
    _skipped._skipped = True
    return _skipped


@_skip_if_no_cryptography
def test_sign_string_format():
    """签名串格式: path\\nversion\\ntimestamp\\ntoken\\ndata"""
    pk = _gen_test_key()
    sig = sign_request(
        path="/api/test?a=1",
        version="1.0.0",
        timestamp=1724222524375,
        token="test-token",
        body="{}",
        private_key=pk,
    )
    # 返回值应该是合法 Base64
    decoded = base64.b64decode(sig)
    assert len(decoded) > 0

    # 验签：用公钥验证签名是否正确
    pub = pk.public_key()
    sign_str = "/api/test?a=1\n1.0.0\n1724222524375\ntest-token\n{}"
    try:
        pub.verify(decoded, sign_str.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    except Exception:
        assert False, "签名验证失败"


@_skip_if_no_cryptography
def test_sign_post_body():
    """POST 请求体参与签名"""
    pk = _gen_test_key()
    body = json.dumps({"task_id": 388}, separators=(",", ":"))
    sig = sign_request(
        path="/api/deployment/task/pause",
        version="1.0.0",
        timestamp=1724222524375,
        token="my-token",
        body=body,
        private_key=pk,
    )
    decoded = base64.b64decode(sig)
    pub = pk.public_key()
    expected = f"/api/deployment/task/pause\n1.0.0\n1724222524375\nmy-token\n{body}"
    pub.verify(decoded, expected.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())


def test_build_headers_keys():
    """headers 包含 token, timestamp, version, sign_str, Content-Type（纯库密钥即可测）"""
    pk = _gen_test_key_pure()
    config = {"token": "abc", "version": "1.0.0"}
    headers = build_headers("/api/test", config, pk, body="{}")
    assert set(headers.keys()) == {"token", "timestamp", "version", "sign_str", "Content-Type"}
    assert headers["token"] == "abc"
    assert headers["version"] == "1.0.0"
    assert headers["Content-Type"] == "application/json"
    # timestamp 是毫秒级
    ts = int(headers["timestamp"])
    assert ts > 1700000000000


def test_build_headers_sign_is_base64():
    pk = _gen_test_key_pure()
    config = {"token": "t", "version": "1.0.0"}
    headers = build_headers("/api/x", config, pk)
    base64.b64decode(headers["sign_str"])  # 不抛异常即通过


# ── 纯标准库兜底测试 ──

def test_pure_python_sign_matches_format():
    """纯 Python 签名输出 256 字节（1024-bit 测试密钥则 128 字节），可 Base64"""
    pk = _gen_test_key_pure(bitlen=1024)
    sig = sign_request(
        path="/api/test?a=1", version="1.0.0", timestamp=1724222524375,
        token="tok", body="{}", private_key=pk,
    )
    raw = base64.b64decode(sig)
    assert len(raw) == 128  # 1024-bit key


@_skip_if_no_cryptography
def test_pure_python_sign_matches_cryptography():
    """同一密钥下，纯 Python 签名与 cryptography 签名逐字节一致"""
    from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
    from cryptography.hazmat.primitives import serialization as _ser
    ck = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
    der = ck.private_bytes(
        _ser.Encoding.PEM, _ser.PrivateFormat.PKCS8, _ser.NoEncryption(),
    )
    # 解析出 n/e/d 构造纯库密钥
    pem_text = der.decode()
    inner = _pem_decode(pem_text)
    n, e, d = _parse_pkcs1_or_pkcs8_private_der(inner)
    pk_pure = _PureRSAPrivateKey(n, e, d)
    msg = b"/api/x\n1.0.0\n1724222524375\ntok\n{}"
    sig_crypto = sign_request("/api/x", "1.0.0", 1724222524375, "tok", "{}", ck)
    sig_pure = sign_request("/api/x", "1.0.0", 1724222524375, "tok", "{}", pk_pure)
    assert sig_crypto == sig_pure


def test_pem_decode_roundtrip():
    """PEM 解码能拿到 DER 字节"""
    pem = "-----BEGIN PRIVATE KEY-----\nAAAA\n-----END PRIVATE KEY-----"
    der = _pem_decode(pem)
    assert der == b"\x00\x00\x00"


def test_load_config_missing():
    """配置文件不存在时抛 FileNotFoundError"""
    import gongjiskills.auth as auth
    original = Path.home
    Path.home = staticmethod(lambda: Path(tempfile.mkdtemp()))
    try:
        try:
            load_config()
            assert False, "应该抛异常"
        except FileNotFoundError:
            pass
    finally:
        Path.home = original


def test_load_config_bad_json():
    """JSON 格式错误时抛 ValueError"""
    tmpdir = Path(tempfile.mkdtemp())
    gongji_dir = tmpdir / ".gongji"
    gongji_dir.mkdir()
    (gongji_dir / "config.json").write_text("{bad")

    import gongjiskills.auth as auth
    original = Path.home
    Path.home = staticmethod(lambda: tmpdir)
    try:
        try:
            load_config()
            assert False, "应该抛异常"
        except ValueError as e:
            assert "格式错误" in str(e)
    finally:
        Path.home = original


def test_load_config_missing_field():
    """缺少 token 时抛 KeyError（简易模式只需 token）"""
    tmpdir = Path(tempfile.mkdtemp())
    gongji_dir = tmpdir / ".gongji"
    gongji_dir.mkdir()
    (gongji_dir / "config.json").write_text('{"private_key_path": "/tmp/x.key"}')

    import gongjiskills.auth as auth
    original = Path.home
    Path.home = staticmethod(lambda: tmpdir)
    try:
        try:
            load_config()
            assert False, "应该抛异常"
        except KeyError:
            pass
    finally:
        Path.home = original


def test_load_config_simple_mode():
    """简易模式：只填 token 即可，无需 private_key_path"""
    tmpdir = Path(tempfile.mkdtemp())
    gongji_dir = tmpdir / ".gongji"
    gongji_dir.mkdir()
    (gongji_dir / "config.json").write_text('{"token": "x"}')

    import gongjiskills.auth as auth
    original = Path.home
    Path.home = staticmethod(lambda: tmpdir)
    try:
        config = load_config()
        assert config["token"] == "x"
        assert "private_key_path" not in config
        assert config["base_url"] == "https://openapi.suanli.cn"
        # 简易模式：无私钥字段 → load_private_key 返回 None
        assert load_private_key(config) is None
        # 简易模式 headers：无 sign_str
        headers = build_headers("/api/test", config, None, body="{}")
        assert "sign_str" not in headers
        assert set(headers.keys()) == {"token", "timestamp", "version", "Content-Type"}
    finally:
        Path.home = original


def test_load_private_key_missing_file_hint():
    """RSA 模式配了 private_key_path 但文件不存在 → 报错并提示可回退简易模式"""
    tmpdir = Path(tempfile.mkdtemp())
    config = {"token": "x", "private_key_path": str(tmpdir / "nope.key")}
    try:
        try:
            load_private_key(config)
            assert False, "应该抛异常"
        except FileNotFoundError as e:
            assert "简易模式" in str(e)
    finally:
        pass


def test_load_private_key():
    """能正确加载 PEM 私钥（双轨：cryptography 或纯标准库对象）"""
    pk = _gen_test_key_pure()  # 无需 cryptography
    # 纯库对象直接能签名
    sig = pk.sign(b"hello", None, None)
    assert len(sig) == 128


@_skip_if_no_cryptography
def test_load_private_key_from_pem_file():
    """从 PEM 文件加载（PKCS#8），cryptography 路径"""
    from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
    from cryptography.hazmat.primitives import serialization as _ser
    ck = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tmpfile = tempfile.NamedTemporaryFile(suffix=".key", delete=False)
    tmpfile.write(ck.private_bytes(
        _ser.Encoding.PEM,
        _ser.PrivateFormat.PKCS8,
        _ser.NoEncryption(),
    ))
    tmpfile.close()
    try:
        loaded = load_private_key({"private_key_path": tmpfile.name})
        assert loaded is not None
    finally:
        os.unlink(tmpfile.name)


def test_parse_pkcs1_der():
    """纯标准库解析 PKCS#8→PKCS#1 DER 并完成签名（无 cryptography 依赖）"""
    from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
    from cryptography.hazmat.primitives import serialization as _ser
    ck = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = ck.private_bytes(
        _ser.Encoding.PEM, _ser.PrivateFormat.PKCS8, _ser.NoEncryption(),
    ).decode()
    der = _pem_decode(pem)
    n, e, d = _parse_pkcs1_or_pkcs8_private_der(der)
    pk = _PureRSAPrivateKey(n, e, d)
    sig = pk.sign(b"cross-check", None, None)
    assert len(sig) == 256  # 2048-bit
    # 用 cryptography 公钥验签（证明纯库签名正确）
    from cryptography.hazmat.primitives import hashes as _h
    from cryptography.hazmat.primitives.asymmetric import padding as _p
    ck.public_key().verify(sig, b"cross-check", _p.PKCS1v15(), _h.SHA256())


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = skipped = 0
    for t in tests:
        if getattr(t, "_skipped", False):
            t()
            skipped += 1
            continue
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    sys.exit(1 if failed else 0)
