/* Frog River: find the English word to help the frog cross the river. */
(function () {
  var root = document.getElementById('frog-game');
  if (!root) return;

  var rnd = JSON.parse(root.dataset.round || '{}');
  var questions = rnd.questions || [];
  var submitUrl = root.dataset.submitUrl;
  var backUrl = root.dataset.backUrl;
  var csrf = root.dataset.csrf;
  var index = 0;
  var step = 0;
  var answers = {};
  var submitting = false;

  function esc(value) {
    var div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function buildRiver() {
    root.innerHTML =
      '<div class="frog-river" aria-label="小青蛙跳过荷叶的进度">' +
        '<div class="river-bank bank-left" aria-hidden="true">🌿</div>' +
        '<div class="lily-pad pad-1" aria-hidden="true">🍃</div>' +
        '<div class="lily-pad pad-2" aria-hidden="true">🍃</div>' +
        '<div class="lily-pad pad-3" aria-hidden="true">🍃</div>' +
        '<div class="lily-pad pad-4" aria-hidden="true">🍃</div>' +
        '<div class="river-bank bank-right" aria-hidden="true">🌼</div>' +
        '<div class="frog" id="frog" role="img" aria-label="小青蛙">🐸</div>' +
      '</div>' +
      '<div id="frog-question"></div>';
  }

  function moveFrog() {
    var frog = document.getElementById('frog');
    frog.style.setProperty('--frog-step', step);
    frog.classList.remove('frog-jump');
    void frog.offsetWidth;
    frog.classList.add('frog-jump');
  }

  function renderQuestion() {
    if (index >= questions.length) return finish();
    var question = questions[index];
    var panel = document.getElementById('frog-question');
    var options = question.options.map(function (option) {
      return '<button class="frog-word" data-id="' + esc(option.id) + '">' +
        esc(option.en) + '</button>';
    }).join('');

    panel.innerHTML =
      '<p class="card-count">第 ' + (index + 1) + ' / ' + questions.length +
        ' 题 · 已跳 ' + step + ' 步</p>' +
      '<div class="card frog-question-card">' +
        '<p class="muted">请找到这个词 Find the word</p>' +
        '<div class="frog-prompt"><span>' + esc(question.emoji) + '</span> ' +
          esc(question.prompt_zh) + '</div>' +
        '<div class="frog-options">' + options + '</div>' +
        '<p class="frog-feedback" id="frog-feedback" aria-live="polite">选对了，小青蛙才会跳哦！</p>' +
      '</div>';

    Array.prototype.forEach.call(panel.querySelectorAll('.frog-word'), function (button) {
      button.onclick = function () { choose(question, button); };
    });
    if (index > 0) {
      var firstOption = panel.querySelector('.frog-word');
      if (firstOption) firstOption.focus();
    }
  }

  function choose(question, button) {
    var chosen = button.dataset.id;
    if (!(question.id in answers)) answers[question.id] = chosen;
    var feedback = document.getElementById('frog-feedback');

    if (chosen !== question.answer_id) {
      button.classList.add('wrong');
      button.disabled = true;
      feedback.textContent = '再找找看！小青蛙在等你 🐸';
      var frog = document.getElementById('frog');
      frog.classList.remove('frog-wiggle');
      void frog.offsetWidth;
      frog.classList.add('frog-wiggle');
      return;
    }

    Array.prototype.forEach.call(root.querySelectorAll('.frog-word'), function (item) {
      item.disabled = true;
      if (item.dataset.id === question.answer_id) item.classList.add('correct');
    });
    feedback.textContent = index === questions.length - 1 ?
      '答对啦！小青蛙到达河对岸！' : '答对啦！小青蛙向前跳！';
    step += 1;
    moveFrog();
    window.setTimeout(function () {
      index += 1;
      renderQuestion();
    }, 950);
  }

  function finish() {
    if (submitting) return;
    submitting = true;
    var panel = document.getElementById('frog-question');
    panel.innerHTML =
      '<div class="card done-banner"><div class="big">🐸🎉</div>' +
      '<p>小青蛙过河啦！正在保存成绩……</p></div>';

    fetch(submitUrl, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
      body: JSON.stringify({answers: answers})
    }).then(function (response) {
      if (!response.ok) throw new Error('save failed');
      return response.json();
    }).then(function (data) {
      panel.innerHTML =
        '<div class="card done-banner"><div class="big">🐸🎉</div>' +
        '<p class="result-line">小青蛙成功过河！</p>' +
        '<p>首次答对 ' + data.score + ' / ' + data.total + '，获得 ⭐ ' +
          (data.stars || 0) + ' 颗星星！</p>' +
        '<div class="btn-row" style="justify-content:center">' +
          '<a class="btn-secondary" href="' + location.pathname + '">再玩一次</a>' +
          '<a class="btn-big" href="' + backUrl + '">返回游戏</a>' +
        '</div></div>';
    }).catch(function () {
      panel.innerHTML =
        '<div class="card done-banner"><div class="big">🐸</div>' +
        '<p>小青蛙已经过河，但成绩没有保存成功。</p>' +
        '<a class="btn-big" href="' + backUrl + '">返回游戏</a></div>';
    });
  }

  buildRiver();
  moveFrog();
  if (questions.length) renderQuestion(); else finish();
})();
