import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta

def get_db_connection():
    """Get database connection with row factory for dictionary-like rows"""
    conn = sqlite3.connect('instagram_app.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect('instagram_app.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  reset_token TEXT,
                  reset_token_expiry TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Scheduled posts table with platforms column
    c.execute('''CREATE TABLE IF NOT EXISTS scheduled_posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  image_path TEXT NOT NULL,
                  caption TEXT,
                  schedule_time TEXT NOT NULL,
                  prompt TEXT,
                  platforms TEXT DEFAULT '["instagram"]',
                  status TEXT DEFAULT 'pending',
                  sentiment_label TEXT DEFAULT NULL,
                  sentiment_score REAL DEFAULT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Add columns if they don't exist (for existing databases)
    for col, definition in [
        ("platforms",       "TEXT DEFAULT '[\"instagram\"]'"),
        ("sentiment_label", "TEXT DEFAULT NULL"),
        ("sentiment_score", "REAL DEFAULT NULL"),
    ]:
        try:
            c.execute(f"ALTER TABLE scheduled_posts ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            pass  # Column already exists
    
    conn.commit()
    conn.close()

class User:
    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def create(username, email, password):
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        try:
            hashed = User.hash_password(password)
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                     (username, email, hashed))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    @staticmethod
    def authenticate(username, password):
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        hashed = User.hash_password(password)
        c.execute("SELECT id, username, email FROM users WHERE username = ? AND password = ?",
                 (username, hashed))
        user = c.fetchone()
        conn.close()
        return user
    
    @staticmethod
    def get_by_email(email):
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        c.execute("SELECT id, username, email FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        return user
    
    @staticmethod
    def set_reset_token(email):
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        token = secrets.token_urlsafe(32)
        expiry = (datetime.now() + timedelta(hours=1)).isoformat()
        
        c.execute("UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE email = ?",
                 (token, expiry, email))
        conn.commit()
        conn.close()
        return token
    
    @staticmethod
    def verify_reset_token(token):
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        c.execute("SELECT id, email FROM users WHERE reset_token = ? AND reset_token_expiry > ?",
                 (token, datetime.now().isoformat()))
        user = c.fetchone()
        conn.close()
        return user
    
    @staticmethod
    def reset_password(token, new_password):
        user = User.verify_reset_token(token)
        if user:
            conn = sqlite3.connect('instagram_app.db')
            c = conn.cursor()
            hashed = User.hash_password(new_password)
            c.execute("UPDATE users SET password = ?, reset_token = NULL, reset_token_expiry = NULL WHERE id = ?",
                     (hashed, user[0]))
            conn.commit()
            conn.close()
            return True
        return False

class ScheduledPost:
    @staticmethod
    def create(user_id, image_path, caption, schedule_time, prompt, platforms=None):
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        platforms_json = json.dumps(platforms if platforms else ['instagram'])
        c.execute("INSERT INTO scheduled_posts (user_id, image_path, caption, schedule_time, prompt, platforms) VALUES (?, ?, ?, ?, ?, ?)",
                 (user_id, image_path, caption, schedule_time, prompt, platforms_json))
        post_id = c.lastrowid
        conn.commit()
        conn.close()
        return post_id
    
    @staticmethod
    def get_by_user(user_id):
        """Get all posts for a user as dictionaries"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM scheduled_posts WHERE user_id = ? ORDER BY schedule_time DESC", (user_id,))
        posts = c.fetchall()
        conn.close()
        # Convert Row objects to dictionaries
        return [dict(post) for post in posts]
    
    @staticmethod
    def get_all_pending():
        """Get all pending posts as tuples"""
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        c.execute("SELECT * FROM scheduled_posts WHERE status = 'pending' ORDER BY schedule_time")
        posts = c.fetchall()
        conn.close()
        return posts
    
    @staticmethod
    def mark_posted(post_id):
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        c.execute("UPDATE scheduled_posts SET status = 'posted' WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_by_id(post_id):
        """Get a specific post as tuple"""
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        c.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,))
        post = c.fetchone()
        conn.close()
        return post
    
    @staticmethod
    def delete(post_id):
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        c.execute("DELETE FROM scheduled_posts WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def save_sentiment(post_id, label, score):
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        c.execute("UPDATE scheduled_posts SET sentiment_label=?, sentiment_score=? WHERE id=?",
                  (label, score, post_id))
        conn.commit()
        conn.close()

    @staticmethod
    def get_analytics(user_id):
        """Return analytics data for the dashboard charts."""
        conn = get_db_connection()
        c = conn.cursor()

        # Total counts
        c.execute("SELECT COUNT(*) FROM scheduled_posts WHERE user_id=?", (user_id,))
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM scheduled_posts WHERE user_id=? AND status='posted'", (user_id,))
        posted = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM scheduled_posts WHERE user_id=? AND status='pending'", (user_id,))
        pending = c.fetchone()[0]

        # Posts per day (last 14 days)
        c.execute("""
            SELECT DATE(created_at) as day, COUNT(*) as cnt
            FROM scheduled_posts WHERE user_id=?
            AND created_at >= DATE('now', '-14 days')
            GROUP BY day ORDER BY day
        """, (user_id,))
        posts_per_day = [dict(r) for r in c.fetchall()]

        # Platform distribution
        c.execute("SELECT platforms FROM scheduled_posts WHERE user_id=?", (user_id,))
        platform_counts = {"instagram": 0, "telegram": 0}
        for row in c.fetchall():
            try:
                plats = json.loads(row["platforms"] or '[]')
                for p in plats:
                    if p in platform_counts:
                        platform_counts[p] += 1
            except Exception:
                pass

        # Sentiment distribution
        c.execute("""
            SELECT sentiment_label, COUNT(*) as cnt
            FROM scheduled_posts
            WHERE user_id=? AND sentiment_label IS NOT NULL
            GROUP BY sentiment_label
        """, (user_id,))
        sentiment_dist = {r["sentiment_label"]: r["cnt"] for r in c.fetchall()}

        # Posts by hour of day — cast key to int properly
        c.execute("""
            SELECT CAST(strftime('%H', schedule_time) AS INTEGER) as hour,
                   COUNT(*) as cnt
            FROM scheduled_posts WHERE user_id=?
            GROUP BY hour ORDER BY hour
        """, (user_id,))
        posts_by_hour = {int(r["hour"]): r["cnt"] for r in c.fetchall() if r["hour"] is not None}

        # Sentiment trend over last 10 posts
        c.execute("""
            SELECT created_at, sentiment_label, sentiment_score
            FROM scheduled_posts
            WHERE user_id=? AND sentiment_label IS NOT NULL
            ORDER BY created_at DESC LIMIT 10
        """, (user_id,))
        sentiment_trend = [dict(r) for r in c.fetchall()]

        conn.close()
        return {
            "total": total,
            "posted": posted,
            "pending": pending,
            "posts_per_day": posts_per_day,
            "platform_counts": platform_counts,
            "sentiment_dist": sentiment_dist,
            "posts_by_hour": posts_by_hour,
            "sentiment_trend": list(reversed(sentiment_trend))
        }