from flask_sqlalchemy import SQLAlchemy

from .clock import utcnow

db = SQLAlchemy()


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(16), default="queued")  # queued|running|paused|done|failed
    parallel = db.Column(db.Integer, default=4)
    created_at = db.Column(db.DateTime, default=utcnow)


class File(db.Model):
    __tablename__ = "files"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"))
    url = db.Column(db.String(512), default="")
    name = db.Column(db.String(256), default="")
    size = db.Column(db.Integer, default=0)
    downloaded = db.Column(db.Integer, default=0)
    status = db.Column(db.String(16), default="queued")  # queued|downloading|done|paused|failed
    retries = db.Column(db.Integer, default=0)
