// Show the text in an element's data-tip attribute in a floating tooltip.
(function () {
  var tip = document.createElement('div');
  tip.className = 'tooltip';
  tip.id = 'tooltip';
  tip.setAttribute('role', 'tooltip');
  tip.hidden = true;
  document.body.appendChild(tip);

  function show(el) {
    tip.textContent = el.dataset.tip;
    tip.hidden = false;
    var box = el.getBoundingClientRect();
    var left = box.left + box.width / 2 - tip.offsetWidth / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - tip.offsetWidth - 8));
    tip.style.left = left + window.scrollX + 'px';
    tip.style.top = box.top + window.scrollY - tip.offsetHeight - 8 + 'px';
  }

  function hide() {
    tip.hidden = true;
  }

  document.querySelectorAll('[data-tip]').forEach(function (el) {
    el.setAttribute('aria-describedby', 'tooltip');
    el.addEventListener('mouseenter', function () { show(el); });
    el.addEventListener('focus', function () { show(el); });
    el.addEventListener('mouseleave', hide);
    el.addEventListener('blur', hide);
    // Tap to toggle on touch screens
    el.addEventListener('click', function () {
      if (tip.hidden) { show(el); } else { hide(); }
    });
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') { hide(); }
  });
})();
