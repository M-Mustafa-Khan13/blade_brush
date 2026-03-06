"""
SQLAlchemy models for Blade & Brush — all application domain objects.

Tables
------
customers             — registered customer accounts (Flask-Login principal)
barbers               — barber applicants / approved team members
barber_specialties    — one specialty row per barber (FK → barbers)
barber_availability   — one availability-slot row per barber (FK → barbers)
services              — offered services with pricing, media, and loyalty data
bookings              — customer appointments (FK → customers, barbers, services)
loyalty_rewards       — redeemable rewards catalogue
loyalty_transactions  — point earn / redeem audit trail (FK → customers, bookings)
"""

from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

# ---------------------------------------------------------------------------
# Domain constants — single source of truth imported by routes
# ---------------------------------------------------------------------------

VALID_DAYS: frozenset = frozenset(
    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
)
VALID_SLOTS: frozenset = frozenset(["Morning", "Afternoon", "Evening"])
VALID_LOCATIONS: frozenset = frozenset(
    ["Kitchener", "London", "Guelph", "Mississauga", "Any"]
)
ALL_BOOKING_SLOTS: list = [
    "09:00", "10:00", "11:00", "12:00",
    "13:00", "14:00", "15:00", "16:00", "17:00",
]
BOOKING_STATUSES: frozenset = frozenset(
    ["pending", "confirmed", "completed", "cancelled"]
)


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------


class Customer(UserMixin, db.Model):
    """Registered customer account — the Flask-Login principal."""

    __tablename__ = "customers"

    id             = db.Column(db.Integer,     primary_key=True)
    full_name      = db.Column(db.String(120), nullable=False)
    email          = db.Column(db.String(254), nullable=False, unique=True, index=True)
    phone          = db.Column(db.String(30),  nullable=False, unique=True, index=True)
    password_hash  = db.Column(db.String(256), nullable=False)
    loyalty_id     = db.Column(db.String(20),  nullable=False, unique=True, index=True)
    loyalty_points = db.Column(db.Integer,     nullable=False, default=0)
    created_at     = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    bookings             = db.relationship("Booking",            backref="customer", lazy=True)
    loyalty_transactions = db.relationship("LoyaltyTransaction", backref="customer", lazy=True)

    # ------------------------------------------------------------------
    # Password helpers
    # ------------------------------------------------------------------

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # ------------------------------------------------------------------
    # Loyalty ID
    # ------------------------------------------------------------------

    @staticmethod
    def _build_loyalty_id(pk: int) -> str:
        """Produce a deterministic sequential loyalty ID from the primary key.

        Call AFTER flushing the session so ``pk`` is populated::

            db.session.add(customer)
            db.session.flush()
            customer.loyalty_id = Customer._build_loyalty_id(customer.id)
            db.session.commit()
        """
        return f"BB-CUS-{100000 + pk}"

    def __repr__(self) -> str:
        return f"<Customer id={self.id} email={self.email!r}>"


# ---------------------------------------------------------------------------
# Barber
# ---------------------------------------------------------------------------


class Barber(db.Model):
    """Barber applicant / approved team member."""

    __tablename__ = "barbers"

    id                   = db.Column(db.Integer,     primary_key=True)
    full_name            = db.Column(db.String(120), nullable=False)
    phone                = db.Column(db.String(30),  nullable=False)
    email                = db.Column(db.String(254), nullable=False, unique=True, index=True)
    bio                  = db.Column(db.Text,        nullable=False)
    experience_years     = db.Column(db.Integer,     nullable=False)
    preferred_location   = db.Column(db.String(80),  nullable=False)
    profile_picture_path = db.Column(db.String(512), nullable=False)
    government_id_path   = db.Column(db.String(512), nullable=False)
    license_path         = db.Column(db.String(512), nullable=False)
    is_approved          = db.Column(db.Boolean,     nullable=False, default=False)
    created_at           = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    specialties  = db.relationship("BarberSpecialty",   backref="barber", lazy=True, cascade="all, delete-orphan")
    availability = db.relationship("BarberAvailability", backref="barber", lazy=True, cascade="all, delete-orphan")
    bookings     = db.relationship("Booking",            backref="barber", lazy=True)

    def __repr__(self) -> str:
        return f"<Barber id={self.id} name={self.full_name!r} approved={self.is_approved}>"


class BarberSpecialty(db.Model):
    __tablename__ = "barber_specialties"

    id             = db.Column(db.Integer, primary_key=True)
    barber_id      = db.Column(
        db.Integer, db.ForeignKey("barbers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    specialty_name = db.Column(db.String(80), nullable=False)

    def __repr__(self) -> str:
        return f"<BarberSpecialty barber_id={self.barber_id} {self.specialty_name!r}>"


class BarberAvailability(db.Model):
    __tablename__ = "barber_availability"

    id          = db.Column(db.Integer, primary_key=True)
    barber_id   = db.Column(
        db.Integer, db.ForeignKey("barbers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    day_of_week = db.Column(db.String(10), nullable=False)
    time_slot   = db.Column(db.String(20), nullable=False)

    def __repr__(self) -> str:
        return f"<BarberAvailability barber_id={self.barber_id} {self.day_of_week} {self.time_slot}>"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class Service(db.Model):
    """An offered barbershop service (catalogue item)."""

    __tablename__ = "services"

    id                     = db.Column(db.Integer,      primary_key=True)
    name                   = db.Column(db.String(80),   nullable=False, unique=True)
    description            = db.Column(db.Text,         nullable=False)
    duration_minutes       = db.Column(db.Integer,      nullable=False)
    price                  = db.Column(db.Numeric(8, 2), nullable=False)
    loyalty_points_awarded = db.Column(db.Integer,      nullable=False, default=10)
    # media_type: "video" | "image"
    media_type             = db.Column(db.String(10),   nullable=False, default="image")
    media_filename         = db.Column(db.String(256),  nullable=True)
    is_active              = db.Column(db.Boolean,      nullable=False, default=True)

    bookings = db.relationship("Booking", backref="service", lazy=True)

    def __repr__(self) -> str:
        return f"<Service id={self.id} name={self.name!r} price={self.price}>"


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------


class Booking(db.Model):
    """
    A customer appointment with a barber for a specific service.

    The UniqueConstraint on (barber_id, appointment_date, appointment_time)
    enforces at the database level that a barber cannot be double-booked.
    Because the constraint is unconditional, cancelled bookings must be
    **deleted** (not just status-updated) to release a time slot.
    """

    __tablename__ = "bookings"

    id               = db.Column(db.Integer,  primary_key=True)
    customer_id      = db.Column(db.Integer,  db.ForeignKey("customers.id"), nullable=False, index=True)
    barber_id        = db.Column(db.Integer,  db.ForeignKey("barbers.id"),   nullable=False, index=True)
    service_id       = db.Column(db.Integer,  db.ForeignKey("services.id"),  nullable=False, index=True)
    appointment_date = db.Column(db.Date,     nullable=False)
    appointment_time = db.Column(db.String(5), nullable=False)   # "HH:MM"
    status           = db.Column(db.String(20), nullable=False, default="pending")
    customer_notes   = db.Column(db.Text,     nullable=True)
    created_at       = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    loyalty_transactions = db.relationship("LoyaltyTransaction", backref="booking", lazy=True)

    __table_args__ = (
        UniqueConstraint(
            "barber_id", "appointment_date", "appointment_time",
            name="uq_barber_date_time",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} barber={self.barber_id}"
            f" {self.appointment_date} {self.appointment_time}"
            f" status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# Loyalty
# ---------------------------------------------------------------------------


class LoyaltyReward(db.Model):
    """A redeemable reward that customers can claim using loyalty points."""

    __tablename__ = "loyalty_rewards"

    id              = db.Column(db.Integer,     primary_key=True)
    title           = db.Column(db.String(120), nullable=False)
    description     = db.Column(db.Text,        nullable=False)
    points_required = db.Column(db.Integer,     nullable=False)
    is_active       = db.Column(db.Boolean,     nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<LoyaltyReward id={self.id} title={self.title!r} pts={self.points_required}>"


class Review(db.Model):
    """Customer review submitted via the /reviews page."""

    __tablename__ = "customer_reviews"

    id         = db.Column(db.Integer,     primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(254), nullable=False)
    rating     = db.Column(db.Integer,     nullable=False)
    message    = db.Column(db.Text,        nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Review id={self.id} name={self.name!r} rating={self.rating}>"


# ---------------------------------------------------------------------------
# Loyalty
# ---------------------------------------------------------------------------


class LoyaltyTransaction(db.Model):
    """
    Audit trail of every point change for a customer.

    points_change  — positive (earned / adjusted-up) or negative (redeemed)
    transaction_type — "earned" | "redeemed" | "adjusted"
    """

    __tablename__ = "loyalty_transactions"

    id               = db.Column(db.Integer,     primary_key=True)
    customer_id      = db.Column(db.Integer,     db.ForeignKey("customers.id"), nullable=False, index=True)
    booking_id       = db.Column(db.Integer,     db.ForeignKey("bookings.id"),  nullable=True,  index=True)
    points_change    = db.Column(db.Integer,     nullable=False)
    transaction_type = db.Column(db.String(20),  nullable=False)
    description      = db.Column(db.String(255), nullable=False)
    created_at       = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<LoyaltyTransaction id={self.id} customer={self.customer_id}"
            f" {self.points_change:+d} type={self.transaction_type!r}>"
        )
