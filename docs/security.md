# 安全

## 凭据保护

| 文件 | 权限 | 说明 |
|------|------|------|
| `~/.gongji/` | `700` | 仅当前用户可访问 |
| `~/.gongji/private.key` | `600` | RSA 私钥 |
| `~/.gongji/config.json` | `600` | 含 token |
| `~/.gongji/public.pem` | `644` | 公钥（不敏感） |

加载配置时**自动检测权限**，过宽时输出警告和修复命令：

```
⚠️  警告：~/.gongji/private.key 权限过宽 (644)，可能被其他用户读取
  修复：chmod 600 ~/.gongji/private.key
```

## Token 传入方式（按安全性排序）

1. **环境变量**（最推荐）

   ```bash
   GONGJI_TOKEN=xxx gongji init --force
   ```

   不会进 shell history。

2. **stdin 管道**

   ```bash
   echo $TOKEN | gongji init --force
   ```

3. **命令行参数**

   ```bash
   gongji init --token xxx --force
   ```

   ⚠️ 会进 shell history，CI/Agent 场景慎用。

4. **交互输入**

   默认情况，终端打 echo 关掉提示输入。

## RSA 签名

每次请求都签名：

```
sign_string = f"{path}\n{version}\n{timestamp}\n{token}\n{body}"
signature = RSA_PKCS1v15_SHA256(private_key, sign_string)
```

- `timestamp` 每次不同，防重放
- 请求不可伪造（签名必须由私钥生成，私钥只在客户端本地）
- 详细规范见 [共绩官方 RSA 模式说明](https://www.gongjiyun.com/docs/platform/openapi/m3p6whioxidzwaksughc4gfhnro/)

## Token 失效 / 重置

控制台 → 头像 → API 密钥 → 重新生成 → `gongji init --force`。

## 多账号

目前 `~/.gongji/` 是硬编码。变通：用不同用户跑，或开 Issue 加 `GONGJI_DIR` 环境变量。
