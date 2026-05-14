import re
from urllib.parse import urlparse


def get_embed_url(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if "youtube.com" in host:
        match = re.search(r"v=([^&]+)", parsed.query)
        if match:
            return f"https://www.youtube.com/embed/{match.group(1)}"

    if "youtu.be" in host and path:
        video_id = path.split("/")[0]
        return f"https://www.youtube.com/embed/{video_id}"

    if "rutube.ru" in host:
        parts = path.split("/")
        if "video" in parts:
            try:
                video_id = parts[parts.index("video") + 1]
                return f"https://rutube.ru/play/embed/{video_id}"
            except IndexError:
                return None

    return None


def register_template_filters(app):
    @app.template_filter("embed_url")
    def embed_url_filter(url):
        return get_embed_url(url)