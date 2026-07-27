### Ci-templates

## 生成 SSH 登录密钥

```bash
# 在项目根目录生成 ed25519 密钥对（私钥 deploy_key / 公钥 deploy_key.pub）
ssh-keygen -t ed25519 -C "github-actions" -f deploy_key -N ""
```

生成后：

1. **私钥** `deploy_key`：写入 `deploy-github.toml` 的 `deploy.ssh_key` / `ssh_key_file`，由 `setup_deploy_github.py` 同步到 GitHub Secret `DEPLOY_SSH_KEY`
2. **公钥** `deploy_key.pub`：追加到服务器 `~/.ssh/authorized_keys`（不要只把 `.pub` 文件放进目录）

```bash
# 服务器上（以 root 为例）
mkdir -p /root/.ssh && chmod 700 /root/.ssh
cat deploy_key.pub >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
```

本地验证：

```bash
ssh -i deploy_key root@你的服务器IP
```
