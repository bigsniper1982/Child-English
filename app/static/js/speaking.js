/* School Helper — controlled speaking practice.
   Uses the browser SpeechRecognition API when available, always with a text
   fallback. Raw audio is never uploaded: only the recognised text is sent so
   the server can give keyword feedback. */
(function () {
  var root = document.getElementById('chat');
  if (!root) return;

  var turns = JSON.parse(root.dataset.turns || '[]');
  var theme = root.dataset.theme || 'school_life';
  var attemptUrl = root.dataset.attemptUrl;
  var csrf = root.dataset.csrf;
  var backUrl = root.dataset.backUrl;

  var idx = 0;
  var misses = 0;   // consecutive unrecognised attempts

  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var recognition = null;
  if (SR) {
    recognition = new SR();
    recognition.lang = 'en-GB';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
  }

  function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; }

  function render() {
    if (idx >= turns.length) return finish();
    var t = turns[idx];
    var kw = t.keywords.slice(0, 6).map(function (k) {
      return '<button class="kw" data-kw="' + esc(k) + '">' + esc(k) + '</button>';
    }).join('');

    root.innerHTML =
      '<div class="card">' +
        '<p class="card-count">Turn ' + (idx + 1) + ' / ' + turns.length + '</p>' +
        '<p class="turn-q">🦊 ' + esc(t.question) + '</p>' +
        '<button class="speak-btn" id="hear">听问题 Hear it</button>' +
        '<p class="frame">💡 ' + esc(t.sentence_frame) + '</p>' +
        '<p class="muted">需要帮忙？点一个词 Tap a word to help:</p>' +
        '<div class="kw-row">' + kw + '</div>' +
        '<div style="text-align:center;margin:12px 0">' +
          (recognition ? '<button class="mic-btn" id="mic" aria-label="Speak">🎤</button>' : '') +
        '</div>' +
        '<label class="muted" for="say-input">或直接打字 Or type your answer:</label>' +
        '<input class="speak-input" id="say-input" type="text" autocomplete="off" ' +
               'placeholder="' + esc(t.sentence_frame.replace("____","...")) + '">' +
        '<div class="btn-row" style="margin-top:10px">' +
          '<button class="btn-secondary" id="skip" style="flex:1;display:none">跳过 Skip ➡</button>' +
          '<button class="btn-big" id="send" style="flex:2">说好了 Send</button>' +
        '</div>' +
        '<div id="fb"></div>' +
      '</div>';

    document.getElementById('hear').onclick = function () { TTS.speak(t.question); };
    var input = document.getElementById('say-input');
    Array.prototype.forEach.call(root.querySelectorAll('.kw'), function (b) {
      b.onclick = function () {
        input.value = t.sentence_frame.replace('____', b.dataset.kw);
      };
    });
    document.getElementById('send').onclick = function () { submit(input.value); };

    var skipBtn = document.getElementById('skip');
    skipBtn.onclick = function () { next(); };
    if (misses >= 2) skipBtn.style.display = '';

    if (recognition) setupMic(input);
    TTS.speak(t.question);
  }

  function setupMic(input) {
    var mic = document.getElementById('mic');
    if (!mic) return;
    mic.onclick = function () {
      try {
        mic.classList.add('recording');
        recognition.start();
      } catch (e) { mic.classList.remove('recording'); }
    };
    recognition.onresult = function (ev) {
      var text = ev.results[0][0].transcript;
      input.value = text;                 // show what was heard, do NOT store audio
      mic.classList.remove('recording');
      submit(text);
    };
    recognition.onerror = function () {
      mic.classList.remove('recording');
      showHeard('（没听清，可以再试一次，或直接打字）');
    };
    recognition.onend = function () { mic.classList.remove('recording'); };
  }

  function showHeard(msg) {
    var fb = document.getElementById('fb');
    if (fb) fb.innerHTML = '<p class="transcript">' + esc(msg) + '</p>';
  }

  function submit(text) {
    fetch(attemptUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ turn: idx, text: text, theme: theme })
    }).then(function (r) { return r.json(); }).then(function (d) {
      handle(d, text);
    }).catch(function () { showHeard('网络出了点问题，请再试一次。'); });
  }

  function handle(d, text) {
    var fb = document.getElementById('fb');
    var extra = '';
    if (d.hit && d.advance) {
      misses = 0;
      extra = '<div class="btn-row" style="margin-top:10px">' +
              '<button class="btn-big" id="next" style="width:100%">下一个 Next ➡</button></div>';
    } else {
      if (!text || d.allow_skip) misses += 1;
      var skipBtn = document.getElementById('skip');
      if (misses >= 2 && skipBtn) skipBtn.style.display = '';
    }
    fb.innerHTML =
      (text ? '<p class="transcript">你说：“' + esc(text) + '”</p>' : '') +
      '<div class="feedback">🦊 ' + esc(d.feedback) + '</div>' + extra;
    var nx = document.getElementById('next');
    if (nx) nx.onclick = next;
  }

  function next() { idx += 1; misses = 0; render(); }

  function finish() {
    root.innerHTML =
      '<div class="card done-banner">' +
        '<div class="big">🌟🦊🌟</div>' +
        '<p>你和 School Helper 聊完啦，太棒了！</p>' +
        '<a class="btn-big" href="' + backUrl + '">返回今日任务</a>' +
      '</div>';
  }

  if (turns.length) render(); else finish();
})();
