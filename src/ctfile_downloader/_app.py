"""Web UI for ctfile-downloader: queue tasks, watch per-file progress.

`template_folder` is resolved by Flask against `app.root_path`, which is this
package directory (web/); the templates live in the project root one level up.
The path below is absolute and derived from this module's own file so the
lookup does not depend on the process working directory.
"""

import os

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from . import paths
from .dl.api import bp
from .models import File, Task, db

APP_NAME = "⬇ ctfile-downloader"
MAX_PARALLEL = 16


def build_app():
    """Build the application: configuration, database, then routes."""
    app = Flask(
        __name__, template_folder=str(paths.TEMPLATES_DIR), instance_path=str(paths.INSTANCE_DIR)
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(paths.INSTANCE_DIR / "ctfile.db")
    db.init_app(app)
    with app.app_context():
        paths.ensure_runtime_dirs()
        db.create_all()
    app.register_blueprint(bp)

    def _files(task_id):
        return File.query.filter_by(task_id=task_id).order_by(File.id).all()

    def _progress(f):
        """Fraction of a file already on disk, 0.0 when the size is still unknown."""
        if not f.size:
            return 0.0
        return min(1.0, float(f.downloaded or 0) / float(f.size))

    def _task_rows(limit=20):
        rows = []
        for t in Task.query.order_by(Task.id.desc()).limit(limit).all():
            files = _files(t.id)
            rows.append(
                {
                    "t": t,
                    "files": files,
                    "done": sum(1 for f in files if f.status == "done"),
                    "failed": sum(1 for f in files if f.status == "failed"),
                    "got": sum(f.downloaded or 0 for f in files),
                    "want": sum(f.size or 0 for f in files),
                }
            )
        return rows

    @app.template_filter("human")
    def human(n):
        """Format a byte count (or a millisecond count) with a short unit suffix."""
        try:
            n = float(n or 0)
        except (TypeError, ValueError):
            return str(n)
        for unit in ("B", "kB", "MB", "GB", "TB"):
            if n < 1024 or unit == "TB":
                return ("%d %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit))
            n /= 1024.0

    def _page_context(**extra):
        """Context every page needs, plus a default `form` for the queue form.

        `index.html` renders the queue form on a plain GET, when no submission has
        been attempted yet, so `form` must always be defined -- an Undefined there
        is a 500 on the landing page.
        """
        ctx = {
            "app_name": APP_NAME,
            "form": extra.pop("form", {}),
            "task_count": Task.query.count(),
            "file_count": File.query.count(),
            "done_count": File.query.filter_by(status="done").count(),
            "max_parallel": MAX_PARALLEL,
        }
        ctx.update(extra)
        return ctx

    @app.get("/")
    def index():
        return render_template(
            "index.html", tasks=_task_rows(), routes=_app_routes(), **_page_context()
        )

    @app.post("/tasks")
    def create_task_form():
        """HTML twin of POST /api/tasks: same rows, redirect instead of JSON."""
        raw = request.form.get("urls", "")
        urls = [u.strip() for u in raw.replace(",", "\n").splitlines() if u.strip()]
        parallel_raw = (request.form.get("parallel") or "4").strip()
        parallel = int(parallel_raw) if parallel_raw.isdigit() else 0
        errors = []
        if not urls:
            errors.append("paste at least one share URL")
        if not 1 <= parallel <= MAX_PARALLEL:
            errors.append("parallel must be between 1 and %d" % MAX_PARALLEL)
        if errors:
            for msg in errors:
                flash(msg, "error")
            return render_template(
                "index.html",
                tasks=_task_rows(),
                form={"urls": raw, "parallel": parallel_raw},
                routes=_app_routes(),
                **_page_context(),
            ), 400
        task = Task(parallel=parallel, status="queued")
        db.session.add(task)
        db.session.flush()
        for u in urls:
            db.session.add(
                File(task_id=task.id, url=u, name=u.rstrip("/").split("/")[-1] or "download")
            )
        db.session.commit()
        flash("queued %d file(s) in task %d" % (len(urls), task.id), "success")
        return redirect(url_for("task_detail", tid=task.id))

    @app.get("/tasks/<int:tid>")
    def task_detail(tid):
        t = db.session.get(Task, tid)
        if t is None:
            return render_template("404.html", missing="task %d" % tid, **_page_context()), 404
        files = _files(t.id)
        return render_template(
            "task.html",
            task=t,
            files=files,
            done=sum(1 for f in files if f.status == "done"),
            got=sum(f.downloaded or 0 for f in files),
            want=sum(f.size or 0 for f in files),
            progress=_progress,
            **_page_context(),
        )

    @app.post("/tasks/<int:tid>/status/<state>")
    def set_status(tid, state):
        """Pause or resume a whole task from the UI (the API has the JSON twin)."""
        t = db.session.get(Task, tid)
        if t is None:
            flash("task %d is gone" % tid, "error")
            return redirect(url_for("index"))
        if state not in ("paused", "running"):
            flash("unknown state %s" % state, "error")
        else:
            t.status = state
            db.session.commit()
            flash("task %d is now %s" % (t.id, state), "success")
        return redirect(url_for("task_detail", tid=tid))

    @app.post("/tasks/<int:tid>/delete")
    def delete_task(tid):
        t = db.session.get(Task, tid)
        if t is None:
            flash("task %d is gone" % tid, "error")
            return redirect(url_for("index"))
        File.query.filter_by(task_id=t.id).delete()
        db.session.delete(t)
        db.session.commit()
        flash("task %d removed" % tid, "success")
        return redirect(url_for("index"))

    @app.post("/tasks/<int:tid>/files/<int:fid>/retry")
    def retry_file(tid, fid):
        f = db.session.get(File, fid)
        if f is None or f.task_id != tid:
            flash("file %d is gone" % fid, "error")
        else:
            f.status = "queued"
            f.retries = 0
            db.session.commit()
            flash("requeued %s" % f.name, "success")
        return redirect(url_for("task_detail", tid=tid))

    @app.get("/api/health")
    def api_health():
        return jsonify(
            {
                "status": "ok",
                "tasks": Task.query.count(),
                "files": File.query.count(),
                "done": File.query.filter_by(status="done").count(),
                "failed": File.query.filter_by(status="failed").count(),
                "bytes": sum(f.downloaded or 0 for f in File.query.all()),
            }
        )

    def _app_routes():
        rows = []
        for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
            methods = sorted(m for m in (rule.methods or set()) if m in ("GET", "POST"))
            rows.append(
                {"rule": str(rule), "endpoint": rule.endpoint, "methods": ", ".join(methods)}
            )
        return rows

    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))

    return app


app = build_app()
