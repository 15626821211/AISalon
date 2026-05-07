# AISalon 部署文档

## 一、环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | CentOS 7/8 |
| CPU | 2核+ |
| 内存 | 4GB+ |
| 磁盘 | 20GB+ |
| 网络 | 可访问外网（拉取 Docker 镜像） |
| 权限 | root |
| MySQL | Azure Database for MySQL（云数据库，无需本地安装） |

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

## 三、数据库说明

使用 Azure Database for MySQL 云数据库，无需本地安装 MySQL。

| 项目 | 值 |
|------|------|
| 主机 | `datp-dev-pas-n3-mysql001.mysql.database.chinacloudapi.cn` |
| 用户名 | `ai_salonuser` |
| 密码 | `AISalon2026!` |
| 数据库 | `ai_salondb` |
| 端口 | 3306 |

> 应用首次启动时会自动建表，无需手动初始化。

---

## 四、部署步骤

### 4.1 拉取代码

```bash
cd /opt
git clone https://github.com/15626821211/AISalon.git
cd AISalon/event-platform
```

### 4.2 配置环境变量

```bash
cp .env.production.example .env.production
vi .env.production
```

需填写的关键配置：

| 变量 | 说明 | 示例 |
|------|------|------|
| SECRET_KEY | Flask密钥，随机字符串 | `openssl rand -hex 32` 生成 |
| DATABASE_URL | 数据库连接串 | `mysql+pymysql://ai_salonuser:AISalon2026!@datp-dev-pas-n3-mysql001.mysql.database.chinacloudapi.cn:3306/ai_salondb` |
| OPENAI_API_KEY | Azure OpenAI 密钥 | 找开发获取 |
| GITHUB_TOKEN | GitHub Token（可选） | 提升 API 限额 |

> **注意**：DATABASE_URL 中的主机名为 Azure MySQL 云数据库地址，应用容器需能访问外网。

### 4.3 启动服务

```bash
bash deploy.sh
```

首次启动需要构建镜像，约 3-5 分钟。

### 4.4 创建管理员账号

```bash
docker exec aisalon-app python -c "
from app import create_app
from users.services import UserService
app = create_app()
with app.app_context():
    result = UserService.register('admin', 'admin123456', email='admin@aisalon.com')
    print('创建成功' if result else '用户已存在')
"
```

### 4.5 验证服务

```bash
# 检查容器状态（2个容器都应为 running）
docker compose ps

# 检查应用日志
docker compose logs app

# 访问测试
curl http://localhost:8180
```

---

## 五、服务架构

```
用户 → Nginx(:8180) → Flask App(:5000) → Azure MySQL(云数据库)
```

| 容器 | 说明 | 端口 |
|------|------|------|
| aisalon-nginx | 反向代理 | 8180 (对外) |
| aisalon-app | Flask应用 (Gunicorn 4 workers) | 5000 (内部) |

MySQL 使用 Azure 云数据库，非本地实例。

---

## 六、日常运维

| 操作 | 命令 |
|------|------|
| 查看容器状态 | `docker compose ps` |
| 查看应用日志 | `docker compose logs -f app` |
| 重启所有服务 | `docker compose restart` |
| 重启应用 | `docker compose restart app` |
| 停止所有服务 | `docker compose down` |
| 更新代码并重新部署 | `git pull && docker compose up -d --build` |
| 进入应用容器 | `docker exec -it aisalon-app bash` |
| 进入数据库 | `mysql -u ai_salonuser -p'AISalon2026!' -h datp-dev-pas-n3-mysql001.mysql.database.chinacloudapi.cn ai_salondb` |
| 查看磁盘占用 | `docker system df` |
| 清理无用镜像 | `docker image prune -f` |

---

## 七、数据备份

```bash
# 备份数据库
mysqldump -u ai_salonuser -p'AISalon2026!' -h datp-dev-pas-n3-mysql001.mysql.database.chinacloudapi.cn ai_salondb > backup_$(date +%Y%m%d).sql

# 恢复数据库
mysql -u ai_salonuser -p'AISalon2026!' -h datp-dev-pas-n3-mysql001.mysql.database.chinacloudapi.cn ai_salondb < backup_20260506.sql
```

建议设置 crontab 定时备份：
```bash
# 每天凌晨3点自动备份，保留7天
0 3 * * * mysqldump -u ai_salonuser -p'AISalon2026!' -h datp-dev-pas-n3-mysql001.mysql.database.chinacloudapi.cn ai_salondb | gzip > /opt/backup/aisalon_$(date +\%Y\%m\%d).sql.gz && find /opt/backup -name "aisalon_*.sql.gz" -mtime +7 -delete
```

---

## 八、防火墙配置

```bash
# 开放 8180 端口
firewall-cmd --permanent --add-port=8180/tcp
firewall-cmd --reload
```

> 如果是阿里云 ECS，还需在安全组中放行 8180 端口（TCP 入方向）。

---

## 九、故障排查

| 问题 | 排查方法 |
|------|----------|
| 页面无法访问 | `docker compose ps` 确认容器运行; `firewall-cmd --list-ports` 确认端口开放; 阿里云安全组是否放行 |
| 应用500错误 | `docker compose logs -f app` 查看错误日志 |
| 数据库连接失败 | 确认服务器可访问 Azure MySQL; 确认用户名密码正确; 检查 Azure 防火墙规则是否放行服务器 IP |
| 容器启动失败 | `docker compose logs 容器名` 查看具体报错 |
| 磁盘满 | `docker system prune -a` 清理；扩容磁盘 |
| AI分析超时 | 正常现象，LLM调用需1-2分钟，已设 300s 超时 |
| Docker Hub拉取失败 | 镜像已配置为 DaoCloud 代理，检查服务器外网连通性 |
