# application-template

最小架构验收应用与通用 Helm 部署契约。镜像支持 ARM64/AMD64；前端和 API 共域名，路由 `/api`，提供 WebSocket、SSE、数据库读写、健康检查、Prometheus 与 OpenTelemetry。

`deploy/values.yaml` 支持静态前端服务、普通 HTTP/SSR 服务、后端 API、常驻 worker 和 CronJob。真实静态/SSR 项目替换镜像与命令，保留探针、资源和安全约定。

部署必须提供真实镜像 digest：`helm upgrade --install acceptance deploy -n app-acceptance --set image.digest=sha256:...`。镜像默认禁止 root、禁止提权、只读根文件系统；网络默认拒绝，按模板仅开放 DNS、入口、数据库与遥测。

正式环境与每套测试环境须分别使用 namespace、数据库账号和 Secret。测试环境最多一套，24 小时 TTL；业务数据迁移不进入镜像，不在应用回滚时自动降级。

本地引导构建仅用于服务器验收。远端生产发布必须经过 CI 的扫描、签名和验签，使用 GHCR digest 后更新 GitOps。
