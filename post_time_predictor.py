"""
post_time_predictor.py
-----------------------
Trains a RandomForestClassifier on engagement patterns to predict
the best hour of day to post on Instagram/social media.

Features used:
  - day_of_week (0=Mon … 6=Sun)
  - caption_length
  - hashtag_count
  - has_emoji
  - platform (instagram=0, telegram=1)

Target: best_hour bucket (0-23)

On first run it trains on synthetic seed data that reflects real
Instagram engagement research. As users post more, the model
retrains on their actual posting history.
"""

import os
import json
import pickle
import sqlite3
import numpy as np
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

MODEL_PATH = "best_time_model.pkl"
DB_PATH    = "instagram_app.db"


# ── Seed training data ────────────────────────────────────────
# Based on published Instagram engagement research:
# Best hours: 6-9am, 11am-1pm, 7-9pm
# Best days: Tue, Wed, Thu, Fri
def _generate_seed_data():
    """
    Generate realistic synthetic training data based on
    Instagram engagement research patterns.
    Returns list of (day_of_week, caption_len, hashtag_count,
                     has_emoji, platform, best_hour)
    """
    rng = np.random.default_rng(42)
    data = []

    # High-engagement time slots (from research)
    peak_hours = [7, 8, 9, 11, 12, 13, 19, 20, 21]
    off_hours  = [0, 1, 2, 3, 4, 5, 14, 15, 16, 22, 23]

    for _ in range(600):
        day = int(rng.integers(0, 7))
        cap_len = int(rng.integers(10, 300))
        htags = int(rng.integers(0, 25))
        emoji = int(rng.integers(0, 2))
        platform = int(rng.integers(0, 2))

        # Weekdays (1-4) + peak hours = higher engagement
        if day in [1, 2, 3, 4] and rng.random() > 0.3:
            hour = int(rng.choice(peak_hours))
        elif day in [5, 6]:  # weekend — evening peaks
            hour = int(rng.choice([10, 11, 19, 20, 21] if rng.random() > 0.4 else off_hours))
        else:
            hour = int(rng.choice(peak_hours if rng.random() > 0.5 else off_hours))

        data.append([day, cap_len, htags, emoji, platform, hour])

    return data


def _extract_features(caption: str, platform: str, dt: datetime):
    """Extract feature vector from a post."""
    hashtag_count = len([w for w in caption.split() if w.startswith('#')])
    has_emoji = int(any(ord(c) > 127 for c in caption))
    caption_length = len(caption)
    day_of_week = dt.weekday()
    plat_code = 0 if platform == 'instagram' else 1
    return [day_of_week, caption_length, hashtag_count, has_emoji, plat_code]


def train_model(user_id=None):
    """
    Train (or retrain) the RandomForest model.
    Uses seed data + any real posts from the database.
    Returns accuracy score.
    """
    rows = _generate_seed_data()

    # Add real posts from DB if available
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        query = "SELECT caption, platforms, schedule_time, status FROM scheduled_posts WHERE status='posted'"
        params = []
        if user_id:
            query += " AND user_id=?"
            params.append(user_id)
        c.execute(query, params)
        db_posts = c.fetchall()
        conn.close()

        for caption, platforms_json, schedule_time, status in db_posts:
            try:
                caption = caption or ""
                platforms = json.loads(platforms_json or '["instagram"]')
                platform = platforms[0] if platforms else 'instagram'
                dt = datetime.fromisoformat(schedule_time)
                feats = _extract_features(caption, platform, dt)
                rows.append(feats + [dt.hour])
            except Exception:
                continue
    except Exception:
        pass  # DB not ready yet — use seed data only

    data = np.array(rows)
    X = data[:, :5]
    y = data[:, 5].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"Best-time model trained. Accuracy: {acc:.2%} | Samples: {len(rows)}")

    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)

    return round(acc, 4)


def _load_model():
    if not os.path.exists(MODEL_PATH):
        train_model()
    with open(MODEL_PATH, 'rb') as f:
        return pickle.load(f)


def predict_best_times(caption: str, platform: str = 'instagram', top_n: int = 3) -> dict:
    """
    Predict the top N best times to post.
    Slot 1 = best remaining hour TODAY
    Slot 2 & 3 = best hours on the next best upcoming days

    Returns:
        {
            "top_slots": [
                {"hour": 19, "label": "7:00 PM", "day": "Today",
                 "date": "2026-05-11", "confidence": 0.82,
                 "reason": "Evening peak engagement"},
                ...
            ],
            "best_datetime": "2026-05-11 19:00",
            "model_info": "RandomForest trained on 600+ engagement samples"
        }
    """
    model = _load_model()
    now   = datetime.now()

    def score_hour(day_offset, hour):
        """Get model confidence for a specific day+hour."""
        dt_fake = now.replace(hour=hour, minute=0)
        feats = _extract_features(caption, platform, dt_fake)
        feats[0] = (now.weekday() + day_offset) % 7
        proba  = model.predict_proba([feats])[0]
        classes = list(model.classes_)
        return proba[classes.index(hour)] if hour in classes else 0.0

    day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    def get_reason(h):
        if h in range(6, 10):  return "Morning commute — high engagement"
        if h in range(11, 14): return "Lunch break — peak scroll time"
        if h in range(17, 20): return "After work — active browsing"
        if h in range(19, 22): return "Evening prime time — highest reach"
        return "Moderate engagement window"

    def fmt_hour(h):
        suffix  = "AM" if h < 12 else "PM"
        display = h if h <= 12 else h - 12
        if display == 0: display = 12
        return f"{display}:00 {suffix}"

    slots = []

    # ── Slot 1: best remaining hour TODAY ───────────────────
    today_scores = {}
    for hour in range(now.hour + 1, 24):   # only future hours today
        today_scores[hour] = score_hour(0, hour)

    if today_scores:
        best_hour_today = max(today_scores, key=today_scores.get)
        target_today = now.replace(hour=best_hour_today, minute=0, second=0, microsecond=0)
        slots.append({
            "hour":       best_hour_today,
            "label":      fmt_hour(best_hour_today),
            "day":        "Today",
            "date":       target_today.strftime("%Y-%m-%d"),
            "datetime":   target_today.strftime("%Y-%m-%d %H:%M"),
            "confidence": round(float(today_scores[best_hour_today]) * 100, 1),
            "reason":     get_reason(best_hour_today)
        })
    else:
        # No hours left today — use tomorrow as slot 1
        tomorrow = now + __import__('datetime').timedelta(days=1)
        scores_tmr = {h: score_hour(1, h) for h in range(24)}
        bh = max(scores_tmr, key=scores_tmr.get)
        target = tomorrow.replace(hour=bh, minute=0, second=0, microsecond=0)
        slots.append({
            "hour": bh, "label": fmt_hour(bh), "day": "Tomorrow",
            "date": target.strftime("%Y-%m-%d"),
            "datetime": target.strftime("%Y-%m-%d %H:%M"),
            "confidence": round(float(scores_tmr[bh]) * 100, 1),
            "reason": get_reason(bh)
        })

    # ── Slots 2 & 3: best hours on next 6 days (pick 2 different days) ──
    from datetime import timedelta
    used_days = {0}   # today already used
    day_offset = 1

    while len(slots) < top_n and day_offset <= 6:
        if day_offset not in used_days:
            day_scores = {h: score_hour(day_offset, h) for h in range(24)}
            bh = max(day_scores, key=day_scores.get)
            target_dt = (now + timedelta(days=day_offset)).replace(
                hour=bh, minute=0, second=0, microsecond=0
            )
            day_label = "Tomorrow" if day_offset == 1 else day_names[(now.weekday() + day_offset) % 7]
            slots.append({
                "hour":       bh,
                "label":      fmt_hour(bh),
                "day":        day_label,
                "date":       target_dt.strftime("%Y-%m-%d"),
                "datetime":   target_dt.strftime("%Y-%m-%d %H:%M"),
                "confidence": round(float(day_scores[bh]) * 100, 1),
                "reason":     get_reason(bh)
            })
            used_days.add(day_offset)
        day_offset += 1

    return {
        "top_slots":              slots,
        "best_datetime":          slots[0]["datetime"],
        "best_datetime_display":  slots[0]["datetime"],
        "model_info": f"RandomForest · {len(model.estimators_)} trees · trained on engagement patterns"
    }
