import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types


MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
]

SCENE_DURATIONS = [4, 4, 4, 4, 4, 5]
EXPECTED_SCENES = 6


def get_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY missing hai.")

    return genai.Client(api_key=api_key)


def create_prompt() -> str:
    return """
You are the creative song and story director for an original preschool
cartoon series called "Milo & Friends".

TARGET AUDIENCE:
- Children aged 2 to 6 years.
- Children must understand the story without difficult words.
- The Short must feel like a tiny sing-along rhyme, not a lecture.
- Use cheerful repetition that children can copy and sing.

PERMANENT ORIGINAL CHARACTERS:

Milo:
- baby orange-and-white kitten
- large blue eyes
- blue T-shirt
- red shorts
- white shoes
- brave, kind and curious

Coco:
- small white puppy
- light-brown floppy ears
- yellow hoodie
- blue shoes
- loyal, energetic and funny

Poko:
- cute baby panda
- green overalls
- tiny red backpack
- lovable and clumsy

Ducky:
- tiny yellow duckling
- purple cap
- tiny blue bag
- cheerful and clever

VISUAL STYLE:
- original premium 3D preschool cartoon
- rounded, cute and expressive characters
- bright family-friendly colors
- soft cinematic lighting
- clear visible movement
- simple uncluttered backgrounds
- vertical 9:16 composition
- no text inside images
- no logos or watermarks
- do not copy any existing cartoon, studio, song or copyrighted character
