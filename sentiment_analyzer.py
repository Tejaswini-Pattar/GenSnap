"""
sentiment_analyzer.py
----------------------
Runs a real pre-trained NLP model (distilbert-base-uncased-finetuned-sst-2-english)
locally using HuggingFace Transformers to analyse caption sentiment.

No API key needed — model downloads once (~67MB) and runs offline after that.
"""

from transformers import pipeline
import re

_sentiment_pipeline = None


def init_sentiment_analyzer():
    """Load the model once at startup. Downloads ~67MB on first run."""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        print("Loading sentiment model (downloads once ~67MB)...")
        _sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            truncation=True,
            max_length=512
        )
        print("Sentiment model loaded.")
    return _sentiment_pipeline


def analyse_sentiment(text: str) -> dict:
    """
    Analyse the sentiment of a caption.

    Returns:
        {
            "label":      "POSITIVE" | "NEGATIVE" | "NEUTRAL",
            "score":      0.97,          # confidence 0-1
            "emoji":      "😊",
            "color":      "#16a34a",
            "warning":    None | "string message if negative",
            "breakdown":  { "positive": 0.97, "negative": 0.03 }
        }
    """
    if not text or not text.strip():
        return {
            "label": "NEUTRAL",
            "score": 0.5,
            "emoji": "😐",
            "color": "#d97706",
            "warning": None,
            "breakdown": {"positive": 0.5, "negative": 0.5}
        }

    pipe = init_sentiment_analyzer()

    # Clean text — remove hashtags and URLs for cleaner analysis
    clean = re.sub(r'#\w+', '', text)
    clean = re.sub(r'http\S+', '', clean).strip()
    if not clean:
        clean = text  # fallback to original if nothing left

    result = pipe(clean[:512])[0]
    raw_label = result["label"]   # "POSITIVE" or "NEGATIVE"
    score = round(result["score"], 4)

    # Map to 3-class with neutral zone (50-65% confidence = neutral)
    if score < 0.65:
        label = "NEUTRAL"
        emoji = "😐"
        color = "#d97706"
    elif raw_label == "POSITIVE":
        label = "POSITIVE"
        emoji = "😊"
        color = "#16a34a"
    else:
        label = "NEGATIVE"
        emoji = "😟"
        color = "#dc2626"

    # Breakdown scores
    if raw_label == "POSITIVE":
        breakdown = {"positive": score, "negative": round(1 - score, 4)}
    else:
        breakdown = {"positive": round(1 - score, 4), "negative": score}

    # Warning for negative captions
    warning = None
    if label == "NEGATIVE":
        warning = "This caption has a negative tone. Consider revising before posting to maintain a positive brand image."
    elif label == "NEUTRAL" and raw_label == "NEGATIVE":
        warning = "This caption leans slightly negative. Review before posting."

    return {
        "label": label,
        "score": score,
        "emoji": emoji,
        "color": color,
        "warning": warning,
        "breakdown": breakdown
    }
