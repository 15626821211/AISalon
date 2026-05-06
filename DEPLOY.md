# AISalon 部署文档

## 一、环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | CentOS 7/8 |
| CPU | 2核+ |
| 内存 | 4GB+ |
| 磁盘 | 20GB+ |
| 网络 | 可访问外网（拉取镜像） |
| 权限 | root |

---

## 二、安装 Docker

```bash
# 1. 安装依赖
yum install -y yum-utils git

# 2. 添加 Docker 仓库
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 3. 安装 Docker + Compose 插件
yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 4. 启动并设置开机自启
systemctl enable docker
systemctl start docker

# 5. 验证安装
docker --version
docker compose version
```

---

## 三、部署步骤

### 3.1 拉取代码

```bash
cd /opt
git clone https://github.com/15626821211/AISalon.git
cd AISalon/event-platform
```

### 3.2 配置环境变量

```bash
cp .env.production.example .env.production
vi .env.production
```

需填写的关键配置：

| 变量 | 说明 | 示例 |
|------|------|------|
| SECRET_KEY | Flask密钥，随机字符串 | `openssl rand -hex 32` 生成 |
| MYSQL_ROOT_PASSWORD | MySQL root密码 | `AiSalon2026!` |
| DATABASE_URL | 数据库连接串 | `mysql+pymysql://root:密码@mysql:3306/ai_salon` |
| OPENAI_API_KEY | Azure OpenAI 密钥 | 找开发获取 |
| GITHUB_TOKEN | GitHub Token（可选） | 提升 API 限额 |

> **注意**：DATABASE_URL 中的主机名必须是 `mysql`（Docker 内部网络名称），密码需与 MYSQL_ROOT_PASSWORD 一致。

### 3.3 启动服务

```bash
bash deploy.sh
```

首次启动需要构建镜像，约 3-5 分钟。

### 3.4 验证服务

```bash
# 检查容器状态（3个容器都应为 running）
docker compose ps

# 检查应用日志
docker compose logs app

# 访问测试
curl http://localhost
```

---

## 四、服务架构

```
用户 → Nginx(:80) → Flask App(:5000) → MySQL(:3306)
```

| 容器 | 说明 | 端口 |
|------|------|------|
| aisalon-nginx | 反向代理 | 80 (对外) |
| aisalon-app | Flask应用 (Gunicorn) | 5000 (内部) |
| aisalon-mysql | MySQL 8.0 数据库 | 3306 (内部) |

---

## 五、日常运维

| 操作 | 命令 |
|------|------|
| 查看所有容器状态 | `docker compose ps` |
| 查看应用日志 | `docker compose logs -f app` |
| 查看数据库日志 | `docker compose logs -f mysql` |
| 重启所有服务 | `docker compose restart` |
| 重启单个服务 | `docker compose restart app` |
| 停止所有服务 | `docker compose down` |
| 更新代码并重新部署 | `git pull && docker compose up -d --build` |
| 进入数据库 | `docker exec -it aisalon-mysql mysql -uroot -p ai_salon` |
| 进入应用容器 | `docker exec -it aisalon-app bash` |
| 查看磁盘占用 | `docker system df` |
| 清理无用镜像 | `docker image prune -f` |

---

## 六、数据备份

```bash
# 备份数据库
docker exec aisalon-mysql mysqldump -uroot -p'你的密码' ai_salon > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker exec -i aisalon-mysql mysql -uroot -p'你的密码' ai_salon < backup_20260506.sql
```

建议设置 crontab 定时备份：
```bash
# 每天凌晨3点自动备份，保留7天
0 3 * * * cd /opt/AISalon/event-platform && docker exec aisalon-mysql mysqldump -uroot -p'密码' ai_salon | gzip > /opt/backup/aisalon_$(date +\%Y\%m\%d).sql.gz && find /opt/backup -name "aisalon_*.sql.gz" -mtime +7 -delete
```

---

## 七、防火墙配置

```bash
# 开放 80 端口
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --reload
```

---

## 八、故障排查

| 问题 | 排查方法 |
|------|----------|
| 页面无法访问 | `docker compose ps` 确认容器运行; `firewall-cmd --list-ports` 确认端口开放 |
| 应用500错误 | `docker compose logs -f app` 查看错误日志 |
| 数据库连接失败 | 确认 .env.production 中 DATABASE_URL 密码正确，主机名为 `mysql` |
| 容器启动失败 | `docker compose logs 容器名` 查看具体报错 |
| 磁盘满 | `docker system prune -a` 清理；扩容磁盘 |
| AI分析超时 | 正常现象，LLM调用需1-2分钟，已设 300s 超时 |
