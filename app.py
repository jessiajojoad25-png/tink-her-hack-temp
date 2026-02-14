"""
SkinPilot - Skincare Habit Tracker
Flask backend with SQLite database
"""

import os
import sqlite3
from datetime import datetime, date, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    send_from_directory,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# --- Config ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "skinpilot-dev-secret-key-change-in-prod")
app.config["UPLOAD_FOLDER"] = Path(__file__).parent / "uploads"
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["UPLOAD_FOLDER"].mkdir(exist_ok=True)

DB_PATH = Path(__file__).parent / "database.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS routine_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            step_name TEXT NOT NULL,
            step_order INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS daily_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            completed_date DATE NOT NULL,
            UNIQUE(user_id, completed_date),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reminder_time TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS selfies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("signin"))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# --- Auth routes ---
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("signin"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template("signup.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("signup.html")
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, generate_password_hash(password)),
            )
            conn.commit()
            session["user_id"] = cur.lastrowid
            session["username"] = username
            flash("Account created! Welcome to SkinPilot.", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "error")
            return render_template("signup.html")
        finally:
            conn.close()
    return render_template("signup.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("signin.html")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        conn.close()
        if row and check_password_hash(row["password"], password):
            session["user_id"] = row["id"]
            session["username"] = row["username"]
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("signin.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("signin"))


# --- Dashboard ---
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=session.get("username", "User"))


# --- Routine ---
@app.route("/routine", methods=["GET", "POST"])
@login_required
def routine():
    conn = get_db()
    cur = conn.cursor()
    if request.method == "POST":
        step_name = request.form.get("step_name", "").strip()
        if step_name:
            cur.execute(
                "SELECT COALESCE(MAX(step_order), 0) + 1 FROM routine_steps WHERE user_id = ?",
                (session["user_id"],),
            )
            order = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO routine_steps (user_id, step_name, step_order) VALUES (?, ?, ?)",
                (session["user_id"], step_name, order),
            )
            conn.commit()
            flash("Step added!", "success")
    cur.execute(
        "SELECT id, step_name, step_order FROM routine_steps WHERE user_id = ? ORDER BY step_order",
        (session["user_id"],),
    )
    steps = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template("routine.html", steps=steps)


@app.route("/routine/delete/<int:step_id>", methods=["POST"])
@login_required
def delete_routine_step(step_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM routine_steps WHERE id = ? AND user_id = ?",
        (step_id, session["user_id"]),
    )
    conn.commit()
    conn.close()
    flash("Step removed.", "info")
    return redirect(url_for("routine"))


@app.route("/routine/mark-done", methods=["POST"])
@login_required
def mark_routine_done():
    today = date.today().isoformat()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO daily_completions (user_id, completed_date) VALUES (?, ?)",
        (session["user_id"], today),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Routine marked as done for today!"})


# --- Selfie Check ---
@app.route("/selfie", methods=["GET", "POST"])
@login_required
def selfie():
    if request.method == "POST" and "photo" in request.files:
        f = request.files["photo"]
        if f.filename and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            unique = f"{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            filepath = app.config["UPLOAD_FOLDER"] / unique
            f.save(str(filepath))
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO selfies (user_id, filename) VALUES (?, ?)",
                (session["user_id"], unique),
            )
            conn.commit()
            conn.close()
            flash("Selfie uploaded! Here's your analysis.", "success")
            return redirect(url_for("selfie_result", filename=unique))
        flash("Please upload a valid image (PNG, JPG, GIF, WebP).", "error")
    return render_template("selfie.html")


@app.route("/selfie/result/<filename>")
@login_required
def selfie_result(filename):
    return render_template("selfie.html", uploaded_filename=filename, show_result=True)


@app.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# --- Streak ---
@app.route("/streak")
@login_required
def streak():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT completed_date FROM daily_completions WHERE user_id = ? ORDER BY completed_date DESC",
        (session["user_id"],),
    )
    dates = [r["completed_date"] for r in cur.fetchall()]
    conn.close()

    streak_count = 0
    today = date.today().isoformat()
    if dates and dates[0] == today:
        streak_count = 1
        for i in range(1, len(dates)):
            prev = (date.today() - timedelta(days=i)).isoformat()
            if dates[i] == prev:
                streak_count += 1
            else:
                break

    return render_template("streak.html", streak=streak_count, completed_dates=dates)


# --- Reminders ---
@app.route("/reminders", methods=["GET", "POST"])
@login_required
def reminders():
    conn = get_db()
    cur = conn.cursor()
    if request.method == "POST":
        time_str = request.form.get("reminder_time", "").strip()
        if time_str:
            cur.execute(
                "INSERT INTO reminders (user_id, reminder_time) VALUES (?, ?)",
                (session["user_id"], time_str),
            )
            conn.commit()
            flash("Reminder set!", "success")
    cur.execute(
        "SELECT id, reminder_time, enabled FROM reminders WHERE user_id = ? ORDER BY reminder_time",
        (session["user_id"],),
    )
    reminders_list = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template("reminders.html", reminders=reminders_list)


@app.route("/reminders/delete/<int:reminder_id>", methods=["POST"])
@login_required
def delete_reminder(reminder_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM reminders WHERE id = ? AND user_id = ?",
        (reminder_id, session["user_id"]),
    )
    conn.commit()
    conn.close()
    flash("Reminder removed.", "info")
    return redirect(url_for("reminders"))


# --- Insights ---
@app.route("/insights")
@login_required
def insights():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT completed_date FROM daily_completions WHERE user_id = ? ORDER BY completed_date",
        (session["user_id"],),
    )
    completed = [r["completed_date"] for r in cur.fetchall()]
    cur.execute(
        "SELECT COUNT(*) FROM routine_steps WHERE user_id = ?", (session["user_id"],)
    )
    routine_count = cur.fetchone()[0]
    conn.close()

    streak_count = 0
    today = date.today().isoformat()
    if completed and completed[-1] == today:
        streak_count = 1
        for i in range(len(completed) - 2, -1, -1):
            expected = (date.today() - timedelta(days=streak_count)).isoformat()
            if completed[i] == expected:
                streak_count += 1
            else:
                break

    total_days = len(completed)
    this_week = sum(
        1
        for d in completed
        if date.today() - date.fromisoformat(d) <= timedelta(days=7)
    )
    this_month = sum(
        1
        for d in completed
        if date.today() - date.fromisoformat(d) <= timedelta(days=30)
    )

    return render_template(
        "insights.html",
        streak=streak_count,
        total_days=total_days,
        this_week=this_week,
        this_month=this_month,
        routine_steps_count=routine_count,
        completed_dates=completed,
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
