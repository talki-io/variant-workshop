# AWS EC2 + Caddy 部署实录

本文记录 **2026-07-10 实际跑通的一次部署**，不是设想方案。命令都在真实机器上执行过。
栈本身的说明见 [`README.md`](README.md)；为什么是单机 Compose 见 [ADR 0004](../docs/decisions/0004-deployment-single-node-compose.md)。

**线上环境**：`https://sahamdata.top` · Ubuntu 22.04 · 2 vCPU / 7.6 GB / 155 GB · us-east-2

---

## 拓扑：两层反代，各司其职

Caddy 只做两件事——终结 TLS、反代到 8080。静态资源、SPA fallback、`/api` 全在容器内的 nginx 处理。

```
公网 :443 ──► Caddy（Let's Encrypt 自动签发/续期、HSTS）
                 └─反代─► 127.0.0.1:8080 ──► 容器内 nginx
                                                 ├─ 静态资源 + SPA fallback
                                                 └─ /api ──► backend ──► db
```

暴露面（服务器上 `ss -ltnp` 实测）：公网只有 `:22` `:80` `:443`；`8080` 只绑回环；db 与 backend 无宿主端口。
**所以即便安全组放行了 8080，外部也进不来**——进程层面就不监听公网。

---

## 部署步骤

### 1. 装 Docker

Ubuntu 官方源的 docker.io 版本旧，用 Docker 官方仓库：

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker ubuntu   # 需重新登录才生效
sudo systemctl enable --now docker
```

### 2. 拉代码到 `/opt`（**不要放 `/www` 或任何 web 根目录**）

私有仓库用只读 deploy key：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/gh_deploy -N "" -C "ec2-deploy"
cat ~/.ssh/gh_deploy.pub    # 加到 GitHub → Settings → Deploy keys（勾只读）

sudo mkdir -p /opt && sudo chown $USER:$USER /opt && cd /opt
GIT_SSH_COMMAND="ssh -i ~/.ssh/gh_deploy -o IdentitiesOnly=yes" \
  git clone git@github.com:talki-io/variant-workshop.git
cd variant-workshop
git config core.sshCommand "ssh -i ~/.ssh/gh_deploy -o IdentitiesOnly=yes"   # 固化，之后 git pull 直接可用
```

### 3. 配 `.env` 并起栈

```bash
cd deploy && cp .env.example .env && chmod 600 .env
openssl rand -base64 24   # → POSTGRES_PASSWORD
openssl rand -hex 32      # → JWT_SECRET

cd /opt/variant-workshop
docker compose -f deploy/docker-compose.prod.yml up -d --build   # 首次 3–5 分钟，大头是拉 Chromium
```

`HTTP_BIND` 保持 `127.0.0.1:8080`。启动时自动跑 `alembic upgrade head`。

### 4. 建管理员

生产 `SEED_DEMO_DATA=false`，空库没有任何用户：

```bash
# 素材员（默认 editor）
docker compose -f deploy/docker-compose.prod.yml exec backend python -m app.create_user 001
# 管理员
docker compose -f deploy/docker-compose.prod.yml exec backend python -m app.create_user admin --role admin
```

顺手确认后门堵上了（应返回 401）：

```bash
curl -so /dev/null -w '%{http_code}\n' -X POST localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' -d '{"username":"admin","password":"demo1234"}'
```

### 5. Caddy + HTTPS

DNS 的 A 记录先指向本机公网 IP（根域和 `www` 都要），否则 ACME 的 HTTP-01 验证过不了。

```bash
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update && sudo apt-get install -y caddy
```

`/etc/caddy/Caddyfile`：

```caddyfile
sahamdata.top, www.sahamdata.top {
	reverse_proxy 127.0.0.1:8080

	header {
		Strict-Transport-Security "max-age=31536000; includeSubDomains"
		-Server
	}

	log {
		output file /var/log/caddy/access.log {
			roll_size 10MiB
			roll_keep 3
		}
	}
}
```

```bash
sudo systemctl restart caddy
sudo journalctl -u caddy -f | grep certificate   # 等 "certificate obtained successfully"
```

安全组只放行 `22 / 80 / 443`。**8080 不要放行。**

### 6. 备份

`/opt/backup-vw.sh` + crontab `0 3 * * *`，`pg_dump -Fc` 到 `/opt/backups`，保留 14 天。
脚本里 `docker compose exec` 必须带 `</dev/null`（见下）。

---

## 踩过的坑（按被坑顺序）

### `docker compose exec -T` 会吞掉 stdin

在 heredoc 或 `while read` 循环里调用它，**后续所有命令都会被它读走**。表现为脚本静默截断、只执行了一部分。

```bash
# 错：循环只跑一次，后面的行被 exec 吃掉
while read -r line; do
  docker compose exec -T backend python -m app.create_user "$line"
done < users.txt

# 对：
  docker compose exec -T backend python -m app.create_user "$line" </dev/null
```

### 不要用 `sudo caddy validate`

它会以 root 身份实例化日志写入器，创建出 `root:root 600` 的 `/var/log/caddy/access.log`。
之后 caddy 服务以 `caddy` 用户启动就 `permission denied`，且报错完全不提日志文件权限，很容易误判成证书问题。

用 `sudo systemctl reload caddy` 让服务自己校验配置。

### `restart` 不重读 `.env`

`env_file` 只在容器**创建**时注入。改完 `deploy/.env` 必须：

```bash
docker compose -f deploy/docker-compose.prod.yml up -d --force-recreate backend
```

`docker compose restart backend` 会让你以为改动生效了，其实没有。

### 富化只在入库那一刻发生

M3 的 Haiku 富化开关是 `enrich = USE_REAL_LLM and bool(ANTHROPIC_API_KEY)`，在**抓取时**求值。

**先填 key，再抓新闻。** 顺序反了，那批新闻会「裸抓」入库：没有要点/标的抽取、`label=none`、相关性硬过滤整个跳过（无关新闻全部留在库里）。而且富化**不会回填**——只能删掉重抓。

重抓前必须清 `etag` / `last_modified`，否则条件请求返回 304，什么也抓不到：

```sql
update crawl_source set etag=null, last_modified=null;
```

### Chromium 需要更大的 `/dev/shm`

Docker 默认给 64 MB，Playwright 渲染重页面会崩。compose 已设 `shm_size: 1gb`。

### nginx 的 60s 代理超时

生成一批变体常到分钟级。容器内 nginx 已设 `proxy_read_timeout 300s`。
**Caddy 的 `reverse_proxy` 默认不设响应超时**，所以 Caddy 这层不用调（这点和 nginx 相反）。

---

## 已知问题

**IDX 源抓不到内容。** `crawl_playwright.py` 的选择器（`.bzg_c` / `.card-title`）按 IDX 旧版结构写死，站点改版后返回「渲染成功但未抽到匹配的新闻链接」，而 `health` 仍标成 `ok` —— 抓取源页面看起来正常，实际零产出。

**定时抓取漏掉 HTML 类型源。** `scheduler.py` 只查 `type == "RSS"` 和 `type == "Playwright"`；OJK 是 `type == "HTML"`，因此打开 `CRAWL_SCHEDULER_ENABLED` 后它永远不会被自动抓，只能手动触发。`sources.py` 的手动抓取端点是支持 HTML 的。

**中文文案没有确定性合规护栏。** `compliance/rules.py` 的 34 条禁词全是印尼语/英语，而系统已切换为生成中文文案。规则层（确定性）对中文完全失效，只剩 Haiku 语义层（概率判断）在兜底——生成管线会拦下，但 `POST /api/compliance/check` 只跑规则层，素材员拿中文文案自检几乎永远得到 `pass`。补中文词表涉及合规口径，属业务/法务决策。

**系统没有修改密码功能。** `auth.py` 只有 `login` 与 `/me`。换密码 = 删号重建。

---

## 🔴 红线 A-1

部署 ≠ 放行投放。系统没有对外发布端点，把它跑起来不触碰 A-1；
**拿产出的文案对外投放**仍需需求方法务书面确认。见 [`docs/decisions/0001-arch-review-closure.md`](../docs/decisions/0001-arch-review-closure.md)。
