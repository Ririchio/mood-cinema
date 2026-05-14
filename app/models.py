from datetime import datetime

from app.extensions import db


movie_genres = db.Table(
    "movie_genres",
    db.Column("movie_id", db.Integer, db.ForeignKey("movies.id"), primary_key=True),
    db.Column("genre_id", db.Integer, db.ForeignKey("genres.id"), primary_key=True),
)


movie_countries = db.Table(
    "movie_countries",
    db.Column("movie_id", db.Integer, db.ForeignKey("movies.id"), primary_key=True),
    db.Column("country_id", db.Integer, db.ForeignKey("countries.id"), primary_key=True),
)


class Movie(db.Model):
    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    kp_id = db.Column(db.Integer, unique=True, nullable=False, index=True)

    title = db.Column(db.String(255), nullable=False)
    original_title = db.Column(db.String(255), nullable=True)

    description = db.Column(db.Text, nullable=True)
    short_description = db.Column(db.Text, nullable=True)

    year = db.Column(db.Integer, nullable=True)
    type = db.Column(db.String(50), nullable=False, default="FILM")

    poster_url = db.Column(db.Text, nullable=True)
    rating_kp = db.Column(db.Float, nullable=True)
    kinopoisk_url = db.Column(db.Text, nullable=True)

    trailer_url = db.Column(db.Text, nullable=True)
    trailer_site = db.Column(db.String(100), nullable=True)

    genres = db.relationship(
        "Genre",
        secondary=movie_genres,
        back_populates="movies",
    )

    countries = db.relationship(
        "Country",
        secondary=movie_countries,
        back_populates="movies",
    )

    emotion_profile = db.relationship(
        "MovieEmotionProfile",
        back_populates="movie",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def type_label(self):
        if self.type == "FILM":
            return "Фильм"

        if self.type == "TV_SERIES":
            return "Сериал"

        if self.type == "MINI_SERIES":
            return "Мини-сериал"

        return self.type or "Не указано"

    def has_description(self):
        return bool(
            clean_model_text(self.description)
            or clean_model_text(self.short_description)
        )

    def short_text(self):
        return clean_model_text(self.short_description) or clean_model_text(self.description)


class Genre(db.Model):
    __tablename__ = "genres"

    id = db.Column(db.Integer, primary_key=True)
    kp_id = db.Column(db.Integer, nullable=True, index=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    movies = db.relationship(
        "Movie",
        secondary=movie_genres,
        back_populates="genres",
    )


class Country(db.Model):
    __tablename__ = "countries"

    id = db.Column(db.Integer, primary_key=True)
    kp_id = db.Column(db.Integer, nullable=True, index=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    movies = db.relationship(
        "Movie",
        secondary=movie_countries,
        back_populates="countries",
    )


class MovieEmotionProfile(db.Model):
    __tablename__ = "movie_emotion_profiles"

    id = db.Column(db.Integer, primary_key=True)

    movie_id = db.Column(
        db.Integer,
        db.ForeignKey("movies.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    lightness = db.Column(db.Float, nullable=False, default=0)
    humor = db.Column(db.Float, nullable=False, default=0)
    warmth = db.Column(db.Float, nullable=False, default=0)
    romance = db.Column(db.Float, nullable=False, default=0)
    sadness = db.Column(db.Float, nullable=False, default=0)
    catharsis = db.Column(db.Float, nullable=False, default=0)
    tension = db.Column(db.Float, nullable=False, default=0)
    adrenaline = db.Column(db.Float, nullable=False, default=0)
    wonder = db.Column(db.Float, nullable=False, default=0)
    inspiration = db.Column(db.Float, nullable=False, default=0)
    nostalgia = db.Column(db.Float, nullable=False, default=0)
    darkness = db.Column(db.Float, nullable=False, default=0)
    complexity = db.Column(db.Float, nullable=False, default=0)
    pace = db.Column(db.Float, nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    movie = db.relationship("Movie", back_populates="emotion_profile")

    def to_dict(self):
        return {
            "lightness": self.lightness,
            "humor": self.humor,
            "warmth": self.warmth,
            "romance": self.romance,
            "sadness": self.sadness,
            "catharsis": self.catharsis,
            "tension": self.tension,
            "adrenaline": self.adrenaline,
            "wonder": self.wonder,
            "inspiration": self.inspiration,
            "nostalgia": self.nostalgia,
            "darkness": self.darkness,
            "complexity": self.complexity,
            "pace": self.pace,
        }


class MoodProfile(db.Model):
    __tablename__ = "mood_profiles"

    id = db.Column(db.Integer, primary_key=True)

    main_state = db.Column(db.String(100), nullable=True)
    mood_direction = db.Column(db.String(100), nullable=True)
    energy = db.Column(db.String(100), nullable=True)
    mental_load = db.Column(db.String(100), nullable=True)
    pace = db.Column(db.String(100), nullable=True)
    reality_mode = db.Column(db.String(100), nullable=True)
    warmth_need = db.Column(db.String(100), nullable=True)
    humor_need = db.Column(db.String(100), nullable=True)
    tension_need = db.Column(db.String(100), nullable=True)
    romance_need = db.Column(db.String(100), nullable=True)
    heavy_topics = db.Column(db.String(100), nullable=True)
    ending = db.Column(db.String(100), nullable=True)
    preferred_type = db.Column(db.String(100), nullable=True)
    rating_policy = db.Column(db.String(100), nullable=True)

    summary = db.Column(db.Text, nullable=True)
    raw_answers = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def clean_model_text(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None