import time

import click
import requests
from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Movie, Genre, Country


class ImportStopped(Exception):
    pass


def register_popular_import_cli(app):
    @app.cli.command("import-top-quality")
    @click.option("--top", default="TOP_250_BEST_FILMS", help="TOP_250_BEST_FILMS или TOP_100_POPULAR_FILMS")
    @click.option("--pages", default=13, type=int, help="Сколько страниц топа просмотреть")
    @click.option("--target", default=250, type=int, help="Сколько новых записей максимум добавить")
    @click.option("--min-rating", default=7.0, type=float, help="Минимальный рейтинг Кинопоиска")
    @click.option("--delay", default=0.25, type=float, help="Пауза между запросами")
    @click.option("--delete-empty-existing/--keep-empty-existing", default=True)
    def import_top_quality(top, pages, target, min_rating, delay, delete_empty_existing):
        """
        Импортировать качественные фильмы из топов Кинопоиска.
        Новая запись сохраняется только если есть постер, описание и нормальный рейтинг.
        """
        created = 0
        updated_empty = 0
        skipped_existing = 0
        skipped_no_quality = 0
        deleted_empty = 0
        checked = 0

        try:
            for page in range(1, pages + 1):
                click.echo("")
                click.echo(f"Топ={top}, страница={page}")

                top_data = kinopoisk_get(
                    "/v2.2/films/top",
                    params={
                        "type": top,
                        "page": page,
                    },
                )

                items = top_data.get("films") or top_data.get("items") or []

                if not items:
                    click.echo("На странице ничего не пришло. Останавливаю этот топ.")
                    break

                for item in items:
                    if created >= target:
                        raise ImportStopped

                    kp_id = extract_kp_id(item)

                    if not kp_id:
                        continue

                    checked += 1

                    result = import_or_enrich_one(
                        kp_id=kp_id,
                        min_rating=min_rating,
                        delete_empty_existing=delete_empty_existing,
                    )

                    if result == "created":
                        created += 1
                    elif result == "updated_empty":
                        updated_empty += 1
                    elif result == "existing":
                        skipped_existing += 1
                    elif result == "deleted_empty":
                        deleted_empty += 1
                    else:
                        skipped_no_quality += 1

                    db.session.commit()
                    time.sleep(delay)

        except ImportStopped:
            click.echo("Достигнут лимит новых записей для этой команды.")
        except RuntimeError as error:
            db.session.rollback()
            click.echo("")
            click.echo(f"Импорт остановлен: {error}")
            click.echo("Если это лимит API, сегодня больше не запускай импорт и дозагрузку описаний.")
        finally:
            click.echo("")
            click.echo("Итог импорта из топа:")
            click.echo(f"Проверено кандидатов: {checked}")
            click.echo(f"Создано новых записей: {created}")
            click.echo(f"Дозаполнено старых пустых: {updated_empty}")
            click.echo(f"Пропущено уже существующих нормальных: {skipped_existing}")
            click.echo(f"Пропущено без описания/постера/рейтинга: {skipped_no_quality}")
            click.echo(f"Удалено старых пустых: {deleted_empty}")

    @app.cli.command("import-voted-quality")
    @click.option("--type", "content_type", default="FILM", help="FILM, TV_SERIES или ALL")
    @click.option("--year-from", default=1970, type=int)
    @click.option("--year-to", default=2024, type=int)
    @click.option("--pages", default=10, type=int)
    @click.option("--target", default=200, type=int)
    @click.option("--min-rating", default=7.0, type=float)
    @click.option("--delay", default=0.25, type=float)
    @click.option("--delete-empty-existing/--keep-empty-existing", default=True)
    def import_voted_quality(content_type, year_from, year_to, pages, target, min_rating, delay, delete_empty_existing):
        """
        Импортировать популярные фильмы/сериалы по числу оценок.
        Это лучше, чем просто идти по свежим годам: меньше случайных новинок и пустых карточек.
        """
        created = 0
        updated_empty = 0
        skipped_existing = 0
        skipped_no_quality = 0
        deleted_empty = 0
        checked = 0

        try:
            for page in range(1, pages + 1):
                click.echo("")
                click.echo(
                    f"Популярность по оценкам: тип={content_type}, годы={year_from}-{year_to}, страница={page}"
                )

                list_data = kinopoisk_get(
                    "/v2.2/films",
                    params={
                        "order": "NUM_VOTE",
                        "type": content_type,
                        "ratingFrom": min_rating,
                        "ratingTo": 10,
                        "yearFrom": year_from,
                        "yearTo": year_to,
                        "page": page,
                    },
                )

                items = list_data.get("items") or list_data.get("films") or []

                if not items:
                    click.echo("На странице ничего не пришло. Останавливаю этот импорт.")
                    break

                for item in items:
                    if created >= target:
                        raise ImportStopped

                    kp_id = extract_kp_id(item)

                    if not kp_id:
                        continue

                    checked += 1

                    result = import_or_enrich_one(
                        kp_id=kp_id,
                        min_rating=min_rating,
                        delete_empty_existing=delete_empty_existing,
                        expected_type=content_type,
                    )

                    if result == "created":
                        created += 1
                    elif result == "updated_empty":
                        updated_empty += 1
                    elif result == "existing":
                        skipped_existing += 1
                    elif result == "deleted_empty":
                        deleted_empty += 1
                    else:
                        skipped_no_quality += 1

                    db.session.commit()
                    time.sleep(delay)

        except ImportStopped:
            click.echo("Достигнут лимит новых записей для этой команды.")
        except RuntimeError as error:
            db.session.rollback()
            click.echo("")
            click.echo(f"Импорт остановлен: {error}")
            click.echo("Если это лимит API, сегодня больше не запускай импорт и дозагрузку описаний.")
        finally:
            click.echo("")
            click.echo("Итог импорта по популярности:")
            click.echo(f"Проверено кандидатов: {checked}")
            click.echo(f"Создано новых записей: {created}")
            click.echo(f"Дозаполнено старых пустых: {updated_empty}")
            click.echo(f"Пропущено уже существующих нормальных: {skipped_existing}")
            click.echo(f"Пропущено без описания/постера/рейтинга: {skipped_no_quality}")
            click.echo(f"Удалено старых пустых: {deleted_empty}")


def kinopoisk_get(path, params=None):
    api_key = current_app.config.get("KINOPOISK_API_KEY")
    api_base = current_app.config.get("KINOPOISK_API_BASE") or "https://kinopoiskapiunofficial.tech/api"

    if not api_key:
        raise RuntimeError("В .env не указан KINOPOISK_API_KEY.")

    url = api_base.rstrip("/") + path

    try:
        response = requests.get(
            url,
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            params=params or {},
            timeout=30,
        )
    except requests.RequestException as error:
        raise RuntimeError(f"Ошибка соединения с API: {error}") from error

    if response.status_code in [401, 403]:
        raise RuntimeError(f"API не принял ключ. Статус: {response.status_code}")

    if response.status_code in [402, 429]:
        raise RuntimeError(f"Похоже, закончился лимит API. Статус: {response.status_code}")

    if response.status_code >= 400:
        text = response.text[:500]
        raise RuntimeError(f"API вернул ошибку {response.status_code}: {text}")

    return response.json()


def extract_kp_id(item):
    return (
        item.get("kinopoiskId")
        or item.get("filmId")
        or item.get("id")
    )


def import_or_enrich_one(kp_id, min_rating, delete_empty_existing, expected_type=None):
    existing_movie = Movie.query.filter_by(kp_id=kp_id).first()

    if existing_movie and existing_movie.has_description() and existing_movie.poster_url:
        return "existing"

    details = kinopoisk_get(f"/v2.2/films/{kp_id}")

    if not is_good_details(details, min_rating=min_rating, expected_type=expected_type):
        if existing_movie and delete_empty_existing and not existing_movie.has_description():
            title = existing_movie.title
            delete_movie(existing_movie)
            click.echo(f"Удалено старое без описания: {title}")
            return "deleted_empty"

        return "skipped_no_quality"

    if existing_movie:
        fill_movie_from_details(existing_movie, details)
        click.echo(f"Дозаполнено: {existing_movie.title}")
        return "updated_empty"

    movie = Movie(kp_id=kp_id, title="Без названия")
    db.session.add(movie)

    fill_movie_from_details(movie, details)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return "existing"

    click.echo(f"Добавлено: {movie.title}")
    return "created"


def is_good_details(details, min_rating, expected_type=None):
    title = clean_text(details.get("nameRu")) or clean_text(details.get("nameOriginal")) or clean_text(details.get("nameEn"))
    poster = clean_text(details.get("posterUrlPreview")) or clean_text(details.get("posterUrl"))
    description = clean_text(details.get("description")) or clean_text(details.get("shortDescription"))
    rating = safe_float(details.get("ratingKinopoisk"))
    content_type = clean_text(details.get("type"))

    if not title:
        return False

    if not poster:
        return False

    if not description:
        return False

    if rating is None or rating < min_rating:
        return False

    if content_type not in ["FILM", "TV_SERIES"]:
        return False

    if expected_type in ["FILM", "TV_SERIES"] and content_type != expected_type:
        return False

    return True


def fill_movie_from_details(movie, details):
    title = (
        clean_text(details.get("nameRu"))
        or clean_text(details.get("nameOriginal"))
        or clean_text(details.get("nameEn"))
        or movie.title
    )

    movie.title = title
    movie.original_title = clean_text(details.get("nameOriginal"))
    movie.description = clean_text(details.get("description"))
    movie.short_description = clean_text(details.get("shortDescription"))
    movie.year = safe_int(details.get("year"))
    movie.type = clean_text(details.get("type")) or "FILM"
    movie.poster_url = clean_text(details.get("posterUrlPreview")) or clean_text(details.get("posterUrl"))
    movie.rating_kp = safe_float(details.get("ratingKinopoisk"))
    movie.kinopoisk_url = clean_text(details.get("webUrl")) or f"https://www.kinopoisk.ru/film/{movie.kp_id}/"

    movie.genres.clear()

    for genre_item in details.get("genres", []):
        genre_name = clean_text(genre_item.get("genre"))

        if not genre_name:
            continue

        genre = Genre.query.filter_by(name=genre_name).first()

        if genre is None:
            genre = Genre(name=genre_name)
            db.session.add(genre)
            db.session.flush()

        if genre not in movie.genres:
            movie.genres.append(genre)

    movie.countries.clear()

    for country_item in details.get("countries", []):
        country_name = clean_text(country_item.get("country"))

        if not country_name:
            continue

        country = Country.query.filter_by(name=country_name).first()

        if country is None:
            country = Country(name=country_name)
            db.session.add(country)
            db.session.flush()

        if country not in movie.countries:
            movie.countries.append(country)


def delete_movie(movie):
    movie.genres.clear()
    movie.countries.clear()
    db.session.delete(movie)


def clean_text(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def safe_int(value):
    try:
        if value is None:
            return None

        return int(value)
    except (ValueError, TypeError):
        return None


def safe_float(value):
    try:
        if value is None:
            return None

        return float(value)
    except (ValueError, TypeError):
        return None