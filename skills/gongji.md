# /gongji — 共绩算力弹性部署

管理共绩算力 GPU 弹性部署任务。Agent 需要 GPU 算力时自动调用。

TRIGGER: 用户提到"部署"、"发布任务"、"GPU"、"算力"、"共绩"、"弹性部署"、"跑模型"、"推理服务"，或需要创建/管理 GPU 计算任务时触发。

## 命令速查

```bash
python3 gongji.py init --token <token>       # 初始化（非交互，Agent用）
python3 gongji.py resources --json            # 查GPU资源（JSON）
python3 gongji.py deploy <image> -n <name> -g <gpu> -p <port> --json  # 部署（JSON返回URL）
python3 gongji.py list --json                 # 列出任务+URL（JSON）
python3 gongji.py status <id> --json          # 任务详情（JSON）
python3 gongji.py logs <id>                   # 查看日志
python3 gongji.py logs <id> --events          # 查看事件（排查启动失败）
python3 gongji.py stop <id> -f                # 释放资源
```

## Agent 调用关键点

1. **用 `--json` 获取结构化输出**，不要解析人类可读文本
2. deploy 返回 `{"task_id": 388, "status": "Running", "urls": [{"url": "https://...", "port": 8080}]}`
3. list 返回 `[{"task_id": 388, "task_name": "...", "status": "...", "urls": [...]}]`
4. deploy **自动选最便宜的有库存资源**
5. 部署失败时用 `logs <id> --events` 查原因

## 典型 Agent 工作流

```bash
# 1. 部署，拿到URL
python3 gongji.py deploy my-registry/vllm:latest -n my-llm -g 4090 -p 8080 --json
# 输出: {"task_id": 388, "status": "Running", "urls": [{"url": "https://xxx:8080", "port": 8080}]}

# 2. 用URL调推理API
# curl https://xxx:8080/v1/chat/completions ...

# 3. 出问题查日志
python3 gongji.py logs 388
python3 gongji.py logs 388 --events

# 4. 用完释放
python3 gongji.py stop 388 -f
```

## deploy 参数

```bash
python3 gongji.py deploy <image> \
  -n <name>             # 任务名（必填）
  -g <gpu>              # GPU型号: 4090/H800（可选）
  -p <port>             # 端口（默认8080）
  --points <N>          # 节点数（默认1）
  --env <env>           # 环境变量
  --start-cmd <cmd>     # 启动命令
  --start-args "<args>" # 启动参数
  --no-wait             # 不等待就绪
  --json                # JSON输出
```

## 前置条件

如果配置不存在，运行:
```bash
python3 gongji.py init --token <your-token>
```
或引导用户: https://www.gongjiyun.com → 头像 → API密钥 → RSA模式
