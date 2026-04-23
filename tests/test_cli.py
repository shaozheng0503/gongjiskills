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


def test_list_json_is_valid_json():
    """--json 输出无论成功或失败都必须是合法 JSON"""
    out, _, rc = run(["list", "--json"])
    data = json.loads(out)
    # 成功: list返回数组; 失败: 返回 {"error": "..."}
    assert isinstance(data, (list, dict))


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
    assert rc == 1
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
    """内置模板应来自平台预制镜像，覆盖核心分类"""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from gongjiskills.cli import BUILTIN_TEMPLATES, CATEGORIES
    # 短名 + 代表性分类模板
    must_have = {"vllm", "ollama", "qwen3.5-9b", "whisper", "mineru",
                 "qwen-image", "ubuntu2404", "wan2.2"}
    assert must_have.issubset(set(BUILTIN_TEMPLATES.keys())), \
        f"缺少模板: {must_have - set(BUILTIN_TEMPLATES.keys())}"
    # 每个模板必须有 image + category，category 必须是合法值
    for name, t in BUILTIN_TEMPLATES.items():
        assert "image" in t, f"模板 {name} 缺 image"
        # 只接受平台 registry 的镜像（杜绝假的上游镜像混进来）
        assert t["image"].startswith("harbor.suanleme.cn/"), \
            f"模板 {name} 的镜像不是平台镜像: {t['image']}"
        assert "category" in t, f"模板 {name} 缺 category"
        assert t["category"] in CATEGORIES, \
            f"模板 {name} 的 category [{t['category']}] 不在 CATEGORIES 中"


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
