"""CLI 基础测试 — 验证参数解析、错误处理、JSON 输出格式"""

import json
import subprocess
import sys
from pathlib import Path

GONGJI = str(Path(__file__).resolve().parent.parent / "gongji.py")


def run(args: list, input_text: str = None) -> tuple:
    """运行 CLI 命令，返回 (stdout, stderr, returncode)"""
    result = subprocess.run(
        [sys.executable, GONGJI] + args,
        capture_output=True, text=True, input=input_text,
    )
    return result.stdout, result.stderr, result.returncode


def test_help():
    out, _, rc = run(["--help"])
    assert rc == 0
    assert "deploy" in out
    assert "list" in out
    assert "logs" in out


def test_deploy_help():
    out, _, rc = run(["deploy", "--help"])
    assert rc == 0
    assert "--json" in out
    assert "--gpu" in out


def test_deploy_missing_args():
    _, _, rc = run(["deploy"])
    assert rc == 2  # argparse error


def test_deploy_invalid_port():
    _, err, rc = run(["deploy", "img:v1", "-n", "test", "-p", "abc"])
    assert rc == 1
    assert "端口格式无效" in err


def test_deploy_json_error_is_valid_json():
    """--json 模式下报错也必须是合法 JSON"""
    out, _, rc = run(["deploy", "img:v1", "-n", "test", "--json"])
    assert rc == 1
    data = json.loads(out)
    assert "error" in data


def test_list_json_error_is_valid_json():
    out, _, rc = run(["list", "--json"])
    assert rc == 1
    data = json.loads(out)
    assert "error" in data


def test_status_json_error_is_valid_json():
    out, _, rc = run(["status", "999", "--json"])
    assert rc == 1
    data = json.loads(out)
    assert "error" in data


def test_stop_json_no_confirm():
    """--json 模式下 stop 不应弹 input() 确认"""
    out, _, rc = run(["stop", "999", "--json"])
    assert rc == 1
    data = json.loads(out)
    assert "error" in data


def test_stop_pause_resume_exclusive():
    _, err, rc = run(["stop", "1", "--pause", "--resume"])
    assert rc == 2
    assert "not allowed" in err


def test_init_help():
    out, _, rc = run(["init", "--help"])
    assert rc == 0
    assert "--token" in out


def test_resources_help():
    out, _, rc = run(["resources", "--help"])
    assert rc == 0
    assert "--json" in out


def test_logs_help():
    out, _, rc = run(["logs", "--help"])
    assert rc == 0
    assert "--events" in out


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
