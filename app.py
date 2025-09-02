import os
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from huggingface_ai import generate_flashcards
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

# ---- DB setup ----
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
dbname = os.getenv("DB_NAME")
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
db = SQLAlchemy(app)


# ---- Login manager ----
login_manager = LoginManager()
login_manager.login_view = "index"  # redirect to "/" if unauthenticated
login_manager.init_app(app)

# Return JSON for AJAX when unauthorized (prevents HTML being parsed as JSON)
@login_manager.unauthorized_handler
def unauthorized():
    if request.is_json or request.headers.get("Content-Type") == "application/json" or request.path == "/generate":
        return jsonify({"error": "Login required."}), 401
    flash("Please log in to continue.", "danger")
    return redirect(url_for("index"))

# ---- Paystack ----
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_URL = "https://api.paystack.co/transaction/initialize"
if not PAYSTACK_SECRET_KEY:
    raise RuntimeError("⚠️ Missing PAYSTACK_SECRET_KEY in .env")

# ---------------- Models ----------------
class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255))
    answer = db.Column(db.String(255))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    prompts_used = db.Column(db.Integer, default=0)
    subscribed = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- Routes ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    email = request.form["email"]
    password = request.form["password"]

    if User.query.filter_by(email=email).first():
        flash("Email already registered!", "danger")
        return redirect(url_for("index"))

    new_user = User(
        email=email,
        password=generate_password_hash(password, method="pbkdf2:sha256")
    )
    db.session.add(new_user)
    db.session.commit()

    flash("Registration successful! Please log in.", "success")
    return redirect(url_for("index"))

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        flash("Invalid credentials", "danger")
        return redirect(url_for("index"))

    login_user(user)
    flash("Logged in successfully!", "success")
    return redirect(url_for("index"))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("index"))

@app.route("/generate", methods=["POST"])
@login_required
def generate():
    if not current_user.subscribed and current_user.prompts_used >= 5:
        return jsonify({"error": "Limit reached. Please subscribe for 1 month at Ksh 299."}), 402

    text = request.json.get("text")
    mode = request.json.get("mode", "flashcards")

    if not text:
        return jsonify({"error": "No input text provided."}), 400

    if mode == "flashcards":
        flashcards = generate_flashcards(text)
        for q, a in flashcards:
            db.session.add(Flashcard(question=q, answer=a))
        current_user.prompts_used += 1
        db.session.commit()
        return jsonify({"flashcards": flashcards, "remaining": 5 - current_user.prompts_used})

    elif mode == "quiz":
        # Placeholder quiz until you wire a real generator
        quiz = [
            {
                "question": "What is the boiling point of water?",
                "options": ["90°C", "95°C", "100°C", "110°C"],
                "answer": "100°C"
            },
            {
                "question": "What percentage of the human body is water?",
                "options": ["50%", "60%", "70%", "80%"],
                "answer": "70%"
            }
        ]
        current_user.prompts_used += 1
        db.session.commit()
        return jsonify({"quiz": quiz, "remaining": 5 - current_user.prompts_used})

    else:
        return jsonify({"error": "Invalid mode"}), 400
    
@app.route("/subscribe", methods=["POST"])
@login_required
def subscribe():
    print("USING PAYSTACK KEY:", PAYSTACK_SECRET_KEY[:8] + "...")

    payload = {
        "email": current_user.email,
        "amount": 29900,  # Ksh 299 → minor units
        "currency": "KES",  # ✅ use "KES" instead of "KSH"
        "callback_url": "http://127.0.0.1:5000/verify"
    }

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(PAYSTACK_URL, json=payload, headers=headers, timeout=10)
        res_data = response.json()
        print("PAYSTACK RESPONSE:", res_data)  # 👈 debug log
    except Exception as e:
        return jsonify({"error": f"Failed to connect to Paystack: {str(e)}"}), 500

    # ✅ Handle Paystack errors gracefully
    if not res_data.get("status"):
        error_message = res_data.get("message", "Payment failed.")
        if "No active channel" in error_message:
            flash("Payment temporarily unavailable. Please try again later.", "warning")
        else:
            flash(f"Paystack error: {error_message}", "danger")
        return redirect(url_for("index"))

    # ✅ Success: redirect to authorization URL
    if res_data.get("data") and res_data["data"].get("authorization_url"):
        return redirect(res_data["data"]["authorization_url"])

    flash("Unexpected Paystack response. Please try again.", "danger")
    return redirect(url_for("index"))


@app.route("/verify")
@login_required
def verify():
    reference = request.args.get("reference")
    if not reference:
        flash("Missing transaction reference.", "danger")
        return redirect(url_for("index"))

    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}

    try:
        response = requests.get(verify_url, headers=headers, timeout=10)
        res_data = response.json()
    except Exception as e:
        flash(f"Failed to connect to Paystack: {str(e)}", "danger")
        return redirect(url_for("index"))

    if res_data.get("status") and res_data["data"]["status"] == "success":
        current_user.subscribed = True
        db.session.commit()
        flash("Subscription successful! 🎉", "success")
    else:
        flash("Payment verification failed. Please try again.", "danger")

    return redirect(url_for("index"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()   # ✅ creates tables (User, Flashcard, etc.)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)


