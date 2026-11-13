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
  const seg = (el.dataset.start ? `&start=${el.dataset.start}` : '') + (el.dataset.end ? `&end=${el.dataset.end}` : '');
  f.src = `https://www.youtube-nocookie.com/embed/${el.dataset.id}?autoplay=1&playsinline=1&enablejsapi=1&rel=0&modestbranding=1${seg}`;
  f.title = el.getAttribute('aria-label') || 'YouTube video';
  f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
  f.allowFullscreen = true;
  el.replaceWith(f);
  // Some browsers hold autoplay even after a click. Nudge the player once it has loaded.
  f.addEventListener('load', () => {
    try {
      f.contentWindow.postMessage('{"event":"command","func":"playVideo","args":[]}', '*');
    } catch (err) { /* cross-origin: the viewer presses play on the YouTube button instead */ }
  });
}));

// Brand chips + text search. Works on the Builds grid and the Reviews lists.
function wireFilter({ chips, search, items, groups, empty }) {
  if (!items.length) return;
  let brand = '*', q = '';
  const apply = () => {
    let hits = 0;
    items.forEach(el => {
      const show = (brand === '*' || el.dataset.brand === brand) &&
                   (!q || (el.dataset.search || '').includes(q));
      el.hidden = !show;
      if (show) hits++;
    });
    // hide a section heading and its list when everything inside is filtered out
    groups.forEach(([heading, list, blurb]) => {
      const any = [...list.children].some(li => !li.hidden);
      [heading, list, blurb].forEach(n => { if (n) n.hidden = !any; });
    });
    if (empty) empty.hidden = hits > 0;
  };
  chips.forEach(c => c.addEventListener('click', () => {
    chips.forEach(x => x.setAttribute('aria-pressed', String(x === c)));
    brand = c.dataset.filter;
    apply();
  }));
  if (search) search.addEventListener('input', () => { q = search.value.trim().toLowerCase(); apply(); });
}

// Builds page
const grid = document.getElementById('build-grid');
if (grid) wireFilter({
  chips: [...document.querySelectorAll('.chips .chip')],
  search: document.getElementById('build-search'),
  items: [...grid.querySelectorAll('.card')],
  groups: [],
  empty: document.querySelector('.no-hits'),
});

// Reviews page: several lists, each under its own heading
const finder = document.getElementById('rev-filter');
if (finder) {
  const lists = [...document.querySelectorAll('.rev-list')];
  wireFilter({
    chips: [...finder.querySelectorAll('.chip')],
    search: document.getElementById('rev-search'),
    items: lists.flatMap(l => [...l.children]),
    groups: lists.map(l => {
      // walk back from the list to its <h2>, picking up any <p> blurb in between
      let blurb = null, n = l.previousElementSibling;
      if (n && n.tagName === 'P') { blurb = n; n = n.previousElementSibling; }
      return [n && n.tagName === 'H2' ? n : null, l, blurb];
    }),
    empty: finder.querySelector('.no-hits'),
  });
}
