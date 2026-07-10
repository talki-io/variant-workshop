# 在宝塔面板服务器上部署

前置：服务器已装宝塔 + Docker。通用部署说明见 [`README.md`](README.md)，本文只讲**宝塔特有的部分**。

> 本文的命令未在宝塔环境实测过（写它的时候手头只有本地 Docker）。每一步都给了自检命令，按输出走。

---

## 核心思路：两层 Nginx，各干各的

宝塔的 Nginx 已经占着 80/443。本项目的栈里也有一个 Nginx（容器内），但它默认只绑 `127.0.0.1:8080`，**不和宝塔抢端口**。

```
公网 :443 ──► 宝塔 Nginx          终结 TLS（Let's Encrypt）
                  │
                  ▼ 反代
            127.0.0.1:8080 ──► 容器内 nginx     静态资源 + SPA fallback + /api 反代
                                    │
                                    ▼
                                 backend  ──►  db
```

所以宝塔那层只做两件事：**终结 HTTPS** 和 **反代到 8080**。别让它去碰静态文件。

---

## 0. 先自检

SSH 上服务器跑一遍，四条输出决定后面怎么走：

```bash
docker compose version                  # 需要 v2.x；只有 docker-compose(v1) 的话 compose 文件里的 deploy.resources 不生效
df -h /var/lib/docker                   # 后端镜像带 Chromium，留够 5G
curl -s -o /dev/null -w "docker-hub:%{http_code}\n" https://registry-1.docker.io/v2/
curl -s -o /dev/null -m 10 -w "anthropic:%{http_code}\n" https://api.anthropic.com/v1/messages
```

- `anthropic:401` → 通（401 是没带 key，说明网络到得了）。
- `anthropic:000` 或超时 → **不通**，服务器多半在中国大陆。不影响部署，但要按 [§7](#7-服务器在中国大陆时) 配中转，否则生成功能起不来。
- `docker-hub` 非 200/401 → 拉不动镜像，先在宝塔 Docker 模块配镜像加速器。

---

## 1. 放代码：**不要放在 `/www/wwwroot`**

宝塔的站点目录会被 Nginx 直接当静态根暴露。代码放进去，`deploy/.env`（里面有数据库密码和 `ANTHROPIC_API_KEY`）可能被当成普通文件请求到。

放到面板管不着的地方：

```bash
mkdir -p /opt && cd /opt
git clone https://github.com/talki-io/variant-workshop.git
cd variant-workshop
```

私有仓库要认证，用 deploy key 或 PAT（PAT 会留在 `.git/config` 里，注意权限）。

---

## 2. 填密钥

```bash
cd /opt/variant-workshop/deploy
cp .env.example .env
chmod 600 .env

openssl rand -base64 24   # → POSTGRES_PASSWORD
openssl rand -hex 32      # → JWT_SECRET
                          # → ANTHROPIC_API_KEY 填你自己的
```

**`HTTP_BIND` 保持 `127.0.0.1:8080` 不要动。** 改成 `0.0.0.0:8080` 就等于把未加密的服务直接挂到公网，绕过了宝塔那层 TLS。

`DATABASE_URL` 不用填，compose 会自己组装。

---

## 3. 起栈

在**仓库根目录**跑（不是 `deploy/` 里）：

```bash
cd /opt/variant-workshop
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

首次构建 3–5 分钟，大头是拉 Chromium。启动时会自动跑 `alembic upgrade head`，不用手工迁移。

```bash
docker compose -f deploy/docker-compose.prod.yml ps      # 三个服务都该是 healthy
curl -s localhost:8080/healthz                            # → ok
```

---

## 4. 建管理员

生产不灌演示账号，空库里没有任何用户，必须手工开第一个口子：

```bash
docker compose -f deploy/docker-compose.prod.yml exec backend python -m app.create_user <用户名> --role admin
```

按提示输两遍密码（≥12 位）。

顺手确认后门确实堵上了：

```bash
curl -so /dev/null -w '%{http_code}\n' -X POST localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' -d '{"username":"admin","password":"demo1234"}'
# → 401。返回 200 就立刻停服查 SEED_DEMO_DATA。
```

---

## 5. 宝塔配站点

1. **网站 → 添加站点**：填域名，PHP 版本选「纯静态」，不用建数据库。
2. **站点设置 → 反向代理 → 添加反向代理**：
   - 目标 URL：`http://127.0.0.1:8080`
   - 发送域名：`$host`
3. **站点设置 → SSL → Let's Encrypt**：申请证书，然后打开「强制 HTTPS」。

> 申请证书要走 HTTP 验证，**宝塔安全 → 防火墙**必须放行 80 和 443。
> **8080 不要放行**——它只绑回环，放行也没用，反而容易误配成对外。

---

## 6. ⚠️ 改掉宝塔 Nginx 的代理超时

这是最容易踩的一个坑。**生成一批变体要等模型跑几十秒到分钟级**，而 Nginx 默认 `proxy_read_timeout` 是 60 秒——超时就是 504，前端看到「生成失败」，但后端其实还在跑、token 照烧。

容器内那层 Nginx 我已经设成 300s 了，**但宝塔这层是独立的一层，得单独改**。

宝塔不同版本的反代模板默认值不一样，别猜，直接确认：

```bash
grep -rn "proxy_read_timeout" /www/server/panel/vhost/nginx/proxy/<你的域名>/
```

在 **站点设置 → 配置文件**，找到反代的 `location` 块，确保有这三行：

```nginx
proxy_connect_timeout 10s;
proxy_send_timeout    300s;
proxy_read_timeout    300s;
```

改完 `nginx -t && nginx -s reload`，或用面板的「重载配置」。

> 相关的已知边界：后端 `llm.py` 里 OpenAI 兼容路径的 httpx `timeout=90`。
> 走中转且单次生成超过 90 秒时，会先在后端超时——这时候调大 Nginx 也没用。

---

## 7. 服务器在中国大陆时

### 镜像拉不动

宝塔 **Docker → 配置 → 镜像加速**，或直接写 `/etc/docker/daemon.json`：

```json
{ "registry-mirrors": ["https://docker.m.daocloud.io"] }
```

然后 `systemctl restart docker`。

### `api.anthropic.com` 不通

**不用改代码。** 项目内建多厂商模型库，`llm.py` 的两条调用路径都支持自定义 `base_url`。

部署起来之后，用管理员登录 → **模型管理** 页：

1. 「模型库」区新增一个模型，`provider` 选 `openai`（走 OpenAI 兼容 `/chat/completions`，覆盖绝大多数中转），填中转的 `base_url` 和 `api_key`。
2. 点「测试」确认连通。
3. 到「场景绑定」区，把 `generate` / `clean` / `compliance` 三个场景改绑到这个模型。

保存即刷新进程缓存，不用重启容器。

> `provider` 选 `anthropic` 时也可以填 `base_url`，走 Anthropic 兼容的中转。
>
> ⚠️ 成本记账有个已知遗留：`routers/variants.py:31` 按 `model_id` 里是否含 `haiku`/`sonnet`/`opus`
> 来选价目表（`usage.py` 的 `RATES`），**匹配不上就静默回退成 Sonnet 价**。换成 DeepSeek、
> Kimi 这类模型后，消耗看板上的费用数字是按 Sonnet 单价算的，**不是真实花费**。
> 配额限流按 token 数走，所以限流本身仍然有效，不影响功能。

---

## 8. 备份

卷里是真实抓取的新闻、token 记账和用户数据。**宝塔 → 计划任务 → Shell 脚本**，每天跑：

```bash
cd /opt/variant-workshop
docker compose -f deploy/docker-compose.prod.yml exec -T db \
  pg_dump -U app -Fc imitator > /opt/backups/vw-$(date +\%F).dump
find /opt/backups -name 'vw-*.dump' -mtime +14 -delete
```

（宝塔的计划任务里 `%` 要写成 `\%`。）

> ⚠️ **永远不要跑 `docker compose ... down -v`。** `-v` 会连 `pgdata` 卷一起删。停服用 `down`，不带 `-v`。

---

## 9. 更新版本

```bash
cd /opt/variant-workshop
git pull
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

新迁移会在启动时自动跑到 head。有秒级中断，属预期（单副本，无滚动更新——原因见 [ADR 0004](../docs/decisions/0004-deployment-single-node-compose.md)）。

---

## 排障速查

| 症状 | 查这里 |
| --- | --- |
| 打开域名 502 | 栈没起来或没绑 8080：`docker compose -f deploy/docker-compose.prod.yml ps` |
| 生成变体时 504 | 宝塔那层的 `proxy_read_timeout`（[§6](#6-️-改掉宝塔-nginx-的代理超时)），容器内那层已是 300s |
| 页面刷新后 404 | 说明请求没进容器内 nginx。宝塔站点别配静态根，全部反代到 8080 |
| 登录提示模型不可用 / 生成报错 | `api.anthropic.com` 不通（[§7](#7-服务器在中国大陆时)），或 `.env` 里 key 没填 |
| 容器反复重启 | `docker compose -f deploy/docker-compose.prod.yml logs backend` |
| Playwright 抓取崩溃 | Chromium 吃 `/dev/shm`，compose 已给 1g；还崩就调大 |

---

## 🔴 红线 A-1

部署 ≠ 放行投放。系统没有对外发布端点，把它跑起来不触碰 A-1；**拿产出的文案对外投放**仍受法务书面确认约束。详见 [`docs/decisions/0001-arch-review-closure.md`](../docs/decisions/0001-arch-review-closure.md)。
