# Регистрация всех API рутов
def register_api_blueprints(app):
    from .auth import api_auth_bp
    from .collections import api_collections_bp
    from .documents import api_documents_bp
    from .huffman import api_huffman_bp
    from .user import api_user_bp
    from .utils import api_utils_bp

    app.register_blueprint(api_auth_bp)
    app.register_blueprint(api_collections_bp)
    app.register_blueprint(api_documents_bp)
    app.register_blueprint(api_huffman_bp)
    app.register_blueprint(api_user_bp)
    app.register_blueprint(api_utils_bp)
