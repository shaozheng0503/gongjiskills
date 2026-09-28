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


def _has_config() -> bool:
    """本机是否已有 ~/.gongji/config.json（无配置时 client 构造先失败，rc=3）"""
    from pathlib import Path as P
    return (P.home() / ".gongji" / "config.json").exists()


def test_deploy_invalid_port():
    _, err, rc = run(["deploy", "img:v1", "-n", "test", "-p", "abc"])
    if not _has_config():
        # 无配置：在端口校验前即退出 3（client 构造失败），合法前置失败
        assert rc == 3
        return
    assert rc == 1  # 本地参数校验 → 一般错误 1
    assert "端口格式无效" in err


def test_deploy_json_error_is_valid_json():
    """--json 模式下报错也必须是合法 JSON，且含 exit_code 字段"""
    out, _, rc = run(["deploy", "img:v1", "-n", "test", "--json"])
    assert rc in (1, 3)
    data = json.loads(out)
    assert "error" in data
    assert "exit_code" in data


def test_exit_code_semantics():
    """退出码语义化：无配置=3；有配置时参数错=1、模板不存在=4"""
    out, _, rc = run(["deploy", "--template", "not-exist-tpl", "-n", "t", "--json"])
    data = json.loads(out)
    if not _has_config():
        assert data["exit_code"] == 3
        return
    # 模板不存在在资源查询前被拦截 → 4
    assert data["exit_code"] == 4
    assert rc == 4


def test_config_missing_exit_code_3():
    """配置文件缺失 → exit_code 3（参数/配置错误）"""
    out, _, rc = run(["list", "--json"])
    # 本机可能已有配置；无配置时应为 3，有配置时 0
    if rc != 0:
        data = json.loads(out)
        assert data.get("exit_code") == 3
        assert rc == 3


def test_list_json_is_valid_json():
    """--json 输出无论成功或失败都必须是合法 JSON"""
    out, _, rc = run(["list", "--json"])
    data = json.loads(out)
    # 成功: list返回数组; 失败: 返回 {"error": "..."}
    assert isinstance(data, (list, dict))


def test_status_json_error_is_valid_json():
    out, _, rc = run(["status", "999", "--json"])
    # 无配置 → 3；有配置但任务不存在 → 1 或 4；均须为合法 JSON
    assert rc in (1, 3, 4)
    data = json.loads(out)
    assert "error" in data


def test_stop_json_no_confirm():
    """--json 模式下 stop 不应弹 input() 确认"""
    out, _, rc = run(["stop", "999", "--json"])
    assert rc in (1, 3)
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


def test_resources_has_all_flag():
    out, _, rc = run(["resources", "--help"])
    assert rc == 0
    assert "--all" in out


def test_ok_accepts_0000():
    """真实 API 返回 code=0000 表示成功"""
    import importlib
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from gongjiskills.cli import _ok
    assert _ok({"code": "0000"}) is True
    assert _ok({"code": "200"}) is True
    assert _ok({"code": 200}) is True
    assert _ok({"code": "401"}) is False
    assert _ok({}) is False


def test_no_urllib3_warning():
    """CLI 输出不应包含 urllib3 Warning"""
    out, err, _ = run(["--help"])
    assert "Warning" not in out
    assert "Warning" not in err


# ── 新增测试：优化项 ──

def test_resources_has_filter_flags():
    """resources 支持 --gpu / --region 筛选"""
    out, _, rc = run(["resources", "--help"])
    assert rc == 0
    assert "--gpu" in out
    assert "--region" in out


def test_deploy_has_ttl_flag():
    """deploy 支持 --ttl 自动释放"""
    out, _, rc = run(["deploy", "--help"])
    assert rc == 0
    assert "--ttl" in out


def test_stop_has_all_flag():
    """stop 支持 --all 批量释放"""
    out, _, rc = run(["stop", "--help"])
    assert rc == 0
    assert "--all" in out


def test_stop_no_task_id_no_all_fails():
    """stop 不加 task_id 也不加 --all 应报错"""
    out, err, rc = run(["stop", "--json"])
    # 无配置 → 3（client 构造失败先触发）；有配置 → 1
    assert rc in (1, 3)
    data = json.loads(out)
    assert "error" in data


def test_merge_resources_dedup():
    """_merge_resources 能合并相同 GPU+卡数+显存 的重复项"""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from gongjiskills.cli import _merge_resources
    raw = [
        {"gpu_name": "4090", "gpu_count": 1, "gpu_memory": 24576,
         "cpu_cores": 16, "memory": 64512,
         "regions": [{"region": "gz", "region_name": "广东一区",
                      "mark": {"mark": "A"}, "inventory": 10}]},
        {"gpu_name": "4090", "gpu_count": 1, "gpu_memory": 24576,
         "cpu_cores": 16, "memory": 64512,
         "regions": [{"region": "hb", "region_name": "河北六区",
                      "mark": {"mark": "B"}, "inventory": 20}]},
        {"gpu_name": "5090", "gpu_count": 1, "gpu_memory": 32768,
         "cpu_cores": 48, "memory": 64512,
         "regions": [{"region": "ah", "region_name": "安徽一区",
                      "mark": {"mark": "C"}, "inventory": 5}]},
    ]
    merged = _merge_resources(raw)
    assert len(merged) == 2, "4090 两个条目应合并为 1 个"
    four = [d for d in merged if d["gpu_name"] == "4090"][0]
    assert len(four["regions"]) == 2
    region_names = {r["region_name"] for r in four["regions"]}
    assert region_names == {"广东一区", "河北六区"}


def test_builtin_templates_expanded():
    """内置模板应来自平台预制镜像，覆盖核心分类（数据源 templates.json）"""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from gongjiskills.cli import BUILTIN_TEMPLATES, CATEGORIES
    from gongjiskills.templates import validate_templates, TEMPLATE_SOURCE
    # 短名 + 代表性分类模板
    must_have = {"vllm", "ollama", "qwen3.5-9b", "whisper", "mineru",
                 "qwen-image", "ubuntu2404", "wan2.2"}
    assert must_have.issubset(set(BUILTIN_TEMPLATES.keys())), \
        f"缺少模板: {must_have - set(BUILTIN_TEMPLATES.keys())}"
    # 数据源应为 JSON（fallback 表示 data/templates.json 有问题）
    assert TEMPLATE_SOURCE == "data", "模板数据应从 data/templates.json 加载"
    # validate_templates 全量通过
    errors = validate_templates(BUILTIN_TEMPLATES, CATEGORIES)
    assert not errors, f"模板校验失败: {errors}"


def test_images_validate_subcommand():
    """gongji images validate 应通过（无需 API 凭据）"""
    out, _, rc = run(["images", "validate"])
    assert rc == 0
    assert "47" in out


def test_ttl_subcommand_exists():
    """gongji ttl 子命令可用（无配置时 list 报 3 而非 argparse 错）"""
    out, _, rc = run(["ttl", "list", "--json"])
    if rc != 0:
        data = json.loads(out)
        assert data.get("exit_code") == 3
    else:
        data = json.loads(out)
        assert isinstance(data, list)


def test_ttl_registry_roundtrip():
    """TTL registry 登记/查询/移除 全流程（monkeypatch HOME）"""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import tempfile
    from pathlib import Path as P
    from gongjiskills import ttl as ttl_mod
    original_home = P.home
    tmpdir = P(tempfile.mkdtemp())
    P.home = staticmethod(lambda: tmpdir)
    try:
        ttl_mod.register(12345, 3600, task_name="unit-test")
        items = ttl_mod.list_expiring()
        assert len(items) == 1
        assert items[0]["task_id"] == 12345
        assert items[0]["expired"] is False
        assert 3500 < items[0]["expires_in"] <= 3600
        ttl_mod.unregister(12345)
        assert ttl_mod.list_expiring() == []
        # 空 registry 的 sweep 不炸
        stats = ttl_mod.sweep(client=None, quiet=True)
        assert stats == {"checked": 0, "expired": 0, "stopped": 0, "ended": 0, "failed": 0}
    finally:
        P.home = original_home


def test_images_command_shows_builtin():
    """gongji images 无 API 凭据也能显示内置模板（按分类分组）"""
    out, _, rc = run(["images"])
    assert rc == 0
    assert "vllm" in out
    assert "qwen-image" in out
    # 应该显示分类标签
    assert "大语言模型推理" in out or "llm" in out


def test_images_json_is_valid():
    out, _, rc = run(["images", "--json"])
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, dict)
    assert "vllm" in data
    # 每条记录有 category 字段
    assert data["vllm"].get("category") == "llm"


def test_images_category_filter():
    """--category 应只输出该分类的模板"""
    out, _, rc = run(["images", "--category", "llm", "--json"])
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, dict)
    assert len(data) > 0
    for name, t in data.items():
        assert t.get("category") == "llm", f"{name} 不是 llm 分类"


def test_images_categories_subcommand():
    """gongji images categories 列出所有分类"""
    out, _, rc = run(["images", "categories", "--json"])
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, dict)
    # 核心分类必须存在且有模板
    assert data.get("llm", 0) > 0
    assert data.get("image-gen", 0) > 0


def test_friendly_error_mapping():
    """_friendly_error 应识别常见错误并给出建议"""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from gongjiskills.client import _friendly_error
    assert "gongji init --force" in _friendly_error("token expired")
    assert "公钥" in _friendly_error("invalid signature")
    assert "充值" in _friendly_error("insufficient balance")
    # 未识别的原样返回
    assert _friendly_error("random error") == "random error"


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
