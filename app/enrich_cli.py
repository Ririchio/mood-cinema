import click
from sqlalchemy import and_, or_

from app.extensions import db
from app.models import Movie, Genre, Country
from app.services.kinopoisk import KinopoiskClient, KinopoiskApiError


def register_enrich_cli(app):
    @app.cli.command("description-stats")
    def description_stats():
        """Показать статистику заполненности описаний."""
        total = Movie.query.count()

        with_full_description = Movie.query.filter(
            Movie.description.isnot(None),
            Movie.description != "",
        ).count()

        with_short_description = Movie.query.filter(
            Movie.short_description.isnot(None),
            Movie.short_description != "",
        ).count()

        with_any_description = Movie.query.filter(
            or_(
                and_(
                    Movie.description.isnot(None),
                    Movie.description != "",
                ),
                and_(
                    Movie.short_description.isnot(None),
                    Movie.short_description != "",
                ),
            )
        ).count()

        without_any_description = Movie.query.filter(
            or_(
                Movie.description.is_(None),
                Movie.description == "",
            ),
            or_(
                Movie.short_description.is_(None),
                Movie.short_description == "",
            ),
        ).count()

        click.echo(f"Всего записей: {total}")
        click.echo(f"С полным описанием: {with_full_description}")
        click.echo(f"С коротким описанием: {with_short_description}")
        click.echo(f"С любым описанием: {with_any_description}")
        click.echo(f"Без какого-либо описания: {without_any_description}")

    @app.cli.command("enrich-missing-descriptions")
    @click.option("--limit", default=100, type=int, help="Сколько записей дозаполнить за раз")
    @click.option("--type", "content_type", default="all", help="all, FILM или TV_SERIES")
    def enrich_missing_descriptions(limit, content_type):
        """
        Дозагрузить подробности для записей без описания.
        Важно: один фильм или сериал = один запрос к API.
        Ничего не удаляет.
        """
        client = KinopoiskClient()

        query = get_movies_without_any_description_query()

        if content_type != "all":
            query = query.filter(Movie.type == content_type)

        movies = (
            query
            .order_by(
                Movie.rating_kp.desc(),
                Movie.year.desc(),
                Movie.id.desc(),
            )
            .limit(limit)
            .all()
        )

        if not movies:
            click.echo("Записей без описания не найдено.")
            return

        updated = 0
        still_empty = 0
        api_errors = 0

        for movie in movies:
            click.echo(f"Загружаю описание: {movie.title}")

            try:
                details = client.movie_details(movie.kp_id)
            except KinopoiskApiError as error:
                click.echo(f"Не удалось загрузить {movie.title}: {error}")
                api_errors += 1

                if is_limit_error(error):
                    click.echo("Похоже, лимит API закончился. Останавливаю команду, чтобы не тратить попытки.")
                    break

                continue

            update_movie_from_details(movie, details)
            db.session.commit()

            if has_any_description(movie):
                updated += 1
            else:
                still_empty += 1

        click.echo("")
        click.echo("Итог дозагрузки описаний:")
        click.echo(f"Обновлено: {updated}")
        click.echo(f"Остались без описания: {still_empty}")
        click.echo(f"Ошибок API: {api_errors}")

    @app.cli.command("enrich-or-delete-missing-descriptions")
    @click.option("--limit", default=500, type=int, help="Сколько записей обработать за раз")
    @click.option("--type", "content_type", default="all", help="all, FILM или TV_SERIES")
    def enrich_or_delete_missing_descriptions(limit, content_type):
        """
        Дозагрузить описания. Если API успешно ответил, но описания всё равно нет,
        удалить такую запись из базы.
        """
        client = KinopoiskClient()

        query = get_movies_without_any_description_query()

        if content_type != "all":
            query = query.filter(Movie.type == content_type)

        movies = (
            query
            .order_by(
                Movie.rating_kp.desc(),
                Movie.year.desc(),
                Movie.id.desc(),
            )
            .limit(limit)
            .all()
        )

        if not movies:
            click.echo("Записей без описания не найдено.")
            return

        updated = 0
        deleted = 0
        api_errors = 0
        processed = 0

        for movie in movies:
            processed += 1
            click.echo(f"[{processed}/{len(movies)}] Проверяю: {movie.title}")

            try:
                details = client.movie_details(movie.kp_id)
            except KinopoiskApiError as error:
                click.echo(f"Не удалось загрузить {movie.title}: {error}")
                api_errors += 1

                if is_limit_error(error):
                    click.echo("Похоже, лимит API закончился. Останавливаю команду. Необработанные записи НЕ удалены.")
                    break

                continue

            update_movie_from_details(movie, details)

            if has_any_description(movie):
                db.session.commit()
                updated += 1
                click.echo(f"Описание найдено: {movie.title}")
                continue

            title = movie.title

            delete_movie(movie)
            db.session.commit()

            deleted += 1
            click.echo(f"Удалено без описания: {title}")

        click.echo("")
        click.echo("Итог обработки:")
        click.echo(f"Обработано: {processed}")
        click.echo(f"Дозаполнено описаний: {updated}")
        click.echo(f"Удалено без описания: {deleted}")
        click.echo(f"Ошибок API: {api_errors}")


def get_movies_without_any_description_query():
    return Movie.query.filter(
        or_(
            Movie.description.is_(None),
            Movie.description == "",
        ),
        or_(
            Movie.short_description.is_(None),
            Movie.short_description == "",
        ),
    )


def update_movie_from_details(movie: Movie, details: dict):
    movie.title = (
        clean_text(details.get("nameRu"))
        or clean_text(details.get("nameOriginal"))
        or clean_text(details.get("nameEn"))
        or movie.title
    )

    movie.original_title = clean_text(details.get("nameOriginal")) or movie.original_title
    movie.description = clean_text(details.get("description")) or movie.description
    movie.short_description = clean_text(details.get("shortDescription")) or movie.short_description
    movie.year = safe_int(details.get("year")) or movie.year
    movie.type = details.get("type") or movie.type
    movie.poster_url = details.get("posterUrlPreview") or details.get("posterUrl") or movie.poster_url
    movie.rating_kp = safe_float(details.get("ratingKinopoisk")) or movie.rating_kp
    movie.kinopoisk_url = details.get("webUrl") or movie.kinopoisk_url

    movie.genres.clear()

    for genre_item in details.get("genres", []):
        genre_name = clean_text(genre_item.get("genre"))

        if not genre_name:
            continue

        genre = Genre.query.filter_by(name=genre_name).first()

        if not genre:
            genre = Genre(name=genre_name)
            db.session.add(genre)

        movie.genres.append(genre)

    movie.countries.clear()

    for country_item in details.get("countries", []):
        country_name = clean_text(country_item.get("country"))

        if not country_name:
            continue

        country = Country.query.filter_by(name=country_name).first()

        if not country:
            country = Country(name=country_name)
            db.session.add(country)

        movie.countries.append(country)


def delete_movie(movie: Movie):
    movie.genres.clear()
    movie.countries.clear()
    db.session.delete(movie)


def has_any_description(movie: Movie) -> bool:
    description = clean_text(movie.description)
    short_description = clean_text(movie.short_description)

    return bool(description or short_description)


def is_limit_error(error: Exception) -> bool:
    text = str(error).lower()

    return (
        "429" in text
        or "limit" in text
        or "лимит" in text
        or "too many" in text
        or "quota" in text
    )


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
    except ValueError:
        return None


def safe_float(value):
    try:
        if value is None:
            return None

        return float(value)
    except (ValueError, TypeError):
        return None