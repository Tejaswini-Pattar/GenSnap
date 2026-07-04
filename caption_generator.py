"""
caption_generator.py
--------------------
AI-powered caption generator using Google Gemini Vision API.
Analyses the actual image and generates multiple caption styles.

Requires: pip install google-genai
Free tier: 15 requests/min, 1M tokens/day - no credit card needed.
Get API key: https://aistudio.google.com/app/apikey
"""

from google import genai
from PIL import Image
import os
import json
import re

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_client = None


def init_caption_generator(api_key: str):
    """Call once at app startup with your Gemini API key."""
    global GEMINI_API_KEY, _client
    GEMINI_API_KEY = api_key
    _client = genai.Client(api_key=api_key)
    print("Caption generator (Gemini Vision) initialised")


def _get_client():
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("Gemini API key not set. Call init_caption_generator(api_key) first.")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _call_gemini(client, contents):
    """Try models in order until one works - handles quota and 404 errors."""
    # Only models confirmed available for this API key (from ListModels)
    models = [
        "gemini-2.0-flash-lite",    # lightest, most quota
        "gemini-2.0-flash-lite-001",
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
        "gemini-flash-lite-latest",
        "gemini-flash-latest",
    ]
    last_error = None
    for model in models:
        try:
            response = client.models.generate_content(model=model, contents=contents)
            print(f"Caption generated using {model}")
            return response
        except Exception as e:
            err_str = str(e)
            if "404" in err_str or "NOT_FOUND" in err_str:
                print(f"Model {model} not available, trying next...")
                last_error = e
                continue
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                print(f"Quota exceeded for {model}, trying next...")
                last_error = e
                continue
            else:
                raise
    raise last_error


# Caption styles
CAPTION_STYLES = {
    "engaging": {
        "label": "Engaging",
        "icon": "fa-fire",
        "color": "#f97316",
        "description": "High-energy, hook-driven caption to maximise reach",
        "prompt_hint": "Write an engaging, attention-grabbing caption with a strong hook. Use emojis naturally. End with a call-to-action or question to boost engagement."
    },
    "professional": {
        "label": "Professional",
        "icon": "fa-briefcase",
        "color": "#0284c7",
        "description": "Clean, brand-friendly tone for business accounts",
        "prompt_hint": "Write a clean, professional caption suitable for a brand or business account. Minimal emojis, polished language, clear message."
    },
    "storytelling": {
        "label": "Storytelling",
        "icon": "fa-book-open",
        "color": "#7c5cfc",
        "description": "Narrative style that draws the audience in",
        "prompt_hint": "Write a short storytelling caption that draws the reader in with a narrative or personal touch. Make it feel authentic and relatable."
    },
    "minimal": {
        "label": "Minimal",
        "icon": "fa-minus",
        "color": "#64748b",
        "description": "Short, punchy - less is more",
        "prompt_hint": "Write a very short, minimal caption - 1-2 lines maximum. Punchy, poetic, or thought-provoking. No hashtags."
    },
    "funny": {
        "label": "Funny / Witty",
        "icon": "fa-face-laugh",
        "color": "#eab308",
        "description": "Humorous caption with personality",
        "prompt_hint": "Write a funny, witty, or playful caption with personality. Use humour, wordplay, or a clever observation about the image."
    },
}


def _build_prompt(styles, user_hint=""):
    style_instructions = "\n".join(
        f'{i+1}. [{key.upper()}] {CAPTION_STYLES[key]["prompt_hint"]}'
        for i, key in enumerate(styles)
        if key in CAPTION_STYLES
    )
    hint_section = f'\nUser context: "{user_hint}"' if user_hint.strip() else ""
    keys_json = ", ".join(f'"{k}": "caption text here"' for k in styles if k in CAPTION_STYLES)

    prompt = (
        "You are a professional social media copywriter specialising in Instagram captions.\n\n"
        f"Analyse this image carefully and write {len(styles)} different captions - one per style.{hint_section}\n\n"
        "STYLES TO GENERATE:\n"
        f"{style_instructions}\n\n"
        "RULES:\n"
        "- Each caption must be unique in tone and structure.\n"
        "- Keep captions between 1-4 sentences (Minimal: 1-2 lines).\n"
        "- Do NOT include hashtags.\n"
        "- Return ONLY valid JSON, nothing else:\n\n"
        "{\n"
        '  "image_description": "one sentence describing what you see",\n'
        '  "captions": {\n'
        f"    {keys_json}\n"
        "  }\n"
        "}"
    )
    return prompt


def _parse_response(raw, styles):
    """Parse Gemini JSON response and enrich with style metadata."""
    # Strip markdown code fences if present
    clean = raw.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```[a-z]*\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)

    data = json.loads(clean)

    result_captions = {}
    for key in styles:
        if key in CAPTION_STYLES and key in data.get("captions", {}):
            result_captions[key] = {
                **CAPTION_STYLES[key],
                "text": data["captions"][key]
            }

    return {
        "success": True,
        "captions": result_captions,
        "image_description": data.get("image_description", "")
    }


def generate_captions(image_path: str, user_hint: str = "", styles: list = None) -> dict:
    """
    Analyse the image with Gemini Vision and generate captions in multiple styles.
    Returns: { "success": True, "captions": {...}, "image_description": "..." }
    """
    if styles is None:
        styles = list(CAPTION_STYLES.keys())

    try:
        img = Image.open(image_path)
        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
    except Exception as e:
        return {"success": False, "error": f"Could not open image: {e}"}

    prompt = _build_prompt(styles, user_hint)

    try:
        client = _get_client()
        response = _call_gemini(client, [prompt, img])
        return _parse_response(response.text, styles)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON parse error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_captions_from_text(prompt_text: str, styles: list = None) -> dict:
    """Text-only caption generation - used when no image is available yet."""
    if styles is None:
        styles = list(CAPTION_STYLES.keys())

    style_instructions = "\n".join(
        f'{i+1}. [{key.upper()}] {CAPTION_STYLES[key]["prompt_hint"]}'
        for i, key in enumerate(styles)
        if key in CAPTION_STYLES
    )
    keys_json = ", ".join(f'"{k}": "caption text here"' for k in styles if k in CAPTION_STYLES)

    prompt = (
        "You are a professional social media copywriter specialising in Instagram captions.\n\n"
        f'Based on this topic: "{prompt_text}"\n\n'
        f"Write {len(styles)} different captions - one per style:\n"
        f"{style_instructions}\n\n"
        "RULES:\n"
        "- Each caption must be unique in tone and structure.\n"
        "- Keep captions between 1-4 sentences (Minimal: 1-2 lines).\n"
        "- Do NOT include hashtags.\n"
        "- Return ONLY valid JSON:\n\n"
        "{\n"
        '  "image_description": "brief description of the topic",\n'
        '  "captions": {\n'
        f"    {keys_json}\n"
        "  }\n"
        "}"
    )

    try:
        client = _get_client()
        response = _call_gemini(client, prompt)
        return _parse_response(response.text, styles)
    except Exception as e:
        return {"success": False, "error": str(e)}
