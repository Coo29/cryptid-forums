# import start
import os
import uuid
import re
import sqlite3
import requests
import bleach
from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy 
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_dance.contrib.discord import make_discord_blueprint, discord
from flask_migrate import Migrate
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from datetime import datetime
from markupsafe import escape, Markup
from mimetypes import guess_type
from sqlalchemy import event
from sqlalchemy.engine import Engine
# import end

# init junk start
load_dotenv(override=True)
app = Flask(__name__)
app.config.from_object('config.Config')
# init junk end

# upload folder verif start
upload_folder_images = os.path.join(app.root_path, 'static', 'uploads', 'images')
os.makedirs(upload_folder_images, exist_ok=True)

upload_folder_files = os.path.join(app.root_path, 'static', 'uploads', 'files')
os.makedirs(upload_folder_files, exist_ok=True)
# upload folder verif end

# post formatting start
ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'span', 'blockquote', 'pre', 'code']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel', 'target'],
    'span': ['style'],
    'p': ['style'],
    'li': ['style'],
                    }

@app.template_filter('format_post_content')
def format_post_content(content):
    safe_content = bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    tagged = re.sub(r"#(\w+)", r'<a href="/tags/\1" class="tag">#\1</a>', content)
    return Markup(content)

app.jinja_env.filters['format_post_content'] = format_post_content
# post formatting end

# user discord id start
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "discord.login"

discord_bp = make_discord_blueprint(
    client_id=os.getenv("DISCORD_CLIENT_ID"),
    client_secret=os.getenv("DISCORD_CLIENT_SECRET"),
    scope=["identify"],
)

app.register_blueprint(discord_bp, url_prefix="/login")

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(30), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    avatar_hash = db.Column(db.String(128), nullable=True)
    discriminator = db.Column(db.String(4), nullable=True)
    can_post = db.Column(db.Boolean, default=False)

    @property
    def avatar_url(self):
        if self.avatar_hash:
            return f"https://cdn.discordapp.com/avatars/{self.discord_id}/{self.avatar_hash}.png"
        elif self.discriminator:
            default_id = int(self.discriminator) % 5
            return f"https://cdn.discordapp.com/embed/avatars/{default_id}.png"
        else:
            return "https://cdn.discordapp.com/embed/avatars/0.png"
# user discord id end

# user post setup start
UPLOAD_FOLDER_IMAGES = os.path.join(app.root_path, 'uploads', 'images')
UPLOAD_FOLDER_FILES = os.path.join(app.root_path, 'uploads', 'files')

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='posts')
    deleted = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.relationship('Like', backref='post', lazy='dynamic')
    images = db.relationship('PostImage', backref='post', cascade='all, delete-orphan')
    attachments = db.relationship('PostAttachment', backref='post', cascade='all, delete-orphan')
    attachment = db.Column(db.String(225))

@app.route("/create", methods=["POST"])
@login_required
def create_post():
    if not current_user.can_post:
        flash("You are unable to create a post right now.")
        return redirect(url_for("index"))
    title = request.form.get("title", '').strip()
    content = request.form.get("content", '')
    safe_content = bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    files = request.files.getlist('attachment')

    if not title:
        flash("Title is required!")
        return redirect(url_for("index"))

    if not content and not files:
        flash("Post cannot be empty!")
        return redirect(url_for("index"))

    post = Post(title=title, content=safe_content, user_id=current_user.id)
    db.session.add(post)
    db.session.flush()

    for file in files:
        if file and file.filename:
            original_filename = file.filename
            filename = secure_filename(original_filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            mime_type, _ = guess_type(filename)

            if mime_type and mime_type.startswith('image/'):
                save_path = os.path.join(upload_folder_images, unique_filename)
                file.save(save_path)
                image = PostImage(
                    filename=unique_filename,
                    post_id=post.id
                    )
                db.session.add(image)
            else:
                save_path = os.path.join(upload_folder_files, unique_filename)
                file.save(save_path)
                attachment = PostAttachment(
                    filename=unique_filename,
                    original_filename=original_filename,
                    post_id=post.id
                )
                db.session.add(attachment)

    db.session.commit()
    return redirect(url_for("index"))

@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = Post.query.get_or_404(post_id)

    posts = Post.query.filter_by(deleted=False).order_by(Post.timestamp.desc()).all()

    return render_template("post.html", post=post, user=current_user)

@app.route("/uploads/files/<path:filename>")
def uploaded_file_file(filename):
    attachment = PostAttachment.query.filter_by(filename=filename).first()
    if not attachment:
        abort(404)
    return send_from_directory(
        'static/uploads/files',
        filename,
        as_attachment=True,
        download_name=attachment.original_filename
        )

@app.route("/uploads/images/<path:filename>")
def uploaded_file_image(filename):
    return send_from_directory('static/uploads/images', filename)

class PostImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class PostAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String, nullable=False)
    original_filename = db.Column(db.String, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

def format_post_content(content):
    escaped = escape(content)
    tagged = re.sub(r"#(\w+)", r'<a href="/tags/\1" class="tag">#\1</a>', escaped)
    paragraphs = ''.join(f'<p>{line}</p>' for line in tagged.split('\n') if line.strip())
    return paragraphs
# user post setup end

# moderation stuff start
def is_moderator():
    is_mod = (
        current_user.is_authenticated and
        str(current_user.discord_id) in app.config.get("MODERATOR_IDS", [])
    )
    return is_mod

@app.route("/delete_post/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    if not is_moderator():
        flash("You don't have permisison to do that.")
        return redirect(url_for("index"))
    
    post = Post.query.get_or_404(post_id)
    post.deleted = True
    db.session.commit()
    flash("Post deleted.")
    return redirect(url_for("index"))

@app.route("/moderation")
@login_required
def moderation_panel():
    if not is_moderator():
        abort(403)
    
    deleted_posts = Post.query.filter_by(deleted=True).all()
    users = User.query.all()
    return render_template("moderation.html", posts=deleted_posts, users=users, user=current_user)

@app.route("/restore_post/<int:post_id>", methods=["POST"])
@login_required
def restore_post(post_id):
    if not is_moderator():
        abort(403)
    
    post = Post.query.get_or_404(post_id)
    post.deleted = False
    db.session.commit()
    flash("Post restored.")
    return redirect(url_for("moderation_panel"))

@app.route("/delete/<int:post_id>", methods=["POST"])
@login_required
def permanent_delete_post(post_id):
    if not is_moderator():
        abort(403)
    
    post = Post.query.get_or_404(post_id)
    
    for image in post.images:
        image_path = os.path.join(upload_folder_images, image.filename)
        if os.path.exists(image_path):
            os.remove(image_path)
        db.session.delete(image)

    for attachment in post.attachments:
        file_path = os.path.join(upload_folder_files, attachment.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(attachment)

    for comment in post.comments:
        db.session.delete(comment)

    db.session.delete(post)
    db.session.commit()

    flash("Post and media permanently deleted.")
    return redirect(url_for("moderation_panel"))

@app.route("/toggle_post_permission/<int:user_id>", methods=["POST"])
@login_required
def toggle_post_permission(user_id):
    if not is_moderator():
        abort(403)
    user = User.query.get_or_404(user_id)
    user.can_post = not user.can_post
    db.session.commit()
    flash(f"{'Disabled' if not user.can_post else 'Allowed'} {user.username} posting.")
    return redirect(url_for("moderation_panel"))

@app.context_processor
def inject_globals():
    return dict(is_moderator=is_moderator)

@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    if not is_moderator():
        abort(403)
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    flash("Comment Deleted")
    return redirect(url_for("view_post", post_id=post_id))
# moderation stuff end

# login start
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    sort = request.args.get("sort", "newest")

    if sort == "newest":
        order = Post.timestamp.desc()
    elif sort == "oldest":
        order = Post.timestamp.asc()
    elif sort == "most_likes":
        order = db.desc(db.func.count(Like.id))
    elif sort == "most_comments":
        order = db.desc(db.func.count(Comment.id))
    else:
        order = Post.timestamp.desc()

    query = Post.query.filter_by(deleted=False)

    if sort in ("most_likes", "most_comments"):
        if sort == "most_likes":
            query = query.outerjoin(Like).group_by(Post.id)
        else:
            query = query.outerjoin(Comment).group_by(Post.id)

    posts = query.order_by(order).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "index.html",
        user=current_user,
        posts=posts.items,
        pagination=posts,
        config=app.config,
        page=page,
        per_page=per_page,
        sort=sort
    )

@app.route("/login")
def login():
    if not discord.authorized:
        return redirect(url_for("discord.login"))

    resp = discord.get("/api/users/@me")
    assert resp.ok
    discord_info = resp.json()
    discord_id = discord_info["id"]
    username = discord_info["username"]
    avatar_hash = discord_info.get("avatar")
    discriminator = discord_info.get("discriminator")

    user = User.query.filter_by(discord_id=discord_id).first()
    if not user:
        user = User(
            discord_id=discord_id,
            username=username,
            avatar_hash=avatar_hash,
            discriminator=discriminator,
            )
        
        db.session.add(user)
    
    else:
        user.avatar_hash = avatar_hash
        user.username = username
        user.discriminator = discriminator

    db.session.commit()

    login_user(user)
    return redirect(url_for("index"))
# login end

# logout start
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))
# logout end

# comment start
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    likes = db.relationship('CommentLike', backref='comment', lazy='dynamic')
    user = db.relationship('User')
    post = db.relationship('Post', backref='comments')

@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    if not current_user.can_post:
        flash("You are unable to comment right now.")
        return redirect(url_for("view_post", post_id=post_id))
    content = request.form.get("comment")
    if not content:
        flash("Comment cannot be empty.")
        return redirect(url_for("view_post", post_id=post_id))
    
    comment = Comment(content=content, user_id=current_user.id, post_id=post_id)
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for("view_post", post_id=post_id))
# comment end

# voting start
class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='unique_like'),)

@app.route("/post/<int:post_id>/like", methods=["POST"])
@login_required
def  toggle_like(post_id):
    existing_like = Like.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    if existing_like:
        db.session.delete(existing_like)
    else:
        like = Like(post_id=post_id, user_id=current_user.id)
        db.session.add(like)
    db.session.commit()
    return redirect(url_for("view_post", post_id=post_id))

class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('comment_id', 'user_id', name='unique_comment_like'),)

    @app.route("/comment/<int:comment_id>/like", methods=["POST"])
    @login_required
    def toggle_comment_like(comment_id):
        comment = Comment.query.get_or_404(comment_id)
        existing_like = CommentLike.query.filter_by(comment_id=comment_id, user_id=current_user.id).first()
        if existing_like:
            db.session.delete(existing_like)
        else:
            like = CommentLike(comment_id=comment_id, user_id=current_user.id)
            db.session.add(like)
        db.session.commit()
        return redirect(url_for("view_post", post_id=comment.post_id))

# voting end

# tag stuff start
def extract_tags(content):
    return re.findall(r"#(\w+)", content)

@app.route('/tags/<tag>')
def show_tagged_posts(tag):
    posts = Post.query.filter(Post.content.ilike(f'%#{tag}%')).all()  
    return render_template('tagged_posts.html', tag=tag, posts=posts)
# tag stuff end

# Discord Bot Testing Start
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

@app.route("/bug_report", methods=["POST"])
@login_required
def bug_report():
    report = request.form.get("report")
    if not report:
        flash("Report cannot be empty.")
        return redirect(url_for("index"))
    payload = {
        "content": f"Bug Report from {current_user.username} ({current_user.discord_id}):\n{report}",
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        flash("Bug report sent successfully!")
    except Exception as e:
        flash(f"Failed to send bug report.")
    return redirect(url_for("index"))
# Discord Bot Testing End

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=80, debug=True)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()