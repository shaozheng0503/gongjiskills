"""镜像模板库 — 数据与逻辑分离

模板数据存放在包内 ``data/templates.json``（随 pip 安装分发），
本模块只负责加载、校验、合并用户自定义模板。

数据维护（手工流程，平台暂无公开数据源）：
    1. 编辑 ``gongjiskills/data/templates.json``
    2. 运行 ``gongji images validate`` 校验格式
    3. 发版

用户自定义模板存 ``~/.gongji/templates.json``（权限 600），
与内置重名时按字段覆盖、未覆盖字段保留。

字段说明：
    image (必填) : Docker 镜像地址（必须 harbor.suanleme.cn/ 前缀）
    category     : 分类 key（见 CATEGORIES）
    description  : 简要说明（中文）
    port         : 默认暴露端口，多个用逗号分隔
    gpu          : 推荐 GPU 型号关键词（如 4090 / H20）
    gpu_count    : 推荐 GPU 卡数（整数）
    env          : 环境变量字符串（KEY=val KEY2=val2）
    start_cmd    : 容器启动命令
    start_args   : 启动参数，list[str] 或 str
    docs         : 平台文档链接
    note         : 备注（硬件要求等）
"""

from __future__ import annotations

import json
from pathlib import Path

# 分类定义保留在代码里（结构性配置，非易变数据）
CATEGORIES: dict[str, str] = {
    "llm": "大语言模型推理",
    "multimodal": "多模态视觉",
    "image-gen": "文生图",
    "image-edit": "图像编辑/人像",
    "video": "视频生成",
    "3d": "3D 重建",
    "audio": "语音合成/识别",
    "music": "音乐生成",
    "ocr": "文档解析/OCR",
    "dev": "训练/开发环境",
    "tools": "工具类",
}

# JSON 数据文件缺失/损坏时的最小回退集（保证 deploy 核心路径可用）
_FALLBACK_TEMPLATES: dict[str, dict] = {
    "vllm": {
        "image": "harbor.suanleme.cn/public-hub/vllm-openai:v0.19.0-copy",
        "category": "llm",
        "description": "平台预制 vLLM（回退内置）",
        "port": "8000",
        "gpu": "4090",
    },
    "qwen3.5-9b": {
        "image": "harbor.suanleme.cn/public-hub/qwen35-9b:v0.17.0-rc1",
        "category": "llm",
        "description": "Qwen3.5-9B vLLM 推理（回退内置）",
        "port": "8000",
        "gpu": "4090",
    },
    "z-image": {
        "image": "harbor.suanleme.cn/public-hub/z-image:0.11.0-20260129113314700",
        "category": "image-gen",
        "description": "Z-Image 文生图（回退内置）",
        "port": "8188,3000",
        "gpu": "4090",
    },
}


def _data_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "templates.json"


def _load_builtin() -> tuple[dict, str]:
    """加载内置模板 JSON。返回 (templates, source)，
    source 为 'data'（正常）或 'fallback'（JSON 不可用时）。"""
    path = _data_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        templates = raw.get("templates")
        if isinstance(templates, dict) and templates:
            # 基本合法性：每条都有 image
            clean = {
                name: t for name, t in templates.items()
                if isinstance(t, dict) and t.get("image")
            }
            if clean:
                return clean, "data"
    except (json.JSONDecodeError, OSError):
        pass
    return dict(_FALLBACK_TEMPLATES), "fallback"


# 兼容旧接口：cli.py 与测试直接 import BUILTIN_TEMPLATES
BUILTIN_TEMPLATES, TEMPLATE_SOURCE = _load_builtin()


def group_by_category(templates: dict) -> dict[str, list[tuple[str, dict]]]:
    """把模板按 category 分组，返回 {category_key: [(name, tmpl), ...]}

    未指定分类的模板放在 "_uncategorized"。
    """
    groups: dict[str, list[tuple[str, dict]]] = {}
    for name, tmpl in templates.items():
        cat = tmpl.get("category") or "_uncategorized"
        groups.setdefault(cat, []).append((name, tmpl))
    for cat in groups:
        groups[cat].sort(key=lambda x: x[0])
    return groups


def validate_templates(templates: dict | None = None, categories: dict | None = None) -> list[str]:
    """校验模板数据合法性，返回错误列表（空列表 = 全部通过）。

    校验规则：
    - image 必填且以 harbor.suanleme.cn/ 开头（平台内网 registry）
    - category 必填且在 CATEGORIES 中
    - port 若存在必须为逗号分隔的数字
    - gpu_count 若存在必须为正整数
    """
    tmpl = templates if templates is not None else BUILTIN_TEMPLATES
    cats = categories if categories is not None else CATEGORIES
    errors: list[str] = []
    for name, t in tmpl.items():
        if not isinstance(t, dict):
            errors.append(f"{name}: 条目必须是对象")
            continue
        image = t.get("image", "")
        if not image:
            errors.append(f"{name}: 缺少 image")
        elif not image.startswith("harbor.suanleme.cn/"):
            errors.append(f"{name}: 镜像不是平台 registry 地址: {image}")
        cat = t.get("category")
        if not cat:
            errors.append(f"{name}: 缺少 category")
        elif cat not in cats:
            errors.append(f"{name}: category [{cat}] 不在 CATEGORIES 中")
        port = t.get("port")
        if port is not None:
            for p in str(port).split(","):
                if not p.strip().isdigit():
                    errors.append(f"{name}: port 含非数字: {port}")
                    break
        gc = t.get("gpu_count")
        if gc is not None and (not isinstance(gc, int) or gc < 1):
            errors.append(f"{name}: gpu_count 必须为正整数: {gc}")
    return errors
