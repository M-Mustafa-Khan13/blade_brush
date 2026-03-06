import html
import json
import logging
import os
import shutil
import uuid
import re
from datetime import date as date_type, datetime, timezone

from flask import (
    Flask, abort, jsonify, flash, redirect,
    render_template, request, url_for,
)
from flask_login import (
    LoginManager, current_user, login_required, login_user, logout_user,
)
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# App + configuration
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = "blade-and-brush-secret-key-change-in-production"

_FLASK_APP_DIR = os.path.dirname(os.path.abspath(__file__))

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + os.path.join(_FLASK_APP_DIR, "barbers.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB Werkzeug hard limit

# ---------------------------------------------------------------------------
# SQLAlchemy init
# ---------------------------------------------------------------------------

from models import (  # noqa: E402
    ALL_BOOKING_SLOTS,
    VALID_DAYS,
    VALID_LOCATIONS,
    VALID_SLOTS,
    Barber,
    BarberAvailability,
    BarberSpecialty,
    Booking,
    Customer,
    LoyaltyReward,
    LoyaltyTransaction,
    Review,
    Service,
    db,
)

db.init_app(app)

# ---------------------------------------------------------------------------
# Flask-Login
# ---------------------------------------------------------------------------

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access that page."
login_manager.login_message_category = "error"


@login_manager.user_loader
def load_user(user_id: str):
    return Customer.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Reviews database (raw SQLite — kept separate from SQLAlchemy)
# ---------------------------------------------------------------------------

from database import DB_PATH, get_reviews, init_db  # noqa: E402

init_db()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
app.logger.info("[APP] Reviews DB  -> %s", DB_PATH)
app.logger.info("[APP] Barbers DB  -> %s", os.path.join(_FLASK_APP_DIR, "barbers.db"))

# ---------------------------------------------------------------------------
# Upload configuration
# ---------------------------------------------------------------------------

_UPLOAD_BASE    = os.path.join(app.static_folder, "uploads")
UPLOAD_PROFILE  = os.path.join(_UPLOAD_BASE, "profile")
UPLOAD_ID       = os.path.join(_UPLOAD_BASE, "id")
UPLOAD_LICENSE  = os.path.join(_UPLOAD_BASE, "license")
UPLOAD_BARBER   = os.path.join(_UPLOAD_BASE, "barber_applications")

for _d in (UPLOAD_PROFILE, UPLOAD_ID, UPLOAD_LICENSE, UPLOAD_BARBER):
    os.makedirs(_d, exist_ok=True)

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "webp"}
ALLOWED_DOC_EXT   = {"png", "jpg", "jpeg", "webp", "pdf"}

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

_DEFAULT_SERVICES = [
    {
        "name": "Fade",
        "description": (
            "Our signature fade blends seamlessly from skin to your desired length. "
            "Using precision clippers and expert technique, we craft low, mid, or high "
            "fades tailored to your head shape and personal style."
        ),
        "duration_minutes": 40, "price": 40.00,
        "loyalty_points_awarded": 15,
        "media_type": "video", "media_filename": "fade.mp4",
    },
    {
        "name": "Taper",
        "description": (
            "A classic taper gradually reduces hair length toward the neckline and ears, "
            "creating a clean, professional silhouette. Ideal for business or casual wear."
        ),
        "duration_minutes": 35, "price": 35.00,
        "loyalty_points_awarded": 12,
        "media_type": "video", "media_filename": "taper.mp4",
    },
    {
        "name": "Beard Styling",
        "description": (
            "Expert beard shaping designed to frame your face. Includes a hot towel "
            "treatment, precision trimming with straight-razor edge definition, and "
            "premium beard oil finish that lasts all day."
        ),
        "duration_minutes": 25, "price": 28.00,
        "loyalty_points_awarded": 10,
        "media_type": "video", "media_filename": "beard_styling.mp4",
    },
    {
        "name": "Scissor Cut",
        "description": (
            "A hand-crafted scissor cut for those who want texture, movement, and "
            "precise layering. Finished with a blow-dry and styling product tailored "
            "to your hair type."
        ),
        "duration_minutes": 45, "price": 45.00,
        "loyalty_points_awarded": 15,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Hair Coloring",
        "description": (
            "From subtle highlights to bold transformations, our color services use "
            "professional-grade products that nourish while they color. Includes a "
            "consultation and aftercare advice."
        ),
        "duration_minutes": 90, "price": 75.00,
        "loyalty_points_awarded": 25,
        "media_type": "video", "media_filename": "hair_coloring.mp4",
    },
    {
        "name": "Kids Cut",
        "description": (
            "A gentle, fun haircut experience for children up to 12. Our patient barbers "
            "create a relaxed environment so every kid leaves with a smile and a sharp "
            "new look."
        ),
        "duration_minutes": 25, "price": 22.00,
        "loyalty_points_awarded": 8,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Line-up",
        "description": (
            "Crisp straight-razor edge work along the hairline, temples, and neckline. "
            "The perfect finishing touch for any fresh cut or standalone cleanup between "
            "appointments."
        ),
        "duration_minutes": 20, "price": 18.00,
        "loyalty_points_awarded": 7,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Facial Treatment",
        "description": (
            "A deep-cleansing facial using premium skincare products. Includes steam, "
            "extraction, mask application, and a hydrating serum finish that leaves "
            "skin refreshed and glowing."
        ),
        "duration_minutes": 50, "price": 55.00,
        "loyalty_points_awarded": 20,
        "media_type": "video", "media_filename": "facial_treatment.mp4",
    },
    {
        "name": "Scalp Treatment",
        "description": (
            "A therapeutic scalp massage combined with a nourishing treatment oil "
            "to stimulate circulation, reduce flakiness, and promote healthier hair "
            "growth. Your scalp will thank you."
        ),
        "duration_minutes": 30, "price": 35.00,
        "loyalty_points_awarded": 12,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Waxing",
        "description": (
            "Precise waxing for brows, ears, nose, and neck. Quick and effective "
            "with minimal irritation, leaving you looking polished from every angle."
        ),
        "duration_minutes": 20, "price": 20.00,
        "loyalty_points_awarded": 7,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Hair Spa",
        "description": (
            "A full hair spa treatment including deep conditioning, steam therapy, "
            "and a relaxing scalp massage. Restores moisture and shine to dry or "
            "chemically treated hair."
        ),
        "duration_minutes": 60, "price": 60.00,
        "loyalty_points_awarded": 20,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Massage",
        "description": (
            "A soothing chair massage targeting the neck, shoulders, and upper back. "
            "The perfect add-on after any service, or a standalone stress-relief "
            "treatment."
        ),
        "duration_minutes": 30, "price": 40.00,
        "loyalty_points_awarded": 13,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Pedicure",
        "description": (
            "A thorough foot care treatment including soaking, nail trimming, cuticle "
            "care, callus removal, and a moisturising massage. Gentleman grooming from "
            "head to toe."
        ),
        "duration_minutes": 45, "price": 45.00,
        "loyalty_points_awarded": 15,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Eyebrow Threading",
        "description": (
            "The ancient art of threading removes unwanted brow hair with surgical "
            "precision, defining your arches naturally without chemicals or wax. "
            "Results last up to four weeks."
        ),
        "duration_minutes": 15, "price": 15.00,
        "loyalty_points_awarded": 5,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Custom Styles",
        "description": (
            "Bring your vision and our artists will bring it to life. From intricate "
            "hair designs to avant-garde cuts, custom styling is where creativity meets "
            "craftsmanship. Consultation required."
        ),
        "duration_minutes": 75, "price": 80.00,
        "loyalty_points_awarded": 25,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Hot Towel Shave",
        "description": (
            "The classic gentleman's ritual. Your skin is prepped with warm steam, "
            "lathered with premium shaving cream, and finished with a straight-razor "
            "shave so close you'll wonder why you ever used anything else."
        ),
        "duration_minutes": 35, "price": 32.00,
        "loyalty_points_awarded": 12,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Beard Conditioning",
        "description": (
            "A targeted deep-conditioning treatment for your beard and skin underneath. "
            "We apply a professional-grade beard mask, steam it in, and finish with a "
            "light trim to keep your shape on point."
        ),
        "duration_minutes": 20, "price": 22.00,
        "loyalty_points_awarded": 8,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Kids Fade",
        "description": (
            "A fresh fade sized for the young ones. Our barbers are patient, gentle, "
            "and know exactly how to keep kids comfortable in the chair while delivering "
            "a clean, modern look every parent will love."
        ),
        "duration_minutes": 30, "price": 28.00,
        "loyalty_points_awarded": 10,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Shape-Up & Design",
        "description": (
            "Precision hairline work combined with custom razor-art designs. Whether "
            "it's geometric patterns, initials, or a signature look, our artists carve "
            "it in with surgical precision."
        ),
        "duration_minutes": 45, "price": 50.00,
        "loyalty_points_awarded": 18,
        "media_type": "image", "media_filename": None,
    },
    {
        "name": "Hair Relaxer Treatment",
        "description": (
            "A professional relaxer treatment that smooths, straightens, and tames "
            "unruly or coarse hair. Applied with care by our certified stylists and "
            "followed with a deep conditioning rinse."
        ),
        "duration_minutes": 70, "price": 65.00,
        "loyalty_points_awarded": 22,
        "media_type": "image", "media_filename": None,
    },
]

_DEFAULT_REWARDS = [
    {
        "title": "Free Beard Trim",
        "description": "Redeem for a complimentary beard trim on your next visit.",
        "points_required": 50,
    },
    {
        "title": "Free Hair Wash",
        "description": "Enjoy a free hair wash and conditioning treatment.",
        "points_required": 75,
    },
    {
        "title": "20% Off Haircut",
        "description": "Get 20% off any single haircut service.",
        "points_required": 100,
    },
    {
        "title": "Half Price Service",
        "description": "50% off any service of your choice.",
        "points_required": 150,
    },
    {
        "title": "Free Facial Treatment",
        "description": "Indulge in a complimentary full facial treatment.",
        "points_required": 200,
    },
    {
        "title": "Free Line-up",
        "description": "Redeem for a complimentary edge-up / line-up session.",
        "points_required": 30,
    },
    {
        "title": "Free Kids Cut",
        "description": "Bring the little ones in for a complimentary kids cut.",
        "points_required": 60,
    },
    {
        "title": "Free Scalp Treatment",
        "description": "Enjoy a nourishing scalp treatment and massage on us.",
        "points_required": 120,
    },
    {
        "title": "VIP Hot Towel Shave",
        "description": "A premium hot towel straight-razor shave — completely free.",
        "points_required": 175,
    },
    {
        "title": "Free Custom Style",
        "description": "Bring your vision and get a custom style session at no charge.",
        "points_required": 300,
    },
    {
        "title": "Birthday Special — Free Service",
        "description": "Any single service of your choice, completely free. Happy Birthday!",
        "points_required": 400,
    },
]


# ---------------------------------------------------------------------------
# Demo barbers — seeded so the booking page works out of the box
# ---------------------------------------------------------------------------

_DEFAULT_BARBERS = [
    {
        "full_name": "Marcus Cole",
        "phone": "5551000001",
        "email": "marcus.cole@bladeandbrush.com",
        "bio": (
            "15 years behind the chair. Marcus built Blade & Brush on one principle — "
            "every client leaves sharper than they walked in. Master of precision fades, "
            "classic cuts, and sculpted beards."
        ),
        "experience_years": 15,
        "preferred_location": "Kitchener",
        "profile_picture_path": "uploads/placeholder/placeholder.jpg",
        "government_id_path":   "uploads/placeholder/placeholder.jpg",
        "license_path":         "uploads/placeholder/placeholder.jpg",
        "is_approved": True,
    },
    {
        "full_name": "Elijah Brooks",
        "phone": "5551000002",
        "email": "elijah.brooks@bladeandbrush.com",
        "bio": (
            "Fade specialist with an eye for symmetry. Eli's blends are the reason "
            "clients keep coming back. 8 years of experience turning ordinary haircuts "
            "into works of art."
        ),
        "experience_years": 8,
        "preferred_location": "London",
        "profile_picture_path": "uploads/placeholder/placeholder.jpg",
        "government_id_path":   "uploads/placeholder/placeholder.jpg",
        "license_path":         "uploads/placeholder/placeholder.jpg",
        "is_approved": True,
    },
    {
        "full_name": "Sofia Reyes",
        "phone": "5551000003",
        "email": "sofia.reyes@bladeandbrush.com",
        "bio": (
            "From textured crops to bold color work, Sofia brings a creative edge "
            "to the classic barbershop. Certified colorist with 6 years of experience "
            "across multiple award-winning salons."
        ),
        "experience_years": 6,
        "preferred_location": "Guelph",
        "profile_picture_path": "uploads/placeholder/placeholder.jpg",
        "government_id_path":   "uploads/placeholder/placeholder.jpg",
        "license_path":         "uploads/placeholder/placeholder.jpg",
        "is_approved": True,
    },
    {
        "full_name": "James Okoro",
        "phone": "5551000004",
        "email": "james.okoro@bladeandbrush.com",
        "bio": (
            "Hungry to learn, quick with the clippers, and already building a loyal "
            "client base. Specialising in fades, tapers, and line-ups with a fresh "
            "perspective and relentless attention to detail."
        ),
        "experience_years": 2,
        "preferred_location": "Mississauga",
        "profile_picture_path": "uploads/placeholder/placeholder.jpg",
        "government_id_path":   "uploads/placeholder/placeholder.jpg",
        "license_path":         "uploads/placeholder/placeholder.jpg",
        "is_approved": True,
    },
]


def _seed_database() -> None:
    """
    Idempotent seed — adds only rows that don't already exist (by name/title/email).
    Safe to run on every startup without duplicating data.
    """
    # Services
    existing_services = {s.name for s in Service.query.all()}
    new_services = [s for s in _DEFAULT_SERVICES if s["name"] not in existing_services]
    for svc in new_services:
        db.session.add(Service(**svc))
    if new_services:
        app.logger.info("[SEED] %d new service(s) inserted.", len(new_services))

    # Loyalty rewards
    existing_rewards = {r.title for r in LoyaltyReward.query.all()}
    new_rewards = [r for r in _DEFAULT_REWARDS if r["title"] not in existing_rewards]
    for rw in new_rewards:
        db.session.add(LoyaltyReward(**rw))
    if new_rewards:
        app.logger.info("[SEED] %d new reward(s) inserted.", len(new_rewards))

    # Demo barbers (only if no approved barbers exist yet)
    if Barber.query.filter_by(is_approved=True).count() == 0:
        for b in _DEFAULT_BARBERS:
            if not Barber.query.filter_by(email=b["email"]).first():
                db.session.add(Barber(**b))
        app.logger.info("[SEED] Demo barbers inserted.")

    db.session.commit()


with app.app_context():
    db.create_all()
    _seed_database()

# ---------------------------------------------------------------------------
# Static data used in templates
# ---------------------------------------------------------------------------

SERVICE_CARDS = [
    {"name": "Haircut",    "icon": "scissors", "desc": "Classic to modern — every cut crafted to match your look."},
    {"name": "Beard Trim", "icon": "razor",    "desc": "Straight-razor lines and conditioning for the perfect beard."},
    {"name": "Fade",       "icon": "comb",     "desc": "Seamless gradient blends from skin to length."},
    {"name": "Hot Towel",  "icon": "spray",    "desc": "Warm towel wrap with eucalyptus oil — pure relaxation."},
]

MOCK_SLOTS = {
    "morning":   ["09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM"],
    "afternoon": ["12:00 PM", "12:30 PM", "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM"],
    "evening":   ["03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM", "05:00 PM"],
}

SERVICES_HOME = [
    {"id": 1, "name": "Haircut",         "price": 35, "duration": "30 min", "desc": "Precision cut tailored to your style, finished with a hot towel refresh."},
    {"id": 2, "name": "Beard Trim",      "price": 25, "duration": "20 min", "desc": "Sharp beard shaping with straight-razor edge-up and beard oil finish."},
    {"id": 3, "name": "Fade",            "price": 40, "duration": "40 min", "desc": "Seamless skin, low, mid, or high fade blended to perfection."},
    {"id": 4, "name": "Haircut + Beard", "price": 55, "duration": "50 min", "desc": "The full package — precision cut plus a crisp beard sculpt."},
]

TEAM = [
    {"name": "Marcus Cole",   "role": "Master Barber & Founder", "bio": "15 years behind the chair. Marcus built Blade & Brush on one principle — every client leaves sharper than they walked in.", "img": None},
    {"name": "Elijah Brooks", "role": "Senior Barber",           "bio": "Fade specialist with an eye for symmetry. Eli's blends are the reason clients keep coming back.", "img": None},
    {"name": "Sofia Reyes",   "role": "Stylist & Colorist",      "bio": "From textured crops to bold color work, Sofia brings a creative edge to the classic barbershop.", "img": None},
    {"name": "James Okoro",   "role": "Junior Barber",           "bio": "Hungry to learn, quick with the clippers, and already building a loyal client base.", "img": None},
]

LOCATIONS = [
    {"city": "Kitchener",   "address": "285 King St W, Kitchener, ON N2G 1B1",      "badge": "Now Open",        "badge_color": "green", "maps_url": "https://maps.google.com/?q=285+King+St+W+Kitchener+ON",     "image_url": "images/locations/kitchener.webp"},
    {"city": "London",      "address": "186 Dundas St, London, ON N6A 1G7",         "badge": "Popular",         "badge_color": "red",   "maps_url": "https://maps.google.com/?q=186+Dundas+St+London+ON",        "image_url": "images/locations/london.webp"},
    {"city": "Guelph",      "address": "42 Wyndham St N, Guelph, ON N1H 4E6",       "badge": "Premium Location","badge_color": "amber", "maps_url": "https://maps.google.com/?q=42+Wyndham+St+N+Guelph+ON",      "image_url": "images/locations/guelph.webp"},
    {"city": "Mississauga", "address": "100 City Centre Dr, Mississauga, ON L5B 2C9","badge": "Now Open",       "badge_color": "green", "maps_url": "https://maps.google.com/?q=100+City+Centre+Dr+Mississauga+ON","image_url": "images/locations/mississauga.jpg"},
]

SPECIALTIES = [
    "Fade", "Taper", "Beard Styling", "Scissor Cuts",
    "Kids Cuts", "Hair Coloring", "Line-ups", "Custom Styles",
    "Massage", "Manicure", "Pedicure", "Facial Treatment",
    "Hair Spa", "Scalp Treatment", "Eyebrow Threading", "Waxing",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def allowed_file(filename: str, allowed_exts: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_exts


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email))


def validate_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-\(\)\+]", "", phone)
    return len(cleaned) >= 7 and cleaned.isdigit()


def _save_upload(file_obj, dest_folder: str, prefix: str = "") -> str:
    """Save an upload and return its path relative to the static folder."""
    filename = prefix + secure_filename(file_obj.filename)
    abs_path = os.path.join(dest_folder, filename)
    file_obj.save(abs_path)
    return os.path.relpath(abs_path, app.static_folder).replace("\\", "/")


def _flash_errors(errors: list) -> None:
    for e in errors:
        flash(e, "error")


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------


@app.route("/")
def home():
    return render_template(
        "home.html",
        services=SERVICES_HOME,
        cards=SERVICE_CARDS,
        locations=LOCATIONS,
    )


@app.route("/about")
def about():
    return render_template("about.html", team=TEAM)


# ---------------------------------------------------------------------------
# Customer authentication
# ---------------------------------------------------------------------------


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("customer_dashboard"))

    if request.method == "GET":
        return render_template("signup.html")

    # ---- POST ----
    full_name        = request.form.get("full_name", "").strip()
    email            = request.form.get("email", "").strip().lower()
    phone            = request.form.get("phone", "").strip()
    password         = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    errors: list = []

    if not full_name or len(full_name) < 2:
        errors.append("Full name must be at least 2 characters.")
    elif len(full_name) > 120:
        errors.append("Full name must be 120 characters or less.")

    if not email or not validate_email(email):
        errors.append("Please enter a valid email address.")

    if not phone or not validate_phone(phone):
        errors.append("Please enter a valid phone number.")

    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")

    if password != confirm_password:
        errors.append("Passwords do not match.")

    # Uniqueness checks only when other fields are valid
    if not errors:
        if Customer.query.filter_by(email=email).first():
            errors.append("An account with this email address already exists.")
        if Customer.query.filter_by(phone=phone).first():
            errors.append("An account with this phone number already exists.")

    if errors:
        _flash_errors(errors)
        return render_template("signup.html", form=request.form)

    try:
        customer = Customer(
            full_name=html.escape(full_name),
            email=email,
            phone=phone,
            loyalty_id="TEMP",  # replaced after flush
        )
        customer.set_password(password)
        db.session.add(customer)
        db.session.flush()  # assigns customer.id without committing
        customer.loyalty_id = Customer._build_loyalty_id(customer.id)
        db.session.commit()

        login_user(customer)
        app.logger.info(
            "[SIGNUP] New customer #%d <%s> loyalty_id=%s",
            customer.id, customer.email, customer.loyalty_id,
        )
        flash(
            f"Welcome to Blade & Brush, {customer.full_name}! "
            f"Your loyalty ID is {customer.loyalty_id}.",
            "success",
        )
        return redirect(url_for("customer_dashboard"))

    except IntegrityError:
        db.session.rollback()
        flash("That email or phone is already registered. Please log in.", "error")
        return render_template("signup.html", form=request.form)
    except Exception as exc:
        db.session.rollback()
        app.logger.error("[SIGNUP] Unexpected error: %s", exc)
        flash("Something went wrong. Please try again.", "error")
        return render_template("signup.html", form=request.form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("customer_dashboard"))

    if request.method == "GET":
        return render_template("login.html")

    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    remember = bool(request.form.get("remember"))

    customer = Customer.query.filter_by(email=email).first()
    if not customer or not customer.check_password(password):
        flash("Invalid email or password.", "error")
        return render_template("login.html", form=request.form)

    login_user(customer, remember=remember)
    app.logger.info("[LOGIN] Customer #%d <%s>", customer.id, customer.email)

    next_url = request.args.get("next")
    # Safety check — only redirect to relative URLs
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for("customer_dashboard"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


# ---------------------------------------------------------------------------
# Customer dashboard
# ---------------------------------------------------------------------------


@app.route("/customer-dashboard")
@login_required
def customer_dashboard():
    today = date_type.today()

    upcoming = (
        Booking.query
        .filter_by(customer_id=current_user.id)
        .filter(Booking.status.in_(["pending", "confirmed"]))
        .filter(Booking.appointment_date >= today)
        .order_by(Booking.appointment_date, Booking.appointment_time)
        .all()
    )
    past = (
        Booking.query
        .filter_by(customer_id=current_user.id)
        .filter(
            (Booking.appointment_date < today) |
            Booking.status.in_(["completed", "cancelled"])
        )
        .order_by(Booking.appointment_date.desc(), Booking.appointment_time.desc())
        .limit(10)
        .all()
    )
    recent_txns = (
        LoyaltyTransaction.query
        .filter_by(customer_id=current_user.id)
        .order_by(LoyaltyTransaction.created_at.desc())
        .limit(5)
        .all()
    )
    total_bookings = Booking.query.filter_by(customer_id=current_user.id).count()

    return render_template(
        "customer_dashboard.html",
        upcoming=upcoming,
        past=past,
        recent_txns=recent_txns,
        total_bookings=total_bookings,
    )


# ---------------------------------------------------------------------------
# Services page
# ---------------------------------------------------------------------------


@app.route("/services")
def services():
    all_services = (
        Service.query
        .filter_by(is_active=True)
        .order_by(Service.id)
        .all()
    )
    # Check which media files actually exist on disk
    services_data = []
    for svc in all_services:
        has_media = False
        if svc.media_filename and svc.media_type == "video":
            media_path = os.path.join(
                app.static_folder, "videos", "services", svc.media_filename
            )
            has_media = os.path.isfile(media_path)
        services_data.append({"service": svc, "has_media": has_media})

    return render_template("services.html", services_data=services_data)


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------


@app.route("/booking", methods=["GET", "POST"])
@login_required
def booking():
    barbers  = Barber.query.filter_by(is_approved=True).all()
    services = Service.query.filter_by(is_active=True).order_by(Service.name).all()

    if request.method == "GET":
        preselect_service = request.args.get("service_id", type=int)
        return render_template(
            "booking.html",
            barbers=barbers,
            services=services,
            today=date_type.today().isoformat(),
            preselect_service=preselect_service,
        )

    # ---- POST ----
    barber_id  = request.form.get("barber_id",       type=int)
    service_id = request.form.get("service_id",      type=int)
    date_str   = request.form.get("appointment_date", "").strip()
    time_str   = request.form.get("appointment_time", "").strip()
    notes      = request.form.get("customer_notes",  "").strip()

    errors: list = []

    barber = Barber.query.get(barber_id) if barber_id else None
    if not barber or not barber.is_approved:
        errors.append("Please select a valid barber.")

    service = Service.query.get(service_id) if service_id else None
    if not service or not service.is_active:
        errors.append("Please select a valid service.")

    appt_date = None
    if not date_str:
        errors.append("Please select an appointment date.")
    else:
        try:
            appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if appt_date < date_type.today():
                errors.append("Appointment date cannot be in the past.")
        except ValueError:
            errors.append("Please select a valid appointment date.")

    if time_str not in ALL_BOOKING_SLOTS:
        errors.append("Please select a valid time slot.")

    # Application-level clash check (excludes cancelled via status field)
    if not errors:
        clash = (
            Booking.query
            .filter_by(
                barber_id=barber_id,
                appointment_date=appt_date,
                appointment_time=time_str,
            )
            .filter(Booking.status != "cancelled")
            .first()
        )
        if clash:
            errors.append(
                "This time slot is already booked. Please choose another."
            )

    if errors:
        _flash_errors(errors)
        return render_template(
            "booking.html",
            barbers=barbers,
            services=services,
            today=date_type.today().isoformat(),
            form=request.form,
        )

    try:
        new_booking = Booking(
            customer_id=current_user.id,
            barber_id=barber_id,
            service_id=service_id,
            appointment_date=appt_date,
            appointment_time=time_str,
            customer_notes=html.escape(notes) if notes else None,
        )
        db.session.add(new_booking)
        db.session.commit()

        app.logger.info(
            "[BOOKING] #%d customer=%d barber=%d service=%d %s %s",
            new_booking.id, current_user.id, barber_id, service_id, appt_date, time_str,
        )
        flash(
            f"Booking confirmed for {appt_date.strftime('%B %d, %Y')} at {time_str} "
            f"with {barber.full_name}!",
            "success",
        )
        return redirect(url_for("customer_dashboard"))

    except IntegrityError:
        db.session.rollback()
        flash(
            "That slot was just taken by another customer. "
            "Please choose a different time.",
            "error",
        )
        return render_template(
            "booking.html",
            barbers=barbers,
            services=services,
            today=date_type.today().isoformat(),
            form=request.form,
        )
    except Exception as exc:
        db.session.rollback()
        app.logger.error("[BOOKING] Unexpected error: %s", exc)
        flash("Something went wrong. Please try again.", "error")
        return render_template(
            "booking.html",
            barbers=barbers,
            services=services,
            today=date_type.today().isoformat(),
            form=request.form,
        )


@app.route("/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id: int):
    """
    Customers can cancel their own pending or confirmed bookings.
    The row is deleted so the slot is freed for re-booking.
    """
    bkg = Booking.query.get_or_404(booking_id)
    if bkg.customer_id != current_user.id:
        abort(403)
    if bkg.status not in ("pending", "confirmed"):
        flash("Only pending or confirmed bookings can be cancelled.", "error")
        return redirect(url_for("customer_dashboard"))

    db.session.delete(bkg)
    db.session.commit()
    flash("Your booking has been cancelled and the slot has been freed.", "success")
    return redirect(url_for("customer_dashboard"))


# ---------------------------------------------------------------------------
# Available-slots API
# ---------------------------------------------------------------------------


@app.route("/api/available-slots/<int:barber_id>/<date_str>")
def available_slots(barber_id: int, date_str: str):
    """
    Return the list of time slots that are still available for a given
    barber on a given date.

    GET /api/available-slots/3/2026-03-10
    -> {"slots": ["09:00", "11:00", ...], "barber": "Marcus Cole", "date": "2026-03-10"}
    """
    barber = Barber.query.get(barber_id)
    if not barber or not barber.is_approved:
        return jsonify({"error": "Barber not found."}), 404

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    booked_times = {
        b.appointment_time
        for b in Booking.query
        .filter_by(barber_id=barber_id, appointment_date=target_date)
        .filter(Booking.status != "cancelled")
        .all()
    }

    available = [slot for slot in ALL_BOOKING_SLOTS if slot not in booked_times]
    return jsonify({
        "slots":  available,
        "barber": barber.full_name,
        "date":   date_str,
        "booked": sorted(booked_times),
    })


# ---------------------------------------------------------------------------
# Complete booking (awards loyalty points) — admin action
# ---------------------------------------------------------------------------


@app.route("/api/booking/<int:booking_id>/complete", methods=["POST"])
def complete_booking(booking_id: int):
    """
    Mark a booking as completed and award loyalty points to the customer.

    Protected by a simple admin key for now.
    Replace with proper admin role-based auth before going to production.
    """
    admin_key = request.form.get("admin_key") or request.headers.get("X-Admin-Key", "")
    expected  = app.config.get("ADMIN_KEY", "blade-brush-admin-2026")
    if admin_key != expected:
        abort(403)

    bkg = Booking.query.get_or_404(booking_id)
    if bkg.status == "completed":
        return jsonify({"error": "Booking is already marked as completed."}), 400

    bkg.status = "completed"

    customer = bkg.customer
    points   = bkg.service.loyalty_points_awarded
    customer.loyalty_points += points

    txn = LoyaltyTransaction(
        customer_id=customer.id,
        booking_id=bkg.id,
        points_change=points,
        transaction_type="earned",
        description=f"Earned {points} pts for completing '{bkg.service.name}'",
    )
    db.session.add(txn)
    db.session.commit()

    app.logger.info(
        "[COMPLETE] Booking #%d — +%d pts to customer #%d (total %d)",
        bkg.id, points, customer.id, customer.loyalty_points,
    )
    return jsonify({
        "message":       f"Booking completed. {points} loyalty points awarded.",
        "points_awarded": points,
        "customer_total": customer.loyalty_points,
    })


# ---------------------------------------------------------------------------
# Loyalty
# ---------------------------------------------------------------------------


@app.route("/loyalty")
@login_required
def loyalty():
    rewards = (
        LoyaltyReward.query
        .filter_by(is_active=True)
        .order_by(LoyaltyReward.points_required)
        .all()
    )
    transactions = (
        LoyaltyTransaction.query
        .filter_by(customer_id=current_user.id)
        .order_by(LoyaltyTransaction.created_at.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "loyalty.html",
        rewards=rewards,
        transactions=transactions,
    )


@app.route("/redeem-reward/<int:reward_id>", methods=["POST"])
@login_required
def redeem_reward(reward_id: int):
    reward = LoyaltyReward.query.get_or_404(reward_id)

    if not reward.is_active:
        flash("This reward is no longer available.", "error")
        return redirect(url_for("loyalty"))

    if current_user.loyalty_points < reward.points_required:
        flash(
            f"You need {reward.points_required} points to redeem this reward. "
            f"You currently have {current_user.loyalty_points}.",
            "error",
        )
        return redirect(url_for("loyalty"))

    try:
        current_user.loyalty_points -= reward.points_required
        txn = LoyaltyTransaction(
            customer_id=current_user.id,
            booking_id=None,
            points_change=-reward.points_required,
            transaction_type="redeemed",
            description=f"Redeemed '{reward.title}'",
        )
        db.session.add(txn)
        db.session.commit()

        app.logger.info(
            "[REDEEM] Customer #%d redeemed reward #%d (%s) for %d pts",
            current_user.id, reward.id, reward.title, reward.points_required,
        )
        flash(
            f"You've redeemed '{reward.title}'! Show this confirmation at reception. "
            f"Remaining points: {current_user.loyalty_points}.",
            "success",
        )
    except Exception as exc:
        db.session.rollback()
        app.logger.error("[REDEEM] Error: %s", exc)
        flash("Something went wrong. Please try again.", "error")

    return redirect(url_for("loyalty"))


# ---------------------------------------------------------------------------
# Barber registration
# ---------------------------------------------------------------------------


@app.route("/register-barber", methods=["GET", "POST"])
def register_barber():
    if request.method == "GET":
        return render_template("register_barber.html", specialties=SPECIALTIES)

    errors: list = []

    full_name            = request.form.get("full_name", "").strip()
    phone                = request.form.get("phone", "").strip()
    email                = request.form.get("email", "").strip().lower()
    bio                  = request.form.get("bio", "").strip()
    years_exp            = request.form.get("years_experience", "").strip()
    preferred_location   = request.form.get("preferred_location", "").strip()
    selected_specialties = request.form.getlist("specialties")
    schedule_json        = request.form.get("availability_schedule", "{}").strip()

    if not full_name or len(full_name) < 2:
        errors.append("Full name must be at least 2 characters.")
    elif len(full_name) > 120:
        errors.append("Full name must be 120 characters or less.")

    if not phone or not validate_phone(phone):
        errors.append("Please enter a valid phone number.")

    if not email or not validate_email(email):
        errors.append("Please enter a valid email address.")

    if not bio or len(bio) < 20:
        errors.append("Professional bio must be at least 20 characters.")
    elif len(bio) > 2000:
        errors.append("Professional bio must be 2000 characters or less.")

    if not years_exp:
        errors.append("Years of experience is required.")
    elif not years_exp.isdigit() or not (0 <= int(years_exp) <= 50):
        errors.append("Years of experience must be a whole number between 0 and 50.")

    if preferred_location not in VALID_LOCATIONS:
        errors.append("Please select a valid preferred location.")

    if not selected_specialties:
        errors.append("Please select at least one specialty.")
    else:
        if any(s not in SPECIALTIES for s in selected_specialties):
            errors.append("One or more selected specialties are not recognised.")

    gov_id         = request.files.get("gov_id")
    profile_pic    = request.files.get("profile_pic")
    barber_license = request.files.get("barber_license")

    if not gov_id or gov_id.filename == "":
        errors.append("Government ID upload is required.")
    elif not allowed_file(gov_id.filename, ALLOWED_DOC_EXT):
        errors.append("Government ID must be PNG, JPG, WEBP, or PDF.")

    if not profile_pic or profile_pic.filename == "":
        errors.append("Profile picture upload is required.")
    elif not allowed_file(profile_pic.filename, ALLOWED_IMAGE_EXT):
        errors.append("Profile picture must be PNG, JPG, or WEBP.")

    if not barber_license or barber_license.filename == "":
        errors.append("Barber license upload is required.")
    elif not allowed_file(barber_license.filename, ALLOWED_DOC_EXT):
        errors.append("Barber license must be PNG, JPG, WEBP, or PDF.")

    if not errors and Barber.query.filter_by(email=email).first():
        errors.append(
            "An application with this email already exists. "
            "Contact us if you need to update your submission."
        )

    if errors:
        _flash_errors(errors)
        return render_template(
            "register_barber.html",
            specialties=SPECIALTIES,
            form=request.form,
            selected_specialties=selected_specialties,
        )

    # Save uploaded files
    app_id     = str(uuid.uuid4())
    app_folder = os.path.join(UPLOAD_BARBER, app_id)
    os.makedirs(app_folder, exist_ok=True)

    try:
        gov_id_path      = _save_upload(gov_id,         app_folder, "gov_id_")
        profile_pic_path = _save_upload(profile_pic,    app_folder, "profile_")
        license_path     = _save_upload(barber_license, app_folder, "license_")
    except Exception as exc:
        shutil.rmtree(app_folder, ignore_errors=True)
        app.logger.error("[BARBER] File save failed: %s", exc)
        flash("File upload failed. Please try again.", "error")
        return render_template(
            "register_barber.html",
            specialties=SPECIALTIES,
            form=request.form,
            selected_specialties=selected_specialties,
        )

    try:
        schedule = json.loads(schedule_json)
        if not isinstance(schedule, dict):
            schedule = {}
    except (json.JSONDecodeError, ValueError):
        schedule = {}

    try:
        barber = Barber(
            full_name=html.escape(full_name),
            phone=phone,
            email=email,
            bio=html.escape(bio),
            experience_years=int(years_exp),
            preferred_location=preferred_location,
            profile_picture_path=profile_pic_path,
            government_id_path=gov_id_path,
            license_path=license_path,
        )

        for spec in selected_specialties:
            if spec in SPECIALTIES:
                barber.specialties.append(BarberSpecialty(specialty_name=spec))

        for day, slots in schedule.items():
            if day not in VALID_DAYS or not isinstance(slots, list):
                continue
            for slot in slots:
                if slot in VALID_SLOTS:
                    barber.availability.append(
                        BarberAvailability(day_of_week=day, time_slot=slot)
                    )

        db.session.add(barber)
        db.session.commit()

        app.logger.info(
            "[BARBER] Application #%d — %r <%s>  specialties=%d  avail=%d",
            barber.id, barber.full_name, barber.email,
            len(barber.specialties), len(barber.availability),
        )
    except Exception as exc:
        db.session.rollback()
        shutil.rmtree(app_folder, ignore_errors=True)
        app.logger.error("[BARBER] DB insert failed: %s", exc)
        flash("Something went wrong saving your application. Please try again.", "error")
        return render_template(
            "register_barber.html",
            specialties=SPECIALTIES,
            form=request.form,
            selected_specialties=selected_specialties,
        )

    return redirect(url_for("application_submitted"))


@app.route("/application-submitted")
def application_submitted():
    return render_template("application_submitted.html")


# ---------------------------------------------------------------------------
# Review routes
# ---------------------------------------------------------------------------


@app.route("/submit-review", methods=["POST"])
def submit_review():
    name        = request.form.get("name", "").strip()
    rating_str  = request.form.get("rating", "0").strip()
    review_text = request.form.get("review", "").strip()

    errors = []
    if not name or len(name) < 2:
        errors.append("Name must be at least 2 characters.")
    elif len(name) > 120:
        errors.append("Name must be 120 characters or less.")

    try:
        rating = int(rating_str)
    except ValueError:
        rating = 0
    if not 1 <= rating <= 5:
        errors.append("Rating must be between 1 and 5.")

    if not review_text or len(review_text) < 10:
        errors.append("Review must be at least 10 characters.")
    elif len(review_text) > 500:
        errors.append("Review must be 500 characters or less.")

    if errors:
        _flash_errors(errors)
        return redirect(url_for("reviews") + "#review-form")

    try:
        review = Review(
            name=html.escape(name),
            email="",
            rating=rating,
            message=html.escape(review_text),
        )
        db.session.add(review)
        db.session.commit()
        app.logger.info("Review #%d saved — name=%r rating=%d", review.id, name, rating)
    except Exception as exc:
        db.session.rollback()
        app.logger.error("Failed to save review: %s", exc)
        flash("Something went wrong saving your review. Please try again.", "error")
        return redirect(url_for("reviews") + "#review-form")

    flash("Thanks for your review! It's now live.", "success")
    return redirect(url_for("reviews"))


@app.route("/api/reviews", methods=["POST"])
def api_create_review():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    name       = str(data.get("name", "")).strip()
    email      = str(data.get("email", "")).strip()
    rating_raw = data.get("rating")
    message    = str(data.get("message", "")).strip()

    errors = []
    if not name or len(name) < 2:
        errors.append("Name must be at least 2 characters.")
    elif len(name) > 120:
        errors.append("Name must be 120 characters or less.")

    if not email or "@" not in email:
        errors.append("A valid email address is required.")

    try:
        rating = int(rating_raw)
    except (TypeError, ValueError):
        rating = 0
    if not 1 <= rating <= 5:
        errors.append("Rating must be between 1 and 5.")

    if not message or len(message) < 10:
        errors.append("Review must be at least 10 characters.")
    elif len(message) > 1000:
        errors.append("Review must be 1000 characters or less.")

    if errors:
        return jsonify({"error": errors[0]}), 422

    try:
        review = Review(
            name=html.escape(name),
            email=html.escape(email),
            rating=rating,
            message=html.escape(message),
        )
        db.session.add(review)
        db.session.commit()
        app.logger.info("Review #%d (API) — name=%r rating=%d", review.id, name, rating)
    except Exception as exc:
        db.session.rollback()
        app.logger.error("DB insert failed: %s", exc)
        return jsonify({"error": "Could not save your review. Please try again."}), 500

    return jsonify({"id": review.id, "message": "Review submitted successfully!"}), 201


@app.route("/api/reviews", methods=["GET"])
def api_get_reviews():
    try:
        limit  = min(max(int(request.args.get("limit",  6)), 1), 20)
        offset = max(int(request.args.get("offset", 0)), 0)
    except (TypeError, ValueError):
        limit, offset = 6, 0

    sort = request.args.get("sort", "newest")
    if sort not in ("newest", "highest"):
        sort = "newest"

    tag = request.args.get("tag", "").strip() or None
    reviews, total = get_reviews(limit=limit, offset=offset, sort=sort, tag=tag)
    return jsonify({"reviews": reviews, "total": total})


# ---------------------------------------------------------------------------
# Testimonials + utilities
# ---------------------------------------------------------------------------


def _time_ago(iso: str) -> str:
    try:
        dt   = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        diff = int((datetime.now(timezone.utc) - dt).total_seconds())
        if diff < 60:         return "Just now"
        if diff < 3600:       return f"{diff // 60}m ago"
        if diff < 86400:      return f"{diff // 3600}h ago"
        if diff < 2_592_000:  return f"{diff // 86400}d ago"
        if diff < 31_536_000: return f"{diff // 2_592_000}mo ago"
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso


@app.route("/testimonials")
def testimonials():
    return redirect(url_for("reviews"), 301)


@app.route("/reviews")
def reviews():
    all_reviews = (
        Review.query.order_by(Review.created_at.desc()).limit(50).all()
    )
    review_list = []
    for r in all_reviews:
        review_list.append({
            "id":         r.id,
            "name":       r.name,
            "rating":     r.rating,
            "message":    r.message,
            "time_ago":   _time_ago(r.created_at.isoformat()),
        })
    total = Review.query.count()
    app.logger.info("Reviews page: %d/%d", len(review_list), total)
    return render_template("reviews.html", reviews=review_list, total=total)




@app.route("/location")
def location():
    return render_template("location.html", locations=LOCATIONS)


@app.route("/locations")
def locations():
    return render_template("location.html", locations=LOCATIONS)


@app.route("/debug/reviews")
def debug_reviews():
    reviews, total = get_reviews(limit=3, offset=0, sort="newest")
    return jsonify({"reviews_db_path": DB_PATH, "total_reviews": total, "last_3": reviews})


@app.route("/partials/slots")
def partials_slots():
    service_id = request.args.get("service_id", "1")
    appt_date  = request.args.get("date", "")
    return render_template(
        "partials/_slots.html",
        slots=MOCK_SLOTS, date=appt_date, service_id=service_id,
    )


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
