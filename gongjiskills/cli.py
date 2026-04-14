#!/usr/bin/env python3
"""共绩算力 CLI — init / resources / deploy / list / status / logs / stop"""

import argparse
import json
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from .client import GongjiClient


_json_mode = False

# ── 内置镜像模板 ──────────────────────────────────────────────────────────────

BUILTIN_TEMPLATES: dict[str, dict] = {
    "ffmpeg": {
        "image": "harbor.suanleme.cn/library/ffmpeg-api:cpu",
        "port": "8080",
        "description": "FFmpeg 媒体处理 API",
    },
}


def _templates_path() -> Path:
    return Path.home() / ".gongji" / "templates.json"


def _load_templates() -> dict:
    """加载模板：内置 + 用户自定义（用户覆盖内置）"""
    templates = dict(BUILTIN_TEMPLATES)
    path = _templates_path()
    if path.exists():
        try:
            user = json.loads(path.read_text())
            if isinstance(user, dict):
                templates.update(user)
        except Exception:
            pass
    return templates


def _save_user_templates(user_templates: dict):
    """只保存用户自定义部分"""
    path = _templates_path()
    path.write_text(json.dumps(user_templates, indent=2, ensure_ascii=False))
    os.chmod(str(path), 0o600)


def _get_user_templates() -> dict:
    """加载仅用户自定义部分（不含内置）"""
    path = _templates_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _ok(res: dict) -> bool:
    code = str(res.get("code", ""))
    return code in ("200", "0000")


def _fmt_price(raw) -> str:
    """API 价格单位是微元/秒，转为元/小时"""
    if raw is None:
        return "-"
    yuan_per_hour = raw * 3600 / 1000000
    return f"{yuan_per_hour:.2f}"


def _fmt_mem(mb) -> str:
    """MB 转 GB"""
    if not mb:
        return "0"
    gb = mb / 1024
    return f"{gb:.0f}" if gb == int(gb) else f"{gb:.1f}"


def _fail(msg: str):
    sys.stdout.flush()
    if _json_mode:
        print(json.dumps({"error": msg}, ensure_ascii=False))
        sys.exit(1)
    print(f"错误: {msg}", file=sys.stderr)
    sys.exit(1)


def _json_out(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))
    sys.exit(0)


def _get_latest_event(client, task_id: int) -> str:
    """获取任务最新事件的简短描述"""
    try:
        points_res = client.list_points(task_id)
        if not _ok(points_res):
            return ""
        points = points_res.get("data", {}).get("results", [])
        if not points:
            return ""
        point_id = points[0].get("point_id")
        ev_res = client.pod_event(point_id)
        if not _ok(ev_res):
            return ""
        events = ev_res.get("data", {}).get("events", [])
        if not events:
            return ""
        ev = events[0]
        return f"[{ev.get('reason', '')}] {ev.get('message', '')}"
    except Exception:
        return ""


def _get_fail_reason(client, task_id: int) -> str:
    """获取任务失败原因"""
    try:
        points_res = client.list_points(task_id, status="Failed")
        if not _ok(points_res):
            return ""
        points = points_res.get("data", {}).get("results", [])
        if not points:
            # 尝试查所有节点
            points_res = client.list_points(task_id)
            if not _ok(points_res):
                return ""
            points = points_res.get("data", {}).get("results", [])
        if not points:
            return ""
        point_id = points[0].get("point_id")
        ev_res = client.pod_event(point_id)
        if not _ok(ev_res):
            return ""
        events = ev_res.get("data", {}).get("events", [])
        # 找 Warning 类型事件
        for ev in events:
            if ev.get("type") == "Warning":
                return f"{ev.get('reason', '')}: {ev.get('message', '')}"
        if events:
            return f"{events[0].get('reason', '')}: {events[0].get('message', '')}"
        return ""
    except Exception:
        return ""


def _get_urls(data: dict) -> list:
    """从任务数据中提取所有访问 URL"""
    urls = []
    for svc in data.get("services", []):
        for port in svc.get("remote_ports", []):
            url = port.get("url")
            if url:
                urls.append({"url": url, "port": port.get("service_port")})
    return urls


# ── init ──

def cmd_init(args):
    """引导首次配置"""
    gongji_dir = Path.home() / ".gongji"
    config_path = gongji_dir / "config.json"
    key_path = gongji_dir / "private.key"
    pub_path = gongji_dir / "public.pem"

    print("=== 共绩算力 CLI 初始化 ===\n")
    gongji_dir.mkdir(exist_ok=True)
    os.chmod(str(gongji_dir), 0o700)  # 仅当前用户可访问

    # 1. 生成密钥
    if key_path.exists() and not args.force:
        print(f"私钥已存在: {key_path}（跳过，用 --force 覆盖）")
    else:
        print("生成 RSA 密钥对...")
        subprocess.run(["openssl", "genrsa", "-out", str(key_path), "2048"],
                       check=True, capture_output=True)
        subprocess.run(["openssl", "rsa", "-pubout", "-in", str(key_path), "-out", str(pub_path)],
                       check=True, capture_output=True)
        os.chmod(str(key_path), 0o600)
        os.chmod(str(pub_path), 0o644)
        print(f"  私钥: {key_path}")
        print(f"  公钥: {pub_path}")

    # 2. 显示公钥
    if pub_path.exists():
        print(f"\n请将以下公钥粘贴到共绩算力控制台（API密钥 → RSA模式）：")
        print("-" * 50)
        print(pub_path.read_text().strip())
        print("-" * 50)

    # 3. Token（多种安全传入方式）
    if config_path.exists() and not args.force:
        print(f"\n配置已存在: {config_path}（跳过，用 --force 覆盖）")
    else:
        # 优先级: --token 参数 > GONGJI_TOKEN 环境变量 > 交互输入
        token = args.token or os.environ.get("GONGJI_TOKEN")
        if not token:
            print("\n登录 https://www.gongjiyun.com → 头像 → API密钥")
            print("新建密钥（RSA模式），上传公钥后获取 Token\n")
            token = input("请输入 API Token: ").strip()
        if not token:
            _fail("Token 不能为空")
        config = {"token": token, "private_key_path": str(key_path)}
        config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
        os.chmod(str(config_path), 0o600)  # 仅当前用户可读写
        print(f"配置已写入: {config_path}")

    # 4. 验证
    print("\n验证 API 连通性...")
    try:
        client = GongjiClient()
        res = client.search_resources()
        if _ok(res):
            count = res.get("data", {}).get("count", 0)
            print(f"连接成功! 当前有 {count} 种 GPU 资源可用")
        else:
            msg = res.get("message", "")
            print(f"API 返回: {msg}")
            if "token" in msg.lower():
                print("Token 可能无效，请重新运行 init --force")
    except Exception as e:
        print(f"连接失败: {e}")

    print("\n初始化完成!")


# ── resources ──

def cmd_resources(client: GongjiClient, args):
    """查看可用 GPU 资源"""
    res = client.search_resources()
    if not _ok(res):
        _fail(f"查询失败: {res.get('message', res)}")

    results = res.get("data", {}).get("results", [])
    if not results:
        print("当前无可用 GPU 资源")
        return

    if args.json:
        _json_out(results)

    show_all = args.all
    shown = 0

    # 按最低折扣价排序（便宜的在前）
    def _min_price(d):
        prices = [r.get("discount_price") or r.get("price") or float("inf")
                  for r in d.get("regions", []) if show_all or r.get("inventory", 0) > 0]
        return min(prices) if prices else float("inf")
    results = sorted(results, key=_min_price)

    for device in results:
        gpu = device.get("gpu_name", "?")
        gpu_count = device.get("gpu_count", "?")
        gpu_mem = _fmt_mem(device.get("gpu_memory", 0))
        cpu = device.get("cpu_cores", 0)
        mem = _fmt_mem(device.get("memory", 0))

        # 过滤：默认只显示有库存的区域
        regions = device.get("regions", [])
        if not show_all:
            regions = [r for r in regions if r.get("inventory", 0) > 0]
        if not regions:
            continue

        shown += 1
        print(f"\n{gpu} x{gpu_count}  (显存 {gpu_mem}G | {cpu}核 | {mem}G)")
        print(f"  {'区域':<12} {'库存':<6} {'单价(元/h)':<12} {'折扣价(元/h)':<12}")
        print(f"  {'-'*46}")

        for r in regions:
            region_name = r.get("region_name", "?")
            inventory = r.get("inventory", 0)
            price = _fmt_price(r.get("price"))
            discount = _fmt_price(r.get("discount_price"))
            stock_mark = "" if inventory > 0 else " (售罄)"
            print(f"  {region_name:<12} {inventory:<6} {price:<12} {discount:<12}{stock_mark}")

    total = res.get("data", {}).get("count", 0)
    if show_all:
        print(f"\n共 {total} 种规格")
    else:
        print(f"\n有库存 {shown} 种（共 {total} 种，用 --all 查看全部）")


# ── deploy ──

def _find_cheapest(results: list, gpu_filter: str = None, gpu_count: int = None, region_filter: str = None):
    """找到有库存且最便宜的资源，可按 GPU/卡数/区域 过滤"""
    candidates = []
    for device in results:
        gpu = device.get("gpu_name", "")
        if gpu_filter and gpu_filter.lower() not in gpu.lower():
            continue
        if gpu_count and device.get("gpu_count") != gpu_count:
            continue
        for region_info in device.get("regions", []):
            if region_info.get("inventory", 0) <= 0:
                continue
            if region_filter:
                rname = region_info.get("region_name", "")
                rid = region_info.get("region", "")
                if region_filter.lower() not in rname.lower() and region_filter.lower() not in rid.lower():
                    continue
            price = region_info.get("discount_price") or region_info.get("price")
            if price is None:
                price = float("inf")
            candidates.append((price, device, region_info))

    if not candidates:
        return None, None

    candidates.sort(key=lambda x: x[0])
    _, device, region = candidates[0]
    return device, region


def cmd_deploy(client: GongjiClient, args):
    """查资源 → 选最便宜的 → 创建任务 → 等待就绪 → 返回URL"""

    # 0. 应用模板（如果指定）
    if args.template:
        templates = _load_templates()
        if args.template not in templates:
            _fail(f"模板 [{args.template}] 不存在，用 gongji images 查看可用模板")
        tmpl = templates[args.template]
        # 模板作为默认值，命令行参数优先
        if not args.image:
            args.image = tmpl.get("image")
        if not args.gpu:
            args.gpu = tmpl.get("gpu")
        if args.port == "8080" and tmpl.get("port"):
            args.port = tmpl["port"]
        if not args.start_cmd and tmpl.get("start_cmd"):
            args.start_cmd = tmpl["start_cmd"]
        if not args.start_args and tmpl.get("start_args"):
            args.start_args = tmpl["start_args"]

    if not args.image:
        _fail("缺少镜像地址，请指定 <image> 或 --template <名称>")

    # 1. 校验端口
    try:
        ports = [int(p) for p in args.port.split(",")]
    except ValueError:
        _fail(f"端口格式无效: {args.port}，应为数字，多个用逗号分隔（如 8080,8443）")

    # 2. 查可用资源
    if not args.json:
        print("正在查询可用 GPU 资源...")
    res = client.search_resources()
    if not _ok(res):
        _fail(f"查询资源失败: {res.get('message', res)}")

    results = res.get("data", {}).get("results", [])
    if not results:
        _fail("当前无可用 GPU 资源")

    # 3. 选最便宜的有库存资源
    matched, matched_region = _find_cheapest(
        results, args.gpu, getattr(args, 'gpu_count', None), getattr(args, 'region', None)
    )

    if not matched or not matched_region:
        gpu_hint = f" ({args.gpu})" if args.gpu else ""
        print(f"未找到有库存的 GPU 资源{gpu_hint}", file=sys.stderr)
        print("当前可用资源（用 resources 命令查看详情）:")
        for d in results:
            for r in d.get("regions", []):
                if r.get("inventory", 0) > 0:
                    p = _fmt_price(r.get("discount_price") or r.get("price"))
                    print(f"  {d['gpu_name']} x{d['gpu_count']} | {r['region_name']} | 库存 {r['inventory']} | {p}元/h")
        sys.exit(1)

    mark = matched_region.get("mark", {}).get("mark", "")
    mark_resource = matched_region.get("mark", {}).get("resource", {})
    price = _fmt_price(matched_region.get("discount_price") or matched_region.get("price"))

    if not args.json:
        print(f"选中资源: {matched['gpu_name']} x{matched['gpu_count']} | {matched_region['region_name']} | {price}元/h (最低价)")

    # 4. 创建任务
    create_kwargs = dict(
        task_name=args.name,
        mark=mark,
        service_image=args.image,
        ports=ports,
        gpu_name=mark_resource.get("gpu_name"),
        gpu_count=mark_resource.get("gpu_count"),
        gpu_memory=mark_resource.get("gpu_memory"),
        memory=mark_resource.get("memory"),
        cpu_cores=mark_resource.get("cpu_cores"),
        region=mark_resource.get("region"),
        device_name=mark_resource.get("device_name"),
        points=args.points,
    )
    if args.env:
        create_kwargs["env"] = args.env
    if args.start_cmd:
        create_kwargs["command"] = args.start_cmd
    if args.start_args:
        create_kwargs["args"] = args.start_args.split()

    if not args.json:
        print(f"正在创建任务 [{args.name}]...")
    res = client.create_task(**create_kwargs)
    if not _ok(res):
        _fail(f"创建任务失败: {res.get('message', res)}")

    task_id = res.get("data", {}).get("task_id")
    if not task_id:
        _fail(f"创建任务异常，返回数据: {res}")

    if not args.json:
        print(f"任务已创建, task_id={task_id}")

    # 5. 等待就绪（显示实时事件）
    if not args.no_wait:
        if not args.json:
            print("等待任务启动...")
        retries = 0
        last_event = ""
        for _ in range(60):
            time.sleep(5)
            try:
                detail = client.task_detail(task_id)
                retries = 0
            except Exception:
                retries += 1
                if retries >= 3:
                    _fail(f"连续查询失败，请手动查询: gongji status {task_id}")
                continue

            data = detail.get("data") or {}
            status = data.get("status", "")

            if status == "Running":
                urls = _get_urls(data)
                if args.json:
                    _json_out({"task_id": task_id, "status": "Running", "urls": urls})
                print("Running!")
                for u in urls:
                    print(f"访问地址: {u['url']} (端口 {u['port']})")
                return

            if status in ("End", "Other"):
                # 自动拉事件，告诉用户失败原因
                reason = _get_fail_reason(client, task_id)
                msg = f"任务异常终止 (status={status})"
                if reason:
                    msg += f"\n原因: {reason}"
                _fail(msg)

            # 显示最新事件（不重复）
            if not args.json:
                event = _get_latest_event(client, task_id)
                if event and event != last_event:
                    print(f"  {event}")
                    last_event = event

        _fail(f"等待超时 (5分钟)，请查询: gongji status {task_id}")

    # --no-wait 模式
    if args.json:
        _json_out({"task_id": task_id, "status": "Pending"})
    else:
        print(json.dumps({"task_id": task_id}, ensure_ascii=False))


# ── list ──

def cmd_list(client: GongjiClient, args):
    """列出当前任务"""
    status = args.status if args.status else "Running,Pending"
    res = client.search_tasks(status=status)
    if not _ok(res):
        _fail(f"查询失败: {res.get('message', res)}")

    tasks = res.get("data", {}).get("results", [])
    if not tasks:
        if args.json:
            _json_out([])
        print("当前没有任务")
        return

    if args.json:
        out = []
        for t in tasks:
            out.append({
                "task_id": t.get("task_id"),
                "task_name": t.get("task_name"),
                "status": t.get("status"),
                "urls": _get_urls(t),
            })
        _json_out(out)

    for t in tasks:
        task_id = t.get("task_id", "?")
        name = t.get("task_name", "")
        st = t.get("status", "")
        running = t.get("runing_points", 0)
        total = t.get("points") or running

        gpu_info = ""
        resources = t.get("resources", [])
        if resources:
            r = resources[0].get("resource", {})
            gpu_info = f"{r.get('gpu_name', '')} x{r.get('gpu_count', '')}"

        urls = _get_urls(t)
        print(f"[{task_id}] {name}  {st}  节点 {running}/{total}  {gpu_info}")
        for u in urls:
            print(f"  -> {u['url']} (:{u['port']})")


# ── status ──

def cmd_status(client: GongjiClient, args):
    """查看任务详情和访问URL"""
    res = client.task_detail(args.task_id)
    if not _ok(res):
        _fail(f"查询失败: {res.get('message', res)}")

    data = res.get("data")
    if not data:
        _fail(f"任务 {args.task_id} 不存在")

    if args.json:
        _json_out(data)

    print(f"任务ID:   {data.get('task_id')}")
    print(f"名称:     {data.get('task_name')}")
    print(f"状态:     {data.get('status')}")
    print(f"节点数:   {data.get('runing_points', 0)} / {data.get('points', 0)}")

    resources = data.get("resources", [])
    if resources:
        r = resources[0].get("resource", {})
        print(f"GPU:      {r.get('gpu_name', '')} x{r.get('gpu_count', '')} (显存 {_fmt_mem(r.get('gpu_memory', 0))}G)")
        print(f"内存:     {_fmt_mem(r.get('memory', 0))}G | CPU: {r.get('cpu_cores', 0)} 核")

    billing = data.get("billing_value", 0)
    if billing:
        print(f"已花费:   {billing / 1000000:.2f} 元")

    for u in _get_urls(data):
        print(f"访问地址: {u['url']} (端口 {u['port']})")


# ── logs ──

def cmd_logs(client: GongjiClient, args):
    """查看节点日志或事件"""
    # 先拿任务详情，获取 point/service 信息
    detail = client.task_detail(args.task_id)
    if not _ok(detail):
        _fail(f"查询任务失败: {detail.get('message', detail)}")

    data = detail.get("data")
    if not data:
        _fail(f"任务 {args.task_id} 不存在")

    # 获取节点列表
    points_res = client.list_points(args.task_id)
    if not _ok(points_res):
        _fail(f"查询节点失败: {points_res.get('message', points_res)}")

    points = points_res.get("data", {}).get("results", [])
    if not points:
        _fail(f"任务 {args.task_id} 暂无节点")

    # 对每个节点输出日志或事件
    for pt in points:
        point_id = pt.get("point_id")
        point_name = pt.get("name", f"point-{point_id}")
        point_status = pt.get("status", "?")

        print(f"=== {point_name} ({point_status}) ===")

        if args.events:
            # 查事件
            ev_res = client.pod_event(point_id)
            if _ok(ev_res):
                events = ev_res.get("data", {}).get("events", [])
                if not events:
                    print("  (无事件)")
                for ev in events:
                    etype = ev.get("type", "")
                    reason = ev.get("reason", "")
                    msg = ev.get("message", "")
                    etime = ev.get("event_time", "")
                    print(f"  [{etype}] {reason}: {msg}  ({etime})")
            else:
                print(f"  查询事件失败: {ev_res.get('message', '')}")
        else:
            # 查日志：需要 service_id
            containers = pt.get("containers", [])
            if not containers:
                # 尝试从任务详情拿 service_id
                services = data.get("services", [])
                if services:
                    sid = services[0].get("service_id")
                    if sid:
                        containers = [{"service_id": sid, "service_name": services[0].get("service_name", "")}]

            if not containers:
                print("  (无容器信息，尝试 --events 查看事件)")
                continue

            for c in containers:
                service_id = c.get("service_id")
                if not service_id:
                    continue
                log_res = client.point_log(args.task_id, point_id, service_id)
                if _ok(log_res):
                    logs = log_res.get("data", {}).get("logs", "")
                    if logs:
                        print(logs)
                    else:
                        print("  (日志为空)")
                else:
                    print(f"  查询日志失败: {log_res.get('message', '')}")

        print()


# ── stop ──

def cmd_stop(client: GongjiClient, args):
    """停止/暂停/恢复任务"""
    if args.action == "pause":
        print(f"正在暂停任务 {args.task_id}（资源将释放，可恢复）...")
        res = client.pause_task(args.task_id)
        action = "暂停"
    elif args.action == "resume":
        print(f"正在恢复任务 {args.task_id}...")
        res = client.recover_task(args.task_id)
        action = "恢复"
    else:
        if not args.force and not args.json:
            confirm = input(f"确认删除任务 {args.task_id}？此操作不可恢复 (y/N): ")
            if confirm.lower() != "y":
                print("已取消")
                return
        if not args.json:
            print(f"正在删除任务 {args.task_id}...")
        res = client.stop_task(args.task_id)
        action = "删除"

    if not _ok(res):
        _fail(f"{action}失败: {res.get('message', res)}")

    if args.json:
        _json_out({"task_id": args.task_id, "action": action, "ok": True})

    print(f"任务 {args.task_id} 已{action}")


# ── images ──

def cmd_images(args):
    """管理镜像模板（无需 API 凭据）"""
    subaction = getattr(args, "subaction", None)

    if subaction == "add":
        # gongji images add <name> --image <addr> [--gpu ...] [--port ...] [--desc ...]
        user_tmpls = _get_user_templates()
        entry = {
            "image": args.image,
        }
        if args.gpu:
            entry["gpu"] = args.gpu
        if args.port:
            entry["port"] = args.port
        if args.desc:
            entry["description"] = args.desc
        if args.start_cmd:
            entry["start_cmd"] = args.start_cmd
        if args.start_args:
            entry["start_args"] = args.start_args
        user_tmpls[args.name] = entry
        _save_user_templates(user_tmpls)
        print(f"模板 [{args.name}] 已保存")
        print(f"  镜像: {entry['image']}")
        if entry.get("gpu"):
            print(f"  GPU:  {entry['gpu']}")
        if entry.get("port"):
            print(f"  端口: {entry['port']}")
        print(f"\n部署示例: gongji deploy --template {args.name} -n my-svc")
        return

    if subaction == "rm":
        user_tmpls = _get_user_templates()
        if args.name not in user_tmpls:
            if args.name in BUILTIN_TEMPLATES:
                _fail(f"[{args.name}] 是内置模板，不可删除")
            else:
                _fail(f"模板 [{args.name}] 不存在")
        del user_tmpls[args.name]
        _save_user_templates(user_tmpls)
        print(f"模板 [{args.name}] 已删除")
        return

    # 默认：列出所有模板
    templates = _load_templates()
    user_tmpls = _get_user_templates()

    if args.json:
        _json_out(templates)

    if not templates:
        print("暂无模板，用 gongji images add <name> --image <addr> 添加")
        return

    print(f"{'名称':<16} {'镜像':<50} {'GPU':<8} {'端口':<6} 说明")
    print("-" * 100)
    for name, tmpl in templates.items():
        tag = " [内置]" if name in BUILTIN_TEMPLATES and name not in user_tmpls else ""
        img = tmpl.get("image", "-")
        gpu = tmpl.get("gpu", "-")
        port = tmpl.get("port", "-")
        desc = tmpl.get("description", "")
        print(f"{name + tag:<16} {img:<50} {gpu:<8} {port:<6} {desc}")

    print(f"\n共 {len(templates)} 个模板")
    print("  部署: gongji deploy --template <名称> -n <任务名>")
    print("  添加: gongji images add <名称> --image <镜像地址>")
    print("  删除: gongji images rm <名称>")


# ── main ──

def main():
    parser = argparse.ArgumentParser(
        description="共绩算力 CLI — 弹性部署 GPU 任务",
        epilog="文档: https://github.com/shaozheng0503/gongjiskills",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # init
    p_init = sub.add_parser("init", help="初始化配置（生成密钥、写入Token）")
    p_init.add_argument("--force", "-f", action="store_true", help="覆盖已有配置")
    p_init.add_argument("--token", "-t", default=None, help="直接传入Token（非交互模式，供Agent调用）")

    # resources
    p_res = sub.add_parser("resources", help="查看可用 GPU 资源和价格")
    p_res.add_argument("--all", "-a", action="store_true", help="显示全部（含售罄）")
    p_res.add_argument("--json", "-j", action="store_true", help="JSON格式输出")

    # deploy
    p_deploy = sub.add_parser("deploy", help="创建弹性部署任务")
    p_deploy.add_argument("image", nargs="?", default=None, help="Docker 镜像地址（与 --template 二选一）")
    p_deploy.add_argument("--template", "-t", default=None, help="使用镜像模板（见 gongji images）")
    p_deploy.add_argument("--name", "-n", required=True, help="任务名称")
    p_deploy.add_argument("--gpu", "-g", default=None, help="GPU型号关键词，如 4090/H800")
    p_deploy.add_argument("--gpu-count", "-c", type=int, default=None, help="GPU卡数，如 1/2/4/8")
    p_deploy.add_argument("--region", "-r", default=None, help="区域关键词，如 广东/河南/河北")
    p_deploy.add_argument("--port", "-p", default="8080", help="暴露端口，多个用逗号分隔 (默认 8080)")
    p_deploy.add_argument("--points", type=int, default=1, help="节点数量 (默认 1)")
    p_deploy.add_argument("--env", default=None, help="环境变量")
    p_deploy.add_argument("--start-cmd", default=None, help="容器启动命令")
    p_deploy.add_argument("--start-args", default=None, help="容器启动参数（引号包裹）")
    p_deploy.add_argument("--no-wait", action="store_true", help="不等待任务就绪")
    p_deploy.add_argument("--json", "-j", action="store_true", help="JSON格式输出（供Agent解析）")

    # list
    p_list = sub.add_parser("list", help="列出任务")
    p_list.add_argument("--status", "-s", default=None, help="筛选状态 (默认 Running,Pending)，可选: Paused,End")
    p_list.add_argument("--json", "-j", action="store_true", help="JSON格式输出")

    # status
    p_status = sub.add_parser("status", help="查看任务详情")
    p_status.add_argument("task_id", type=int, help="任务ID")
    p_status.add_argument("--json", "-j", action="store_true", help="JSON格式输出")

    # logs
    p_logs = sub.add_parser("logs", help="查看节点日志")
    p_logs.add_argument("task_id", type=int, help="任务ID")
    p_logs.add_argument("--events", "-e", action="store_true", help="查看事件而非日志（排查启动失败）")

    # images
    p_img = sub.add_parser("images", help="管理镜像模板（无需配置文件）")
    p_img.add_argument("--json", "-j", action="store_true", help="JSON格式输出")
    img_sub = p_img.add_subparsers(dest="subaction")
    p_img_add = img_sub.add_parser("add", help="添加镜像模板")
    p_img_add.add_argument("name", help="模板名称，如 vllm / comfyui")
    p_img_add.add_argument("--image", "-i", required=True, help="Docker 镜像地址")
    p_img_add.add_argument("--gpu", "-g", default=None, help="推荐 GPU 型号，如 4090")
    p_img_add.add_argument("--port", "-p", default=None, help="默认暴露端口")
    p_img_add.add_argument("--desc", "-d", default=None, help="说明")
    p_img_add.add_argument("--start-cmd", default=None, help="默认启动命令")
    p_img_add.add_argument("--start-args", default=None, help="默认启动参数")
    p_img_rm = img_sub.add_parser("rm", help="删除镜像模板")
    p_img_rm.add_argument("name", help="模板名称")

    # stop
    p_stop = sub.add_parser("stop", help="停止/暂停/恢复任务")
    p_stop.add_argument("task_id", type=int, help="任务ID")
    action_group = p_stop.add_mutually_exclusive_group()
    action_group.add_argument("--pause", dest="action", action="store_const", const="pause", help="暂停（可恢复）")
    action_group.add_argument("--resume", dest="action", action="store_const", const="resume", help="恢复暂停的任务")
    p_stop.add_argument("--force", "-f", action="store_true", help="跳过确认直接删除")
    p_stop.add_argument("--json", "-j", action="store_true", help="JSON格式输出")

    args = parser.parse_args()

    # 设置全局 JSON 模式，让 _fail 也输出 JSON
    global _json_mode
    _json_mode = getattr(args, "json", False)

    if args.cmd == "init":
        cmd_init(args)
        return

    # images 命令不需要 API 凭据
    if args.cmd == "images":
        cmd_images(args)
        return

    try:
        client = GongjiClient()
    except (FileNotFoundError, KeyError, ValueError) as e:
        _fail(f"{e}\n\n提示: 运行 python3 gongji.py init 进行初始化配置")

    commands = {
        "resources": cmd_resources,
        "deploy": cmd_deploy,
        "list": cmd_list,
        "status": cmd_status,
        "logs": cmd_logs,
        "stop": cmd_stop,
    }
    try:
        commands[args.cmd](client, args)
    except KeyboardInterrupt:
        print("\n已中断")
        sys.exit(130)
    except Exception as e:
        _fail(str(e))


if __name__ == "__main__":
    main()
