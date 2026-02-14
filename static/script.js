/**
 * SkinPilot - Frontend scripts
 * Flash auto-dismiss, smooth behavior
 */

(function () {
    'use strict';

    // Auto-dismiss flash messages after 4 seconds
    var flashEls = document.querySelectorAll('.flash');
    flashEls.forEach(function (el) {
        setTimeout(function () {
            el.style.opacity = '0';
            el.style.transform = 'translateY(-10px)';
            el.style.transition = 'opacity 0.3s, transform 0.3s';
            setTimeout(function () {
                el.remove();
            }, 300);
        }, 4000);
    });

    // Smooth scroll for in-page links
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Card hover effect reinforcement (optional)
    document.querySelectorAll('.dashboard-card').forEach(function (card) {
        card.addEventListener('mouseenter', function () {
            this.style.willChange = 'transform';
        });
        card.addEventListener('mouseleave', function () {
            this.style.willChange = 'auto';
        });
    });
})();
