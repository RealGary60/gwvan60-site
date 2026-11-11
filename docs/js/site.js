// Mobile menu
const btn = document.querySelector('.menu-btn');
const nav = document.getElementById('nav');
if (btn && nav) btn.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  btn.setAttribute('aria-expanded', String(open));
});

// Click-to-play YouTube: nothing loads from YouTube until a visitor presses play.
document.querySelectorAll('.yt').forEach(el => el.addEventListener('click', () => {
  const f = document.createElement('iframe');
  f.src = `https://www.youtube-nocookie.com/embed/${el.dataset.id}?autoplay=1&rel=0&modestbranding=1`;
  f.title = el.getAttribute('aria-label') || 'YouTube video';
  f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
  f.allowFullscreen = true;
  el.replaceWith(f);
}));

// Brand filter on the Builds page
const chips = document.querySelectorAll('.chip');
chips.forEach(c => c.addEventListener('click', () => {
  chips.forEach(x => x.setAttribute('aria-pressed', String(x === c)));
  const f = c.dataset.filter;
  document.querySelectorAll('#build-grid .card').forEach(card => {
    card.hidden = !(f === '*' || card.dataset.brand === f);
  });
}));
