# Регистрация всех эндпоинтов
def register_blueprints(app):
    from .api import register_api_blueprints
    from .auth import auth_bp
    from .collections import collections_bp
    from .index import index_bp

    register_api_blueprints(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(collections_bp)
    app.register_blueprint(index_bp)
