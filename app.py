from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
from functools import wraps
import os
import sqlite3
import json
import threading
import schedule
import time
from models import init_db, User, ScheduledPost
from instagram_bot import InstagramBot
from telegram_bot import TelegramBot
from image_generator import generate_and_save_image, init_generator
from caption_generator import generate_captions, generate_captions_from_text, init_caption_generator, CAPTION_STYLES
from sentiment_analyzer import analyse_sentiment, init_sentiment_analyzer
from post_time_predictor import predict_best_times, train_model as train_time_model

from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename

# Replace the scheduler functions with APScheduler (more reliable)
scheduler = BackgroundScheduler()
scheduler_running = False

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret-key")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploaded_images'
app.config['GENERATED_FOLDER'] = 'generated_images'

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database
init_db()

# Initialize image generator with API token
huggingface_token = os.environ.get("HUGGINGFACE_TOKEN", "")
init_generator(huggingface_token)

# Initialize AI caption generator (Gemini Vision)
# Get your FREE key at: https://aistudio.google.com/app/apikey  (takes 30 seconds)
# Then either set env var:  set GEMINI_API_KEY=your_key_here
# Or paste it directly below:
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
try:
    if GEMINI_API_KEY and GEMINI_API_KEY != "PASTE_YOUR_GEMINI_KEY_HERE":
        init_caption_generator(GEMINI_API_KEY)
    else:
        print("⚠️  Gemini API key not set — AI captions disabled. Get free key at https://aistudio.google.com/app/apikey")
except Exception as e:
    print(f"⚠️  Caption generator not initialised: {e}")

# Initialize sentiment analyser (loads model in background thread to not block startup)
import threading
def _load_sentiment_bg():
    try:
        init_sentiment_analyzer()
    except Exception as e:
        print(f"⚠️  Sentiment analyser not loaded: {e}")
threading.Thread(target=_load_sentiment_bg, daemon=True).start()

# Train best-time predictor model at startup
try:
    train_time_model()
except Exception as e:
    print(f"⚠️  Best-time model not trained: {e}")

# Instagram bot instance
instagram_bot = InstagramBot()

# Telegram bot instance
telegram_bot = TelegramBot()

# Try to load saved Telegram config
telegram_bot.load_config()

# Email configuration (update with your SMTP settings)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "poisonousplants2024@gmail.com"
SMTP_PASSWORD = "wtfghdcknihmbaog"

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def send_reset_email(email, token):
    """Send password reset email"""
    try:
        reset_link = url_for('reset_password', token=token, _external=True)
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = email
        msg['Subject'] = "Password Reset Request - Social Media Bot"
        
        body = f"""
        Hello,
        
        You requested to reset your password for your Social Media Bot account.
        
        Click the link below to reset your password:
        {reset_link}
        
        This link will expire in 1 hour.
        
        If you didn't request this, please ignore this email.
        
        Best regards,
        Social Media Bot Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email error: {str(e)}")
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        user = User.create(username, email, password)
        if user:
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username or email already exists', 'danger')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.authenticate(username, password)
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash(f'Welcome back, {user[1]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.get_by_email(email)
        
        if user:
            token = User.set_reset_token(email)
            if send_reset_email(email, token):
                flash('Password reset link sent to your email!', 'success')
            else:
                flash('Error sending email. Please try again later.', 'danger')
        else:
            flash('Email not found in our records.', 'danger')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters!', 'danger')
        else:
            if User.reset_password(token, password):
                flash('Password reset successful! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Invalid or expired reset link.', 'danger')
    
    return render_template('reset_password.html', token=token)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    posts = ScheduledPost.get_by_user(session['user_id'])
    # Get platform connection status
    ig_connected = os.path.exists('session.json')
    telegram_connected = telegram_bot.verify_chat_id() if telegram_bot.chat_id else False
    return render_template('dashboard.html', posts=posts, ig_connected=ig_connected, telegram_connected=telegram_connected)

def post_scheduled_image(post_id, image_path, caption, platforms=None):
    """Post to selected platforms based on user preferences"""
    try:
        results = []
        
        # If platforms not provided, get from database or use defaults
        if platforms is None:
            # Get from database
            conn = sqlite3.connect('instagram_app.db')
            c = conn.cursor()
            c.execute("SELECT platforms FROM scheduled_posts WHERE id = ?", (post_id,))
            result = c.fetchone()
            conn.close()
            if result and result[0]:
                platforms = json.loads(result[0])
            else:
                # Default to all connected platforms
                platforms = []
                if os.path.exists('session.json'):
                    platforms.append('instagram')
                if telegram_bot.chat_id and telegram_bot.verify_chat_id():
                    platforms.append('telegram')
        
        # Post to Instagram
        if 'instagram' in platforms and os.path.exists('session.json'):
            insta_success = instagram_bot.post_image(image_path, caption)
            results.append(f"Instagram: {'✓' if insta_success else '✗'}")
        
        # Post to Telegram
        if 'telegram' in platforms and telegram_bot.chat_id:
            telegram_success, telegram_msg = telegram_bot.send_image(image_path, caption)
            results.append(f"Telegram: {'✓' if telegram_success else '✗'}")
        
        if any('✓' in r for r in results):
            ScheduledPost.mark_posted(post_id)
            print(f"✅ Posted at {datetime.now()}: {' | '.join(results)}")
        else:
            print(f"❌ Failed to post on all platforms: {' | '.join(results)}")
            
        return results
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return [f"Error: {str(e)}"]

def load_and_schedule_posts():
    """Load all pending posts from database and schedule them"""
    posts = ScheduledPost.get_all_pending()
    
    for post in posts:
        # Use index access instead of unpacking — safe regardless of column count
        post_id       = post[0]
        user_id       = post[1]
        image_path    = post[2]
        caption       = post[3]
        schedule_time = post[4]
        prompt        = post[5]

        # platforms column is index 6 in new schema, may not exist in old
        try:
            platforms = post[6] if len(post) > 6 else json.dumps(['instagram'])
            # In old schema index 6 was status — detect by checking if it looks like JSON
            if platforms and not platforms.strip().startswith('['):
                platforms = json.dumps(['instagram'])
        except Exception:
            platforms = json.dumps(['instagram'])
        
        try:
            # Parse schedule time
            if isinstance(schedule_time, str):
                if ':' in schedule_time and len(schedule_time) <= 8:
                    time_parts = schedule_time.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    now = datetime.now()
                    scheduled_time_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    if scheduled_time_today < now:
                        scheduled_time_today += timedelta(days=1)
                else:
                    scheduled_time_today = datetime.fromisoformat(schedule_time)
            else:
                scheduled_time_today = datetime.fromisoformat(str(schedule_time))
            
            # Parse platforms if stored as JSON string
            if isinstance(platforms, str):
                platforms_list = json.loads(platforms)
            else:
                platforms_list = platforms
            
            # Schedule job
            scheduler.add_job(
                func=post_scheduled_image,
                trigger='date',
                run_date=scheduled_time_today,
                args=[post_id, image_path, caption],
                kwargs={'platforms': platforms_list},
                id=f"post_{post_id}",
                replace_existing=True
            )
            
            print(f"📅 Scheduled post {post_id} for {scheduled_time_today} to platforms: {platforms_list}")
            
        except Exception as e:
            print(f"⚠️ Error scheduling post {post_id}: {str(e)}")

def start_scheduler():
    """Start the scheduler if not already running"""
    global scheduler_running
    
    if not scheduler.running:
        scheduler.start()
        scheduler_running = True
        print("🔄 Scheduler started")
        
        # Load existing posts
        load_and_schedule_posts()

@app.route('/generate-image', methods=['GET', 'POST'])
@login_required
def generate_image():
    if request.method == 'POST':
        prompt = request.form['prompt']
        caption = request.form.get('caption', '')
        schedule_time = request.form.get('schedule_time')
        schedule_date = request.form.get('schedule_date')
        
        # Get platform selection
        platforms = request.form.getlist('platforms')
        if not platforms:
            flash('Please select at least one platform to post to', 'danger')
            return redirect(url_for('generate_image'))
        
        session['preview_platforms'] = platforms
        
        # Generate hashtags if auto-hashtag is checked
        auto_hashtags = request.form.get('auto_hashtags') == 'on'
        if auto_hashtags:
            from hashtag_generator import generate_hashtags
            text_to_analyze = prompt + ' ' + caption
            hashtags = generate_hashtags(text_to_analyze)
            caption = caption + '\n\n' + hashtags if caption else hashtags
        
        # Generate image
        try:
            image_path = generate_and_save_image(prompt, session['user_id'])
            
            # Store in session for preview
            session['preview_image'] = image_path
            session['preview_prompt'] = prompt
            session['preview_caption'] = caption
            session['preview_schedule_time'] = schedule_time
            session['preview_schedule_date'] = schedule_date
            
            # Redirect to preview page
            return redirect(url_for('preview_post'))
            
        except Exception as e:
            flash(f'❌ Error generating image: {str(e)}', 'danger')
            return redirect(url_for('generate_image'))
    
    # Get connection status for platform display
    ig_connected = os.path.exists('session.json')
    telegram_connected = telegram_bot.verify_chat_id() if telegram_bot.chat_id else False
    
    return render_template('generate_image.html', 
                         ig_connected=ig_connected, 
                         telegram_connected=telegram_connected)

@app.route('/upload-image', methods=['GET', 'POST'])
@login_required
def upload_image():
    if request.method == 'POST':
        caption = request.form.get('caption', '')
        schedule_time = request.form.get('schedule_time')
        schedule_date = request.form.get('schedule_date')

        platforms = request.form.getlist('platforms')
        if not platforms:
            flash('Please select at least one platform to post to', 'danger')
            return redirect(url_for('upload_image'))

        session['preview_platforms'] = platforms

        user_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"user_{session['user_id']}")
        os.makedirs(user_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # ── Case 1: edited image sent as base64 from the canvas editor ──
        edited_data = request.form.get('edited_image_data', '').strip()
        # Also accept attached_image_data (from AI Generate page upload button)
        if not edited_data:
            edited_data = request.form.get('attached_image_data', '').strip()

        # ── Case 0: multiple images sent as JSON array ──
        multi_data = request.form.get('multi_image_data', '').strip()
        if multi_data and multi_data.startswith('['):
            import base64
            try:
                data_list = json.loads(multi_data)
            except Exception:
                data_list = []
            if len(data_list) > 1:
                saved_paths = []
                for idx, data_url in enumerate(data_list):
                    if not data_url or not data_url.startswith('data:image'):
                        continue
                    _, b64 = data_url.split(',', 1)
                    img_bytes = base64.b64decode(b64)
                    img_path = os.path.join(user_dir, f"{timestamp}_img{idx+1}.jpg")
                    with open(img_path, 'wb') as f:
                        f.write(img_bytes)
                    saved_paths.append(img_path)
                if not saved_paths:
                    flash('No valid images in multi-image data', 'danger')
                    return redirect(url_for('upload_image'))
                session['preview_images'] = saved_paths
                session['preview_image'] = saved_paths[0]
                session['preview_caption'] = caption
                session['preview_schedule_time'] = schedule_time
                session['preview_schedule_date'] = schedule_date
                session['preview_prompt'] = 'Uploaded images'
                return redirect(url_for('preview_post'))
            elif len(data_list) == 1:
                # Treat single entry as edited_data
                edited_data = data_list[0] if data_list else edited_data

        if edited_data and edited_data.startswith('data:image'):
            import base64, re
            header, b64 = edited_data.split(',', 1)
            img_bytes = base64.b64decode(b64)
            image_path = os.path.join(user_dir, f"{timestamp}_edited.jpg")
            with open(image_path, 'wb') as f:
                f.write(img_bytes)

        # ── Case 2: plain file upload (no edits applied) ──
        elif 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if not allowed_file(file.filename):
                flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP', 'danger')
                return redirect(url_for('upload_image'))
            filename = secure_filename(f"{timestamp}_{file.filename}")
            image_path = os.path.join(user_dir, filename)
            file.save(image_path)

        else:
            flash('No image provided', 'danger')
            return redirect(url_for('upload_image'))

        # Generate hashtags if requested
        auto_hashtags = request.form.get('auto_hashtags') == 'on'
        if auto_hashtags:
            from hashtag_generator import generate_hashtags
            hashtags = generate_hashtags(caption)
            caption = caption + '\n\n' + hashtags if caption else hashtags

        session['preview_image']         = image_path
        session['preview_caption']       = caption
        session['preview_schedule_time'] = schedule_time
        session['preview_schedule_date'] = schedule_date
        session['preview_prompt']        = 'Uploaded image'

        return redirect(url_for('preview_post'))

    ig_connected       = os.path.exists('session.json')
    telegram_connected = telegram_bot.verify_chat_id() if telegram_bot.chat_id else False
    return render_template('upload_image.html',
                           ig_connected=ig_connected,
                           telegram_connected=telegram_connected)

@app.route('/scheduled-posts')
@login_required
def scheduled_posts():
    posts = ScheduledPost.get_by_user(session['user_id'])
    return render_template('scheduled_posts.html', posts=posts)

@app.route('/cancel-post/<int:post_id>')
@login_required
def cancel_post(post_id):
    post = ScheduledPost.get_by_id(post_id)
    if post and post[1] == session['user_id']:
        # Remove from scheduler if exists
        try:
            scheduler.remove_job(f"post_{post_id}")
        except:
            pass
        ScheduledPost.delete(post_id)
        flash('Post cancelled successfully', 'success')
    else:
        flash('Post not found or unauthorized', 'danger')
    
    return redirect(url_for('scheduled_posts'))

@app.route('/preview-post', methods=['GET', 'POST'])
@login_required
def preview_post():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'confirm':
            # Get preview data from session
            image_path = session.get('preview_image')
            caption = session.get('preview_caption')
            schedule_time = session.get('preview_schedule_time')
            schedule_date = session.get('preview_schedule_date')
            prompt = session.get('preview_prompt')
            platforms = session.get('preview_platforms', ['instagram'])
            preview_images = session.get('preview_images', [])  # multi-image list

            # If edited canvas data was submitted, save it over the session image
            edited_preview = request.form.get('edited_preview_data', '').strip()
            if edited_preview and edited_preview.startswith('data:image') and image_path:
                import base64 as _b64
                _, b64 = edited_preview.split(',', 1)
                img_bytes = _b64.b64decode(b64)
                # Overwrite the existing file with the edited version
                with open(image_path, 'wb') as f:
                    f.write(img_bytes)

            # If user edited the caption in the preview page, use that
            edited_caption = request.form.get('edited_caption', '').strip()
            if edited_caption:
                caption = edited_caption
            
            if not image_path:
                flash('No image to post', 'danger')
                return redirect(url_for('dashboard'))
            
            if schedule_time:
                # Handle scheduling
                if schedule_date:
                    scheduled_datetime = datetime.strptime(
                        f"{schedule_date} {schedule_time}", 
                        "%Y-%m-%d %H:%M"
                    )
                    schedule_time_str = scheduled_datetime.isoformat()
                else:
                    now = datetime.now()
                    time_parts = schedule_time.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    scheduled_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    if scheduled_datetime < now:
                        scheduled_datetime += timedelta(days=1)
                    
                    schedule_time_str = scheduled_datetime.isoformat()
                
                # Save to database with platforms
                post_id = ScheduledPost.create(
                    session['user_id'],
                    image_path,
                    caption,
                    schedule_time_str,
                    prompt,
                    platforms
                )
                
                # Schedule the post
                scheduler.add_job(
                    func=post_scheduled_image,
                    trigger='date',
                    run_date=scheduled_datetime,
                    args=[post_id, image_path, caption],
                    kwargs={'platforms': platforms},
                    id=f"post_{post_id}",
                    replace_existing=True
                )
                
                flash(f'✅ Image scheduled for {scheduled_datetime.strftime("%Y-%m-%d %H:%M")}!', 'success')
                flash(f'📱 Will post to: {", ".join(platforms)}', 'info')
            else:
                # Post immediately to selected platforms
                results = []
                
                # Post to Instagram
                if 'instagram' in platforms and os.path.exists('session.json'):
                    if preview_images and len(preview_images) > 1:
                        insta_success = instagram_bot.post_album(preview_images, caption)
                    else:
                        insta_success = instagram_bot.post_image(image_path, caption)
                    results.append(f"Instagram: {'✅' if insta_success else '❌'}")
                elif 'instagram' in platforms:
                    results.append("Instagram: ❌ (Not connected)")
                
                # Post to Telegram
                if 'telegram' in platforms and telegram_bot.chat_id:
                    telegram_success, telegram_msg = telegram_bot.send_image(image_path, caption)
                    results.append(f"Telegram: {'✅' if telegram_success else '❌'}")
                elif 'telegram' in platforms:
                    results.append("Telegram: ❌ (Not connected)")

                # ── Save to DB so analytics counts it ──
                now_str = datetime.now().isoformat()
                post_id = ScheduledPost.create(
                    session['user_id'],
                    image_path,
                    caption,
                    now_str,          # schedule_time = now
                    prompt or '',
                    platforms
                )
                # Mark as posted immediately
                ScheduledPost.mark_posted(post_id)

                if results:
                    success_count = sum(1 for r in results if '✅' in r)
                    flash(f'Posted to {success_count}/{len(results)} platforms: ' + ' | '.join(results), 
                          'success' if success_count > 0 else 'warning')
                else:
                    flash('No platforms selected. Please select at least one platform.', 'warning')
            
            # Clear preview session data
            session.pop('preview_image', None)
            session.pop('preview_caption', None)
            session.pop('preview_schedule_time', None)
            session.pop('preview_schedule_date', None)
            session.pop('preview_prompt', None)
            session.pop('preview_platforms', None)
            session.pop('preview_images', None)
            
            return redirect(url_for('dashboard'))
        else:
            # Cancel - clear preview and redirect
            session.pop('preview_image', None)
            session.pop('preview_caption', None)
            session.pop('preview_schedule_time', None)
            session.pop('preview_schedule_date', None)
            session.pop('preview_prompt', None)
            session.pop('preview_platforms', None)
            session.pop('preview_images', None)
            flash('Post cancelled', 'info')
            return redirect(url_for('generate_image'))
    
    # GET request - show preview
    image_path = session.get('preview_image')
    caption = session.get('preview_caption', '')
    platforms = session.get('preview_platforms', ['instagram'])
    
    if not image_path:
        flash('No image to preview', 'warning')
        return redirect(url_for('generate_image'))
    
    # Normalise path separators for the browser (Windows uses backslashes)
    image_path_url = image_path.replace('\\', '/')
    
    # Get connection status
    ig_connected = os.path.exists('session.json')
    telegram_connected = telegram_bot.verify_chat_id() if telegram_bot.chat_id else False
    
    return render_template('preview_post.html', 
                         image_path=image_path,
                         image_path_url=image_path_url,
                         caption=caption,
                         platforms=platforms,
                         ig_connected=ig_connected,
                         telegram_connected=telegram_connected)
# Image serving routes
@app.route('/generated_images/<path:filename>')
def serve_generated_image(filename):
    """Serve generated images"""
    return send_from_directory('generated_images', filename)

@app.route('/uploaded_images/<path:filename>')
def serve_uploaded_image(filename):
    """Serve uploaded images"""
    return send_from_directory('uploaded_images', filename)

@app.route('/update-instagram-session', methods=['GET', 'POST'])
@login_required
def update_instagram_session():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            success = instagram_bot.login(username, password)
            if success:
                flash('Instagram session updated successfully!', 'success')
            else:
                flash('Failed to login to Instagram. Check your credentials.', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
        
        return redirect(url_for('dashboard'))
    
    return render_template('update_instagram.html')

# ============ TELEGRAM ROUTES ============

@app.route('/connect-telegram', methods=['GET', 'POST'])
@login_required
def connect_telegram():
    if request.method == 'POST':
        chat_id = request.form.get('chat_id')
        
        if not chat_id:
            flash('Please enter a Chat ID', 'danger')
            return redirect(url_for('connect_telegram'))
        
        # Set the chat ID
        telegram_bot.set_chat_id(chat_id)
        
        # Verify the connection
        if telegram_bot.verify_chat_id():
            flash('✅ Telegram connected successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Failed to connect. Please check your Chat ID.', 'danger')
    
    current_chat_id = telegram_bot.chat_id
    is_connected = telegram_bot.verify_chat_id() if current_chat_id else False
    
    return render_template('connect_telegram.html', 
                         current_chat_id=current_chat_id,
                         is_connected=is_connected)

@app.route('/disconnect-telegram')
@login_required
def disconnect_telegram():
    """Disconnect Telegram"""
    telegram_bot.set_chat_id(None)
    flash('Telegram disconnected successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/test-telegram')
@login_required
def test_telegram():
    """Send a test message to Telegram"""
    if telegram_bot.chat_id and telegram_bot.verify_chat_id():
        success, msg = telegram_bot.send_message("🎉 Test message from your Social Media Bot! Connection is working perfectly.")
        if success:
            flash('Test message sent successfully!', 'success')
        else:
            flash(f'Failed to send: {msg}', 'danger')
    else:
        flash('Telegram not connected. Please connect first.', 'warning')
    
    return redirect(url_for('dashboard'))


# ============ SENTIMENT ANALYSIS ROUTE ============

@app.route('/analyse-sentiment', methods=['POST'])
@login_required
def analyse_sentiment_api():
    """
    AJAX: analyse caption sentiment.
    Body: { "caption": "..." }
    Returns: { "label": "POSITIVE", "score": 0.97, "emoji": "😊", ... }
    """
    data = request.get_json(silent=True) or {}
    caption = data.get('caption', '').strip()
    if not caption:
        return jsonify({"success": False, "error": "No caption provided"}), 400
    try:
        result = analyse_sentiment(caption)
        result['success'] = True
        # Save sentiment to the latest pending post for this user if exists
        conn = sqlite3.connect('instagram_app.db')
        c = conn.cursor()
        c.execute("""SELECT id FROM scheduled_posts
                     WHERE user_id=? ORDER BY created_at DESC LIMIT 1""",
                  (session['user_id'],))
        row = c.fetchone()
        conn.close()
        if row:
            ScheduledPost.save_sentiment(row[0], result['label'], result['score'])
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============ BEST TIME PREDICTOR ROUTE ============

@app.route('/predict-best-time', methods=['POST'])
@login_required
def predict_best_time_api():
    """
    AJAX: predict best posting time.
    Body: { "caption": "...", "platform": "instagram" }
    Returns: { "top_slots": [...], "best_datetime": "..." }
    """
    data = request.get_json(silent=True) or {}
    caption  = data.get('caption', '')
    platform = data.get('platform', 'instagram')
    try:
        result = predict_best_times(caption, platform, top_n=3)
        result['success'] = True
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============ ANALYTICS DASHBOARD ROUTE ============

@app.route('/analytics')
@login_required
def analytics():
    from models import ScheduledPost
    data = ScheduledPost.get_analytics(session['user_id'])
    # Debug: print to console so we can verify
    print(f"[Analytics] user_id={session['user_id']} total={data['total']} posted={data['posted']} pending={data['pending']}")
    return render_template('analytics.html', analytics=data, current_user_id=session['user_id'])

@app.route('/analytics-data')
@login_required
def analytics_data():
    """JSON endpoint for live chart refresh."""
    from models import ScheduledPost
    data = ScheduledPost.get_analytics(session['user_id'])
    return jsonify(data)


# ============ AI CAPTION GENERATOR ROUTES ============

@app.route('/generate-captions', methods=['POST'])
@login_required
def generate_captions_api():
    """
    AJAX endpoint — returns AI-generated captions for an image.
    Accepts JSON:
      { "image_path": "...", "user_hint": "...", "styles": [...] }
      OR
      { "image_b64": "data:image/jpeg;base64,...", "user_hint": "...", "styles": [...] }
    Returns JSON: { "success": true, "captions": {...}, "image_description": "..." }
    """
    data = request.get_json(silent=True) or {}
    image_path = data.get('image_path', '').strip()
    image_b64  = data.get('image_b64', '').strip()
    user_hint  = data.get('user_hint', '').strip()
    styles     = data.get('styles', None)

    # Validate requested styles
    valid_styles = list(CAPTION_STYLES.keys())
    if styles:
        styles = [s for s in styles if s in valid_styles]
    if not styles:
        styles = valid_styles

    # If base64 image sent (upload mode), save to a temp file
    tmp_path = None
    if image_b64 and image_b64.startswith('data:image'):
        try:
            import base64 as _b64
            header, b64data = image_b64.split(',', 1)
            img_bytes = _b64.b64decode(b64data)
            tmp_path = os.path.join('uploaded_images', f'_caption_tmp_{session["user_id"]}.jpg')
            os.makedirs('uploaded_images', exist_ok=True)
            with open(tmp_path, 'wb') as f:
                f.write(img_bytes)
            image_path = tmp_path
        except Exception as e:
            return jsonify({"success": False, "error": f"Could not decode image: {e}"}), 400

    try:
        # If we have an image on disk, use Vision API; otherwise text-only
        if image_path and os.path.exists(image_path):
            result = generate_captions(image_path, user_hint=user_hint, styles=styles)
        elif user_hint:
            result = generate_captions_from_text(user_hint, styles=styles)
        else:
            return jsonify({"success": False, "error": "Provide image_path, image_b64, or user_hint"}), 400
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    status_code = 200 if result.get('success') else 500
    if not result.get('success') and '429' in str(result.get('error', '')):
        result['error'] = 'Gemini API quota exceeded. Please wait a minute and try again, or create a new API key at https://aistudio.google.com/app/apikey'
        status_code = 429
    return jsonify(result), status_code


@app.route('/caption-styles', methods=['GET'])
@login_required
def caption_styles_api():
    """Return available caption styles (for dynamic UI rendering)."""
    styles = {k: {kk: vv for kk, vv in v.items() if kk != 'prompt_hint'}
              for k, v in CAPTION_STYLES.items()}
    return jsonify(styles)


if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('generated_images', exist_ok=True)
    os.makedirs('uploaded_images', exist_ok=True)
    
    # Start scheduler
    start_scheduler()
    
    # Run Flask app with SSL so Web Speech API (voice input) works
    # ssl_context='adhoc' generates a self-signed cert automatically
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context='adhoc')