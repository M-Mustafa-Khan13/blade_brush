from flask import Flask, render_template, request

app = Flask(__name__)

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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("home.html", services=SERVICES, cards=SERVICE_CARDS)


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


@app.route("/barber/register")
def barber_register():
    return render_template("placeholder.html",
                           title="Register as a Barber",
                           message="Barber registration portal coming soon.")


@app.route("/partials/slots")
def partials_slots():
    service_id = request.args.get("service_id", "1")
    date = request.args.get("date", "")
    # Return mock slots regardless of params (demo)
    return render_template("partials/_slots.html",
                           slots=MOCK_SLOTS, date=date, service_id=service_id)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
