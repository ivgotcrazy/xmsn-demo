# 需脉枢纽 前端镜像（M8 T8.2）
# 多阶段：node 构建 user-web + admin-web → nginx 托管静态产物
# 说明：
#  - user-web  构建 base=/（买家/厂商端，根路径）
#  - admin-web 构建 base=/admin/（管理后台子路径；VITE_BASE 由本文件设置）
#  - nginx 路由配置（/admin/ 分发 + /api 反代）见 infra/nginx/nginx.conf（compose 挂载）
#  - VITE_USE_MOCK=false：生产构建不含 MSW mock
FROM node:20-alpine AS builder

RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

WORKDIR /app

# 先拷贝清单，利用依赖层缓存
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps ./apps
COPY packages ./packages
RUN pnpm install --frozen-lockfile

# 买家/厂商端（根路径）
ENV VITE_USE_MOCK=false
RUN pnpm --filter user-web build

# 管理后台（子路径 /admin/）
ENV VITE_BASE=/admin/
RUN pnpm --filter admin-web build

# ---- 运行阶段：nginx 托管 ----
FROM nginx:1.27-alpine

# user-web → /usr/share/nginx/html/user（nginx root）
# admin-web → /usr/share/nginx/html/admin（vite base=/admin/，nginx /admin/ 分发）
COPY --from=builder /app/apps/user-web/dist /usr/share/nginx/html/user
COPY --from=builder /app/apps/admin-web/dist /usr/share/nginx/html/admin

EXPOSE 80

# 健康检查（默认 conf 无 /healthz 反代，实际路由见挂载的 infra/nginx/nginx.conf）
CMD ["nginx", "-g", "daemon off;"]
