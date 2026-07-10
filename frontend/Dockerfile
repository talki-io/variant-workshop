# 前端生产镜像：node 构建 → nginx 静态托管。
# 开发不用它（`npm run dev` 起 Vite，走 vite.config.ts 里的 /api 代理）。

# ---- build ----
FROM node:20-alpine AS build

WORKDIR /app

# 先只拷贝清单，命中 layer 缓存：只改源码时不必重装依赖。
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# `npm run build` = tsc --noEmit && vite build。类型错会在这里断掉构建，故意的。
# import.meta.env.DEV 为 false，dev-only/（走查页 + mock）连同动态 import 被摇除。
RUN npm run build

# ---- serve ----
FROM nginx:1.27-alpine

# 默认站点配置会抢 80，先挪走。
RUN rm /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/app.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/healthz >/dev/null 2>&1 || exit 1
