

const ALICE_EYES_OPEN = '@@';
const ALICE_EYES_CLOSED = '--';
const ALICE_TYPE_DELAY_MS = 80;
const ALICE_BLINK_MS = 150;
const ALICE_LINE_PAUSE_MS = 1200; 

const aliceEl = document.querySelector('.alice');
const aliceCat = document.querySelector('.alice .cat');
const aliceDialog = document.querySelector('.alice .dialog');
const aliceText = document.querySelector('.alice .dialog-text');
const aliceReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let aliceTypingTimer = null;
let aliceBlinkPaused = false;

function aliceCatHTML(angry) {
  const ears  = angry ? '        /\\                /\\'    : '      .#:.              .:#.';
  const brows = angry ? '   #####  \\\\  ######  //  #####' : '   #####      ######      #####';
  const mouth = angry ? ' -=~###########/VV\\###########~=-' : ' -=~########### ww ###########~=-';
  const eye = '<span class="eye">' + ALICE_EYES_OPEN + '</span>';
  return [
    ears,
    '     .####.            .####.',
    '    .######.          .######.',
    '    ########:........:########',
    '   .##########################.',
    '   ############################',
    brows,
    '   #####  ' + eye + '  ######  ' + eye + '  #####',
    '   <span class="cheek">#####</span>      ######      <span class="cheek">#####</span>',
    "   ############.''.############",
    mouth,
    ' ~=-##########################-=~',
    "     '######################'",
    '         ################',
    '        ##################',
    '       ####################',
    '      ######################',
  ].join('\n');
}

aliceCat.innerHTML = aliceCatHTML(aliceEl.classList.contains('angry'));

function aliceGoAngry() {
  aliceEl.classList.add('angry');
  aliceCat.innerHTML = aliceCatHTML(true);
}

function aliceShy() {
  aliceEl.classList.add('shy');
  aliceBlinkPaused = true;
  aliceSetEyes(ALICE_EYES_CLOSED);
}
function aliceUnshy() {
  aliceEl.classList.remove('shy');
  aliceBlinkPaused = false;
  aliceSetEyes(ALICE_EYES_OPEN);
}

function aliceSay(text, onDone) {
  clearTimeout(aliceTypingTimer);
  aliceDialog.hidden = false;
  if (aliceReducedMotion) {
    aliceText.textContent = text;
    if (onDone) onDone();
    return;
  }
  const chars = Array.from(text); 
  let i = 0;
  (function type() {
    aliceText.textContent = chars.slice(0, ++i).join('');
    if (i < chars.length) aliceTypingTimer = setTimeout(type, ALICE_TYPE_DELAY_MS);
    else if (onDone) aliceTypingTimer = setTimeout(onDone, ALICE_LINE_PAUSE_MS);
  })();
}

function aliceSetEyes(text) {
  document.querySelectorAll('.alice .eye').forEach(eye => { eye.textContent = text; });
}
function aliceBlink(times) {
  if (aliceBlinkPaused) return; 
  aliceSetEyes(ALICE_EYES_CLOSED);
  setTimeout(() => {
    aliceSetEyes(ALICE_EYES_OPEN);
    if (times > 1) setTimeout(() => aliceBlink(times - 1), ALICE_BLINK_MS);
  }, ALICE_BLINK_MS);
}
function aliceScheduleBlink() {
  setTimeout(() => {
    aliceBlink(Math.random() < 0.25 ? 2 : 1);
    aliceScheduleBlink();
  }, 2000 + Math.random() * 4000);
}
if (!aliceReducedMotion) aliceScheduleBlink();
