# /gongji — 共绩算力弹性部署

管理共绩算力 GPU 弹性部署任务。在 Agent 开发中需要 GPU 算力时自动调用。

TRIGGER: 用户提到"部署"、"发布任务"、"GPU"、"算力"、"共绩"、"弹性部署"、"跑模型"、"推理服务"，或需要创建/管理 GPU 计算任务时触发。

## 命令速查

```bash
python3 gongji.py init                    # 首次配置（生成密钥、输入Token）
python3 gongji.py resources               # 查看可用GPU和价格
python3 gongji.py deploy <image> -n <name> -g <gpu> -p <port>   # 部署
python3 gongji.py list                    # 列出任务（含访问地址）
python3 gongji.py status <task_id>        # 任务详情
python3 gongji.py stop <task_id>          # 删除任务
```

## 典型工作流

### 首次使用
```bash
python3 gongji.py init
# 按提示：生成密钥 → 上传公钥到控制台 → 输入Token → 验证连通
```

### Agent 需要GPU时
```bash
# 1. 查看可用资源（可选）
python3 gongji.py resources

# 2. 部署（自动查资源→创建→等Running→返回URL）
python3 gongji.py deploy my-registry/vllm:latest -n my-llm -g 4090 -p 8080

# 3. 拿到访问地址后直接调用
# 输出: 访问地址: https://xxx.suanli.cn:8080 (端口 8080)

# 4. 用完释放
python3 gongji.py stop <task_id> --force
```

### deploy 全部参数
```bash
python3 gongji.py deploy <image> \
  -n <name>             # 任务名（必填）
  -g <gpu>              # GPU型号: 4090/H800（可选，默认自动选）
  -p <port>             # 端口，多个逗号分隔（默认8080）
  --points <N>          # 节点数（默认1）
  --env <env>           # 环境变量
  --start-cmd <cmd>     # 启动命令
  --start-args "<args>" # 启动参数（引号包裹）
  --no-wait             # 不等待就绪
```

### stop 操作
```bash
python3 gongji.py stop <id>            # 删除（需确认）
python3 gongji.py stop <id> -f         # 强制删除
python3 gongji.py stop <id> --pause    # 暂停（可恢复）
python3 gongji.py stop <id> --resume   # 恢复
```

## 前置条件

如果配置不存在，引导用户运行 `python3 gongji.py init`，或手动配置：
1. 登录 https://www.gongjiyun.com → 头像 → API 密钥 → RSA 模式
2. `openssl genrsa -out ~/.gongji/private.key 2048`
3. `openssl rsa -pubout -in ~/.gongji/private.key -out public.pem`，上传公钥
4. 创建 `~/.gongji/config.json`：`{"token": "xxx", "private_key_path": "~/.gongji/private.key"}`

## Python API

```python
from core.client import GongjiClient
client = GongjiClient()
resources = client.search_resources()
result = client.create_task(task_name="x", mark="...", service_image="img:v1", ports=[8080])
detail = client.task_detail(task_id=388)
client.stop_task(task_id=388)
```
