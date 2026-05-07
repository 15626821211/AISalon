import os
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:root@localhost:3306/ai_salon')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 连接池参数：避免空闲连接失效与连接池耗尽问题
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
    }
    # Azure MySQL SSL 连接
    if os.environ.get('MYSQL_SSL', '').lower() in ['true', '1']:
        SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {
            'ssl': {
                'ca': os.environ.get('MYSQL_SSL_CA', '/etc/ssl/certs/ca-certificates.crt')
            }
        }
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ['true', '1', 't']
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://dmc-openai-swec.openai.azure.com/openai/v1')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
    GITLAB_TOKEN = os.environ.get('GITLAB_TOKEN', '')
    GITLAB_USERNAME = os.environ.get('GITLAB_USERNAME', '')
    GITLAB_PASSWORD = os.environ.get('GITLAB_PASSWORD', '')
    # 邮件配置
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.example.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_FROM = os.environ.get('SMTP_FROM', '')  # 发件人地址，默认同 SMTP_USER