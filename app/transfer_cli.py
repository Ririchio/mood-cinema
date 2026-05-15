import json
import os

import click

from app.extensions import db
from app.models import Movie, Genre, Country, MovieEmotionProfile, MoodProfile
from app.services.emotion_engine import DIMENSIONS


def register_transfer_cli(app):
    @app.cli.command("export-data")
    @click.option("--path", default="instance/mood_cinema_export.json")
    def export_data(path):
        """
        Экспортировать текущую базу фильмов в JSON.
        Команду надо запускать, когда приложение подключено к ЛОКАЛЬНОЙ MySQL-базе.
        """
        folder = os.path.dirname(path)

        if folder:
            os.makedirs(folder, exist_ok=True)

        genres = []
        countries = []
        movies = []

        for genre in Genre.query.order_by(Genre.id.asc()).all():
            genres.append({
                "kp_id": getattr(genre, "kp_id", None),
                "name": genre.name,
            })

        for country in Country.query.order_by(Country.id.asc()).all():
            countries.append({
                "kp_id": getattr(country, "kp_id", None),
                "name": country.name,
            })

        for movie in Movie.query.order_by(Movie.id.asc()).all():
            profile = getattr(movie, "emotion_profile", None)

            if profile:
                emotion_scores = {}

                for dimension in DIMENSIONS:
                    emotion_scores[dimension] = getattr(profile, dimension, 0)
            else:
                emotion_scores = None

            movies.append({
                "kp_id": getattr(movie, "kp_id", None),
                "title": getattr(movie, "title", None),
                "original_title": getattr(movie, "original_title", None),
                "description": getattr(movie, "description", None),
                "short_description": getattr(movie, "short_description", None),
                "year": getattr(movie, "year", None),
                "type": getattr(movie, "type", None),
                "poster_url": getattr(movie, "poster_url", None),
                "rating_kp": getattr(movie, "rating_kp", None),
                "kinopoisk_url": getattr(movie, "kinopoisk_url", None),
                "genres": [genre.name for genre in movie.genres],
                "countries": [country.name for country in movie.countries],
                "emotion_profile": emotion_scores,
            })

        data = {
            "genres": genres,
            "countries": countries,
            "movies": movies,
        }

        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        click.echo(f"Экспорт готов: {path}")
        click.echo(f"Жанров: {len(genres)}")
        click.echo(f"Стран: {len(countries)}")
        click.echo(f"Фильмов и сериалов: {len(movies)}")

    @app.cli.command("import-data")
    @click.option("--path", default="instance/mood_cinema_export.json")
    @click.option("--clear/--no-clear", default=False)
    def import_data(path, clear):
        """
        Импортировать JSON в текущую базу.
        Команду надо запускать, когда DATABASE_URL указывает на Render PostgreSQL.
        """
        if not os.path.exists(path):
            click.echo(f"Файл не найден: {path}")
            return

        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        db.create_all()

        if clear:
            clear_database()

        genre_by_name = {}
        country_by_name = {}

        for genre_data in data.get("genres", []):
            name = clean_text(genre_data.get("name"))

            if not name:
                continue

            genre = Genre.query.filter_by(name=name).first()

            if genre is None:
                genre = Genre(
                    kp_id=genre_data.get("kp_id"),
                    name=name,
                )
                db.session.add(genre)
                db.session.flush()
            else:
                if hasattr(genre, "kp_id") and genre.kp_id is None:
                    genre.kp_id = genre_data.get("kp_id")

            genre_by_name[name] = genre

        for country_data in data.get("countries", []):
            name = clean_text(country_data.get("name"))

            if not name:
                continue

            country = Country.query.filter_by(name=name).first()

            if country is None:
                country = Country(
                    kp_id=country_data.get("kp_id"),
                    name=name,
                )
                db.session.add(country)
                db.session.flush()
            else:
                if hasattr(country, "kp_id") and country.kp_id is None:
                    country.kp_id = country_data.get("kp_id")

            country_by_name[name] = country

        created = 0
        updated = 0
        profiles_created = 0
        profiles_updated = 0

        for movie_data in data.get("movies", []):
            kp_id = movie_data.get("kp_id")

            movie = None

            if kp_id is not None:
                movie = Movie.query.filter_by(kp_id=kp_id).first()

            if movie is None:
                movie = Movie()
                db.session.add(movie)
                created += 1
            else:
                updated += 1

            movie.kp_id = kp_id
            movie.title = clean_text(movie_data.get("title")) or "Без названия"
            movie.original_title = clean_text(movie_data.get("original_title"))
            movie.description = clean_text(movie_data.get("description"))
            movie.short_description = clean_text(movie_data.get("short_description"))
            movie.year = safe_int(movie_data.get("year"))
            movie.type = clean_text(movie_data.get("type")) or "FILM"
            movie.poster_url = clean_text(movie_data.get("poster_url"))
            movie.rating_kp = safe_float(movie_data.get("rating_kp"))
            movie.kinopoisk_url = clean_text(movie_data.get("kinopoisk_url"))

            movie.genres.clear()
            movie.countries.clear()

            for genre_name in movie_data.get("genres", []):
                genre_name = clean_text(genre_name)

                if not genre_name:
                    continue

                genre = genre_by_name.get(genre_name)

                if genre is None:
                    genre = Genre(name=genre_name)
                    db.session.add(genre)
                    db.session.flush()
                    genre_by_name[genre_name] = genre

                movie.genres.append(genre)

            for country_name in movie_data.get("countries", []):
                country_name = clean_text(country_name)

                if not country_name:
                    continue

                country = country_by_name.get(country_name)

                if country is None:
                    country = Country(name=country_name)
                    db.session.add(country)
                    db.session.flush()
                    country_by_name[country_name] = country

                movie.countries.append(country)

            db.session.flush()

            emotion_scores = movie_data.get("emotion_profile")

            if emotion_scores:
                profile = MovieEmotionProfile.query.filter_by(movie_id=movie.id).first()

                if profile is None:
                    profile = MovieEmotionProfile(movie_id=movie.id)
                    db.session.add(profile)
                    profiles_created += 1
                else:
                    profiles_updated += 1

                for dimension in DIMENSIONS:
                    setattr(profile, dimension, safe_float(emotion_scores.get(dimension)) or 0)

        db.session.commit()

        click.echo("Импорт завершён.")
        click.echo(f"Создано фильмов/сериалов: {created}")
        click.echo(f"Обновлено фильмов/сериалов: {updated}")
        click.echo(f"Создано эмоциональных профилей: {profiles_created}")
        click.echo(f"Обновлено эмоциональных профилей: {profiles_updated}")


def clear_database():
    click.echo("Очищаю текущую базу перед импортом...")

    for movie in Movie.query.all():
        movie.genres.clear()
        movie.countries.clear()

    db.session.flush()

    MovieEmotionProfile.query.delete()

    try:
        MoodProfile.query.delete()
    except Exception:
        pass

    Movie.query.delete()
    Genre.query.delete()
    Country.query.delete()

    db.session.commit()


def clean_text(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def safe_int(value):
    try:
        if value is None or value == "":
            return None

        return int(value)
    except (TypeError, ValueError):
        return None


def safe_float(value):
    try:
        if value is None or value == "":
            return None

        return float(value)
    except (TypeError, ValueError):
        return None