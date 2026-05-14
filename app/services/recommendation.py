import json
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
    "mood_direction",
    "audience_mode",
    "energy",
    "mental_load",
    "pace",
    "reality_mode",
    "warmth_need",
    "humor_need",
    "tension_need",
    "romance_need",
    "heavy_topics",
    "ending",
    "preferred_type",
    "rating_policy",
]


ANSWER_LABELS = {
    "main_state": {
        "sad": "грустно",
        "anxious": "тревожно",
        "tired": "усталость",
        "angry": "раздражение",
        "calm": "спокойно",
        "happy": "хорошее настроение",
        "bored": "скучно",
        "unknown": "непонятное состояние",
    },
    "mood_direction": {
        "live_it": "прожить эмоцию",
        "comfort": "стало спокойнее",
        "laugh": "посмеяться",
        "adrenaline": "встряхнуться",
        "inspire": "воодушевиться",
        "wonder": "уйти в другой мир",
        "think": "остаться с мыслью",
    },
    "audience_mode": {
        "adult": "взрослое",
        "not_childish": "лёгкое, но не детское",
        "family_ok": "семейное тоже можно",
        "animation_ok": "анимация подходит",
        "any": "без ограничений по возрастному тону",
    },
    "energy": {
        "low": "мало сил",
        "medium": "нормальный запас сил",
        "high": "много сил",
    },
    "pace": {
        "slow": "спокойный темп",
        "medium": "ровный темп",
        "fast": "быстрый темп",
    },
}


def extract_answers(form):
    answers = {}

    for field in QUESTION_FIELDS:
        answers[field] = (form.get(field) or "").strip()

    return answers


def create_mood_profile(answers):
    mood_profile = MoodProfile(
        main_state=answers.get("main_state"),
        mood_direction=answers.get("mood_direction"),
        energy=answers.get("energy"),
        mental_load=answers.get("mental_load"),
        pace=answers.get("pace"),
        reality_mode=answers.get("reality_mode"),
        warmth_need=answers.get("warmth_need"),
        humor_need=answers.get("humor_need"),
        tension_need=answers.get("tension_need"),
        romance_need=answers.get("romance_need"),
        heavy_topics=answers.get("heavy_topics"),
        ending=answers.get("ending"),
        preferred_type=answers.get("preferred_type"),
        rating_policy=answers.get("rating_policy"),
        raw_answers=json.dumps(answers, ensure_ascii=False),
    )

    mood_profile.summary = build_profile_summary(answers)

    return mood_profile


def build_profile_summary(answers):
    parts = []

    for field in ["main_state", "mood_direction", "audience_mode", "energy", "pace"]:
        label = get_answer_label(field, answers.get(field))

        if label:
            parts.append(label)

    if not parts:
        return "Система подбирает фильмы и сериалы по текущему запросу."

    return "Текущий запрос: " + "; ".join(parts) + "."


def get_answer_label(field, value):
    return ANSWER_LABELS.get(field, {}).get(value)


def build_user_vector(answers):
    target = {dimension: 2.5 for dimension in DIMENSIONS}
    weights = {dimension: 1.0 for dimension in DIMENSIONS}
    max_values = {}

    def add(dimension, value, weight=0.4):
        target[dimension] = clamp(target[dimension] + value)
        weights[dimension] = clamp(weights[dimension] + weight, 0.2, 4.2)

    main_state = answers.get("main_state")
    mood_direction = answers.get("mood_direction")

    if main_state == "sad":
        add("sadness", 1.2, 0.7)
        add("catharsis", 1.0, 0.7)
        add("warmth", 0.5, 0.5)

    if main_state == "anxious":
        add("warmth", 1.0, 0.8)
        add("tension", -0.9, 0.8)
        add("darkness", -0.9, 0.8)

    if main_state == "tired":
        add("lightness", 1.0, 0.8)
        add("complexity", -1.3, 0.9)
        add("pace", -0.7, 0.6)
        max_values["complexity"] = 3.0

    if main_state == "angry":
        add("adrenaline", 1.4, 0.8)
        add("pace", 1.0, 0.7)
        add("sadness", -0.7, 0.5)

    if main_state == "calm":
        add("warmth", 0.6, 0.5)
        add("wonder", 0.5, 0.4)
        add("tension", -0.4, 0.4)

    if main_state == "happy":
        add("lightness", 1.0, 0.6)
        add("humor", 0.9, 0.7)
        add("pace", 0.4, 0.4)

    if main_state == "bored":
        add("wonder", 1.2, 0.7)
        add("tension", 0.6, 0.5)
        add("complexity", 0.5, 0.5)

    if mood_direction == "live_it":
        add("sadness", 1.2, 0.8)
        add("catharsis", 1.8, 1.0)
        add("warmth", 0.3, 0.4)

    if mood_direction == "comfort":
        add("warmth", 1.8, 1.0)
        add("lightness", 1.0, 0.8)
        add("darkness", -1.2, 1.0)
        add("tension", -1.0, 0.8)
        max_values["darkness"] = 2.7
        max_values["tension"] = 3.0

    if mood_direction == "laugh":
        add("humor", 2.4, 1.4)
        add("lightness", 0.9, 0.8)
        add("sadness", -1.0, 0.7)
        add("darkness", -1.0, 0.7)
        max_values["darkness"] = min(max_values.get("darkness", 5), 3.0)

    if mood_direction == "adrenaline":
        add("adrenaline", 1.9, 1.0)
        add("tension", 1.4, 0.9)
        add("pace", 1.2, 0.7)

    if mood_direction == "inspire":
        add("inspiration", 2.0, 1.0)
        add("catharsis", 0.8, 0.5)
        add("warmth", 0.7, 0.4)

    if mood_direction == "wonder":
        add("wonder", 2.1, 1.0)
        add("inspiration", 0.8, 0.5)
        add("lightness", 0.4, 0.4)

    if mood_direction == "think":
        add("complexity", 1.4, 0.8)
        add("catharsis", 0.7, 0.5)
        add("sadness", 0.4, 0.4)

    energy = answers.get("energy")

    if energy == "low":
        add("lightness", 0.8, 0.6)
        add("complexity", -1.2, 0.8)
        add("pace", -0.7, 0.5)
        max_values["complexity"] = min(max_values.get("complexity", 5), 3.0)

    if energy == "high":
        add("pace", 1.0, 0.6)
        add("adrenaline", 0.8, 0.5)

    mental_load = answers.get("mental_load")

    if mental_load == "simple":
        add("complexity", -1.5, 1.0)
        max_values["complexity"] = min(max_values.get("complexity", 5), 2.6)

    if mental_load == "complex":
        add("complexity", 1.4, 0.9)

    desired_pace = answers.get("pace")

    if desired_pace == "slow":
        add("pace", -1.2, 0.8)

    if desired_pace == "fast":
        add("pace", 1.5, 0.8)
        add("adrenaline", 0.5, 0.4)

    reality_mode = answers.get("reality_mode")

    if reality_mode == "real":
        add("wonder", -0.8, 0.6)
        add("romance", 0.3, 0.3)
        add("catharsis", 0.4, 0.3)

    if reality_mode == "escape":
        add("wonder", 1.7, 0.9)
        add("lightness", 0.4, 0.4)

    warmth_need = answers.get("warmth_need")

    if warmth_need == "high":
        add("warmth", 1.7, 1.0)
        add("darkness", -0.8, 0.7)

    if warmth_need == "low":
        add("warmth", -0.8, 0.5)

    humor_need = answers.get("humor_need")

    if humor_need == "high":
        add("humor", 2.0, 1.2)
        add("lightness", 0.7, 0.6)

    if humor_need == "low":
        add("humor", -1.0, 0.6)

    tension_need = answers.get("tension_need")

    if tension_need == "none":
        add("tension", -1.6, 1.0)
        add("darkness", -0.8, 0.7)
        max_values["tension"] = 2.5

    if tension_need == "medium":
        add("tension", 0.5, 0.5)

    if tension_need == "high":
        add("tension", 1.8, 1.0)
        add("adrenaline", 0.8, 0.6)

    romance_need = answers.get("romance_need")

    if romance_need == "yes":
        add("romance", 1.8, 1.0)
        add("warmth", 0.5, 0.4)

    if romance_need == "no":
        add("romance", -1.5, 0.8)

    heavy_topics = answers.get("heavy_topics")

    if heavy_topics == "avoid":
        add("darkness", -1.8, 1.0)
        add("sadness", -0.8, 0.7)
        add("tension", -0.8, 0.7)
        max_values["darkness"] = 2.4
        max_values["sadness"] = 3.2

    if heavy_topics == "ok":
        add("darkness", 0.6, 0.4)
        add("catharsis", 0.6, 0.4)

    ending = answers.get("ending")

    if ending == "happy":
        add("warmth", 1.0, 0.7)
        add("inspiration", 0.8, 0.5)
        add("darkness", -1.0, 0.8)
        max_values["darkness"] = min(max_values.get("darkness", 5), 3.0)

    if ending == "bittersweet":
        add("sadness", 0.8, 0.5)
        add("catharsis", 1.0, 0.6)

    return {
        "target": {key: round(clamp(value), 2) for key, value in target.items()},
        "weights": weights,
        "max_values": max_values,
        "preferred_type": answers.get("preferred_type") or "any",
        "rating_policy": answers.get("rating_policy") or "balanced",
        "audience_mode": answers.get("audience_mode") or "adult",
        "mood_direction": mood_direction,
        "humor_need": answers.get("humor_need") or "medium",
    }


def get_recommendations(mood_profile):
    answers = json.loads(mood_profile.raw_answers or "{}")
    user_vector = build_user_vector(answers)

    candidates = get_candidate_movies(user_vector)
    scored_items = []

    for movie in candidates:
        item = score_movie(movie, movie.emotion_profile, user_vector)

        if item.score > 0:
            scored_items.append(item)

    scored_items.sort(key=lambda item: item.score, reverse=True)

    groups = build_groups(scored_items, user_vector)

    return RecommendationResult(
        mood_profile=mood_profile,
        profile_summary=mood_profile.summary,
        groups=groups,
    )


def get_candidate_movies(user_vector):
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

    preferred_type = user_vector["preferred_type"]

    if preferred_type in ["FILM", "TV_SERIES"]:
        query = query.filter(Movie.type == preferred_type)

    movies = query.all()

    result = []

    for movie in movies:
        audience = get_audience_flags(movie, movie.emotion_profile.to_dict())

        if must_exclude_by_audience(audience, user_vector["audience_mode"]):
            continue

        if violates_hard_limits(movie, movie.emotion_profile.to_dict(), user_vector):
            continue

        result.append(movie)

    return result


def violates_hard_limits(movie, scores, user_vector):
    for dimension, max_value in user_vector["max_values"].items():
        if scores.get(dimension, 0) > max_value + 0.7:
            return True

    if user_vector["mood_direction"] == "laugh":
        if scores.get("humor", 0) < 2.4 and not has_genre(movie, ["комедия"]):
            return True

    if user_vector["rating_policy"] == "safe":
        if movie.rating_kp is None or movie.rating_kp < 6.8:
            return True

    return False


def score_movie(movie, emotion_profile, user_vector):
    scores = emotion_profile.to_dict()
    audience = get_audience_flags(movie, scores)

    total = 0.0
    tags = []

    for dimension in DIMENSIONS:
        movie_value = scores.get(dimension, 0)
        target_value = user_vector["target"].get(dimension, 2.5)
        weight = user_vector["weights"].get(dimension, 1.0)

        closeness = 5 - abs(movie_value - target_value)
        total += max(0, closeness) * weight

    total += score_genre_fit(movie, scores, user_vector)
    total += audience_bonus_or_penalty(audience, user_vector["audience_mode"], scores)
    total += score_rating(movie, user_vector["rating_policy"])

    if user_vector["mood_direction"] == "laugh":
        total += score_laugh_request(movie, scores, audience, user_vector)

    if scores.get("darkness", 0) <= 2.2 and scores.get("warmth", 0) >= 3.0:
        tags.append("мягкое")

    if scores.get("humor", 0) >= 3.5:
        tags.append("есть юмор")

    if scores.get("tension", 0) >= 3.8:
        tags.append("держит в напряжении")

    if scores.get("romance", 0) >= 3.5:
        tags.append("есть романтическая линия")

    if scores.get("wonder", 0) >= 3.5:
        tags.append("уносит из реальности")

    if scores.get("catharsis", 0) >= 3.5:
        tags.append("эмоциональное проживание")

    if scores.get("inspiration", 0) >= 3.5:
        tags.append("может вдохновить")

    reason = build_reason(movie, scores, user_vector, tags, audience)

    return RecommendedItem(
        movie=movie,
        score=round(total, 2),
        reason=reason,
        tags=tags[:4],
    )


def score_genre_fit(movie, scores, user_vector):
    mood_direction = user_vector["mood_direction"]
    total = 0

    if mood_direction == "laugh":
        if has_genre(movie, ["комедия"]):
            total += 18

        if has_genre(movie, ["мультфильм", "детский", "семейный"]):
            total -= 25

    if mood_direction == "adrenaline":
        if has_genre(movie, ["боевик", "триллер", "криминал", "детектив"]):
            total += 12

    if mood_direction == "wonder":
        if has_genre(movie, ["фантастика", "фэнтези", "приключения"]):
            total += 12

    if mood_direction == "live_it":
        if has_genre(movie, ["драма", "мелодрама"]):
            total += 10

    if mood_direction == "comfort":
        if has_genre(movie, ["семейный", "мелодрама", "комедия"]):
            total += 5

    return total


def score_rating(movie, rating_policy):
    if movie.rating_kp is None:
        return -4

    if rating_policy == "safe":
        return min(movie.rating_kp, 10) * 2.4

    if rating_policy == "balanced":
        return min(movie.rating_kp, 10) * 1.8

    return min(movie.rating_kp, 10) * 1.1


def score_laugh_request(movie, scores, audience, user_vector):
    total = 0

    if scores.get("humor", 0) >= 4.0:
        total += 16
    elif scores.get("humor", 0) >= 3.0:
        total += 9
    else:
        total -= 14

    if has_genre(movie, ["комедия"]):
        total += 12

    if user_vector["audience_mode"] in ["adult", "not_childish"]:
        if audience["animation"] or audience["family"] or audience["childlike"]:
            total -= 50

    if scores.get("darkness", 0) > 3.3:
        total -= 8

    if scores.get("sadness", 0) > 3.5:
        total -= 6

    return total


def must_exclude_by_audience(audience, audience_mode):
    if audience_mode in ["adult", "not_childish"]:
        if audience["cartoon"] or audience["children"] or audience["family"]:
            return True

    if audience_mode == "adult" and audience["animation"]:
        return True

    return False


def audience_bonus_or_penalty(audience, audience_mode, scores):
    total = 0.0

    if audience_mode == "adult":
        if audience["adult_genre"]:
            total += 7

        if audience["animation"] or audience["family"] or audience["children"]:
            total -= 80

    if audience_mode == "not_childish":
        if audience["adult_genre"]:
            total += 3

        if audience["animation"] or audience["family"] or audience["children"]:
            total -= 70

    if audience_mode == "family_ok":
        if audience["family"] or audience["children"]:
            total += 12

        if scores.get("darkness", 0) > 3.5:
            total -= 10

    if audience_mode == "animation_ok":
        if audience["animation"]:
            total += 10

    if audience_mode == "any":
        if audience["children"]:
            total -= 3

    return total


def get_audience_flags(movie, scores):
    genre_names = get_genre_names(movie)

    text = " ".join(
        [
            movie.title or "",
            movie.original_title or "",
            movie.description or "",
            movie.short_description or "",
            " ".join(genre_names),
        ]
    ).lower()

    cartoon = any("мультфильм" in genre for genre in genre_names)
    children = any("детский" in genre for genre in genre_names)
    family = any("семейный" in genre for genre in genre_names)
    anime = any("аниме" in genre for genre in genre_names)

    adult_genres = [
        "триллер",
        "криминал",
        "детектив",
        "драма",
        "ужасы",
        "военный",
        "боевик",
        "биография",
    ]

    adult_keywords = [
        "убий",
        "преступ",
        "расслед",
        "насили",
        "война",
        "смерть",
        "кров",
        "месть",
        "маньяк",
        "кризис",
        "измена",
        "развод",
    ]

    adult_genre = any(
        adult_genre in genre
        for genre in genre_names
        for adult_genre in adult_genres
    )

    adult_keyword = any(keyword in text for keyword in adult_keywords)

    animation = cartoon or anime

    childlike = (
        (cartoon or children or family)
        and not anime
        and not adult_genre
        and not adult_keyword
        and scores.get("darkness", 0) < 3.0
        and scores.get("tension", 0) < 3.2
    )

    return {
        "animation": animation,
        "cartoon": cartoon,
        "anime": anime,
        "children": children,
        "family": family,
        "adult_genre": adult_genre,
        "adult_keyword": adult_keyword,
        "childlike": childlike,
    }


def build_reason(movie, scores, user_vector, tags, audience):
    reason_parts = []

    audience_mode = user_vector["audience_mode"]

    if audience_mode == "adult":
        reason_parts.append("взрослый зрительский тон")

    if audience_mode == "not_childish":
        reason_parts.append("лёгкость без детского ощущения")

    if audience_mode == "family_ok" and (audience["family"] or audience["children"]):
        reason_parts.append("подходит для семейного режима")

    if audience_mode == "animation_ok" and audience["animation"]:
        reason_parts.append("анимация допустима по запросу")

    important_dimensions = sorted(
        DIMENSIONS,
        key=lambda dimension: user_vector["weights"].get(dimension, 1.0),
        reverse=True,
    )

    for dimension in important_dimensions:
        if len(reason_parts) >= 4:
            break

        movie_value = scores.get(dimension, 0)
        target_value = user_vector["target"].get(dimension, 2.5)

        if abs(movie_value - target_value) <= 1.1:
            label = dimension_label(dimension)

            if label:
                reason_parts.append(label)

    reason_parts.extend(tags[:2])

    if movie.rating_kp and movie.rating_kp >= 7.5:
        reason_parts.append("хороший рейтинг")

    unique_parts = []

    for part in reason_parts:
        if part not in unique_parts:
            unique_parts.append(part)

    if not unique_parts:
        return "Почему подходит: совпадает по настроению, темпу и содержанию."

    return "Почему подходит: " + ", ".join(unique_parts[:4]) + "."


def dimension_label(dimension):
    labels = {
        "lightness": "лёгкость",
        "humor": "юмор",
        "warmth": "тепло",
        "romance": "романтичность",
        "sadness": "грустная окраска",
        "catharsis": "эмоциональное проживание",
        "tension": "напряжение",
        "adrenaline": "динамика",
        "wonder": "ощущение другого мира",
        "inspiration": "воодушевление",
        "nostalgia": "ностальгичность",
        "darkness": "мрачная атмосфера",
        "complexity": "подходящая сложность",
        "pace": "подходящий темп",
    }

    return labels.get(dimension)


def build_groups(scored_items, user_vector):
    used_ids = set()

    best = take_diverse(scored_items, used_ids, 12)

    soft_candidates = sorted(
        scored_items,
        key=lambda item: (
            item.movie.emotion_profile.warmth
            + item.movie.emotion_profile.lightness
            - item.movie.emotion_profile.darkness
            - item.movie.emotion_profile.tension
            + item.score * 0.05
        ),
        reverse=True,
    )

    soft = take_diverse(soft_candidates, used_ids, 8)

    deep_candidates = sorted(
        scored_items,
        key=lambda item: (
            item.movie.emotion_profile.catharsis
            + item.movie.emotion_profile.sadness
            + item.movie.emotion_profile.inspiration
            + item.score * 0.05
        ),
        reverse=True,
    )

    deep = take_diverse(deep_candidates, used_ids, 8)

    surprise_candidates = sorted(
        scored_items,
        key=lambda item: (
            item.movie.emotion_profile.wonder
            + item.movie.emotion_profile.complexity
            + item.movie.emotion_profile.adrenaline
            + item.score * 0.04
        ),
        reverse=True,
    )

    surprise = take_diverse(surprise_candidates, used_ids, 8)

    return {
        "Лучшее совпадение": best,
        "Мягкий запасной вариант": soft,
        "Если хочется глубже": deep,
        "Неожиданный выбор": surprise,
    }


def take_diverse(items, used_ids, limit):
    result = []
    genre_counter = {}
    type_counter = {}

    for item in items:
        movie = item.movie

        if movie.id in used_ids:
            continue

        main_genre = get_main_genre(movie)
        movie_type = movie.type or "UNKNOWN"

        if genre_counter.get(main_genre, 0) >= 4:
            continue

        if type_counter.get(movie_type, 0) >= max(5, limit - 2):
            continue

        used_ids.add(movie.id)
        result.append(item)

        genre_counter[main_genre] = genre_counter.get(main_genre, 0) + 1
        type_counter[movie_type] = type_counter.get(movie_type, 0) + 1

        if len(result) >= limit:
            break

    if len(result) < limit:
        for item in items:
            if item.movie.id in used_ids:
                continue

            used_ids.add(item.movie.id)
            result.append(item)

            if len(result) >= limit:
                break

    return result


def get_genre_names(movie):
    return [
        genre.name.lower().strip()
        for genre in movie.genres
        if genre.name
    ]


def has_genre(movie, target_genres):
    genre_names = get_genre_names(movie)

    return any(
        target_genre in genre_name
        for target_genre in target_genres
        for genre_name in genre_names
    )


def get_main_genre(movie):
    genre_names = get_genre_names(movie)

    if not genre_names:
        return "unknown"

    return genre_names[0]


def clamp(value, min_value=0.0, max_value=5.0):
    return max(min_value, min(max_value, float(value)))