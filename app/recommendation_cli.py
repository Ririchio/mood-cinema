import click
from sqlalchemy import and_, or_

from app.extensions import db
from app.models import Movie, MovieEmotionProfile
from app.services.emotion_engine import build_movie_emotion_scores, apply_scores_to_profile


def register_recommendation_cli(app):
    @app.cli.command("generate-emotion-profiles")
    @click.option("--limit", default=0, type=int, help="Сколько записей обработать. 0 = все")
    @click.option("--force/--only-missing", default=True, help="Пересоздавать уже существующие профили")
    def generate_emotion_profiles(limit, force):
        """
        Сгенерировать эмоциональные признаки фильмов и сериалов.
        Работает локально, лимит API не тратит.
        """
        query = Movie.query.filter(Movie.poster_url.isnot(None), Movie.poster_url != "")

        if not force:
            query = query.outerjoin(MovieEmotionProfile).filter(MovieEmotionProfile.id.is_(None))

        query = query.filter(
            or_(
                and_(Movie.description.isnot(None), Movie.description != ""),
                and_(Movie.short_description.isnot(None), Movie.short_description != ""),
            )
        )

        if limit and limit > 0:
            movies = query.limit(limit).all()
        else:
            movies = query.all()

        created = 0
        updated = 0
        skipped = 0

        for movie in movies:
            scores = build_movie_emotion_scores(movie)

            profile = MovieEmotionProfile.query.filter_by(movie_id=movie.id).first()

            if profile is None:
                profile = MovieEmotionProfile(movie_id=movie.id)
                db.session.add(profile)
                created += 1
            else:
                updated += 1

            apply_scores_to_profile(profile, scores)

            if (created + updated + skipped) % 100 == 0:
                db.session.commit()
                click.echo(f"Обработано: {created + updated + skipped}")

        db.session.commit()

        click.echo("")
        click.echo("Эмоциональные профили готовы.")
        click.echo(f"Создано: {created}")
        click.echo(f"Обновлено: {updated}")
        click.echo(f"Пропущено: {skipped}")

    @app.cli.command("emotion-stats")
    def emotion_stats():
        """Показать статистику эмоциональных профилей."""
        total_movies = Movie.query.count()
        total_profiles = MovieEmotionProfile.query.count()

        movies_with_description = Movie.query.filter(
            or_(
                and_(Movie.description.isnot(None), Movie.description != ""),
                and_(Movie.short_description.isnot(None), Movie.short_description != ""),
            )
        ).count()

        click.echo(f"Всего фильмов и сериалов: {total_movies}")
        click.echo(f"С описанием: {movies_with_description}")
        click.echo(f"Эмоциональных профилей: {total_profiles}")