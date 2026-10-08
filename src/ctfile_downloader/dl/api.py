from .worker import DownloadWorker
from ..models import File, Task, db

from flask import Blueprint, jsonify, request

bp = Blueprint("dl", __name__)
_workers = {}

@bp.post("/api/tasks")
def create_task():
    d = request.get_json(force=True, silent=True) or {}
    urls = d.get("urls", [])
    if not urls:
        return jsonify({"error": "no urls"}), 400
    task = Task(parallel=d.get("parallel", 4))
    db.session.add(task)
    db.session.flush()
    for u in urls:
        db.session.add(File(task_id=task.id, url=u, name=u.split("/")[-1]))
    db.session.commit()
    # start worker thread
    import threading
    threading.Thread(target=_run_task, args=(task.id,), daemon=True).start()
    return jsonify({"task_id": task.id, "status": "queued"})

def _run_task(task_id):
    """Resolve files, download them one by one, and record each outcome.

    `db.session.get` is the SQLAlchemy 2.x accessor; `Query.get` is deprecated and
    emits a LegacyAPIWarning on every call.
    """
    import asyncio
    task = db.session.get(Task, task_id)
    if task is None:
        return
    task.status = "running"
    db.session.commit()
    files = File.query.filter_by(task_id=task_id).all()
    worker = DownloadWorker()
    for f in files:
        f.status = "downloading"
        db.session.commit()
        try:
            asyncio.run(worker.download(f.url, f.name))
            f.status = "done"
        except Exception:
            f.retries += 1
            f.status = "failed" if f.retries >= 3 else "paused"
        db.session.commit()
    task.status = "done"
    db.session.commit()

@bp.get("/api/tasks")
def list_tasks():
    return jsonify({"tasks": [{"id": t.id, "status": t.status, "parallel": t.parallel,
                               "files": [{"name": f.name, "status": f.status,
                                          "progress": f.downloaded / f.size if f.size else 0}
                                         for f in File.query.filter_by(task_id=t.id).all()]}
                              for t in Task.query.order_by(Task.id.desc()).limit(20).all()]})

@bp.post("/api/tasks/<int:tid>/pause")
def pause(tid):
    t = db.get_or_404(Task, tid)
    t.status = "paused"
    db.session.commit()
    return jsonify({"status": "paused"})

@bp.post("/api/tasks/<int:tid>/resume")
def resume(tid):
    t = db.get_or_404(Task, tid)
    t.status = "running"
    db.session.commit()
    return jsonify({"status": "running"})
