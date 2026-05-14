DIMENSIONS = [
    "lightness",
    "humor",
    "warmth",
    "romance",
    "sadness",
    "catharsis",
    "tension",
    "adrenaline",
    "wonder",
    "inspiration",
    "nostalgia",
    "darkness",
    "complexity",
    "pace",
]


GENRE_RULES = {
    "комедия": {
        "lightness": 3.2,
        "humor": 4.7,
        "warmth": 0.8,
        "pace": 1.5,
    },
    "мелодрама": {
        "romance": 4.1,
        "warmth": 2.0,
        "sadness": 2.1,
        "catharsis": 2.4,
    },
    "драма": {
        "sadness": 3.0,
        "catharsis": 3.0,
        "complexity": 2.0,
        "darkness": 1.3,
    },
    "триллер": {
        "tension": 4.6,
        "darkness": 2.7,
        "complexity": 2.1,
        "pace": 2.5,
    },
    "детектив": {
        "tension": 3.1,
        "complexity": 3.1,
        "pace": 1.9,
    },
    "боевик": {
        "adrenaline": 4.6,
        "pace": 4.0,
        "tension": 2.4,
    },
    "приключения": {
        "wonder": 3.0,
        "adrenaline": 2.3,
        "inspiration": 1.4,
        "pace": 3.0,
    },
    "фэнтези": {
        "wonder": 4.0,
        "inspiration": 2.0,
        "lightness": 0.9,
    },
    "фантастика": {
        "wonder": 3.6,
        "complexity": 2.1,
        "inspiration": 1.5,
    },
    "мультфильм": {
        "lightness": 2.0,
        "warmth": 2.2,
        "wonder": 2.5,
        "humor": 0.4,
        "complexity": -0.4,
    },
    "детский": {
        "lightness": 3.0,
        "warmth": 2.8,
        "wonder": 1.8,
        "humor": 0.3,
        "complexity": -1.0,
        "darkness": -0.8,
    },
    "семейный": {
        "warmth": 3.4,
        "lightness": 2.2,
        "inspiration": 1.1,
        "humor": 0.4,
        "darkness": -0.7,
    },
    "ужасы": {
        "tension": 4.7,
        "darkness": 4.6,
        "adrenaline": 2.0,
    },
    "криминал": {
        "tension": 3.1,
        "darkness": 3.0,
        "complexity": 2.0,
    },
    "военный": {
        "sadness": 3.1,
        "darkness": 3.6,
        "tension": 2.6,
        "catharsis": 2.0,
    },
    "биография": {
        "inspiration": 2.6,
        "complexity": 2.0,
        "catharsis": 1.5,
    },
    "документальный": {
        "complexity": 2.6,
        "inspiration": 1.4,
    },
    "аниме": {
        "wonder": 2.4,
        "romance": 1.0,
        "adrenaline": 1.5,
        "catharsis": 1.5,
        "complexity": 0.8,
    },
    "мюзикл": {
        "lightness": 2.0,
        "humor": 1.0,
        "romance": 1.2,
        "inspiration": 1.5,
    },
    "спорт": {
        "adrenaline": 2.0,
        "inspiration": 3.0,
        "pace": 2.0,
    },
}


KEYWORD_RULES = [
    (
        ["любовь", "влюб", "отношен", "роман", "чувств", "свадьб"],
        {"romance": 2.0, "warmth": 0.8},
    ),
    (
        ["семья", "дружба", "друз", "добро", "дом", "детство", "родител"],
        {"warmth": 2.2, "nostalgia": 1.2},
    ),
    (
        ["смерть", "потер", "трагед", "горе", "болезн", "одиноч"],
        {"sadness": 2.5, "darkness": 1.5, "catharsis": 1.0},
    ),
    (
        ["тайна", "расслед", "загад", "преступ", "убий", "исчез"],
        {"tension": 2.0, "complexity": 1.5, "darkness": 1.0},
    ),
    (
        ["магия", "волшеб", "сказ", "королев", "дракон", "вселен"],
        {"wonder": 2.4, "lightness": 0.5},
    ),
    (
        ["битва", "война", "опасн", "спасти", "погон", "сраж"],
        {"adrenaline": 2.0, "tension": 1.5, "pace": 1.5},
    ),
    (
        ["мечта", "путь", "побед", "надежд", "успех", "талант", "цель"],
        {"inspiration": 2.5, "catharsis": 0.8},
    ),
    (
        ["шут", "смеш", "комич", "забав", "юмор", "сатир", "ирони"],
        {"humor": 2.7, "lightness": 1.2},
    ),
    (
        ["вечерин", "авантюр", "безумн", "неловк", "скандал"],
        {"humor": 1.5, "pace": 1.0, "lightness": 0.8},
    ),
    (
        ["мрач", "демон", "прокля", "кошмар", "жесток", "страх"],
        {"darkness": 2.5, "tension": 1.5},
    ),
]


def empty_scores(default_value=0.8):
    return {dimension: float(default_value) for dimension in DIMENSIONS}


def clamp(value, min_value=0.0, max_value=5.0):
    return max(min_value, min(max_value, float(value)))


def add_scores(scores, rules, multiplier=1.0):
    for dimension, value in rules.items():
        if dimension not in scores:
            continue

        scores[dimension] = clamp(scores[dimension] + value * multiplier)


def build_movie_emotion_scores(movie):
    scores = empty_scores(default_value=0.8)

    genre_names = [
        genre.name.lower().strip()
        for genre in movie.genres
        if genre.name
    ]

    for genre_name in genre_names:
        for rule_genre, rule_scores in GENRE_RULES.items():
            if rule_genre in genre_name or genre_name in rule_genre:
                add_scores(scores, rule_scores)

    text = " ".join(
        [
            movie.title or "",
            movie.original_title or "",
            movie.description or "",
            movie.short_description or "",
            " ".join(genre_names),
        ]
    ).lower()

    for keywords, rule_scores in KEYWORD_RULES:
        if any(keyword in text for keyword in keywords):
            add_scores(scores, rule_scores)

    if movie.rating_kp and movie.rating_kp >= 8:
        add_scores(scores, {"inspiration": 0.4, "catharsis": 0.3})

    if movie.type == "TV_SERIES":
        add_scores(scores, {"complexity": 0.3, "pace": -0.2})

    for dimension in DIMENSIONS:
        scores[dimension] = round(clamp(scores[dimension]), 2)

    return scores


def apply_scores_to_profile(profile, scores):
    for dimension in DIMENSIONS:
        setattr(profile, dimension, scores.get(dimension, 0))