"""
SkinPilot - Skincare Habit Tracker
Flask backend with Supabase PostgreSQL database
"""

import os
from supabase import create_client, Client
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
import logging

logging.basicConfig(level=logging.INFO)

# --- Config ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "skinpilot-dev-secret-key-change-in-prod")
app.config["UPLOAD_FOLDER"] = Path(__file__).parent / "uploads"
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["UPLOAD_FOLDER"].mkdir(exist_ok=True)

# Supabase Client Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jhiqtczvlkeggwuigava.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_RgSCA3zmTiGD6gXKWP659w_KvGrGXlY")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logging.error(f"Failed to initialize Supabase: {e}")
    supabase = None


def init_db():
    """Initialize database tables - run once manually via Supabase SQL editor"""
    if not supabase:
        logging.error("Supabase not initialized")
        return
    
    try:
        # These tables should be created in Supabase SQL Editor
        logging.info("Database tables should be created manually in Supabase SQL Editor")
        logging.info("Use the SQL from SUPABASE_SETUP.sql file")
    except Exception as e:
        logging.error(f"Database initialization error: {e}")


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
        try:
            # Insert user into Supabase
            response = supabase.table("users").insert({
                "username": username,
                "email": email,
                "password": generate_password_hash(password)
            }).execute()
            
            # Get the inserted user's ID
            user_id = response.data[0]["id"]
            session["user_id"] = user_id
            session["username"] = username
            flash("Account created! Welcome to SkinPilot.", "success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            logging.error(f"Signup error: {e}")
            flash("Username or email already exists.", "error")
            return render_template("signup.html")
    return render_template("signup.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("signin.html")
        try:
            response = supabase.table("users").select("id, username, password").eq("email", email).execute()
            if response.data:
                user = response.data[0]
                if check_password_hash(user["password"], password):
                    session["user_id"] = user["id"]
                    session["username"] = user["username"]
                    flash("Welcome back!", "success")
                    return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "error")
        except Exception as e:
            logging.error(f"Signin error: {e}")
            flash("An error occurred. Please try again.", "error")
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
    if request.method == "POST":
        step_name = request.form.get("step_name", "").strip()
        if step_name:
            try:
                response = supabase.table("routine_steps").select("step_order").eq("user_id", session["user_id"]).order("step_order", desc=True).limit(1).execute()
                order = response.data[0]["step_order"] + 1 if response.data else 1
                supabase.table("routine_steps").insert({"user_id": session["user_id"], "step_name": step_name, "step_order": order}).execute()
                flash("Step added!", "success")
            except Exception as e:
                logging.error(f"Error adding step: {e}")
                flash("Failed to add step.", "error")
    try:
        response = supabase.table("routine_steps").select("id, step_name, step_order").eq("user_id", session["user_id"]).order("step_order").execute()
        steps = response.data if response.data else []
    except Exception as e:
        logging.error(f"Error fetching steps: {e}")
        steps = []
    return render_template("routine.html", steps=steps)


@app.route("/routine/delete/<int:step_id>", methods=["POST"])
@login_required
def delete_routine_step(step_id):
    try:
        supabase.table("routine_steps").delete().eq("id", step_id).eq("user_id", session["user_id"]).execute()
        flash("Step removed.", "info")
    except Exception as e:
        logging.error(f"Error deleting step: {e}")
        flash("Failed to remove step.", "error")
    return redirect(url_for("routine"))


@app.route("/routine/mark-done", methods=["POST"])
@login_required
def mark_routine_done():
    today = date.today().isoformat()
    try:
        response = supabase.table("daily_completions").select("id").eq("user_id", session["user_id"]).eq("completed_date", today).execute()
        if not response.data:
            supabase.table("daily_completions").insert({"user_id": session["user_id"], "completed_date": today}).execute()
        return jsonify({"success": True, "message": "Routine marked as done for today!"})
    except Exception as e:
        logging.error(f"Error marking done: {e}")
        return jsonify({"success": False, "message": "Error marking routine as done"})


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
            try:
                supabase.table("selfies").insert({"user_id": session["user_id"], "filename": unique}).execute()
            except Exception as e:
                logging.error(f"Error saving selfie record: {e}")
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
    try:
        response = supabase.table("daily_completions").select("completed_date").eq("user_id", session["user_id"]).order("completed_date", desc=True).execute()
        dates = [r["completed_date"] for r in response.data] if response.data else []
    except Exception as e:
        logging.error(f"Error fetching completions: {e}")
        dates = []
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
    if request.method == "POST":
        time_str = request.form.get("reminder_time", "").strip()
        if time_str:
            try:
                supabase.table("reminders").insert({"user_id": session["user_id"], "reminder_time": time_str}).execute()
                flash("Reminder set!", "success")
            except Exception as e:
                logging.error(f"Error setting reminder: {e}")
                flash("Failed to set reminder.", "error")
    try:
        response = supabase.table("reminders").select("id, reminder_time, enabled").eq("user_id", session["user_id"]).order("reminder_time").execute()
        reminders_list = response.data if response.data else []
    except Exception as e:
        logging.error(f"Error fetching reminders: {e}")
        reminders_list = []
    return render_template("reminders.html", reminders=reminders_list)


@app.route("/reminders/delete/<int:reminder_id>", methods=["POST"])
@login_required
def delete_reminder(reminder_id):
    try:
        supabase.table("reminders").delete().eq("id", reminder_id).eq("user_id", session["user_id"]).execute()
        flash("Reminder removed.", "info")
    except Exception as e:
        logging.error(f"Error deleting reminder: {e}")
        flash("Failed to remove reminder.", "error")
    return redirect(url_for("reminders"))


# --- Insights ---
@app.route("/insights")
@login_required
def insights():
    try:
        response = supabase.table("daily_completions").select("completed_date").eq("user_id", session["user_id"]).order("completed_date").execute()
        completed = [r["completed_date"] for r in response.data] if response.data else []
        response = supabase.table("routine_steps").select("id").eq("user_id", session["user_id"]).execute()
        routine_count = len(response.data) if response.data else 0
    except Exception as e:
        logging.error(f"Error fetching insights: {e}")
        completed = []
        routine_count = 0
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
    this_week = sum(1 for d in completed if date.today() - date.fromisoformat(d) <= timedelta(days=7))
    this_month = sum(1 for d in completed if date.today() - date.fromisoformat(d) <= timedelta(days=30))
    return render_template("insights.html", streak=streak_count, total_days=total_days, this_week=this_week, this_month=this_month, routine_steps_count=routine_count, completed_dates=completed)


if __name__ == "__main__":
    if supabase:
        try:
            init_db()
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
    else:
        logging.error("Supabase connection failed!")
    app.run(debug=True, port=5000)
