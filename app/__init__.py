from flask import Flask

from app.config import Config
from app.extensions import db, migrate


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    from app.routes.mood import mood_bp
    app.register_blueprint(mood_bp)

    from app.cli import register_cli
    register_cli(app)

    from app.enrich_cli import register_enrich_cli
    register_enrich_cli(app)

    from app.recommendation_cli import register_recommendation_cli
    register_recommendation_cli(app)

    from app.popular_import_cli import register_popular_import_cli
    register_popular_import_cli(app)

    from app.transfer_cli import register_transfer_cli
    register_transfer_cli(app)

    from app.filters import register_template_filters
    register_template_filters(app)

    return app