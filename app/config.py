import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-later")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    KINOPOISK_API_KEY = os.getenv("KINOPOISK_API_KEY")
    KINOPOISK_API_BASE = os.getenv(
        "KINOPOISK_API_BASE",
        "https://kinopoiskapiunofficial.tech/api"
    )

    ITEMS_PER_PAGE = 16