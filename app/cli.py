import click
import requests

from app.extensions import db
from app.models import Movie, Genre, Country
from app.services.kinopoisk import KinopoiskClient, KinopoiskApiError


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Создать таблицы."""
        db.create_all()
        click.echo("Таблицы созданы.")

    @app.cli.command("reset-db")
    def reset_db():
        """Полностью пересоздать таблицы. Использовать только на этапе разработки."""
        db.drop_all()
        db.create_all()
        click.echo("База пересоздана.")

    @app.cli.command("stats")
    def stats():
        """Показать статистику по базе."""
        total = Movie.query.count()
        films = Movie.query.filter_by(type="FILM").count()
        series = Movie.query.filter_by(type="TV_SERIES").count()
        mini_series = Movie.query.filter_by(type="MINI_SERIES").count()

        without_posters = Movie.query.filter(
            (Movie.poster_url.is_(None)) | (Movie.poster_url == "")
        ).count()

        click.echo(f"Всего записей: {total}")
        click.echo(f"Фильмы: {films}")
        click.echo(f"Сериалы: {series}")
        click.echo(f"Мини-сериалы: {mini_series}")
        click.echo(f"Без постера: {without_posters}")

    @app.cli.command("cleanup-no-posters")
    def cleanup_no_posters():
        """Удалить фильмы и сериалы без ссылки на постер."""
        movies = Movie.query.filter(
            (Movie.poster_url.is_(None)) | (Movie.poster_url == "")
        ).all()

        removed = 0

        for movie in movies:
            movie.genres.clear()
            movie.countries.clear()
            db.session.delete(movie)
            removed += 1

        db.session.commit()

        click.echo(f"Удалено записей без постера: {removed}")

    @app.cli.command("cleanup-bad-posters")
    @click.option("--limit", default=100, type=int, help="Сколько записей проверить за раз")
    def cleanup_bad_posters(limit):
        """
        Проверить ссылки на постеры и удалить записи, у которых постер не открывается.
        Команда не тратит лимит API, но делает обычные запросы к картинкам.
        """
        movies = Movie.query.filter(
            Movie.poster_url.isnot(None),
            Movie.poster_url != "",
        ).limit(limit).all()

        checked = 0
        removed = 0

        for movie in movies:
            checked += 1

            if is_poster_available(movie.poster_url):
                continue

            click.echo(f"Удаляю из-за битого постера: {movie.title}")

            movie.genres.clear()
            movie.countries.clear()
            db.session.delete(movie)
            removed += 1

        db.session.commit()

        click.echo(f"Проверено: {checked}")
        click.echo(f"Удалено с битым постером: {removed}")

    @app.cli.command("sync-filters")
    def sync_filters():
        """Загрузить страны и жанры из API."""
        client = KinopoiskClient()

        try:
            data = client.filters()
        except KinopoiskApiError as error:
            click.echo(f"Ошибка API: {error}")
            return

        countries = data.get("countries", [])
        genres = data.get("genres", [])

        country_created = 0
        country_updated = 0
        genre_created = 0
        genre_updated = 0

        for item in countries:
            kp_id = item.get("id")
            name = clean_text(item.get("country"))

            if not name:
                continue

            country = None

            if kp_id is not None:
                country = Country.query.filter_by(kp_id=kp_id).first()

            if country is None:
                country = Country.query.filter_by(name=name).first()

            if country is None:
                country = Country(kp_id=kp_id, name=name)
                db.session.add(country)
                country_created += 1
            else:
                country.kp_id = country.kp_id or kp_id
                country.name = name
                country_updated += 1

        for item in genres:
            kp_id = item.get("id")
            name = clean_text(item.get("genre"))

            if not name:
                continue

            genre = None

            if kp_id is not None:
                genre = Genre.query.filter_by(kp_id=kp_id).first()

            if genre is None:
                genre = Genre.query.filter_by(name=name).first()

            if genre is None:
                genre = Genre(kp_id=kp_id, name=name)
                db.session.add(genre)
                genre_created += 1
            else:
                genre.kp_id = genre.kp_id or kp_id
                genre.name = name
                genre_updated += 1

        db.session.commit()

        click.echo(f"Стран создано: {country_created}")
        click.echo(f"Стран обновлено: {country_updated}")
        click.echo(f"Жанров создано: {genre_created}")
        click.echo(f"Жанров обновлено: {genre_updated}")

    @app.cli.command("show-filter-ids")
    def show_filter_ids():
        """Показать ID жанров и стран."""
        click.echo("Жанры:")

        for genre in Genre.query.order_by(Genre.name).all():
            click.echo(f"{genre.kp_id}: {genre.name}")

        click.echo("\nСтраны:")

        for country in Country.query.order_by(Country.name).all():
            click.echo(f"{country.kp_id}: {country.name}")

    @app.cli.command("import-kp")
    @click.option("--type", "content_type", default="FILM", help="FILM или TV_SERIES")
    @click.option("--start-page", default=1, type=int, help="С какой страницы API начинать импорт")
    @click.option("--pages", default=3, type=int, help="Сколько страниц импортировать")
    @click.option("--genre", "genre_id", default=None, type=int, help="ID жанра из API")
    @click.option("--country", "country_id", default=None, type=int, help="ID страны из API")
    @click.option("--year", default=None, type=int, help="Год выпуска")
    @click.option("--with-videos/--no-videos", default=False, help="Загружать трейлеры")
    @click.option("--update-existing/--skip-existing", default=False, help="Обновлять уже загруженные записи")
    @click.option("--require-poster/--allow-no-poster", default=True, help="Импортировать только записи с постером")
    def import_kp(
        content_type,
        start_page,
        pages,
        genre_id,
        country_id,
        year,
        with_videos,
        update_existing,
        require_poster,
    ):
        """Импорт фильмов/сериалов из API в локальную базу с подробностями."""
        client = KinopoiskClient()

        result = import_from_api(
            client=client,
            content_type=content_type,
            start_page=start_page,
            pages=pages,
            genre_id=genre_id,
            country_id=country_id,
            year=year,
            with_videos=with_videos,
            update_existing=update_existing,
            require_poster=require_poster,
            max_new=None,
        )

        print_import_result(result)

    @app.cli.command("import-pack")
    @click.option("--max-new", default=100, type=int, help="Сколько новых записей максимум добавить")
    @click.option("--pages-per-combo", default=1, type=int, help="Сколько страниц брать на одну связку жанр+год")
    @click.option(
        "--years",
        default="2025,2024,2023,2022,2021,2020,2019,2018",
        help="Годы через запятую"
    )
    @click.option(
        "--genres",
        default="драма,комедия,мелодрама,триллер,детектив,фантастика,фэнтези,приключения,мультфильм,боевик",
        help="Жанры через запятую"
    )
    @click.option(
        "--types",
        default="FILM,TV_SERIES",
        help="Типы через запятую: FILM,TV_SERIES"
    )
    def import_pack(max_new, pages_per_combo, years, genres, types):
        """
        Подробный импорт по разным жанрам и годам.
        Делает отдельный запрос деталей по каждому новому фильму/сериалу.
        """
        client = KinopoiskClient()

        year_list = parse_int_list(years)
        genre_names = parse_text_list(genres)
        type_list = parse_text_list(types)

        genre_objects = find_genres_by_names(genre_names)

        if not genre_objects:
            click.echo("Не найдены жанры. Сначала выполни: python -m flask --app manage.py sync-filters")
            return

        total = {
            "created": 0,
            "updated": 0,
            "skipped_existing": 0,
            "skipped_no_poster": 0,
            "api_pages": 0,
        }

        click.echo("Найдены жанры для импорта:")
        for genre in genre_objects:
            click.echo(f"- {genre.name} ({genre.kp_id})")

        for content_type in type_list:
            for year in year_list:
                for genre in genre_objects:
                    if total["created"] >= max_new:
                        click.echo("Достигнут лимит новых записей.")
                        print_import_result(total)
                        return

                    click.echo("")
                    click.echo(f"Импорт: тип={content_type}, год={year}, жанр={genre.name}")

                    result = import_from_api(
                        client=client,
                        content_type=content_type,
                        start_page=1,
                        pages=pages_per_combo,
                        genre_id=genre.kp_id,
                        country_id=None,
                        year=year,
                        with_videos=False,
                        update_existing=False,
                        require_poster=True,
                        max_new=max_new - total["created"],
                    )

                    total["created"] += result["created"]
                    total["updated"] += result["updated"]
                    total["skipped_existing"] += result["skipped_existing"]
                    total["skipped_no_poster"] += result["skipped_no_poster"]
                    total["api_pages"] += result["api_pages"]

        print_import_result(total)

    @app.cli.command("import-light-pack")
    @click.option("--target-films", default=250, type=int, help="Сколько новых фильмов добавить")
    @click.option("--target-series", default=250, type=int, help="Сколько новых сериалов добавить")
    @click.option("--pages-per-combo", default=2, type=int, help="Сколько страниц брать на связку жанр+год")
    @click.option("--start-year", default=2025, type=int, help="Начальный год")
    @click.option("--end-year", default=2010, type=int, help="Конечный год")
    @click.option(
        "--genres",
        default="драма,комедия,мелодрама,триллер,детектив,фантастика,фэнтези,приключения,мультфильм,боевик",
        help="Жанры через запятую"
    )
    def import_light_pack(target_films, target_series, pages_per_combo, start_year, end_year, genres):
        """
        Быстрый импорт большого количества уникальных фильмов и сериалов.
        Не делает отдельный запрос деталей по каждому произведению, поэтому бережет лимит API.
        Описания могут быть пустыми, зато быстро растет каталог.
        """
        client = KinopoiskClient()

        genre_names = parse_text_list(genres)
        genre_objects = find_genres_by_names(genre_names)

        if not genre_objects:
            click.echo("Не найдены жанры. Сначала выполни: python -m flask --app manage.py sync-filters")
            return

        years = list(range(start_year, end_year - 1, -1))

        total_created = 0
        total_existing = 0
        total_no_poster = 0
        total_api_pages = 0

        targets = [
            ("FILM", target_films),
            ("TV_SERIES", target_series),
        ]

        click.echo("Жанры для быстрого импорта:")
        for genre in genre_objects:
            click.echo(f"- {genre.name} ({genre.kp_id})")

        for content_type, target_count in targets:
            created_for_type = 0

            click.echo("")
            click.echo(f"=== Импорт типа {content_type}, цель: {target_count} ===")

            for year in years:
                if created_for_type >= target_count:
                    break

                for genre in genre_objects:
                    if created_for_type >= target_count:
                        break

                    for page in range(1, pages_per_combo + 1):
                        if created_for_type >= target_count:
                            break

                        click.echo(f"Тип={content_type}, год={year}, жанр={genre.name}, страница={page}")

                        try:
                            data = client.search_films(
                                page=page,
                                content_type=content_type,
                                genre_id=genre.kp_id,
                                country_id=None,
                                year=year,
                            )
                        except KinopoiskApiError as error:
                            click.echo(f"Ошибка API: {error}")
                            continue

                        total_api_pages += 1

                        items = data.get("items", [])
                        click.echo(f"Получено объектов: {len(items)}")

                        for item in items:
                            if created_for_type >= target_count:
                                break

                            result = save_movie_from_list_item(item, content_type)

                            if result == "created":
                                created_for_type += 1
                                total_created += 1
                            elif result == "existing":
                                total_existing += 1
                            elif result == "no_poster":
                                total_no_poster += 1

                        db.session.commit()

            click.echo(f"Добавлено для {content_type}: {created_for_type}")

        click.echo("")
        click.echo("Итог быстрого импорта:")
        click.echo(f"Создано новых записей: {total_created}")
        click.echo(f"Пропущено уже существующих: {total_existing}")
        click.echo(f"Пропущено без постера: {total_no_poster}")
        click.echo(f"Страниц API просмотрено: {total_api_pages}")


def import_from_api(
    client,
    content_type,
    start_page,
    pages,
    genre_id,
    country_id,
    year,
    with_videos,
    update_existing,
    require_poster,
    max_new=None,
):
    total_created = 0
    total_updated = 0
    total_skipped_existing = 0
    total_skipped_no_poster = 0
    total_api_pages = 0

    end_page = start_page + pages - 1

    for page in range(start_page, end_page + 1):
        click.echo(f"Страница {page}, тип {content_type}")

        try:
            data = client.search_films(
                page=page,
                content_type=content_type,
                genre_id=genre_id,
                country_id=country_id,
                year=year,
            )
        except KinopoiskApiError as error:
            click.echo(f"Ошибка: {error}")
            break

        total_api_pages += 1

        items = data.get("items", [])
        total_pages = data.get("totalPages")

        if total_pages is not None:
            click.echo(f"Получено объектов на странице: {len(items)}; всего страниц API: {total_pages}")
        else:
            click.echo(f"Получено объектов на странице: {len(items)}")

        if not items:
            continue

        for short_item in items:
            if max_new is not None and total_created >= max_new:
                db.session.commit()
                return {
                    "created": total_created,
                    "updated": total_updated,
                    "skipped_existing": total_skipped_existing,
                    "skipped_no_poster": total_skipped_no_poster,
                    "api_pages": total_api_pages,
                }

            kp_id = short_item.get("kinopoiskId")

            if not kp_id:
                continue

            list_poster = short_item.get("posterUrlPreview") or short_item.get("posterUrl")

            if require_poster and not list_poster:
                total_skipped_no_poster += 1
                continue

            existing_movie = Movie.query.filter_by(kp_id=kp_id).first()

            if existing_movie and not update_existing:
                total_skipped_existing += 1
                continue

            try:
                details = client.movie_details(kp_id)
            except KinopoiskApiError as error:
                click.echo(f"Не удалось загрузить {kp_id}: {error}")
                continue

            detail_poster = details.get("posterUrlPreview") or details.get("posterUrl")

            if require_poster and not detail_poster:
                total_skipped_no_poster += 1
                continue

            videos = {}

            if with_videos:
                try:
                    videos = client.movie_videos(kp_id)
                except KinopoiskApiError:
                    videos = {}

            result = save_movie(details, videos)

            if result == "created":
                total_created += 1
            elif result == "updated":
                total_updated += 1
            elif result == "skipped_no_poster":
                total_skipped_no_poster += 1

        db.session.commit()

    return {
        "created": total_created,
        "updated": total_updated,
        "skipped_existing": total_skipped_existing,
        "skipped_no_poster": total_skipped_no_poster,
        "api_pages": total_api_pages,
    }


def save_movie(details: dict, videos: dict) -> str:
    kp_id = details.get("kinopoiskId")

    if not kp_id:
        return "skipped_no_id"

    poster_url = details.get("posterUrlPreview") or details.get("posterUrl")

    if not poster_url:
        return "skipped_no_poster"

    movie = Movie.query.filter_by(kp_id=kp_id).first()
    created = movie is None

    if movie is None:
        movie = Movie(kp_id=kp_id)
        db.session.add(movie)

    movie.title = (
        clean_text(details.get("nameRu"))
        or clean_text(details.get("nameOriginal"))
        or clean_text(details.get("nameEn"))
        or "Без названия"
    )

    movie.original_title = clean_text(details.get("nameOriginal"))
    movie.description = clean_text(details.get("description"))
    movie.short_description = clean_text(details.get("shortDescription"))
    movie.year = safe_int(details.get("year"))
    movie.type = details.get("type") or "FILM"
    movie.poster_url = poster_url
    movie.rating_kp = safe_float(details.get("ratingKinopoisk"))
    movie.kinopoisk_url = details.get("webUrl") or f"https://www.kinopoisk.ru/film/{kp_id}/"

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

    trailer = choose_trailer(videos)

    if trailer:
        movie.trailer_url = trailer.get("url")
        movie.trailer_site = trailer.get("site")

    return "created" if created else "updated"


def save_movie_from_list_item(item: dict, fallback_type: str) -> str:
    kp_id = item.get("kinopoiskId")

    if not kp_id:
        return "no_id"

    existing_movie = Movie.query.filter_by(kp_id=kp_id).first()

    if existing_movie:
        return "existing"

    poster_url = item.get("posterUrlPreview") or item.get("posterUrl")

    if not poster_url:
        return "no_poster"

    movie = Movie(kp_id=kp_id)

    movie.title = (
        clean_text(item.get("nameRu"))
        or clean_text(item.get("nameOriginal"))
        or clean_text(item.get("nameEn"))
        or "Без названия"
    )

    movie.original_title = clean_text(item.get("nameOriginal"))
    movie.description = clean_text(item.get("description"))
    movie.short_description = clean_text(item.get("shortDescription"))
    movie.year = safe_int(item.get("year"))
    movie.type = item.get("type") or fallback_type
    movie.poster_url = poster_url
    movie.rating_kp = safe_float(item.get("ratingKinopoisk"))
    movie.kinopoisk_url = f"https://www.kinopoisk.ru/film/{kp_id}/"

    for genre_item in item.get("genres", []):
        genre_name = clean_text(genre_item.get("genre"))

        if not genre_name:
            continue

        genre = Genre.query.filter_by(name=genre_name).first()

        if not genre:
            genre = Genre(name=genre_name)
            db.session.add(genre)

        movie.genres.append(genre)

    for country_item in item.get("countries", []):
        country_name = clean_text(country_item.get("country"))

        if not country_name:
            continue

        country = Country.query.filter_by(name=country_name).first()

        if not country:
            country = Country(name=country_name)
            db.session.add(country)

        movie.countries.append(country)

    db.session.add(movie)

    return "created"


def choose_trailer(videos: dict) -> dict | None:
    items = videos.get("items", [])

    if not items:
        return None

    for item in items:
        name = (item.get("name") or "").lower()

        if "трейлер" in name or "trailer" in name:
            return item

    return items[0]


def is_poster_available(url: str | None) -> bool:
    if not url:
        return False

    try:
        response = requests.get(url, timeout=8, stream=True)
        content_type = response.headers.get("Content-Type", "")

        return response.status_code == 200 and "image" in content_type.lower()
    except requests.RequestException:
        return False


def find_genres_by_names(names: list[str]) -> list[Genre]:
    all_genres = Genre.query.all()
    result = []

    for wanted_name in names:
        wanted = wanted_name.lower().strip()

        found = None

        for genre in all_genres:
            current = genre.name.lower().strip()

            if current == wanted or wanted in current or current in wanted:
                found = genre
                break

        if found and found.kp_id and found not in result:
            result.append(found)

    return result


def parse_int_list(value: str) -> list[int]:
    result = []

    for item in value.split(","):
        item = item.strip()

        if not item:
            continue

        try:
            result.append(int(item))
        except ValueError:
            continue

    return result


def parse_text_list(value: str) -> list[str]:
    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def print_import_result(result: dict):
    click.echo("")
    click.echo("Итог импорта:")
    click.echo(f"Создано: {result['created']}")
    click.echo(f"Обновлено: {result['updated']}")
    click.echo(f"Пропущено уже существующих: {result['skipped_existing']}")
    click.echo(f"Пропущено без постера: {result['skipped_no_poster']}")
    click.echo(f"Страниц API просмотрено: {result['api_pages']}")


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