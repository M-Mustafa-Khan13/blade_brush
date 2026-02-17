/**
 * Blade & Brush — Home page enhancements
 * Most interactivity is handled by Alpine.js inline.
 * This file provides scroll-triggered fade-in animations.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Fade-up on scroll using IntersectionObserver
    const fadeEls = document.querySelectorAll('.fade-up');
    if (fadeEls.length && 'IntersectionObserver' in window) {
        const obs = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                        obs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.15 }
        );
        fadeEls.forEach((el) => obs.observe(el));
    }
});
