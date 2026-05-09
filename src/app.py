from flask import Flask, render_template
from config import Config
from models import db


def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    # 初始化数据库
    db.init_app(app)

    # 延迟导入 Blueprint，避免循环导入
    from events.routes import event_blueprint
    from users.routes import user_blueprint
    from projects.routes import project_blueprint

    @app.route('/')
    def index():
        return render_template('index.html')

    # Register blueprints
    app.register_blueprint(event_blueprint, url_prefix='/events')
    app.register_blueprint(user_blueprint, url_prefix='/users')
    app.register_blueprint(project_blueprint, url_prefix='/projects')

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html', message=str(e)), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html', message=str(e)), 500

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        # 每次请求/上下文结束后释放会话，防止连接池被占满
        db.session.remove()

    # 自动建表 + 增量迁移
    with app.app_context():
        db.create_all()
        _auto_migrate(db)

    return app


def _auto_migrate(database):
    """检查并添加缺失的列，弥补 create_all() 无法 ALTER 已有表的不足。"""
    from sqlalchemy import text, inspect
    inspector = inspect(database.engine)
    migrations = [
        # (表名, 列名, 列定义)
        ('projects', 'code_files', 'JSON DEFAULT NULL'),
    ]
    for table, column, col_def in migrations:
        if table in inspector.get_table_names():
            existing = [c['name'] for c in inspector.get_columns(table)]
            if column not in existing:
                database.session.execute(text(f'ALTER TABLE `{table}` ADD COLUMN `{column}` {col_def}'))
                database.session.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)