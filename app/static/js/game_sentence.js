/* Build a Sentence. Tap scrambled word-blocks to place them in order. */
(function () {
  var root = document.getElementById('game');
  if (!root) return;

  var rnd = JSON.parse(root.dataset.round || '{}');
  var questions = rnd.questions || [];
  var submitUrl = root.dataset.submitUrl;
  var backUrl = root.dataset.backUrl;
  var csrf = root.dataset.csrf;

  var idx = 0;
  var answers = {};
  var placed = [];   // tokens currently in the sentence slot for this question

  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function render() {
    if (idx >= questions.length) return finish();
    var q = questions[idx];
    placed = [];

    var bank = q.tokens.map(function (t, k) {
      return '<button class="token" data-k="' + k + '">' + esc(t) + '</button>';
    }).join('');

    root.innerHTML =
      '<p class="card-count">第 ' + (idx + 1) + ' / ' + questions.length + ' 题</p>' +
      '<div class="card">' +
        '<p class="hint">提示 Hint: <strong>' + esc(q.hint_zh) + '</strong></p>' +
        '<div class="sentence-target" id="target" aria-label="Your sentence"></div>' +
        '<p class="muted">点词块放进句子；点句子里的词块可以拿回。</p>' +
        '<div class="token-bank" id="bank">' + bank + '</div>' +
        '<button class="btn-big" id="done" style="width:100%">完成 Done</button>' +
      '</div>';

    var bankEl = document.getElementById('bank');
    Array.prototype.forEach.call(bankEl.querySelectorAll('.token'), function (btn) {
      btn.onclick = function () { toBank(btn, q); };
    });
    document.getElementById('done').onclick = function () { done(q); };
    redrawTarget();
  }

  function toBank(btn, q) {
    if (btn.classList.contains('used')) return;
    btn.classList.add('used');
    placed.push({ k: btn.dataset.k, text: q.tokens[btn.dataset.k] });
    redrawTarget();
  }

  function redrawTarget() {
    var target = document.getElementById('target');
    if (placed.length === 0) { target.innerHTML = '<span class="muted">…</span>'; return; }
    target.innerHTML = placed.map(function (p, pos) {
      return '<button class="token slot-token" data-pos="' + pos + '">' + esc(p.text) + '</button>';
    }).join('');
    Array.prototype.forEach.call(target.querySelectorAll('.slot-token'), function (btn) {
      btn.onclick = function () { removeAt(parseInt(btn.dataset.pos, 10)); };
    });
  }

  function removeAt(pos) {
    var item = placed.splice(pos, 1)[0];
    if (item) {
      var b = root.querySelector('.token[data-k="' + item.k + '"]');
      if (b) b.classList.remove('used');
    }
    redrawTarget();
  }

  function done(q) {
    answers[q.id] = placed.map(function (p) { return p.text; });
    idx += 1;
    render();
  }

  function finish() {
    fetch(submitUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ answers: answers })
    }).then(function (r) { return r.json(); }).then(function (d) {
      showResult(d.score, d.total, d.stars);
    }).catch(function () { showResult(0, questions.length, 0); });
  }

  function showResult(s, total, stars) {
    root.innerHTML =
      '<div class="card done-banner">' +
        '<div class="big">🎉</div>' +
        '<p class="result-line">拼对 ' + s + ' / ' + total + '</p>' +
        '<p>获得 ⭐ ' + (stars || 0) + ' 颗星星！</p>' +
        '<div class="btn-row" style="justify-content:center">' +
          '<a class="btn-secondary" href="' + location.pathname + '">再玩一次</a>' +
          '<a class="btn-big" href="' + backUrl + '">返回</a>' +
        '</div>' +
      '</div>';
  }

  if (questions.length) render(); else showResult(0, 0, 0);
})();
