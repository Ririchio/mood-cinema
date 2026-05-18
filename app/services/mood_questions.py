def get_mood_questions():
    return [
        {
            "name": "main_state",
            "title": "Что ты сейчас чувствуешь?",
            "options": [
                ("sad", "Грусть"),
                ("anxious", "Тревогу"),
                ("tired", "Усталость"),
                ("angry", "Раздражение"),
                ("calm", "Спокойствие"),
                ("happy", "Радость"),
                ("bored", "Скуку"),
                ("unknown", "Не понимаю"),
            ],
        },
        {
            "name": "story_need",
            "title": "Какая история сейчас нужна?",
            "options": [
                ("serious", "Серьёзная"),
                ("comfort", "Спокойная"),
                ("comedy", "Смешная"),
                ("drive", "Напряжённая"),
                ("think", "Со смыслом"),
                ("relationships", "Об отношениях"),
            ],
        },

        {
            "name": "serious_type",
            "title": "Какая серьёзная история ближе?",
            "show_if": {"story_need": "serious"},
            "options": [
                ("personal", "Личная"),
                ("romantic", "О любви"),
                ("family", "Семейная"),
                ("social", "О сложной ситуации"),
            ],
        },
        {
            "name": "serious_weight",
            "title": "Насколько тяжёлой может быть история?",
            "show_if": {"story_need": "serious"},
            "options": [
                ("light", "Лёгкой"),
                ("medium", "Умеренной"),
                ("heavy", "Тяжёлой"),
            ],
        },

        {
            "name": "comfort_type",
            "title": "Какое спокойное кино хочется?",
            "show_if": {"story_need": "comfort"},
            "options": [
                ("cozy", "Уютное"),
                ("simple", "Простое"),
                ("slow", "Размеренное"),
                ("hopeful", "Обнадёживающее"),
            ],
        },
        {
            "name": "comfort_avoid",
            "title": "Чего точно не нужно?",
            "show_if": {"story_need": "comfort"},
            "options": [
                ("violence", "Жестокости"),
                ("death", "Смерти и болезней"),
                ("conflict", "Ссор и скандалов"),
                ("confusion", "Запутанного сюжета"),
            ],
        },

        {
            "name": "comedy_type",
            "title": "Какая комедия ближе?",
            "show_if": {"story_need": "comedy"},
            "options": [
                ("everyday", "Бытовая"),
                ("romantic", "Романтическая"),
                ("adventure", "Приключенческая"),
                ("friends", "Про компанию друзей"),
            ],
        },
        {
            "name": "humor_type",
            "title": "Какой юмор подходит?",
            "show_if": {"story_need": "comedy"},
            "options": [
                ("kind", "Добрый"),
                ("black", "Чёрный"),
                ("absurd", "Нелепый"),
                ("adult", "Взрослый"),
            ],
        },

        {
            "name": "drive_type",
            "title": "Какой вид напряжения подходит?",
            "show_if": {"story_need": "drive"},
            "options": [
                ("investigation", "Расследование"),
                ("survival", "Выживание"),
                ("crime", "Криминальная история"),
                ("battle", "Противостояние"),
            ],
        },
        {
            "name": "drive_hardness",
            "title": "Насколько жёсткой может быть история?",
            "show_if": {"story_need": "drive"},
            "options": [
                ("low", "Почти без жести"),
                ("medium", "Средне"),
                ("high", "Жёстко"),
            ],
        },

        {
            "name": "thinking_type",
            "title": "О чём хочется думать?",
            "show_if": {"story_need": "think"},
            "options": [
                ("justice", "О справедливости"),
                ("mystery", "О тайне"),
                ("future", "О будущем"),
                ("memory", "О прошлом"),
                ("life", "О смысле жизни"),
            ],
        },
        {
            "name": "thinking_complexity",
            "title": "Насколько сложной может быть история?",
            "show_if": {"story_need": "think"},
            "options": [
                ("clear", "Понятной"),
                ("layered", "Многослойной"),
                ("complex", "Сложной"),
            ],
        },

        {
            "name": "relationship_type",
            "title": "Какие отношения интереснее?",
            "show_if": {"story_need": "relationships"},
            "options": [
                ("light_romance", "Лёгкая романтика"),
                ("dramatic_love", "Сложная любовь"),
                ("slow_burn", "Постепенное сближение"),
                ("family", "Семья"),
                ("friendship", "Дружба"),
            ],
        },
        {
            "name": "relationship_conflict",
            "title": "Сколько конфликта допустимо?",
            "show_if": {"story_need": "relationships"},
            "options": [
                ("low", "Мало"),
                ("medium", "Умеренно"),
                ("high", "Много"),
            ],
        },

        {
            "name": "format_preference",
            "title": "Что выбрать?",
            "options": [
                ("FILM", "Фильм"),
                ("TV_SERIES", "Сериал"),
                ("any", "Не важно"),
            ],
        },
        {
            "name": "series_style",
            "title": "Какой сериал ближе?",
            "show_if": {"format_preference": "TV_SERIES"},
            "options": [
                ("dorama", "Дорама"),
                ("turkish", "Турецкий"),
                ("western", "Западный"),
                ("russian", "Российский"),
                ("anime", "Аниме"),
                ("any", "Не важно / другое"),
            ],
        },
        {
            "name": "animation_policy",
            "title": "Мультфильмы и анимация подходят?",
            "show_if": {"format_preference": "FILM"},
            "options": [
                ("no", "Нет"),
                ("not_childish", "Да, но без детской подачи"),
                ("yes", "Да"),
                ("any", "Не важно"),
            ],
        },
        {
            "name": "age_category",
            "title": "Какая возрастная категория подходит?",
            "show_if": {"format_preference": "any"},
            "options": [
                ("adult", "18+"),
                ("teen", "16+"),
                ("family", "12+"),
                ("kids", "6+"),
                ("any", "Не важно"),
            ],
        },
        {
            "name": "pace",
            "title": "Как быстро должна развиваться история?",
            "options": [
                ("slow", "Медленно"),
                ("medium", "Ровно"),
                ("fast", "Быстро"),
                ("any", "Не важно"),
            ],
        },
        {
            "name": "rating_policy",
            "title": "Насколько важен рейтинг?",
            "options": [
                ("safe", "Важен"),
                ("balanced", "Немного важен"),
                ("brave", "Не важен"),
            ],
        },
    ]