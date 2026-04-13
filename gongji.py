#!/usr/bin/env python3
"""共绩算力 CLI — deploy / list / status / stop"""

import argparse
import json
import sys
import time

from core.client import GongjiClient


def cmd_deploy(client: GongjiClient, args):
    """查资源 → 创建任务 → 等待就绪 → 返回URL"""

    # 1. 查可用资源
    print(f"正在查询可用 GPU 资源...")
    res = client.search_resources()
    if res.get("code") != "200" and res.get("code") != 200:
        print(f"查询资源失败: {res.get('message', res)}", file=sys.stderr)
        sys.exit(1)

    results = res.get("data", {}).get("results", [])
    if not results:
        print("当前无可用 GPU 资源", file=sys.stderr)
        sys.exit(1)

    # 2. 匹配GPU型号
    matched = None
    matched_region = None
    for device in results:
        gpu = device.get("gpu_name", "")
        if args.gpu and args.gpu.lower() not in gpu.lower():
            continue
        for region_info in device.get("regions", []):
            if region_info.get("inventory", 0) > 0:
                matched = device
                matched_region = region_info
                break
        if matched:
            break

    if not matched or not matched_region:
        gpu_hint = f" ({args.gpu})" if args.gpu else ""
        print(f"未找到有库存的 GPU 资源{gpu_hint}", file=sys.stderr)
        print("当前可用资源:")
        for d in results:
            for r in d.get("regions", []):
                if r.get("inventory", 0) > 0:
                    price = r.get("discount_price") or r.get("price") or "N/A"
                    print(f"  {d['gpu_name']} ×{d['gpu_count']} | {r['region_name']} | 库存 {r['inventory']} | ¥{price}/h")
        sys.exit(1)

    mark = matched_region.get("mark", {}).get("mark", "")
    mark_resource = matched_region.get("mark", {}).get("resource", {})
    price = matched_region.get("discount_price") or matched_region.get("price") or "N/A"

    print(f"选中资源: {matched['gpu_name']} ×{matched['gpu_count']} | {matched_region['region_name']} | ¥{price}/h")

    # 3. 创建任务
    ports = [int(p) for p in args.port.split(",")]
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
    if args.command:
        create_kwargs["command"] = args.command
    if args.args:
        create_kwargs["args"] = args.args

    print(f"正在创建任务 [{args.name}]...")
    res = client.create_task(**create_kwargs)
    if res.get("code") != "200" and res.get("code") != 200:
        print(f"创建任务失败: {res.get('message', res)}", file=sys.stderr)
        sys.exit(1)

    task_id = res["data"]["task_id"]
    print(f"任务已创建, task_id={task_id}")

    # 4. 等待就绪
    if not args.no_wait:
        print("等待任务启动...", end="", flush=True)
        for _ in range(60):
            time.sleep(5)
            detail = client.task_detail(task_id)
            status = detail.get("data", {}).get("status", "")
            if status == "Running":
                print(" Running!")
                _print_task_urls(detail["data"])
                return
            if status in ("End", "Other"):
                print(f"\n任务异常终止, status={status}", file=sys.stderr)
                sys.exit(1)
            print(".", end="", flush=True)
        print("\n等待超时，请手动查询: gongji.py status {task_id}")

    print(json.dumps({"task_id": task_id}, ensure_ascii=False))


def cmd_list(client: GongjiClient, args):
    """列出当前任务"""
    status = args.status if args.status else "Running,Pending,Paused"
    res = client.search_tasks(status=status)
    if res.get("code") != "200" and res.get("code") != 200:
        print(f"查询失败: {res.get('message', res)}", file=sys.stderr)
        sys.exit(1)

    tasks = res.get("data", {}).get("results", [])
    if not tasks:
        print("当前没有任务")
        return

    print(f"{'ID':<8} {'名称':<20} {'状态':<10} {'节点':<6} {'GPU':<20}")
    print("-" * 70)
    for t in tasks:
        gpu_info = ""
        resources = t.get("resources", [])
        if resources:
            r = resources[0].get("resource", {})
            gpu_info = f"{r.get('gpu_name', '')} ×{r.get('gpu_count', '')}"
        print(f"{t.get('task_id', ''):<8} {t.get('task_name', ''):<20} {t.get('status', ''):<10} {t.get('runing_points', 0):<6} {gpu_info:<20}")


def cmd_status(client: GongjiClient, args):
    """查看任务详情和访问URL"""
    res = client.task_detail(args.task_id)
    if res.get("code") != "200" and res.get("code") != 200:
        print(f"查询失败: {res.get('message', res)}", file=sys.stderr)
        sys.exit(1)

    data = res.get("data")
    if not data:
        print(f"任务 {args.task_id} 不存在")
        sys.exit(1)

    print(f"任务ID:   {data.get('task_id')}")
    print(f"名称:     {data.get('task_name')}")
    print(f"状态:     {data.get('status')}")
    print(f"节点数:   {data.get('runing_points', 0)} / {data.get('points', 0)}")

    resources = data.get("resources", [])
    if resources:
        r = resources[0].get("resource", {})
        print(f"GPU:      {r.get('gpu_name', '')} ×{r.get('gpu_count', '')}")
        print(f"内存:     {r.get('memory', 0)} MB | CPU: {r.get('cpu_cores', 0)} 核")

    _print_task_urls(data)

    if args.json:
        print("\n完整数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_stop(client: GongjiClient, args):
    """停止/暂停任务"""
    if args.pause:
        print(f"正在暂停任务 {args.task_id}（资源将释放，可恢复）...")
        res = client.pause_task(args.task_id)
        action = "暂停"
    elif args.resume:
        print(f"正在恢复任务 {args.task_id}...")
        res = client.recover_task(args.task_id)
        action = "恢复"
    else:
        if not args.force:
            confirm = input(f"确认删除任务 {args.task_id}？此操作不可恢复 (y/N): ")
            if confirm.lower() != "y":
                print("已取消")
                return
        print(f"正在删除任务 {args.task_id}...")
        res = client.stop_task(args.task_id)
        action = "删除"

    if res.get("code") != "200" and res.get("code") != 200:
        print(f"{action}失败: {res.get('message', res)}", file=sys.stderr)
        sys.exit(1)

    print(f"任务 {args.task_id} 已{action}")


def _print_task_urls(data: dict):
    """打印任务的访问URL"""
    services = data.get("services", [])
    for svc in services:
        for port in svc.get("remote_ports", []):
            url = port.get("url")
            if url:
                print(f"访问地址: {url} (端口 {port.get('service_port')})")


def main():
    parser = argparse.ArgumentParser(description="共绩算力 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # deploy
    p_deploy = sub.add_parser("deploy", help="创建弹性部署任务")
    p_deploy.add_argument("image", help="Docker 镜像地址")
    p_deploy.add_argument("--name", "-n", required=True, help="任务名称")
    p_deploy.add_argument("--gpu", "-g", default=None, help="GPU型号关键词，如 4090/H800")
    p_deploy.add_argument("--port", "-p", default="8080", help="暴露端口，多个用逗号分隔")
    p_deploy.add_argument("--points", type=int, default=1, help="节点数量 (默认1)")
    p_deploy.add_argument("--env", default=None, help="环境变量")
    p_deploy.add_argument("--command", default=None, help="启动命令")
    p_deploy.add_argument("--args", nargs="*", default=None, help="启动参数")
    p_deploy.add_argument("--no-wait", action="store_true", help="不等待任务就绪")

    # list
    p_list = sub.add_parser("list", help="列出任务")
    p_list.add_argument("--status", "-s", default=None, help="筛选状态: Running,Pending,Paused,End")

    # status
    p_status = sub.add_parser("status", help="查看任务详情")
    p_status.add_argument("task_id", type=int, help="任务ID")
    p_status.add_argument("--json", "-j", action="store_true", help="输出完整JSON")

    # stop
    p_stop = sub.add_parser("stop", help="停止/暂停/恢复任务")
    p_stop.add_argument("task_id", type=int, help="任务ID")
    p_stop.add_argument("--pause", action="store_true", help="暂停（可恢复）")
    p_stop.add_argument("--resume", action="store_true", help="恢复暂停的任务")
    p_stop.add_argument("--force", "-f", action="store_true", help="跳过确认直接删除")

    args = parser.parse_args()
    client = GongjiClient()

    commands = {
        "deploy": cmd_deploy,
        "list": cmd_list,
        "status": cmd_status,
        "stop": cmd_stop,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
