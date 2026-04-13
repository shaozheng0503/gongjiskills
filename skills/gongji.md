# /gongji — 共绩算力弹性部署

管理共绩算力 GPU 弹性部署任务。在 Agent 开发中需要 GPU 算力时自动调用。

TRIGGER: 用户提到"部署"、"发布任务"、"GPU"、"算力"、"共绩"、"弹性部署"、"跑模型"、"推理服务"，或需要创建/管理 GPU 计算任务时触发。

## 使用方式

通过项目根目录下的 `gongji.py` 执行操作：

### 部署任务
```bash
python3 gongji.py deploy <镜像地址> --name <任务名> --gpu <GPU型号> --port <端口>
```

示例:
```bash
# 部署一个推理服务到4090
python3 gongji.py deploy my-registry/my-model:v1 --name my-inference --gpu 4090 --port 8080

# 多端口 + 2节点
python3 gongji.py deploy my-image:latest --name my-svc --gpu 4090 --port 8080,8443 --points 2

# 带启动命令
python3 gongji.py deploy my-image:latest --name my-svc --gpu 4090 --port 8080 --start-cmd "python" --start-args serve.py --host 0.0.0.0
```

### 查看任务列表
```bash
python3 gongji.py list
python3 gongji.py list --status Running
```

### 查看任务状态和访问URL
```bash
python3 gongji.py status <task_id>
python3 gongji.py status <task_id> --json  # 完整详情
```

### 停止/暂停/恢复任务
```bash
python3 gongji.py stop <task_id>            # 删除（不可恢复，需确认）
python3 gongji.py stop <task_id> --force    # 强制删除
python3 gongji.py stop <task_id> --pause    # 暂停（释放资源，可恢复）
python3 gongji.py stop <task_id> --resume   # 恢复暂停的任务
```

## 工作流程

当 Agent 需要 GPU 算力时:

1. 先用 `deploy` 创建任务，会自动查找有库存的 GPU 资源并部署
2. 部署完成后返回访问 URL，Agent 可直接调用该 URL 进行推理
3. 用完后用 `stop` 释放资源，避免持续计费

## 前置条件

需要 `~/.gongji/config.json` 配置文件:
```json
{
  "token": "your-api-token",
  "private_key_path": "~/.gongji/private.key"
}
```

如果配置不存在，引导用户:
1. 登录 https://www.gongjiyun.com 控制台
2. 右上角头像 → API 密钥 → 新建密钥（RSA 加验签模式）
3. 生成 RSA 密钥对: `openssl genrsa -out ~/.gongji/private.key 2048`
4. 导出公钥上传: `openssl rsa -pubout -in ~/.gongji/private.key -out public.pem`
5. 创建配置文件 `~/.gongji/config.json`

## Python API 调用

也可以在代码中直接使用:
```python
from core.client import GongjiClient

client = GongjiClient()

# 查资源
resources = client.search_resources()

# 创建任务
result = client.create_task(
    task_name="my-task",
    mark="resource-mark-from-search",
    service_image="my-image:v1",
    ports=[8080],
)

# 查状态
detail = client.task_detail(task_id=388)

# 停止
client.stop_task(task_id=388)
```
