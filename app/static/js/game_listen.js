/* Listen & Choose. Hear a word, tap the matching picture card. */
(function () {
  var root = document.getElementById('game');
  if (!root) return;

  var rnd = JSON.parse(root.dataset.round || '{}');
  var questions = rnd.questions || [];
  var submitUrl = root.dataset.submitUrl;
  var backUrl = root.dataset.backUrl;
  var csrf = root.dataset.csrf;

  var idx = 0;
  var score = 0;
  var answers = {};

  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function render() {
    if (idx >= questions.length) return finish();
    var q = questions[idx];
    var opts = q.options.map(function (o) {
      return '<button class="btn-choice" data-id="' + esc(o.id) + '">' +
               '<span class="emo" style="display:inline-flex;width:64px;height:64px;' +
               'align-items:center;justify-content:center;border-radius:16px;background:' +
               esc(o.color) + '">' + esc(o.emoji) + '</span>' +
               '<span class="lbl">' + esc(o.en) + '</span>' +
             '</button>';
    }).join('');

    root.innerHTML =
      '<p class="card-count">第 ' + (idx + 1) + ' / ' + questions.length + ' 题 · ⭐ ' + score + '</p>' +
      '<div class="card" style="text-align:center">' +
        '<p class="muted">听一听，点出正确的图片</p>' +
        '<button class="speak-btn" id="say">再听一次 Listen</button>' +
      '</div>' +
      '<div class="options">' + opts + '</div>';

    document.getElementById('say').onclick = function () { TTS.speak(q.prompt_en); };
    Array.prototype.forEach.call(root.querySelectorAll('.btn-choice'), function (btn) {
      btn.onclick = function () { choose(q, btn); };
    });
    TTS.speak(q.prompt_en);
  }

  function choose(q, btn) {
    var chosen = btn.dataset.id;
    answers[q.id] = chosen;
    var buttons = root.querySelectorAll('.btn-choice');
    Array.prototype.forEach.call(buttons, function (b) {
      b.disabled = true;
      if (b.dataset.id === q.answer_id) b.classList.add('correct');
    });
    if (chosen === q.answer_id) { score += 1; } else { btn.classList.add('wrong'); }
    setTimeout(function () { idx += 1; render(); }, 900);
  }

  function finish() {
    fetch(submitUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ answers: answers })
    }).then(function (r) { return r.json(); }).then(function (d) {
      showResult(d.score, d.total, d.stars);
    }).catch(function () { showResult(score, questions.length, score); });
  }

  function showResult(s, total, stars) {
    root.innerHTML =
      '<div class="card done-banner">' +
        '<div class="big">🎉</div>' +
        '<p class="result-line">得分 ' + s + ' / ' + total + '</p>' +
        '<p>获得 ⭐ ' + (stars || 0) + ' 颗星星！</p>' +
        '<div class="btn-row" style="justify-content:center">' +
          '<a class="btn-secondary" href="' + location.pathname + '">再玩一次</a>' +
          '<a class="btn-big" href="' + backUrl + '">返回</a>' +
        '</div>' +
      '</div>';
  }

  if (questions.length) render(); else showResult(0, 0, 0);
})();
