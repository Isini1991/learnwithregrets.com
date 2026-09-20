const $ = (s) => document.querySelector(s);
const CAT = window.CATALOG;

/* ---------- hero sleeve shuffle ---------- */
const shuffleButton = $('#shuffle-records');
const heroFront = $('.front-sleeve');
let shuffleBag = [];
let shuffling = false;
shuffleButton.addEventListener('click', async () => {
  if (shuffling) return;
  shuffling = true;
  shuffleButton.setAttribute('aria-busy', 'true');
  const previous = Number(heroFront.dataset.album);
  if (!shuffleBag.length) {
    shuffleBag = CAT.map((_, i) => i).filter(i => i !== previous);
    for (let i = shuffleBag.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffleBag[i], shuffleBag[j]] = [shuffleBag[j], shuffleBag[i]];
    }
  }
  const next = shuffleBag.pop();
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const stack = $('.sleeves');
  const rear = $('.back-one');
  const middle = $('.back-two');
  const animations = [];
  const move = (el, frames, duration, delay = 0) => {
    const animation = el.animate(frames.map(transform => ({transform})), {
      duration: reduced ? 0 : duration, delay: reduced ? 0 : delay,
      easing: 'cubic-bezier(.22,.75,.2,1)', fill: 'forwards'
    });
    animations.push(animation);
    return animation.finished;
  };
  const clearAnimations = () => { animations.splice(0).forEach(a => a.cancel()); };
  try {
    const image = new Image(); image.src = CAT[next].asset;
    await image.decode();
    stack.classList.add('is-shuffling');
    // Open a three-dimensional fan. Every sleeve stays solid.
    await Promise.all([
      move(heroFront, ['translate3d(0,0,0) rotate(0deg)', 'translate3d(-27%,-12%,130px) rotate(-21deg) rotateY(18deg)'], 470),
      move(middle, ['rotate(5deg) translate(12px,-8px)', 'translate3d(23%,-5%,45px) rotate(21deg) rotateY(-18deg)'], 470, 65),
      move(rear, ['rotate(-7deg) translate(-14px,6px)', 'translate3d(-3%,-19%,-60px) rotate(-5deg) rotateX(15deg)'], 470, 110)
    ]);
    // Sweep the outgoing record under the deck while the next rises.
    await Promise.all([
      move(heroFront, ['translate3d(-27%,-12%,130px) rotate(-21deg) rotateY(18deg)', 'translate3d(-34%,8%,-100px) rotate(-28deg) rotateY(30deg)', 'translate3d(0,7%,-130px) rotate(7deg)'], 440),
      move(middle, ['translate3d(23%,-5%,45px) rotate(21deg) rotateY(-18deg)', 'translate3d(12%,-16%,150px) rotate(12deg) rotateY(-8deg)'], 440),
      move(rear, ['translate3d(-3%,-19%,-60px) rotate(-5deg) rotateX(15deg)', 'translate3d(-17%,-3%,20px) rotate(-17deg)'], 440)
    ]);
    const backOne = $('.back-one img');
    const backTwo = $('.back-two img');
    backOne.src = backTwo.src; backOne.alt = backTwo.alt;
    backTwo.src = CAT[previous].asset; backTwo.alt = CAT[previous].title + ' cover';
    heroFront.dataset.album = String(next);
    heroFront.setAttribute('aria-label', 'Open ' + CAT[next].title + ' in the listening room');
    $('.front-sleeve img').src = CAT[next].asset;
    $('.front-sleeve img').alt = CAT[next].title + ' cover';
    $('.sleeve-bar span').textContent = 'BOY / ' + CAT[next].title.toUpperCase();
    clearAnimations();
    await Promise.all([
      move(heroFront, ['translate3d(12%,-16%,150px) rotate(12deg) rotateY(-8deg)', 'translate3d(-2%,2%,15px) rotate(-3deg)', 'translate3d(1%,-1%,0) rotate(1deg)', 'translate3d(0,0,0) rotate(0deg)'], 640),
      move(middle, ['translate3d(0,7%,-130px) rotate(7deg)', 'rotate(5deg) translate(12px,-8px)'], 520, 30),
      move(rear, ['translate3d(-17%,-3%,20px) rotate(-17deg)', 'rotate(-7deg) translate(-14px,6px)'], 560, 60)
    ]);
  } finally {
    clearAnimations();
    stack.classList.remove('is-shuffling');
    shuffling = false;
    shuffleButton.removeAttribute('aria-busy');
  }
});

/* ---------- catalog ---------- */
const catalog = $('#catalog');
function sleeves() {
  catalog.className = 'catalog';
  catalog.innerHTML = CAT.map((a, i) => `
    <button class="card" data-album="${i}" aria-label="Open ${a.title} in the listening room">
      <span class="cover"><img src="${a.asset}" alt="${a.title} cover" loading="lazy" width="500" height="500"></span>
      <h3>${a.title}${a.title === 'For Lovers' ? '<span class="new-tag">JUST OUT</span>' : ''}</h3>
      <span class="cdate">${a.date}</span>
    </button>`).join('');
}
function indexView() {
  catalog.className = 'catalog list';
  const sorted = CAT.map((a, i) => ({ a, i })).sort((x, y) => y.a.iso.localeCompare(x.a.iso));
  catalog.innerHTML = sorted.map(({ a, i }, n) => `
    <button class="card" data-album="${i}" aria-label="Open ${a.title} in the listening room">
      <span class="list-num">${String(n + 1).padStart(2, '0')}</span>
      <span class="cover"><img src="${a.asset}" alt="" loading="lazy" width="44" height="44"></span>
      <h3>${a.title}${a.title === 'For Lovers' ? '<span class="new-tag">JUST OUT</span>' : ''}</h3>
      <span class="cdate">${a.date}</span>
      <span class="list-meta">${a.tracks.length} TRACKS</span>
    </button>`).join('');
}
sleeves();
$('#grid-view').addEventListener('click', () => {
  sleeves(); $('#grid-view').classList.add('active'); $('#list-view').classList.remove('active');
  $('#grid-view').setAttribute('aria-pressed', 'true'); $('#list-view').setAttribute('aria-pressed', 'false');
});
$('#list-view').addEventListener('click', () => {
  indexView(); $('#list-view').classList.add('active'); $('#grid-view').classList.remove('active');
  $('#list-view').setAttribute('aria-pressed', 'true'); $('#grid-view').setAttribute('aria-pressed', 'false');
});

/* ---------- featured tracks (For Lovers) ---------- */
const featured = CAT.findIndex(a => a.title === 'For Lovers');
const picks = CAT[featured].tracks.filter(t => !/skit/i.test(t.t)).slice(0, 4);
$('#featured-tracks').innerHTML = picks.map(t => `
  <button class="track-row" data-album="${featured}" data-track="${t.t}">
    <span class="idx">▶</span><span>${t.t}</span><span class="dur">${t.d}</span>
  </button>`).join('');

/* ---------- listening room dialog ---------- */
const dialog = $('#record-dialog');
let current = null;
function openRecord(i, trackTitle) {
  const a = CAT[i]; current = a;
  $('#dialog-art').src = a.asset;
  $('#dialog-art').alt = a.title + ' cover';
  $('#record-meta').textContent = 'BOY / ' + a.date;
  $('#record-title').textContent = a.title;
  $('#record-note').textContent = a.about || '';
  $('#record-tracks').innerHTML = a.tracks.map((t, n) =>
    `<li><span class="n">${String(n + 1).padStart(2, '0')}</span><span>${t.t}</span><span class="d">${t.d}</span></li>`).join('');
  $('#player').innerHTML = '';
  $('#load-player').style.display = 'inline-block';
  $('#buy-link').href = a.url;
  dialog.showModal();
  // Playback is explicitly loaded by the listener.
}
function loadPlayer(trackTitle) {
  if (!current) return;
  const t = '';
  $('#player').innerHTML =
    `<iframe title="Bandcamp player for ${current.title}" src="https://bandcamp.com/EmbeddedPlayer/album=${current.id}${t}/size=large/tracklist=true/artwork=small/seamless=true" loading="lazy" allowfullscreen></iframe>`;
  $('#load-player').style.display = 'none';
}
$('#load-player').addEventListener('click', () => loadPlayer());
$('#close-dialog').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', e => { const r=dialog.getBoundingClientRect(); if(e.target===dialog && (e.clientX<r.left || e.clientX>r.right || e.clientY<r.top || e.clientY>r.bottom)) dialog.close(); });
dialog.addEventListener('close',()=>{ $('#player').replaceChildren(); document.body.style.overflow=''; });
dialog.addEventListener('cancel',()=>{ $('#player').replaceChildren(); });
document.addEventListener('click', e => {
  const el = e.target.closest('[data-album]');
  if (!el) return;
  openRecord(Number(el.dataset.album), el.dataset.track);
});
