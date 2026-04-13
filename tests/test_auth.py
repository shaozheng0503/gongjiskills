"""auth 模块单元测试 — 签名串构建、Base64编码、请求头"""

import base64
import json
import sys
import tempfile
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gongjiskills.auth import sign_request, build_headers, load_config, load_private_key


def _gen_test_key():
    """生成测试用 RSA 密钥对"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key


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
    """headers 包含 token, timestamp, version, sign_str, Content-Type"""
    pk = _gen_test_key()
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
    pk = _gen_test_key()
    config = {"token": "t", "version": "1.0.0"}
    headers = build_headers("/api/x", config, pk)
    base64.b64decode(headers["sign_str"])  # 不抛异常即通过


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
    """缺少必填字段时抛 KeyError"""
    tmpdir = Path(tempfile.mkdtemp())
    gongji_dir = tmpdir / ".gongji"
    gongji_dir.mkdir()
    (gongji_dir / "config.json").write_text('{"token": "x"}')

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


def test_load_private_key():
    """能正确加载 PEM 私钥"""
    pk = _gen_test_key()
    tmpfile = tempfile.NamedTemporaryFile(suffix=".key", delete=False)
    tmpfile.write(pk.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    tmpfile.close()
    try:
        loaded = load_private_key({"private_key_path": tmpfile.name})
        assert loaded is not None
    finally:
        os.unlink(tmpfile.name)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
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
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
