/* Flash-card learning / review flow. One card at a time, English audio,
   "I know it" vs "practise again", server-saved progress. */
(function () {
  var deck = document.getElementById('deck');
  if (!deck) return;

  var words = JSON.parse(deck.dataset.words || '[]');
  var reviewUrl = deck.dataset.reviewUrl;
  var csrf = deck.dataset.csrf;
  var todayUrl = deck.dataset.todayUrl;
  var mode = deck.dataset.mode;
  var i = 0;
  var submitting = false;

  var count = document.getElementById('cardcount');

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : s;
    return d.innerHTML;
  }

  function render() {
    if (i >= words.length) { return finish(); }
    var w = words[i];
    if (count) count.textContent = (i + 1) + ' / ' + words.length;
    var againLabel = mode === 'learn' ? '⏰ 稍后复习' :
      (mode === 'practice' ? '⏭️ 下一个' : '🔁 再练一次');
    deck.innerHTML =
      '<div class="wordcard pop">' +
        '<div class="visual" style="background:' + esc(w.color) + '">' + esc(w.emoji) + '</div>' +
        '<div class="en">' + esc(w.en) + '</div>' +
        '<div class="pos">' + esc(w.pos) + '</div>' +
        '<div class="zh">' + esc(w.zh) + '</div>' +
        '<button class="speak-btn" id="say">Listen</button>' +
        '<div><span class="chunk">' + esc(w.chunk) + '</span></div>' +
        '<div class="example">' + esc(w.example) + '</div>' +
        '<div class="btn-row" style="margin-top:16px">' +
          '<button class="btn-choice btn-again" id="again" style="flex:1">' + againLabel + '</button>' +
          '<button class="btn-choice btn-know" id="know" style="flex:1">✅ 我认识</button>' +
        '</div>' +
      '</div>';

    document.getElementById('say').onclick = function () { TTS.speak(w.en); };
    document.getElementById('know').onclick = function () { answer(w.id, true); };
    document.getElementById('again').onclick = function () { answer(w.id, false); };
    // auto play the word on arrival
    TTS.speak(w.en);
  }

  function answer(wordId, correct) {
    if (mode === 'practice') {
      i += 1;
      render();
      return;
    }
    if (submitting) return;
    submitting = true;
    document.getElementById('again').disabled = true;
    document.getElementById('know').disabled = true;
    fetch(reviewUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ word_id: wordId, correct: correct, mode: mode })
    }).then(function (response) {
      if (!response.ok) throw new Error('save failed');
      submitting = false;
      i += 1;
      render();
    }).catch(function () {
      submitting = false;
      document.getElementById('again').disabled = false;
      document.getElementById('know').disabled = false;
      window.alert('没有保存成功，请再试一次。');
    });
  }

  function finish() {
    if (count) count.textContent = '';
    var message = mode === 'review' ? '复习完成！' :
      (mode === 'practice' ? '自由巩固完成！' : '新词学完啦！');
    deck.innerHTML =
      '<div class="done-banner">' +
        '<div class="big">🎉</div>' +
        '<p>' + message + '</p>' +
        '<a class="btn-secondary" href="' + todayUrl + '">回到今日任务</a>' +
      '</div>';
  }

  if (words.length) render(); else finish();
})();
