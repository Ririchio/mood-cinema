import json
import re
from dataclasses import dataclass

from sqlalchemy import and_, or_

from app.models import Movie, MovieEmotionProfile, MoodProfile
from app.services.emotion_engine import DIMENSIONS


@dataclass
class RecommendedItem:
    movie: Movie
    score: float
    reason: str
    tags: list[str]


@dataclass
class RecommendationResult:
    mood_profile: MoodProfile
    profile_summary: str
    groups: dict[str, list[RecommendedItem]]


QUESTION_FIELDS = [
    "main_state",
    "story_need",
    "serious_type",
    "serious_weight",
    "comfort_type",
    "comfort_avoid",
    "comedy_type",
    "humor_type",
    "drive_type",
    "drive_hardness",
    "thinking_type",
    "thinking_complexity",
    "relationship_type",
    "relationship_conflict",
    "format_preference",
    "series_style",
    "animation_policy",
    "age_category",
    "pace",
    "rating_policy",
]


ANSWER_LABELS = {
    "main_state": {
        "sad": "грусть",
        "anxious": "тревога",
        "tired": "усталость",
        "angry": "раздражение",
        "calm": "спокойствие",
        "happy": "радость",
        "bored": "скука",
        "unknown": "непонятное состояние",
    },
    "story_need": {
        "serious": "серьёзная история",
        "comfort": "спокойная история",
        "comedy": "смешная история",
        "drive": "напряжённая история",
        "think": "история со смыслом",
        "relationships": "история об отношениях",
    },
    "format_preference": {
        "FILM": "фильм",
        "TV_SERIES": "сериал",
        "any": "любой формат",
    },
    "pace": {
        "slow": "медленный темп",
        "medium": "ровный темп",
        "fast": "быстрый темп",
        "any": "любой темп",
    },
    "rating_policy": {
        "safe": "рейтинг важен",
        "balanced": "рейтинг немного важен",
        "brave": "рейтинг не важен",
    },
}


TEXT_KEYWORDS = {
    "cozy": ["уют", "дом", "тепл", "добро", "добр", "забот", "поддерж", "семь", "друж", "сосед", "праздник", "маленький город"],
    "simple": ["прост", "легк", "повседнев", "обычн", "работ", "учеб", "друз", "жизн", "город"],
    "hope": ["надежд", "мечт", "помог", "спас", "новая жизнь", "начать заново", "примир", "исцел"],
    "romance": ["любов", "роман", "отношен", "влюб", "чувств", "симпат", "свадь", "брак", "пара", "расстав"],
    "friendship": ["дружб", "друз", "компания", "подруга", "друг", "команда", "вместе"],
    "family": ["семь", "мать", "отец", "родител", "сын", "дочь", "брат", "сест", "родн"],
    "comedy": ["комед", "смеш", "юмор", "забав", "нелеп", "курьез", "неудач", "случайн"],
    "adult_comedy": ["вечерин", "бар", "развод", "измена", "кризис", "любовник", "любовница", "взросл"],
    "black_humor": ["черн", "мрачн", "цинич", "абсурд", "смерт", "похорон"],
    "investigation": ["расслед", "тайн", "загад", "детектив", "улика", "исчез", "секрет", "подозрева", "дело"],
    "survival": ["выжив", "опасн", "ловуш", "катастроф", "плен", "остров", "борьб", "спастись"],
    "crime": ["преступ", "кримин", "маф", "банд", "убий", "ограб", "полици", "детектив", "наркот", "тюрьм"],
    "battle": ["противостоя", "борьб", "враг", "месть", "конфликт", "битв", "сраж"],
    "serious": ["драма", "трудн", "сложн", "кризис", "судьб", "испытан", "потер", "траг", "болезн", "смерт"],
    "social": ["общество", "власть", "закон", "несправедлив", "бедност", "полит", "система", "суд", "правд"],
    "thinking": ["смысл", "память", "прошл", "будущ", "выбор", "тайн", "загад", "жизн", "справедлив", "вина"],
    "future": ["будущ", "технолог", "робот", "космос", "планет", "галактик", "иноплан", "искусственный интеллект"],
    "memory": ["память", "прошл", "воспомин", "детств", "тайна прошлого"],
    "violence": ["жесток", "насили", "кров", "пытк", "маньяк", "убий"],
    "death": ["смерт", "болезн", "умира", "похорон", "потеря", "трагед"],
    "conflict": ["ссор", "скандал", "конфликт", "развод", "измена", "вражд"],
}


SERIES_COUNTRIES = {
    "dorama": ["южная корея", "корея", "япония", "китай", "тайвань", "таиланд"],
    "turkish": ["турция"],
    "western": ["сша", "великобритания", "канада", "австралия"],
    "russian": ["россия"],
}


BAD_GENRES = [
    "реальное тв", "реалити-шоу", "ток-шоу", "игра", "новости",
    "спорт", "концерт", "церемония", "документальный",
]

BAD_TEXT = [
    "дом-2", "дом 2", "тнт", "стс", "пятница", "нтв", "телеканал",
    "реалити", "ток-шоу", "телешоу", "передача", "выпуск",
    "стендап", "stand up", "youtube", "ютуб", "интервью",
]

LOW_QUALITY_TV_TITLES = [
    "тётя марта", "тетя марта", "инспектор гаврилов", "папины дочки",
    "супер папочка", "сокровища гномов",
]

CHILDISH_WORDS = [
    "гном", "гномов", "сказочный", "волшебный", "папины дочки",
    "папочка", "мама вернулась", "дети", "школьник", "школьница",
]


def extract_answers(form):
    return {field: (form.get(field) or "").strip() for field in QUESTION_FIELDS}


def create_mood_profile(answers):
    mood_profile = MoodProfile(
        main_state=answers.get("main_state"),
        mood_direction=answers.get("story_need"),
        pace=answers.get("pace"),
        preferred_type=answers.get("format_preference"),
        rating_policy=answers.get("rating_policy"),
        raw_answers=json.dumps(answers, ensure_ascii=False),
    )
    mood_profile.summary = build_profile_summary(answers)
    return mood_profile


def build_profile_summary(answers):
    parts = []

    for field in ["main_state", "story_need", "format_preference", "pace", "rating_policy"]:
        label = ANSWER_LABELS.get(field, {}).get(answers.get(field))

        if label:
            parts.append(label)

    if not parts:
        return "Система подбирает фильмы и сериалы по текущему запросу."

    return "Текущий запрос: " + "; ".join(parts) + "."


def get_recommendations(mood_profile):
    answers = json.loads(mood_profile.raw_answers or "{}")
    profile = build_user_profile(answers)

    candidates = get_candidate_movies(profile, relaxed=False)
    print(f"[Mood Cinema] Проанализировано кандидатов после строгих фильтров: {len(candidates)}")

    scored_items = [score_movie(movie, movie.emotion_profile, profile) for movie in candidates]
    scored_items = [item for item in scored_items if item.score > 0]
    scored_items.sort(key=lambda item: item.score, reverse=True)

    if len(scored_items) < 8:
        candidates = get_candidate_movies(profile, relaxed=True)
        print(f"[Mood Cinema] Строгих совпадений мало, мягкий режим: {len(candidates)} кандидатов")
        scored_items = [score_movie(movie, movie.emotion_profile, profile) for movie in candidates]
        scored_items = [item for item in scored_items if item.score > 0]
        scored_items.sort(key=lambda item: item.score, reverse=True)

    return RecommendationResult(
        mood_profile=mood_profile,
        profile_summary=mood_profile.summary,
        groups={
            "Рекомендации по степени совпадения": diversify_ranked_items(scored_items),
        },
    )


def build_user_profile(answers):
    target = {dimension: 2.5 for dimension in DIMENSIONS}
    weights = {dimension: 1.0 for dimension in DIMENSIONS}
    max_values = {}
    min_values = {}

    required_genres = set()
    bonus_genres = set()
    excluded_genres = set()

    text_positive = []
    text_negative = []

    def add(dimension, value, weight=0.4):
        target[dimension] = clamp(target[dimension] + value)
        weights[dimension] = clamp(weights[dimension] + weight, 0.2, 5.0)

    main_state = answers.get("main_state")
    story_need = answers.get("story_need")

    if main_state == "sad":
        add("sadness", 0.6, 0.5)
        add("catharsis", 0.5, 0.5)
        add("warmth", 0.6, 0.6)

    if main_state == "anxious":
        add("warmth", 1.0, 0.8)
        add("tension", -1.4, 1.0)
        add("darkness", -1.3, 1.0)
        max_values["tension"] = 2.6
        max_values["darkness"] = 2.6

    if main_state == "tired":
        add("lightness", 1.1, 0.8)
        add("complexity", -1.3, 1.0)
        add("pace", -0.8, 0.7)
        max_values["complexity"] = 2.8

    if main_state == "angry":
        add("adrenaline", 1.0, 0.7)
        add("pace", 0.8, 0.6)
        add("tension", 0.5, 0.5)

    if main_state == "calm":
        add("warmth", 0.7, 0.6)
        add("tension", -0.7, 0.6)
        add("darkness", -0.6, 0.5)

    if main_state == "happy":
        add("lightness", 1.1, 0.8)
        add("humor", 0.9, 0.7)
        add("warmth", 0.5, 0.5)

    if main_state == "bored":
        add("pace", 0.9, 0.6)
        add("wonder", 0.8, 0.6)
        add("tension", 0.4, 0.4)

    if story_need == "comfort":
        bonus_genres.update(["мелодрама", "комедия"])
        excluded_genres.update([
            "ужасы", "боевик", "военный", "криминал", "триллер",
            "детектив", "мультфильм", "детский",
        ])
        text_positive.extend(["cozy", "hope"])
        text_negative.extend(["violence", "death", "conflict"])
        add("warmth", 2.2, 1.5)
        add("lightness", 1.3, 1.0)
        add("tension", -1.9, 1.4)
        add("darkness", -1.9, 1.4)
        add("complexity", -0.8, 0.7)
        max_values["tension"] = 2.2
        max_values["darkness"] = 2.2
        max_values["complexity"] = 3.2

    elif story_need == "comedy":
        required_genres.add("комедия")
        excluded_genres.update(["ужасы", "военный", "детский"])
        text_positive.append("comedy")
        add("humor", 2.4, 1.6)
        add("lightness", 1.1, 0.9)
        add("sadness", -1.0, 0.8)
        add("darkness", -1.0, 0.8)
        min_values["humor"] = 2.4
        max_values["darkness"] = 3.2

    elif story_need == "serious":
        bonus_genres.update(["драма", "мелодрама", "биография"])
        text_positive.append("serious")
        add("catharsis", 1.1, 0.8)
        add("sadness", 0.5, 0.5)
        add("humor", -0.8, 0.6)

    elif story_need == "drive":
        bonus_genres.update(["триллер", "детектив", "криминал", "боевик"])
        add("tension", 1.4, 1.0)
        add("adrenaline", 1.5, 1.0)
        add("pace", 1.0, 0.7)

    elif story_need == "think":
        bonus_genres.update(["драма", "детектив", "фантастика", "биография"])
        text_positive.append("thinking")
        add("complexity", 1.1, 0.8)
        add("catharsis", 0.8, 0.6)

    elif story_need == "relationships":
        bonus_genres.update(["мелодрама", "драма", "комедия"])
        text_positive.append("romance")
        add("romance", 1.8, 1.2)
        add("warmth", 0.9, 0.7)

    apply_branch_answers(
        answers, target, weights, max_values, min_values,
        required_genres, bonus_genres, excluded_genres,
        text_positive, text_negative,
    )

    pace = answers.get("pace")

    if pace == "slow":
        add("pace", -1.1, 0.8)

    if pace == "fast":
        add("pace", 1.3, 0.8)
        add("adrenaline", 0.5, 0.4)

    return {
        "answers": answers,
        "target": {key: round(clamp(value), 2) for key, value in target.items()},
        "weights": weights,
        "max_values": max_values,
        "min_values": min_values,
        "required_genres": required_genres,
        "bonus_genres": bonus_genres,
        "excluded_genres": excluded_genres,
        "text_positive": text_positive,
        "text_negative": text_negative,
        "story_need": story_need or "comfort",
        "format_preference": answers.get("format_preference") or "any",
        "series_style": answers.get("series_style") or "any",
        "animation_policy": answers.get("animation_policy") or "any",
        "age_category": answers.get("age_category") or "any",
        "pace": answers.get("pace") or "any",
        "rating_policy": answers.get("rating_policy") or "balanced",
    }


def apply_branch_answers(
    answers, target, weights, max_values, min_values,
    required_genres, bonus_genres, excluded_genres,
    text_positive, text_negative,
):
    def add(dimension, value, weight=0.4):
        target[dimension] = clamp(target[dimension] + value)
        weights[dimension] = clamp(weights[dimension] + weight, 0.2, 5.0)

    if answers.get("comfort_type") == "cozy":
        text_positive.append("cozy")
        add("warmth", 1.0, 0.9)

    if answers.get("comfort_type") == "simple":
        text_positive.append("simple")
        add("complexity", -1.1, 0.9)
        max_values["complexity"] = min(max_values.get("complexity", 5), 2.6)

    if answers.get("comfort_type") == "slow":
        add("pace", -1.1, 0.8)

    if answers.get("comfort_type") == "hopeful":
        text_positive.append("hope")
        add("inspiration", 1.1, 0.8)
        add("darkness", -0.8, 0.6)

    if answers.get("comfort_avoid") == "violence":
        text_negative.append("violence")
        excluded_genres.update(["боевик", "ужасы", "криминал", "триллер"])
        max_values["darkness"] = min(max_values.get("darkness", 5), 2.1)

    if answers.get("comfort_avoid") == "death":
        text_negative.append("death")
        max_values["sadness"] = min(max_values.get("sadness", 5), 2.8)

    if answers.get("comfort_avoid") == "conflict":
        text_negative.append("conflict")
        max_values["tension"] = min(max_values.get("tension", 5), 2.3)

    if answers.get("comfort_avoid") == "confusion":
        add("complexity", -1.3, 0.9)
        max_values["complexity"] = min(max_values.get("complexity", 5), 2.5)

    if answers.get("serious_type") == "romantic":
        bonus_genres.add("мелодрама")
        text_positive.append("romance")
        add("romance", 1.0, 0.7)

    if answers.get("serious_type") == "family":
        text_positive.append("family")
        add("warmth", 0.8, 0.6)

    if answers.get("serious_type") == "social":
        text_positive.append("social")
        add("complexity", 0.5, 0.4)

    if answers.get("serious_weight") == "light":
        add("darkness", -0.8, 0.7)
        add("tension", -0.5, 0.5)
        max_values["darkness"] = min(max_values.get("darkness", 5), 3.0)

    if answers.get("serious_weight") == "heavy":
        add("darkness", 1.0, 0.7)
        add("catharsis", 0.8, 0.6)

    if answers.get("comedy_type") == "everyday":
        text_positive.append("simple")

    if answers.get("comedy_type") == "romantic":
        bonus_genres.add("мелодрама")
        text_positive.append("romance")
        add("romance", 0.9, 0.6)

    if answers.get("comedy_type") == "adventure":
        bonus_genres.add("приключения")
        add("pace", 0.5, 0.4)
        add("wonder", 0.4, 0.4)

    if answers.get("comedy_type") == "friends":
        text_positive.append("friendship")
        add("warmth", 0.7, 0.5)

    if answers.get("humor_type") == "kind":
        add("warmth", 0.8, 0.6)
        add("darkness", -0.6, 0.5)

    if answers.get("humor_type") == "black":
        text_positive.append("black_humor")
        add("darkness", 0.5, 0.4)

    if answers.get("humor_type") == "absurd":
        add("wonder", 0.7, 0.5)

    if answers.get("humor_type") == "adult":
        text_positive.append("adult_comedy")
        add("darkness", 0.2, 0.3)

    if answers.get("drive_type") == "investigation":
        bonus_genres.update(["детектив", "триллер"])
        text_positive.append("investigation")
        add("complexity", 0.5, 0.5)

    if answers.get("drive_type") == "survival":
        text_positive.append("survival")
        add("adrenaline", 0.8, 0.6)

    if answers.get("drive_type") == "crime":
        bonus_genres.update(["криминал", "триллер"])
        text_positive.append("crime")

    if answers.get("drive_type") == "battle":
        text_positive.append("battle")
        add("tension", 0.7, 0.5)

    if answers.get("drive_hardness") == "low":
        add("darkness", -0.7, 0.5)
        max_values["darkness"] = min(max_values.get("darkness", 5), 3.2)

    if answers.get("drive_hardness") == "high":
        add("darkness", 0.9, 0.7)
        add("tension", 0.7, 0.5)

    if answers.get("thinking_type") == "justice":
        text_positive.append("social")

    if answers.get("thinking_type") == "mystery":
        bonus_genres.update(["детектив", "триллер"])
        text_positive.append("investigation")

    if answers.get("thinking_type") == "future":
        bonus_genres.add("фантастика")
        text_positive.append("future")

    if answers.get("thinking_type") == "memory":
        text_positive.append("memory")
        add("nostalgia", 1.0, 0.7)

    if answers.get("thinking_type") == "life":
        text_positive.append("thinking")
        add("catharsis", 0.8, 0.6)

    if answers.get("thinking_complexity") == "clear":
        add("complexity", -0.8, 0.7)
        max_values["complexity"] = min(max_values.get("complexity", 5), 3.0)

    if answers.get("thinking_complexity") == "complex":
        add("complexity", 1.0, 0.8)

    if answers.get("relationship_type") == "light_romance":
        bonus_genres.update(["мелодрама", "комедия"])
        text_positive.append("romance")
        add("lightness", 0.7, 0.5)

    if answers.get("relationship_type") == "dramatic_love":
        bonus_genres.update(["мелодрама", "драма"])
        text_positive.append("romance")
        add("catharsis", 0.7, 0.5)

    if answers.get("relationship_type") == "slow_burn":
        text_positive.append("romance")
        add("romance", 1.0, 0.7)
        add("pace", -0.3, 0.3)

    if answers.get("relationship_type") == "family":
        text_positive.append("family")
        add("warmth", 1.0, 0.7)

    if answers.get("relationship_type") == "friendship":
        text_positive.append("friendship")
        add("warmth", 0.9, 0.6)

    if answers.get("relationship_conflict") == "low":
        add("tension", -0.8, 0.6)
        max_values["tension"] = min(max_values.get("tension", 5), 3.0)

    if answers.get("relationship_conflict") == "high":
        add("tension", 0.7, 0.5)
        add("catharsis", 0.5, 0.4)


def get_candidate_movies(profile, relaxed=False):
    query = (
        Movie.query
        .join(MovieEmotionProfile)
        .filter(Movie.poster_url.isnot(None), Movie.poster_url != "")
        .filter(
            or_(
                and_(Movie.description.isnot(None), Movie.description != ""),
                and_(Movie.short_description.isnot(None), Movie.short_description != ""),
            )
        )
    )

    if profile["format_preference"] in ["FILM", "TV_SERIES"]:
        query = query.filter(Movie.type == profile["format_preference"])

    movies = query.all()
    result = []

    for movie in movies:
        scores = movie.emotion_profile.to_dict()

        if is_bad_content(movie, profile):
            continue

        if not relaxed:
            if violates_animation_or_age(movie, profile):
                continue

            if violates_series_style(movie, profile):
                continue

            if violates_hard_limits(movie, scores, profile):
                continue

        result.append(movie)

    return result


def violates_animation_or_age(movie, profile):
    genres = get_genre_names(movie)

    is_cartoon = has_any_genre(genres, ["мультфильм"])
    is_anime = has_any_genre(genres, ["аниме"])
    is_family = has_any_genre(genres, ["семейный"])
    is_children = has_any_genre(genres, ["детский"])
    is_childish_text = any(word in get_movie_text(movie) for word in CHILDISH_WORDS)

    animation_policy = profile["animation_policy"]
    age_category = profile["age_category"]
    story_need = profile["story_need"]

    if animation_policy == "no" and (is_cartoon or is_anime):
        return True

    if animation_policy == "not_childish" and (is_cartoon or is_family or is_children or is_childish_text):
        return True

    if age_category == "adult" and (is_cartoon or is_anime or is_family or is_children or is_childish_text):
        return True

    if age_category == "teen" and (is_children or is_cartoon or is_childish_text):
        return True

    if story_need in ["comfort", "comedy"] and age_category in ["", "any"]:
        if is_cartoon or is_family or is_children or is_childish_text:
            return True

    return False


def violates_series_style(movie, profile):
    style = profile["series_style"]

    if style in ["", "any"]:
        return False

    if movie.type != "TV_SERIES":
        return False

    genres = get_genre_names(movie)
    countries = get_country_names(movie)

    if style == "anime":
        return not has_any_genre(genres, ["аниме"])

    expected = SERIES_COUNTRIES.get(style)

    if not expected:
        return False

    return not any(country_part in country for country_part in expected for country in countries)


def violates_hard_limits(movie, scores, profile):
    for dimension, max_value in profile["max_values"].items():
        if scores.get(dimension, 0) > max_value + 0.6:
            return True

    for dimension, min_value in profile["min_values"].items():
        if scores.get(dimension, 0) < min_value - 0.6:
            return True

    if profile["rating_policy"] == "safe":
        if movie.rating_kp is None or movie.rating_kp < 6.7:
            return True

    if profile["story_need"] == "comfort":
        if has_genre(movie, ["ужасы", "боевик", "военный", "криминал", "триллер", "детектив", "мультфильм", "детский"]):
            return True

    if profile["story_need"] == "comedy":
        if scores.get("humor", 0) < 2.2 and not has_genre(movie, ["комедия"]):
            return True

    return False


def score_movie(movie, emotion_profile, profile):
    scores = emotion_profile.to_dict()
    total = 0.0

    for dimension in DIMENSIONS:
        movie_value = scores.get(dimension, 0)
        target_value = profile["target"].get(dimension, 2.5)
        weight = profile["weights"].get(dimension, 1.0)

        closeness = 5 - abs(movie_value - target_value)
        total += max(0, closeness) * weight

    total += score_genres(movie, profile)
    total += score_text(movie, profile)
    total += score_rating(movie, profile["rating_policy"])
    total += score_story_need(movie, scores, profile)
    total += score_format_details(movie, profile)
    total += quality_penalty(movie, profile)

    tags = build_tags(movie, scores, profile)

    return RecommendedItem(
        movie=movie,
        score=round(total, 2),
        reason="",
        tags=tags[:4],
    )


def score_genres(movie, profile):
    total = 0.0
    genres = get_genre_names(movie)

    for genre in profile["required_genres"]:
        total += 20 if any(genre in name for name in genres) else -12

    for genre in profile["bonus_genres"]:
        if any(genre in name for name in genres):
            total += 10

    for genre in profile["excluded_genres"]:
        if any(genre in name for name in genres):
            total -= 40

    return total


def score_text(movie, profile):
    text = get_movie_text(movie)
    total = 0.0

    for group in profile["text_positive"]:
        total += count_keyword_hits(text, TEXT_KEYWORDS.get(group, [])) * 5.5

    for group in profile["text_negative"]:
        total -= count_keyword_hits(text, TEXT_KEYWORDS.get(group, [])) * 9.0

    return total


def score_rating(movie, rating_policy):
    if movie.rating_kp is None:
        return -5

    rating = min(movie.rating_kp, 10)

    if rating_policy == "safe":
        return rating * 2.8

    if rating_policy == "balanced":
        return rating * 1.8

    return rating * 0.8


def score_story_need(movie, scores, profile):
    story_need = profile["story_need"]
    total = 0.0

    if story_need == "comfort":
        if scores.get("warmth", 0) >= 3.5:
            total += 18
        if scores.get("darkness", 0) <= 2.2:
            total += 16
        if scores.get("tension", 0) <= 2.3:
            total += 14
        if scores.get("complexity", 0) <= 3.0:
            total += 8
        if movie.type == "TV_SERIES" and profile["format_preference"] != "TV_SERIES":
            total -= 12

    if story_need == "comedy":
        if scores.get("humor", 0) >= 4:
            total += 20
        elif scores.get("humor", 0) >= 3:
            total += 12
        else:
            total -= 12

    if story_need == "drive":
        if scores.get("tension", 0) >= 3.5:
            total += 12
        if scores.get("adrenaline", 0) >= 3.5:
            total += 12

    if story_need == "serious":
        if scores.get("catharsis", 0) >= 3.3:
            total += 12
        if scores.get("humor", 0) >= 4:
            total -= 8

    if story_need == "think":
        if scores.get("complexity", 0) >= 3.3:
            total += 12
        if scores.get("catharsis", 0) >= 3.0:
            total += 6

    if story_need == "relationships":
        if scores.get("romance", 0) >= 3.4:
            total += 14
        if scores.get("warmth", 0) >= 3.2:
            total += 8

    return total


def score_format_details(movie, profile):
    total = 0.0

    if movie.type == "TV_SERIES" and profile["series_style"] not in ["", "any"]:
        if not violates_series_style(movie, profile):
            total += 18

    genres = get_genre_names(movie)
    is_animation = has_any_genre(genres, ["мультфильм", "аниме"])

    if profile["animation_policy"] == "yes" and is_animation:
        total += 10

    if profile["animation_policy"] == "not_childish" and is_animation:
        total -= 20

    return total


def quality_penalty(movie, profile):
    penalty = 0
    text = get_movie_text(movie)
    countries = get_country_names(movie)
    genres = get_genre_names(movie)

    if movie.rating_kp is not None and movie.rating_kp < 6.2:
        penalty -= 25

    if movie.type == "TV_SERIES" and "россия" in countries and profile["series_style"] != "russian":
        if has_any_genre(genres, ["комедия", "семейный", "детектив"]):
            penalty -= 45

    if profile["story_need"] == "comfort":
        if any(word in text for word in ["полиция", "следователь", "участковый", "преступление", "убийство", "расследование"]):
            penalty -= 40

        if any(word in text for word in CHILDISH_WORDS):
            penalty -= 45

    return penalty


def diversify_ranked_items(scored_items):
    result = []
    title_roots = set()

    for item in scored_items:
        title_root = normalize_text(item.movie.title or "")[:18]

        if title_root in title_roots:
            continue

        title_roots.add(title_root)
        result.append(item)

    return result


def build_tags(movie, scores, profile):
    tags = []

    if profile["story_need"] == "comfort":
        tags.append("спокойный запрос")
    if profile["story_need"] == "comedy":
        tags.append("смешная история")
    if profile["story_need"] == "drive":
        tags.append("напряжение")
    if profile["story_need"] == "serious":
        tags.append("серьёзная история")
    if profile["story_need"] == "think":
        tags.append("со смыслом")
    if profile["story_need"] == "relationships":
        tags.append("про отношения")

    if scores.get("humor", 0) >= 3.5:
        tags.append("юмор")
    if scores.get("warmth", 0) >= 3.5:
        tags.append("тепло")
    if scores.get("tension", 0) >= 3.7:
        tags.append("держит внимание")
    if scores.get("romance", 0) >= 3.5:
        tags.append("отношения")
    if scores.get("complexity", 0) >= 3.5:
        tags.append("сложнее среднего")
    if movie.rating_kp and movie.rating_kp >= 7.5:
        tags.append("высокий рейтинг")

    return list(dict.fromkeys(tags))


def is_bad_content(movie, profile):
    genres = get_genre_names(movie)
    text = get_movie_text(movie)
    title = normalize_text(movie.title or "")

    if has_any_genre(genres, BAD_GENRES):
        return True

    if any(bad in text for bad in BAD_TEXT):
        return True

    if any(bad_title in title for bad_title in LOW_QUALITY_TV_TITLES):
        return True

    if profile["story_need"] == "comfort":
        if movie.type == "TV_SERIES" and "россия" in get_country_names(movie) and profile["series_style"] != "russian":
            if has_any_genre(genres, ["комедия", "семейный", "детектив"]):
                return True

    return False


def get_movie_text(movie):
    return normalize_text(
        " ".join([
            movie.title or "",
            movie.original_title or "",
            movie.description or "",
            movie.short_description or "",
            " ".join(get_genre_names(movie)),
            " ".join(get_country_names(movie)),
        ])
    )


def normalize_text(value):
    value = (value or "").lower().replace("ё", "е")
    value = re.sub(r"[^а-яa-z0-9\s-]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def count_keyword_hits(text, keywords):
    return sum(1 for keyword in keywords if normalize_text(keyword) in text)


def get_genre_names(movie):
    return [normalize_text(genre.name) for genre in movie.genres if genre.name]


def get_country_names(movie):
    return [normalize_text(country.name) for country in movie.countries if country.name]


def has_genre(movie, target_genres):
    return has_any_genre(get_genre_names(movie), target_genres)


def has_any_genre(genre_names, target_genres):
    target_genres = [normalize_text(genre) for genre in target_genres]
    return any(target in genre_name for target in target_genres for genre_name in genre_names)


def get_main_genre(movie):
    genres = get_genre_names(movie)
    return genres[0] if genres else "unknown"


def get_main_country(movie):
    countries = get_country_names(movie)
    return countries[0] if countries else "unknown"


def clamp(value, min_value=0.0, max_value=5.0):
    return max(min_value, min(max_value, float(value)))
