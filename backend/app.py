"""
Task Management API
A full-stack backend built with Flask, Flask-SQLAlchemy and Flask-JWT-Extended.

Features:
- User registration & login (JWT authentication)
- Task CRUD (create, read, update, delete)
- Filtering tasks by status
- SQLite database (dev)
"""

import os
from datetime import datetime, timedelta

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'tasks.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)  # allow the frontend (different origin/port) to call this API


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship("Task", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "username": self.username}


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="pending")  # pending | in_progress | done
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "user_id": self.user_id,
        }


VALID_STATUSES = {"pending", "in_progress", "done"}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already taken"}), 409

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"message": "user created", "access_token": token, "user": user.to_dict()}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid username or password"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": user.to_dict()}), 200


# ---------------------------------------------------------------------------
# Task endpoints (all require a valid JWT)
# ---------------------------------------------------------------------------
def current_user():
    user_id = get_jwt_identity()
    return User.query.get(int(user_id))


@app.route("/api/tasks", methods=["GET"])
@jwt_required()
def list_tasks():
    user = current_user()
    query = Task.query.filter_by(user_id=user.id)

    status = request.args.get("status")
    if status:
        if status not in VALID_STATUSES:
            return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400
        query = query.filter_by(status=status)

    search = request.args.get("q")
    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))

    tasks = query.order_by(Task.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tasks]), 200


@app.route("/api/tasks/<int:task_id>", methods=["GET"])
@jwt_required()
def get_task(task_id):
    user = current_user()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()
    if not task:
        return jsonify({"error": "task not found"}), 404
    return jsonify(task.to_dict()), 200


@app.route("/api/tasks", methods=["POST"])
@jwt_required()
def create_task():
    user = current_user()
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    status = data.get("status", "pending")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400

    task = Task(
        title=title,
        description=data.get("description", ""),
        status=status,
        user_id=user.id,
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@jwt_required()
def update_task(task_id):
    user = current_user()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()
    if not task:
        return jsonify({"error": "task not found"}), 404

    data = request.get_json(silent=True) or {}

    if "title" in data:
        title = data["title"].strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        task.title = title

    if "description" in data:
        task.description = data["description"]

    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400
        task.status = data["status"]

    db.session.commit()
    return jsonify(task.to_dict()), 200


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(task_id):
    user = current_user()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()
    if not task:
        return jsonify({"error": "task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "task deleted"}), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def create_tables():
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    create_tables()
    app.run(debug=True, port=5000)
