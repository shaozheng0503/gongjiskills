# /gongji — 共绩算力弹性部署

管理共绩算力 GPU 弹性部署任务。Agent 需要 GPU 算力时自动调用。

TRIGGER: 用户提到"部署"、"发布任务"、"GPU"、"算力"、"共绩"、"弹性部署"、"跑模型"、"推理服务"，或需要创建/管理 GPU 计算任务时触发。

## 命令速查

```bash
gongji init --token <token>                              # 初始化
gongji resources --json                                  # 查GPU资源
gongji images --json                                     # 查镜像模板
gongji images add vllm --image <addr> --gpu 4090 -p 8000  # 添加模板
gongji deploy <image> -n <name> -g <gpu> -c <卡数> -p <port> --json  # 部署
gongji deploy --template <name> -n <name> --json         # 用模板部署
gongji list --json                                       # 列出任务+URL
gongji status <id> --json                                # 任务详情
gongji logs <id>                                         # 容器日志
gongji logs <id> --events                                # 事件（排查失败）
gongji stop <id> -f                                      # 释放资源
```

## Agent 调用关键点

1. **必须用 `--json`** 获取结构化输出
2. deploy 返回 `{"task_id": N, "status": "Running", "urls": [{"url": "https://...", "port": 8080}]}`
3. 错误也是 JSON: `{"error": "..."}`
4. deploy **自动选最便宜的有库存资源**，用 `-c` 指定卡数
5. 等待过程会显示实时事件，失败时自动输出原因
6. `gongji images` 无需配置文件，可在 init 前使用

## 典型 Agent 工作流

```bash
# 1. 部署，拿到URL
gongji deploy my-registry/vllm:latest -n my-llm -g 4090 -p 8080 --json

# 2. 用URL调推理API
# curl https://xxx/v1/chat/completions ...

# 3. 出问题查日志
gongji logs <id> --events

# 4. 用完释放
gongji stop <id> -f --json
```

## deploy 全部参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `<image>` | Docker 镜像地址 | 必填 |
| `-n` | 任务名 | 必填 |
| `-g` | GPU 型号: 4090/H800 | 自动选最便宜 |
| `-c` | GPU 卡数: 1/2/4/8 | 不限 |
| `-p` | 端口 | 8080 |
| `--points` | 节点数 | 1 |
| `--env` | 环境变量 | - |
| `--start-cmd` | 启动命令 | - |
| `--start-args` | 启动参数（引号包裹） | - |
| `--no-wait` | 不等待就绪 | - |
| `--json` | JSON 输出 | - |

## 前置条件

配置不存在时运行: `gongji init --token <your-token>`
或引导用户: https://www.gongjiyun.com → 头像 → API密钥 → RSA模式
