function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

function animateCount(el, target, duration = 1800) {
  const start = performance.now();
  const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    el.textContent = Math.round(target * ease(progress));
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${window.API_BASE}${path}`, options);
  let data = null;
  try {
    data = await response.json();
  } catch (err) {
    data = null;
  }
  return { ok: response.ok, status: response.status, data };
}
