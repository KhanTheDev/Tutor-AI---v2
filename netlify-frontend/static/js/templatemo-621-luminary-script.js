/*
TemplateMo 621 Luminary
https://templatemo.com/tm-621-luminary
Adapted for Tutor AI Platform
*/

// —— Smooth Scroll (JS-driven, overrides CSS) ——
document.querySelectorAll('a[href^="#"]').forEach(link => {
  link.addEventListener('click', e => {
    const href = link.getAttribute('href');
    if (href === '#') {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    }
  });
});

// —— Reveal ——
const reveals = document.querySelectorAll('.reveal');
const io = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); } });
}, { threshold: 0.12, rootMargin: '0px 0px -30px 0px' });
reveals.forEach(el => io.observe(el));

// —— Counters ——
document.querySelectorAll('.counter').forEach(el => {
  new IntersectionObserver(([e]) => {
    if (!e.isIntersecting) return;
    const t = parseFloat(el.dataset.target), d = parseInt(el.dataset.decimals), dur = 1800, s = performance.now();
    const ease = x => x < 0.5 ? 4*x*x*x : 1 - Math.pow(-2*x+2,3)/2;
    (function u(n) { const p = Math.min((n-s)/dur,1); el.textContent = (t*ease(p)).toFixed(d); if(p<1) requestAnimationFrame(u); })(s);
    e.target._counted = true;
  }, { threshold: 0.5 }).observe(el);
});

// —— Nav scroll ——
const topNav = document.getElementById('topNav');
window.addEventListener('scroll', () => topNav.classList.toggle('scrolled', scrollY > 60), { passive: true });

// —— Hero grid spotlight —— (only on pages with a hero section)
const heroGrid = document.querySelector('.hero-grid');
const heroEl = document.getElementById('hero');

if (heroGrid && heroEl) {
  let gx = 0, gy = 0, tx = 0, ty = 0;

  document.addEventListener('mousemove', e => {
    const heroRect = heroEl.getBoundingClientRect();
    const gridRect = heroGrid.getBoundingClientRect();
    const activeTop = heroRect.top + heroRect.height * 0.3;
    // Only track in the bottom 70% of hero
    if (e.clientY >= activeTop && e.clientY <= heroRect.bottom) {
      tx = e.clientX - gridRect.left;
      ty = e.clientY - gridRect.top;
    } else {
      tx = gridRect.width / 2;
      ty = gridRect.height * 0.3;
    }
  });

  (function lerpGrid() {
    gx += (tx - gx) * 0.08;
    gy += (ty - gy) * 0.08;
    heroGrid.style.setProperty('--mx', gx + 'px');
    heroGrid.style.setProperty('--my', gy + 'px');
    requestAnimationFrame(lerpGrid);
  })();
}

// —— Active nav + Side panels ——
const navAnchors = document.querySelectorAll('.nav-links a');
const sectionEls = document.querySelectorAll('section[id]');
const leftDots = document.querySelectorAll('.side-panel.left .side-dot');
const rightDots = document.querySelectorAll('.side-panel.right .side-dot');
const leftTrack = document.getElementById('leftTrack');
const rightTrack = document.getElementById('rightTrack');
const scrollPctEl = document.getElementById('scrollPct');

function updateNavAndPanels() {
  const y = scrollY + innerHeight * 0.4;
  const maxScroll = document.documentElement.scrollHeight - innerHeight;
  const pct = Math.min(scrollY / maxScroll, 1);

  // Active nav link
  let id = '', activeIndex = 0;
  sectionEls.forEach((s, i) => { if (y >= s.offsetTop) { id = s.id; activeIndex = i; } });
  navAnchors.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + id));

  // Side panel tracks
  const trackPct = (pct * 100).toFixed(0);
  if (leftTrack) leftTrack.style.height = trackPct + '%';
  if (rightTrack) rightTrack.style.height = trackPct + '%';
  if (scrollPctEl) scrollPctEl.textContent = String(trackPct).padStart(2, '0');

  // Side panel dots
  const leftIdx = Math.min(activeIndex, leftDots.length - 1);
  const rightIdx = Math.min(activeIndex, rightDots.length - 1);
  leftDots.forEach((d, i) => d.classList.toggle('active', i === leftIdx));
  rightDots.forEach((d, i) => d.classList.toggle('active', i === rightIdx));
}

window.addEventListener('scroll', updateNavAndPanels, { passive: true });
updateNavAndPanels();

// —— Mobile menu ——
const toggle = document.getElementById('navToggle'), menu = document.getElementById('mobileMenu');
const menuLinks = menu.querySelectorAll('.mobile-menu-link');
let menuOpen = false;
function openMenu() { menuOpen=true; toggle.classList.add('active'); toggle.setAttribute('aria-expanded','true'); menu.classList.add('open'); document.body.classList.add('menu-open'); }
function closeMenu() { if(!menuOpen) return; menuOpen=false; toggle.classList.remove('active'); toggle.setAttribute('aria-expanded','false'); menu.classList.remove('open'); document.body.classList.remove('menu-open'); }
toggle.addEventListener('click', () => menuOpen ? closeMenu() : openMenu());
menuLinks.forEach(l => l.addEventListener('click', closeMenu));
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });
window.addEventListener('resize', () => { if (innerWidth > 1024) closeMenu(); });

// —— Course select jump ——
const courseSelect = document.getElementById('courseSelect');
if (courseSelect) {
  courseSelect.addEventListener('change', () => {
    if (courseSelect.value) window.location.href = courseSelect.value;
  });
}

// —— FAQ accordion ——
const faqItems = document.querySelectorAll('.faq-item');
const faqToggleAll = document.getElementById('faqToggleAll');
let allExpanded = false;

document.querySelectorAll('.faq-question').forEach(btn => {
  btn.addEventListener('click', () => {
    btn.parentElement.classList.toggle('open');
    updateFaqToggleLabel();
  });
});

if (faqToggleAll) {
  faqToggleAll.addEventListener('click', () => {
    allExpanded = !allExpanded;
    if (allExpanded) {
      // Staggered expand — slow cascade, each waits for the previous to start breathing
      faqItems.forEach((item, i) => {
        setTimeout(() => item.classList.add('open'), i * 220);
      });
    } else {
      // Staggered collapse — reverse order
      const total = faqItems.length;
      faqItems.forEach((item, i) => {
        setTimeout(() => item.classList.remove('open'), (total - 1 - i) * 60);
      });
    }
    // Update label after all animations complete
    setTimeout(updateFaqToggleLabel, faqItems.length * 220 + 100);
  });
}

function updateFaqToggleLabel() {
  if (!faqToggleAll) return;
  const openCount = document.querySelectorAll('.faq-item.open').length;
  allExpanded = openCount === faqItems.length;
  faqToggleAll.textContent = allExpanded ? 'Collapse All' : 'Expand All';
}
