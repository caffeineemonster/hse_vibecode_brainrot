# api/utils/brainrot_test_logic.py
import json
from collections import Counter
from characters.models import BrainRotCharacter

BRAINROT_CHARACTER_MAP = {
    'A': {
        'name': 'Тралалело Тралала',
        'slug': 'tralalelo-tralala',
        'description': 'Абсолютный абсурд, digital-дитя, замена мыслей на «тра-ла-ла». Цифровой карнавал в плоти.',
        'category': 'meme',
        'iconic_phrase': 'Тра-ла-ла, всё есть loop!'
    },
    'B': {
        'name': 'Бомбардиро Крокодило',
        'slug': 'bombardiro-krokodilo',
        'description': 'Стратег, тактик, холодная ярость, контроль, милитари-эстетика. План — это всё.',
        'category': 'game',
        'iconic_phrase': 'Побеждает не сильнейший, а умнейший.'
    },
    'C': {
        'name': 'Тунг Тунг Тунг Сахур',
        'slug': 'tung-tung-tung-sahur',
        'description': 'Абсолютная простота, пустота, прямое действие, непоколебимая сила. Нет мыслей — есть удар.',
        'category': 'meme',
        'iconic_phrase': 'Тунг. Тунг. Тунг.'
    },
    'D': {
        'name': 'Балерина Капучино',
        'slug': 'balerina-kapuchino',
        'description': 'Драма, трагедия, театральность, одержимость, эстетика декаданса. Вся жизнь — спектакль.',
        'category': 'movie',
        'iconic_phrase': 'Разбивая фарфор, я танцую.'
    },
    'E': {
        'name': 'Лирили Ларила',
        'slug': 'lirili-larila',
        'description': 'Мудрый хранитель, спокойствие, устойчивость, связь с природой. Древнее спокойствие.',
        'category': 'music',
        'iconic_phrase': 'Ветер стирает горы, но не корни.'
    },
    'F': {
        'name': 'Шпиониро Голубино',
        'slug': 'shpioniro-golubino',
        'description': 'Незаметный наблюдатель, информатор, циничный профессионал, нуар. Ничего личного.',
        'category': 'internet',
        'iconic_phrase': 'Ничего личного, просто наблюдение.'
    }
}

# Персонажи для ничьих
TIE_CHARACTERS = {
    'AD': {
        'name': 'Шимпанзини Бананини',
        'slug': 'shimpanzini-bananini',
        'description': 'Абсурд + драма в форме кринжа. Хаос с трагикомическим подтекстом.',
        'category': 'meme',
        'iconic_phrase': 'Обезьяний крик сквозь слёзы!'
    },
    'BF': {
        'name': 'Капучино Ассасино',
        'slug': 'kapuchino-assasino',
        'description': 'Хладнокровие + профессионализм + скрытность. Идеальный убийца с эспрессо.',
        'category': 'game',
        'iconic_phrase': 'Молчание и кофеин.'
    },
    'EC': {
        'name': 'Брр Брр Патапим',
        'slug': 'brr-brr-patapim',
        'description': 'Спокойствие + древность + непоколебимость. Гора, которая иногда двигается.',
        'category': 'other',
        'iconic_phrase': 'Брр... патапим.'
    },
    'BA': {
        'name': 'Бомбомбини Гусини',
        'slug': 'bombombini-gusini',
        'description': 'Стратегия + абсурд + хаос. Военная тактика через призму сюрреализма.',
        'category': 'meme',
        'iconic_phrase': 'Гусь с планом!'
    },
    'default': {
        'name': 'Трулимеро Труличина',
        'slug': 'trulimero-trulichina',
        'description': 'Вечный внутренний конфликт и неопределённость. Не могу решить, кто я.',
        'category': 'other',
        'iconic_phrase': 'Может да, может нет...'
    }
}


def calculate_brainrot_result(answers):
    """
    Подсчитывает результат теста BrainRot
    answers: список словарей с question_id и answer_id
    Возвращает: {'character': объект персонажа, 'scores': Counter, 'description': str}
    """
    from api.models import AnswerOption

    # Собираем все буквы из ответов
    letters = []
    for answer in answers:
        try:
            answer_option = AnswerOption.objects.get(
                id=answer.get('answer_id'),
                question_id=answer.get('question_id')
            )
            if answer_option.letter:
                letters.append(answer_option.letter)
        except AnswerOption.DoesNotExist:
            continue

    if not letters:
        return None

    # Подсчитываем буквы
    counter = Counter(letters)
    total_answers = len(letters)

    # Находим максимальное количество
    max_count = max(counter.values())
    top_letters = [letter for letter, count in counter.items() if count == max_count]

    # Определяем персонажа
    if len(top_letters) == 1:
        # Один явный лидер
        letter = top_letters[0]
        char_data = BRAINROT_CHARACTER_MAP[letter]
        tie_type = None
    else:
        # Ничья между несколькими буквами
        tie_key = ''.join(sorted(top_letters))

        # Ищем специального персонажа для этой комбинации
        char_data = TIE_CHARACTERS.get(tie_key)
        if not char_data:
            # Проверяем обратную комбинацию
            reverse_key = ''.join(sorted(top_letters, reverse=True))
            char_data = TIE_CHARACTERS.get(reverse_key)

        # Если нет специального персонажа, берём дефолтного
        if not char_data:
            char_data = TIE_CHARACTERS['default']

        tie_type = tie_key

    # Создаём или получаем персонажа
    character, created = BrainRotCharacter.objects.get_or_create(
        slug=char_data['slug'],
        defaults={
            'name': char_data['name'],
            'description': char_data['description'],
            'category': char_data['category'],
            'iconic_phrase': char_data.get('iconic_phrase', ''),
            'popularity_score': 100,
            'is_active': True
        }
    )

    # Рассчитываем процент совпадения
    match_percentage = (max_count / total_answers) * 100

    # Генерируем описание результата
    result_description = generate_result_description(
        character,
        counter,
        match_percentage,
        tie_type
    )

    return {
        'character': character,
        'scores': dict(counter),
        'match_percentage': round(match_percentage, 1),
        'description': result_description,
        'is_tie': len(top_letters) > 1,
        'top_letters': top_letters
    }


def generate_result_description(character, scores, match_percentage, tie_type=None):
    """Генерирует текстовое описание результата"""

    # Сортируем буквы по количеству
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    lines = [
        f"🎭 Твой BrainRot персонаж: **{character.name}**",
        f"📊 Совпадение: **{match_percentage}%**",
        "",
        f"**Описание:** {character.description}",
        "",
        "**Твои результаты по типам:**"
    ]

    # Добавляем статистику по буквам
    for letter, count in sorted_scores:
        letter_name = {
            'A': 'Абсурд (Тралалело)',
            'B': 'Стратегия (Крокодило)',
            'C': 'Простота (Тунг-Тунг)',
            'D': 'Драма (Балерина)',
            'E': 'Спокойствие (Лирили)',
            'F': 'Наблюдение (Шпиониро)'
        }.get(letter, letter)

        percentage = (count / sum(scores.values())) * 100
        lines.append(f"• {letter_name}: {count} ответов ({percentage:.1f}%)")

    if tie_type:
        lines.append("")
        lines.append(f"⚖️ **Ничья между типами:** {tie_type}")
        lines.append("Ты сочетаешь в себе несколько сильных сторон!")

    lines.append("")
    lines.append(f"💬 **Культовая фраза:** «{character.iconic_phrase}»")
    lines.append(f"🏷️ **Категория:** {character.get_category_display()}")

    return "\n".join(lines)


def get_brainrot_test_questions():
    """Получает вопросы для теста BrainRot"""
    from api.models import Question
    return Question.objects.filter(
        test_type='simple',
        is_active=True
    ).order_by('order')