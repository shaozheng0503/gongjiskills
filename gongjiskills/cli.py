#!/usr/bin/env python3
"""共绩算力 CLI — init / resources / deploy / list / status / logs / stop"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .client import GongjiClient


_json_mode = False


def _ok(res: dict) -> bool:
    return str(res.get("code")) == "200"


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
        print(f"  私钥: {key_path}")
        print(f"  公钥: {pub_path}")

    # 2. 显示公钥
    if pub_path.exists():
        print(f"\n请将以下公钥粘贴到共绩算力控制台（API密钥 → RSA模式）：")
        print("-" * 50)
        print(pub_path.read_text().strip())
        print("-" * 50)

    # 3. Token（支持 --token 非交互模式）
    if config_path.exists() and not args.force:
        print(f"\n配置已存在: {config_path}（跳过，用 --force 覆盖）")
    else:
        token = args.token
        if not token:
            print("\n登录 https://www.gongjiyun.com → 头像 → API密钥")
            print("新建密钥（RSA模式），上传公钥后获取 Token\n")
            token = input("请输入 API Token: ").strip()
        if not token:
            _fail("Token 不能为空")
        config = {"token": token, "private_key_path": str(key_path)}
        config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
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

    for device in results:
        gpu = device.get("gpu_name", "?")
        gpu_count = device.get("gpu_count", "?")
        gpu_mem = device.get("gpu_memory", 0)
        cpu = device.get("cpu_cores", 0)
        mem = device.get("memory", 0)

        print(f"\n{gpu} x{gpu_count}  (显存 {gpu_mem}G | {cpu}核 | {mem // 1024}G 内存)")
        print(f"  {'区域':<12} {'库存':<6} {'原价':<10} {'折扣价':<10}")
        print(f"  {'-'*42}")

        for r in device.get("regions", []):
            region_name = r.get("region_name", "?")
            inventory = r.get("inventory", 0)
            price = r.get("price") or "-"
            discount = r.get("discount_price") or "-"
            stock_mark = "" if inventory > 0 else " (售罄)"
            print(f"  {region_name:<12} {inventory:<6} {price:<10} {discount:<10}{stock_mark}")

    count = res.get("data", {}).get("count", 0)
    print(f"\n共 {count} 种规格")


# ── deploy ──

def _find_cheapest(results: list, gpu_filter: str = None):
    """找到有库存且最便宜的资源"""
    candidates = []
    for device in results:
        gpu = device.get("gpu_name", "")
        if gpu_filter and gpu_filter.lower() not in gpu.lower():
            continue
        for region_info in device.get("regions", []):
            if region_info.get("inventory", 0) <= 0:
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
    matched, matched_region = _find_cheapest(results, args.gpu)

    if not matched or not matched_region:
        gpu_hint = f" ({args.gpu})" if args.gpu else ""
        print(f"未找到有库存的 GPU 资源{gpu_hint}", file=sys.stderr)
        print("当前可用资源（用 resources 命令查看详情）:")
        for d in results:
            for r in d.get("regions", []):
                if r.get("inventory", 0) > 0:
                    price = r.get("discount_price") or r.get("price") or "N/A"
                    print(f"  {d['gpu_name']} x{d['gpu_count']} | {r['region_name']} | 库存 {r['inventory']} | {price}/h")
        sys.exit(1)

    mark = matched_region.get("mark", {}).get("mark", "")
    mark_resource = matched_region.get("mark", {}).get("resource", {})
    price = matched_region.get("discount_price") or matched_region.get("price") or "N/A"

    if not args.json:
        print(f"选中资源: {matched['gpu_name']} x{matched['gpu_count']} | {matched_region['region_name']} | {price}/h (最低价)")

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

    # 5. 等待就绪
    if not args.no_wait:
        if not args.json:
            print("等待任务启动", end="", flush=True)
        retries = 0
        for _ in range(60):
            time.sleep(5)
            try:
                detail = client.task_detail(task_id)
                retries = 0
            except Exception:
                retries += 1
                if retries >= 3:
                    if not args.json:
                        print()
                    _fail(f"连续查询失败，请手动查询: python3 gongji.py status {task_id}")
                if not args.json:
                    print("!", end="", flush=True)
                continue

            data = detail.get("data") or {}
            status = data.get("status", "")
            if status == "Running":
                urls = _get_urls(data)
                if args.json:
                    _json_out({"task_id": task_id, "status": "Running", "urls": urls})
                print(" Running!")
                for u in urls:
                    print(f"访问地址: {u['url']} (端口 {u['port']})")
                return
            if status in ("End", "Other"):
                if not args.json:
                    print()
                _fail(f"任务异常终止, status={status}")
            if not args.json:
                print(".", end="", flush=True)

        if not args.json:
            print()
        _fail(f"等待超时，请手动查询: python3 gongji.py status {task_id}")

    # --no-wait 模式
    if args.json:
        _json_out({"task_id": task_id, "status": "Pending"})
    print(json.dumps({"task_id": task_id}, ensure_ascii=False))


# ── list ──

def cmd_list(client: GongjiClient, args):
    """列出当前任务"""
    status = args.status if args.status else "Running,Pending,Paused"
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
        print(f"GPU:      {r.get('gpu_name', '')} x{r.get('gpu_count', '')}")
        print(f"内存:     {r.get('memory', 0)} MB | CPU: {r.get('cpu_cores', 0)} 核")

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
    p_res.add_argument("--json", "-j", action="store_true", help="JSON格式输出")

    # deploy
    p_deploy = sub.add_parser("deploy", help="创建弹性部署任务")
    p_deploy.add_argument("image", help="Docker 镜像地址")
    p_deploy.add_argument("--name", "-n", required=True, help="任务名称")
    p_deploy.add_argument("--gpu", "-g", default=None, help="GPU型号关键词，如 4090/H800")
    p_deploy.add_argument("--port", "-p", default="8080", help="暴露端口，多个用逗号分隔 (默认 8080)")
    p_deploy.add_argument("--points", type=int, default=1, help="节点数量 (默认 1)")
    p_deploy.add_argument("--env", default=None, help="环境变量")
    p_deploy.add_argument("--start-cmd", default=None, help="容器启动命令")
    p_deploy.add_argument("--start-args", default=None, help="容器启动参数（引号包裹）")
    p_deploy.add_argument("--no-wait", action="store_true", help="不等待任务就绪")
    p_deploy.add_argument("--json", "-j", action="store_true", help="JSON格式输出（供Agent解析）")

    # list
    p_list = sub.add_parser("list", help="列出任务")
    p_list.add_argument("--status", "-s", default=None, help="筛选状态: Running,Pending,Paused,End")
    p_list.add_argument("--json", "-j", action="store_true", help="JSON格式输出")

    # status
    p_status = sub.add_parser("status", help="查看任务详情")
    p_status.add_argument("task_id", type=int, help="任务ID")
    p_status.add_argument("--json", "-j", action="store_true", help="JSON格式输出")

    # logs
    p_logs = sub.add_parser("logs", help="查看节点日志")
    p_logs.add_argument("task_id", type=int, help="任务ID")
    p_logs.add_argument("--events", "-e", action="store_true", help="查看事件而非日志（排查启动失败）")

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
