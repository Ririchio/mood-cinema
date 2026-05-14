import requests
from flask import current_app


class KinopoiskApiError(Exception):
    pass


class KinopoiskClient:
    def __init__(self):
        self.base_url = current_app.config["KINOPOISK_API_BASE"]
        self.api_key = current_app.config["KINOPOISK_API_KEY"]

        if not self.api_key:
            raise KinopoiskApiError("Не указан KINOPOISK_API_KEY в .env")

    @property
    def headers(self):
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None):
        url = f"{self.base_url}{path}"

        response = requests.get(
            url,
            headers=self.headers,
            params=params or {},
            timeout=25,
        )

        if response.status_code == 401:
            raise KinopoiskApiError("Ошибка авторизации API. Проверь KINOPOISK_API_KEY.")

        if response.status_code == 429:
            raise KinopoiskApiError("Превышен лимит запросов API. Подожди до завтра.")

        if response.status_code >= 400:
            raise KinopoiskApiError(
                f"Ошибка API: {response.status_code} {response.text}"
            )

        return response.json()

    def filters(self):
        return self._get("/v2.2/films/filters")

    def search_films(
        self,
        page: int = 1,
        content_type: str = "FILM",
        genre_id: int | None = None,
        country_id: int | None = None,
        year: int | None = None,
        keyword: str | None = None,
    ):
        params = {
            "page": page,
            "type": content_type,
            "order": "RATING",
            "ratingFrom": 6,
            "ratingTo": 10,
        }

        if genre_id:
            params["genres"] = genre_id

        if country_id:
            params["countries"] = country_id

        if year:
            params["yearFrom"] = year
            params["yearTo"] = year

        if keyword:
            params["keyword"] = keyword

        return self._get("/v2.2/films", params=params)

    def movie_details(self, kp_id: int):
        return self._get(f"/v2.2/films/{kp_id}")

    def movie_videos(self, kp_id: int):
        return self._get(f"/v2.2/films/{kp_id}/videos")