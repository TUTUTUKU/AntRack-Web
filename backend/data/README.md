# backend/data/
此目录用于存放 SQLite 数据库文件（stock.db）。
- 首次启动后端时会自动创建空数据库并写入默认管理员 admin/admin123。
- Docker 部署时此目录作为 volume 挂载到容器内，容器重建不丢失数据。
- 严禁将任何 .db 文件提交到 Git。
