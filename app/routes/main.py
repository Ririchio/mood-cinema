from flask import Blueprint, jsonify, render_template, request, url_for
from sqlalchemy import or_

from app.config import Config
from app.models import Movie, Genre, Country

main_bp = Blueprint("main", __name__)


def normalize_int_list(values):
    result = []

    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue

        if number > 0 and number not in result:
            result.append(number)

    return result


def build_catalog_query():
    q = request.args.get("q", "", type=str).strip()
    content_type = request.args.get("type", "all", type=str)
    year = request.args.get("year", 0, type=int)

    include_genre_ids = normalize_int_list(request.args.getlist("include_genres"))
    exclude_genre_ids = normalize_int_list(request.args.getlist("exclude_genres"))

    include_country_ids = normalize_int_list(request.args.getlist("include_countries"))
    exclude_country_ids = normalize_int_list(request.args.getlist("exclude_countries"))

    query = Movie.query.filter(
        Movie.poster_url.isnot(None),
        Movie.poster_url != "",
    )

    if q:
        query = query.filter(
            or_(
                Movie.title.like(f"%{q}%"),
                Movie.original_title.like(f"%{q}%"),
            )
        )

    if content_type != "all":
        query = query.filter(Movie.type == content_type)

    if year:
        query = query.filter(Movie.year == year)

    if include_genre_ids:
        query = query.filter(Movie.genres.any(Genre.id.in_(include_genre_ids)))

    if exclude_genre_ids:
        query = query.filter(~Movie.genres.any(Genre.id.in_(exclude_genre_ids)))

    if include_country_ids:
        query = query.filter(Movie.countries.any(Country.id.in_(include_country_ids)))

    if exclude_country_ids:
        query = query.filter(~Movie.countries.any(Country.id.in_(exclude_country_ids)))

    query = query.distinct().order_by(
        Movie.rating_kp.desc(),
        Movie.year.desc(),
        Movie.id.desc(),
    )

    filters = {
        "q": q,
        "type": content_type,
        "year": year,
        "include_genres": include_genre_ids,
        "exclude_genres": exclude_genre_ids,
        "include_countries": include_country_ids,
        "exclude_countries": exclude_country_ids,
    }

    return query, filters


def get_filter_data():
    genres = Genre.query.order_by(Genre.name).all()
    countries = Country.query.order_by(Country.name).all()

    years = [
        row[0]
        for row in Movie.query.with_entities(Movie.year)
        .filter(Movie.year.isnot(None))
        .filter(Movie.poster_url.isnot(None))
        .filter(Movie.poster_url != "")
        .distinct()
        .order_by(Movie.year.desc())
        .all()
    ]

    return genres, countries, years


@main_bp.route("/")
def index():
    page = max(1, request.args.get("page", 1, type=int))

    query, filters = build_catalog_query()

    pagination = query.paginate(
        page=page,
        per_page=Config.ITEMS_PER_PAGE,
        error_out=False,
    )

    genres, countries, years = get_filter_data()

    selected_include_genres = [genre for genre in genres if genre.id in filters["include_genres"]]
    selected_exclude_genres = [genre for genre in genres if genre.id in filters["exclude_genres"]]

    selected_include_countries = [country for country in countries if country.id in filters["include_countries"]]
    selected_exclude_countries = [country for country in countries if country.id in filters["exclude_countries"]]

    return render_template(
        "index.html",
        movies=pagination.items,
        pagination=pagination,
        genres=genres,
        countries=countries,
        years=years,
        filters=filters,
        selected_include_genres=selected_include_genres,
        selected_exclude_genres=selected_exclude_genres,
        selected_include_countries=selected_include_countries,
        selected_exclude_countries=selected_exclude_countries,
    )


@main_bp.route("/api/movies")
def movies_api():
    page = max(1, request.args.get("page", 1, type=int))

    query, _filters = build_catalog_query()

    pagination = query.paginate(
        page=page,
        per_page=Config.ITEMS_PER_PAGE,
        error_out=False,
    )

    html = render_template(
        "partials/_movie_cards.html",
        movies=pagination.items,
    )

    return jsonify({
        "html": html,
        "has_next": pagination.has_next,
        "next_page": pagination.next_num if pagination.has_next else None,
        "total": pagination.total,
    })


@main_bp.route("/api/suggest")
def suggest_api():
    q = request.args.get("q", "", type=str).strip()

    if len(q) < 2:
        return jsonify([])

    movies = (
        Movie.query
        .filter(
            Movie.poster_url.isnot(None),
            Movie.poster_url != "",
        )
        .filter(
            or_(
                Movie.title.like(f"%{q}%"),
                Movie.original_title.like(f"%{q}%"),
            )
        )
        .order_by(
            Movie.rating_kp.desc(),
            Movie.year.desc(),
            Movie.id.desc(),
        )
        .limit(8)
        .all()
    )

    result = []

    for movie in movies:
        result.append({
            "id": movie.id,
            "title": movie.title,
            "original_title": movie.original_title,
            "year": movie.year,
            "type": movie.type_label(),
            "poster_url": movie.poster_url,
            "url": url_for("main.detail", movie_id=movie.id),
        })

    return jsonify(result)


@main_bp.route("/movie/<int:movie_id>")
def detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    return render_template("detail.html", movie=movie)


@main_bp.route("/health")
def health():
    return {"status": "ok"}