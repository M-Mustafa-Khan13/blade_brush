import os
import uuid
import re
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'blade-and-brush-secret-key-change-in-production'

# ---------------------------------------------------------------------------
# Upload config
# ---------------------------------------------------------------------------
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads', 'barber_applications')
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_DOC_EXT = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------
SERVICES = [
    {"id": 1, "name": "Haircut",        "price": 35, "duration": "30 min",
     "desc": "Precision cut tailored to your style, finished with a hot towel refresh."},
    {"id": 2, "name": "Beard Trim",     "price": 25, "duration": "20 min",
     "desc": "Sharp beard shaping with straight-razor edge-up and beard oil finish."},
    {"id": 3, "name": "Fade",           "price": 40, "duration": "40 min",
     "desc": "Seamless skin, low, mid, or high fade blended to perfection."},
    {"id": 4, "name": "Haircut + Beard", "price": 55, "duration": "50 min",
     "desc": "The full package — precision cut plus a crisp beard sculpt."},
]

SERVICE_CARDS = [
    {"name": "Haircut",      "icon": "scissors",  "desc": "Classic to modern — every cut crafted to match your look."},
    {"name": "Beard Trim",   "icon": "razor",     "desc": "Straight-razor lines and conditioning for the perfect beard."},
    {"name": "Fade",         "icon": "comb",       "desc": "Seamless gradient blends from skin to length."},
    {"name": "Hot Towel",    "icon": "spray",      "desc": "Warm towel wrap with eucalyptus oil — pure relaxation."},
]

MOCK_SLOTS = {
    "morning":   ["09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM"],
    "afternoon": ["12:00 PM", "12:30 PM", "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM"],
    "evening":   ["03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM", "05:00 PM"],
}

TEAM = [
    {"name": "Marcus Cole",   "role": "Master Barber & Founder", "bio": "15 years behind the chair. Marcus built Blade & Brush on one principle — every client leaves sharper than they walked in.", "img": None},
    {"name": "Elijah Brooks", "role": "Senior Barber",           "bio": "Fade specialist with an eye for symmetry. Eli's blends are the reason clients keep coming back.", "img": None},
    {"name": "Sofia Reyes",   "role": "Stylist & Colorist",      "bio": "From textured crops to bold color work, Sofia brings a creative edge to the classic barbershop.", "img": None},
    {"name": "James Okoro",   "role": "Junior Barber",           "bio": "Hungry to learn, quick with the clippers, and already building a loyal client base.", "img": None},
]

LOCATIONS = [
    {
        "city": "Kitchener",
        "address": "285 King St W, Kitchener, ON N2G 1B1",
        "badge": "Now Open",
        "badge_color": "green",
        "maps_url": "https://maps.google.com/?q=285+King+St+W+Kitchener+ON",
    },
    {
        "city": "London",
        "address": "186 Dundas St, London, ON N6A 1G7",
        "badge": "Popular",
        "badge_color": "red",
        "maps_url": "https://maps.google.com/?q=186+Dundas+St+London+ON",
    },
    {
        "city": "Guelph",
        "address": "42 Wyndham St N, Guelph, ON N1H 4E6",
        "badge": "Premium Location",
        "badge_color": "amber",
        "maps_url": "https://maps.google.com/?q=42+Wyndham+St+N+Guelph+ON",
    },
    {
        "city": "Mississauga",
        "address": "100 City Centre Dr, Mississauga, ON L5B 2C9",
        "badge": "Now Open",
        "badge_color": "green",
        "maps_url": "https://maps.google.com/?q=100+City+Centre+Dr+Mississauga+ON",
    },
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
def allowed_file(filename, allowed_exts):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts


def validate_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email)


def validate_phone(phone):
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    return len(cleaned) >= 7 and cleaned.isdigit()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("home.html", services=SERVICES, cards=SERVICE_CARDS, locations=LOCATIONS)


@app.route("/about")
def about():
    return render_template("about.html", team=TEAM)


@app.route("/booking")
def booking():
    return render_template("placeholder.html",
                           title="Booking",
                           message="Full booking experience coming soon.")


@app.route("/location")
def location():
    return render_template("placeholder.html",
                           title="Location",
                           message="Interactive map and directions coming soon.")


@app.route("/register-barber", methods=["GET", "POST"])
def register_barber():
    if request.method == "GET":
        return render_template("register_barber.html", specialties=SPECIALTIES)

    # --- POST: validate and save ---
    errors = []

    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    bio = request.form.get("bio", "").strip()
    years_exp = request.form.get("years_experience", "").strip()
    selected_specialties = request.form.getlist("specialties")

    # Text validations
    if not full_name:
        errors.append("Full name is required.")
    if not phone:
        errors.append("Phone number is required.")
    elif not validate_phone(phone):
        errors.append("Please enter a valid phone number.")
    if not email:
        errors.append("Email is required.")
    elif not validate_email(email):
        errors.append("Please enter a valid email address.")
    if not bio:
        errors.append("Professional bio is required.")
    if not years_exp:
        errors.append("Years of experience is required.")
    elif not years_exp.isdigit() or int(years_exp) < 0:
        errors.append("Years of experience must be a valid number.")
    if not selected_specialties:
        errors.append("Please select at least one specialty.")

    # File validations
    gov_id = request.files.get("gov_id")
    profile_pic = request.files.get("profile_pic")
    barber_license = request.files.get("barber_license")

    if not gov_id or gov_id.filename == '':
        errors.append("Government ID is required.")
    elif not allowed_file(gov_id.filename, ALLOWED_DOC_EXT):
        errors.append("Government ID must be an image or PDF file.")

    if not profile_pic or profile_pic.filename == '':
        errors.append("Profile picture is required.")
    elif not allowed_file(profile_pic.filename, ALLOWED_IMAGE_EXT):
        errors.append("Profile picture must be an image file (PNG, JPG, WEBP).")

    if not barber_license or barber_license.filename == '':
        errors.append("Barber license is required.")
    elif not allowed_file(barber_license.filename, ALLOWED_DOC_EXT):
        errors.append("Barber license must be an image or PDF file.")

    if errors:
        for err in errors:
            flash(err, "error")
        return render_template("register_barber.html",
                               specialties=SPECIALTIES,
                               form=request.form,
                               selected_specialties=selected_specialties)

    # Save files
    app_id = str(uuid.uuid4())
    app_folder = os.path.join(UPLOAD_FOLDER, app_id)
    os.makedirs(app_folder, exist_ok=True)

    gov_id.save(os.path.join(app_folder, "gov_id_" + secure_filename(gov_id.filename)))
    profile_pic.save(os.path.join(app_folder, "profile_" + secure_filename(profile_pic.filename)))
    barber_license.save(os.path.join(app_folder, "license_" + secure_filename(barber_license.filename)))

    return render_template("register_barber.html",
                           specialties=SPECIALTIES,
                           success=True)


@app.route("/submit-review", methods=["POST"])
def submit_review():
    name = request.form.get("name", "").strip()
    rating = request.form.get("rating", "0")
    review = request.form.get("review", "").strip()

    if not name or not review or rating == "0":
        flash("Please fill in all fields and select a rating.", "error")
        return redirect(url_for("home") + "#review")

    flash("Thanks for your review!", "success")
    return redirect(url_for("home") + "#review")


@app.route("/partials/slots")
def partials_slots():
    service_id = request.args.get("service_id", "1")
    date = request.args.get("date", "")
    return render_template("partials/_slots.html",
                           slots=MOCK_SLOTS, date=date, service_id=service_id)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
