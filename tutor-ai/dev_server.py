"""Local-only dev server: serves the static frontend + the API together,
approximating how Vercel serves both from one deployment. Not used in
production — Vercel's own static hosting + vercel.json rewrites handle this
there instead.
"""

from pathlib import Path

from flask import send_from_directory

from app import app

ROOT = Path(__file__).resolve().parent


@app.route("/")
def _dev_index():
    return send_from_directory(ROOT, "index.html")


@app.route("/course.html")
def _dev_course():
    return send_from_directory(ROOT, "course.html")


@app.route("/courses/<int:course_id>")
def _dev_course_pretty(course_id):
    return send_from_directory(ROOT, "course.html")


@app.route("/static/<path:filename>")
def _dev_static(filename):
    return send_from_directory(ROOT / "static", filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
