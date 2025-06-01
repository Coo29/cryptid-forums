import os
import uuid
import re
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy 
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_dance.contrib.discord import make_discord_blueprint, discord
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from datetime import datetime
from markupsafe import escape, Markup

load_dotenv()

app = Flask(__name__)
app.config.from_object('config.Config')
app.config['UPLOAD_FOLDER'] = 'static/uploads'

@app.template_filter('format_post_content')
def format_post_content(content):
    escaped = escape(content)
    tagged = re.sub(r"#(\w+)", r'<a href="/tags/\1" class="tag">#\1</a>', escaped)
    paragraphs = ''.join(f'<p>{line}</p>' for line in tagged.split('\n') if line.strip())
    return Markup(paragraphs)

app.jinja_env.filters['format_post_content'] = format_post_content

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "discord.login"

discord_bp = make_discord_blueprint(
    client_id=os.getenv("DISCORD_CLIENT_ID"),
    client_secret=os.getenv("DISCORD_CLIENT_SECRET"),
    scope=["identify"],
)
app.register_blueprint(discord_bp, url_prefix="/login")

# user discord id start
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(30), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    avatar_hash = db.Column(db.String(128), nullable=True)
    discriminator = db.Column(db.String(4), nullable=True)

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
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='posts')
    deleted = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.relationship('Like', backref='post', lazy='dynamic')

@app.route("/create", methods=["POST"])
@login_required
def create_post():
    content = request.form.get("content")
    images = request.files.getlist("images")

    if not content:
        flash("Post content is required!")
        return redirect(url_for("index"))
    
    post = Post(content=content, user_id=current_user.id)
    db.session.add(post)
    db.session.flush()

    for image in images:
        if image and image.filename:
            filename = secure_filename(f"{uuid.uuid4()}_{image.filename}")
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            db.session.add(PostImage(filename=filename, post_id=post.id))

    db.session.commit()
    return redirect(url_for("index"))

@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    posts = Post.query.filter_by(deleted=False).order_by(Post.timestamp.desc()).all()

    return render_template("post.html", post=post, user=current_user)

class PostImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    post = db.relationship('Post', backref='images')

def format_post_content(content):
    escaped = escape(content)
    tagged = re.sub(r"#(\w+)", r'<a href="/tags/\1" class="tag">#\1</a>', escaped)
    paragraphs = ''.join(f'<p>{line}</p>' for line in tagged.split('\n') if line.strip())
    return paragraphs
# user post setup end

# moderation stuff start
def is_moderator():
    return str(current_user.discord_id) in app.config["MODERATOR_IDS"]

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
    return render_template("moderation.html", posts=deleted_posts, user=current_user)

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
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for("moderation_panel"))
# moderation stuff end

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def index():
    posts = Post.query.filter_by(deleted=False).order_by(Post.timestamp.desc()).all()

    return render_template("index.html", user=current_user, posts=posts, config=app.config)

# login start
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

    user = db.relationship('User')
    post = db.relationship('Post', backref='comments')

@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
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
# voting end

# tag stuff start
def extract_tags(content):
    return re.findall(r"#(\w+)", content)

@app.route('/tags/<tag>')
def show_tagged_posts(tag):
    posts = Post.query.filter(Post.content.ilike(f'%#{tag}%')).all()  
    return render_template('tagged_posts.html', tag=tag, posts=posts)

# tag stuff end


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5001, debug=True)