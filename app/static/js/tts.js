/* Speech synthesis helper. Speaks English text using the browser's built-in
   voices (speechSynthesis). Degrades quietly if unavailable. */
(function (global) {
  var supported = 'speechSynthesis' in global;

  function pickVoice() {
    if (!supported) return null;
    var voices = global.speechSynthesis.getVoices() || [];
    // Prefer an English (ideally British) voice for KET-style pronunciation.
    var en = voices.filter(function (v) { return /^en(-|_)/i.test(v.lang); });
    var gb = en.find(function (v) { return /GB|UK/i.test(v.lang); });
    return gb || en[0] || null;
  }

  function speak(text, opts) {
    if (!supported || !text) return;
    opts = opts || {};
    try {
      global.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(text);
      u.lang = opts.lang || 'en-GB';
      u.rate = opts.rate || 0.9;    // a touch slower for children
      u.pitch = opts.pitch || 1.05;
      var v = pickVoice();
      if (v) u.voice = v;
      global.speechSynthesis.speak(u);
    } catch (e) { /* ignore */ }
  }

  // Some browsers load voices asynchronously.
  if (supported && typeof global.speechSynthesis.onvoiceschanged !== 'undefined') {
    global.speechSynthesis.onvoiceschanged = pickVoice;
  }

  global.TTS = { speak: speak, supported: supported };
})(window);
