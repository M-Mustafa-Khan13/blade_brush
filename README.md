# Blade & Brush - Premium Barbershop Website

A sleek, modern barbershop website built with Flask, featuring a cinematic hero video carousel, scissor-cut page transitions, and a bold Black & Red theme.

## Features

- **Hero Video Carousel** - Full-screen video slider with 2 barbershop videos, manual navigation, and sound toggle
- **Scissor-Cut Page Transition** - Full-screen overlay with animated scissors cutting down the center, panels splitting apart, and shattering brand text on every page load
- **Falling Barber Tools Animation** - Continuous background animation of 15 falling SVG barber tools (scissors, combs, razors, spray bottles)
- **Services Section** - Animated service cards with hover effects
- **Trust Section** - Social proof with stats and client testimonials
- **Location Teaser** - Map preview section
- **Responsive Design** - Fully responsive across all screen sizes
- **Accessibility** - Respects `prefers-reduced-motion` settings

## Tech Stack

- **Backend:** Flask (Python) with Jinja2 templates
- **CSS:** Tailwind CSS (CDN) with custom barber color palette
- **Interactivity:** Alpine.js for components (slider, navbar, transitions)
- **Partial Loading:** HTMX for dynamic content
- **Fonts:** Playfair Display (headings) + Inter (body)

## Project Structure

```
Appointment_Booking System/
├── flask_app/
│   ├── app.py                  # Flask routes and mock data
│   ├── config.py               # Configuration
│   ├── pb_client.py            # PocketBase client
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css       # Custom styles, animations, keyframes
│   │   ├── js/
│   │   │   └── home.js         # Scroll-triggered fade-in observer
│   │   └── videos/
│   │       ├── hero1.mp4       # Cinematic barbershop video
│   │       └── hero2.mp4       # B-roll barbershop video
│   └── templates/
│       ├── base.html           # Master layout (navbar, footer, transitions, falling tools)
│       ├── home.html           # Home page (hero slider, services, trust, location)
│       ├── about.html          # About/Team page
│       ├── placeholder.html    # Placeholder for upcoming pages
│       └── partials/
│           └── _slots.html     # HTMX partial for booking slots
├── README.md
└── requirements.txt
```

## Pages

| Route              | Description                          |
|-------------------|--------------------------------------|
| `/`               | Home page with hero video carousel   |
| `/about`          | Team page with barber profiles       |
| `/booking`        | Booking page (placeholder)           |
| `/location`       | Location page (placeholder)          |
| `/barber/register`| Barber registration (placeholder)    |

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone or download the project

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install flask
   ```

4. Run the app:
   ```bash
   python flask_app/app.py
   ```

5. Open **http://127.0.0.1:5000** in your browser

## Color Theme

| Color          | Hex       | Usage                     |
|---------------|-----------|---------------------------|
| Red           | `#dc2626` | Primary accent, buttons   |
| Dark          | `#0a0a0a` | Background                |
| Card          | `#111111` | Card backgrounds          |
| Cream         | `#f5f0e8` | Text                      |
| Muted         | `#1a1a1a` | Secondary backgrounds     |
| Border        | `#ffffff0d` | Subtle borders           |

## License

This project is for educational and personal use.
