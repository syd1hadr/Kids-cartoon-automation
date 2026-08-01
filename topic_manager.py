import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_PATH = Path('data/topic_history.json')
MAX_HISTORY_ITEMS = 100

TOPIC_POOL = [
    {'topic': 'ABC Phonics', 'category': 'alphabet'},
    {'topic': 'Alphabet Train', 'category': 'alphabet'},
    {'topic': 'Letter Sounds A to Z', 'category': 'alphabet'},
    {'topic': 'Beginning Sounds', 'category': 'alphabet'},
    {'topic': 'Vowels Song', 'category': 'alphabet'},
    {'topic': 'Counting 1 to 10', 'category': 'numbers'},
    {'topic': 'Counting 10 to 20', 'category': 'numbers'},
    {'topic': 'Count the Animals', 'category': 'numbers'},
    {'topic': 'Numbers and Actions', 'category': 'numbers'},
    {'topic': 'Simple Addition', 'category': 'numbers'},
    {'topic': 'Simple Subtraction', 'category': 'numbers'},
    {'topic': 'Rainbow Colors', 'category': 'colors'},
    {'topic': 'Primary Colors', 'category': 'colors'},
    {'topic': 'Mixing Colors', 'category': 'colors'},
    {'topic': 'Find the Color', 'category': 'colors'},
    {'topic': 'Shapes Around Us', 'category': 'shapes'},
    {'topic': 'Circle Square Triangle', 'category': 'shapes'},
    {'topic': 'Big and Small Shapes', 'category': 'shapes'},
    {'topic': '3D Shapes', 'category': 'shapes'},
    {'topic': 'Farm Animals', 'category': 'animals'},
    {'topic': 'Wild Animals', 'category': 'animals'},
    {'topic': 'Ocean Animals', 'category': 'animals'},
    {'topic': 'Jungle Animals', 'category': 'animals'},
    {'topic': 'Baby Animals', 'category': 'animals'},
    {'topic': 'Animal Sounds', 'category': 'animals'},
    {'topic': 'Birds Song', 'category': 'animals'},
    {'topic': 'Insects Song', 'category': 'animals'},
    {'topic': 'Dinosaurs', 'category': 'animals'},
    {'topic': 'Pets Song', 'category': 'animals'},
    {'topic': 'Fruits Song', 'category': 'food'},
    {'topic': 'Vegetables Song', 'category': 'food'},
    {'topic': 'Healthy Food', 'category': 'food'},
    {'topic': 'Breakfast Foods', 'category': 'food'},
    {'topic': 'Lunch Time', 'category': 'food'},
    {'topic': 'Snack Time', 'category': 'food'},
    {'topic': 'Sweet and Sour', 'category': 'food'},
    {'topic': 'Vehicles Song', 'category': 'vehicles'},
    {'topic': 'Construction Vehicles', 'category': 'vehicles'},
    {'topic': 'Fire Truck Song', 'category': 'vehicles'},
    {'topic': 'Police Car Song', 'category': 'vehicles'},
    {'topic': 'Bus Song', 'category': 'vehicles'},
    {'topic': 'Train Song', 'category': 'vehicles'},
    {'topic': 'Airplane Song', 'category': 'vehicles'},
    {'topic': 'Boats and Ships', 'category': 'vehicles'},
    {'topic': 'Monster Trucks', 'category': 'vehicles'},
    {'topic': 'Space Adventure', 'category': 'science'},
    {'topic': 'Planets Song', 'category': 'science'},
    {'topic': 'Solar System', 'category': 'science'},
    {'topic': 'Stars and Moon', 'category': 'science'},
    {'topic': 'Weather Song', 'category': 'nature'},
    {'topic': 'Rainy Day', 'category': 'nature'},
    {'topic': 'Snowy Day', 'category': 'nature'},
    {'topic': 'Sunny Day', 'category': 'nature'},
    {'topic': 'Windy Day', 'category': 'nature'},
    {'topic': 'Four Seasons', 'category': 'nature'},
    {'topic': 'Spring Song', 'category': 'nature'},
    {'topic': 'Summer Song', 'category': 'nature'},
    {'topic': 'Autumn Song', 'category': 'nature'},
    {'topic': 'Winter Song', 'category': 'nature'},
    {'topic': 'Days of the Week', 'category': 'calendar'},
    {'topic': 'Months of the Year', 'category': 'calendar'},
    {'topic': 'Morning Routine', 'category': 'routines'},
    {'topic': 'Bedtime Routine', 'category': 'routines'},
    {'topic': 'Bath Time', 'category': 'routines'},
    {'topic': 'Brush Your Teeth', 'category': 'routines'},
    {'topic': 'Clean Up Song', 'category': 'routines'},
    {'topic': 'Getting Dressed', 'category': 'routines'},
    {'topic': 'Potty Training', 'category': 'routines'},
    {'topic': 'School Time', 'category': 'routines'},
    {'topic': 'Good Habits', 'category': 'values'},
    {'topic': 'Sharing Is Caring', 'category': 'values'},
    {'topic': 'Kindness Song', 'category': 'values'},
    {'topic': 'Please and Thank You', 'category': 'values'},
    {'topic': 'Helping Friends', 'category': 'values'},
    {'topic': 'Honesty Song', 'category': 'values'},
    {'topic': 'Safety Song', 'category': 'safety'},
    {'topic': 'Road Safety', 'category': 'safety'},
    {'topic': 'Fire Safety', 'category': 'safety'},
    {'topic': 'Stranger Safety', 'category': 'safety'},
    {'topic': 'Body Parts', 'category': 'body'},
    {'topic': 'Five Senses', 'category': 'body'},
    {'topic': 'Head Shoulders Knees and Toes', 'category': 'body'},
    {'topic': 'Healthy Exercise', 'category': 'body'},
    {'topic': 'Emotions Song', 'category': 'emotions'},
    {'topic': 'Happy and Sad', 'category': 'emotions'},
    {'topic': 'Calm Down Song', 'category': 'emotions'},
    {'topic': 'Feelings and Faces', 'category': 'emotions'},
    {'topic': 'Opposites Song', 'category': 'concepts'},
    {'topic': 'Big and Small', 'category': 'concepts'},
    {'topic': 'Fast and Slow', 'category': 'concepts'},
    {'topic': 'Hot and Cold', 'category': 'concepts'},
    {'topic': 'Up and Down', 'category': 'concepts'},
    {'topic': 'Near and Far', 'category': 'concepts'},
    {'topic': 'Heavy and Light', 'category': 'concepts'},
    {'topic': 'Open and Close', 'category': 'concepts'},
    {'topic': 'Left and Right', 'category': 'concepts'},
    {'topic': 'Music Instruments', 'category': 'music'},
    {'topic': 'Dance and Freeze', 'category': 'music'},
    {'topic': 'Clap and Stomp', 'category': 'music'},
    {'topic': 'Loud and Quiet', 'category': 'music'},
    {'topic': 'Under the Sea', 'category': 'adventure'},
    {'topic': 'Jungle Adventure', 'category': 'adventure'},
    {'topic': 'Treasure Hunt', 'category': 'adventure'},
    {'topic': 'Picnic Adventure', 'category': 'adventure'},
    {'topic': 'Camping Adventure', 'category': 'adventure'},
    {'topic': 'Garden Adventure', 'category': 'adventure'},
    {'topic': 'Supermarket Adventure', 'category': 'adventure'},
    {'topic': 'At the Zoo', 'category': 'adventure'},
    {'topic': 'At the Beach', 'category': 'adventure'},
    {'topic': 'At the Park', 'category': 'adventure'},
]


def normalize_topic(value: str) -> str:
    text = re.sub(r'[^a-z0-9]+', ' ', value.lower())
    return ' '.join(text.split())


def load_history() -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def save_history(history: list[dict[str, Any]]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        json.dumps(history[-MAX_HISTORY_ITEMS:], indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


def choose_topic(suggested_topic: str = '') -> dict[str, str]:
    history = load_history()
    blocked_topics = {
        normalize_topic(str(item.get('topic', '')))
        for item in history[-MAX_HISTORY_ITEMS:]
        if str(item.get('topic', '')).strip()
    }
    recent_categories = [
        str(item.get('category', '')).strip()
        for item in history[-5:]
        if str(item.get('category', '')).strip()
    ]

    suggested_normalized = normalize_topic(suggested_topic)
    if suggested_normalized:
        match = next(
            (item for item in TOPIC_POOL if normalize_topic(item['topic']) == suggested_normalized),
            None,
        )
        if match and suggested_normalized not in blocked_topics:
            return match.copy()

    candidates = [
        item for item in TOPIC_POOL
        if normalize_topic(item['topic']) not in blocked_topics
    ]
    if not candidates:
        save_history([])
        candidates = TOPIC_POOL.copy()

    fresh_categories = [
        item for item in candidates
        if item['category'] not in recent_categories
    ]
    if fresh_categories:
        candidates = fresh_categories

    return random.SystemRandom().choice(candidates).copy()


def get_next_topic(suggested_topic: str = '', reserve: bool = True) -> dict[str, Any]:
    selected = choose_topic(suggested_topic)
    if reserve:
        history = load_history()
        selected_at = datetime.now(timezone.utc).isoformat()
        history.append({
            'topic': selected['topic'],
            'category': selected['category'],
            'source': 'trend_suggestion' if suggested_topic else 'topic_pool',
            'selected_at': selected_at,
        })
        save_history(history)
        selected['selected_at'] = selected_at
    return selected


def main() -> None:
    selected = get_next_topic()
    print('----------------------------------------')
    print('Next unique Milo topic selected:')
    print(f"Topic: {selected['topic']}")
    print(f"Category: {selected['category']}")
    print(f'History file: {HISTORY_PATH}')
    print('----------------------------------------')


if __name__ == '__main__':
    main()
