/**
 * Landing page count-up animation.
 * Vanilla requestAnimationFrame — no CountUp.js dependency (locked by RESEARCH.md).
 * Selects all .stat-card__value[data-target] and animates each to its target value.
 */
(function () {
  'use strict';

  var DURATION = 1200; // ms

  function animateCount(el, target) {
    var start = null;
    var from = 0;

    function step(timestamp) {
      if (!start) start = timestamp;
      var elapsed = timestamp - start;
      var progress = Math.min(elapsed / DURATION, 1);
      // Ease-out cubic
      var eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(from + (target - from) * eased).toLocaleString();
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    }

    requestAnimationFrame(step);
  }

  function init() {
    var cards = document.querySelectorAll('.stat-card__value[data-target]');
    for (var i = 0; i < cards.length; i++) {
      var el = cards[i];
      var target = parseInt(el.getAttribute('data-target'), 10);
      if (!isNaN(target) && target > 0) {
        animateCount(el, target);
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
