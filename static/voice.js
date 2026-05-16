/**
 * NIDIX AI — browser voice input (STT) and spoken responses (TTS).
 * Uses Web Speech API (Chrome / Edge recommended).
 */
const Voice = (() => {
  let recognition = null;
  let listening = false;
  let speaking = false;
  let activeSpeakBtn = null;
  let voiceTranscript = '';
  let skipNextAutoSend = false;
  let opts = {};

  function supportsSTT() {
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  function supportsTTS() {
    return !!window.speechSynthesis;
  }

  function lang() {
    const el = document.getElementById('voiceLang');
    return (el && el.value) || 'fr-FR';
  }

  function autoSendEnabled() {
    const el = document.getElementById('autoSendVoice');
    return !el || el.checked;
  }

  function autoSpeakEnabled() {
    const el = document.getElementById('autoSpeak');
    return el && el.checked;
  }

  function stripForSpeech(text) {
    if (!text) return '';
    return String(text)
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function toast(msg, type) {
    if (opts.toast) opts.toast(msg, type);
  }

  function setMicUI(on) {
    const btn = document.getElementById('micBtn');
    const wrap = document.querySelector('.inp-wrap');
    if (btn) btn.classList.toggle('listening', on);
    if (wrap) wrap.classList.toggle('listening', on);
    const hint = document.getElementById('voiceHint');
    if (hint) hint.style.display = on ? '' : 'none';
  }

  function initRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return null;

    const rec = new SR();
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      listening = true;
      voiceTranscript = '';
      setMicUI(true);
    };

    rec.onresult = (event) => {
      let interim = '';
      let finalText = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += t;
        else interim += t;
      }
      const input = opts.getInput && opts.getInput();
      if (!input) return;

      if (finalText) {
        voiceTranscript = (voiceTranscript + ' ' + finalText).trim();
        input.value = voiceTranscript;
      } else {
        const base = voiceTranscript;
        input.value = base ? base + ' ' + interim : interim;
      }
      if (opts.resizeInput) opts.resizeInput(input);
    };

    rec.onerror = (event) => {
      const err = event.error || 'unknown';
      if (err !== 'aborted' && err !== 'no-speech') {
        toast('Voice input error: ' + err, 'err');
      }
      stopListening();
    };

    rec.onend = () => {
      const input = opts.getInput && opts.getInput();
      const text = (input && input.value.trim()) || voiceTranscript.trim();
      const skip = skipNextAutoSend;
      skipNextAutoSend = false;
      stopListening();
      if (!skip && text && autoSendEnabled() && opts.onSend) {
        opts.onSend();
      }
    };

    return rec;
  }

  function stopListening(suppressAutoSend) {
    if (suppressAutoSend) skipNextAutoSend = true;
    listening = false;
    setMicUI(false);
    if (recognition) {
      try { recognition.abort(); } catch (_) {}
      try { recognition.stop(); } catch (_) {}
    }
  }

  function toggleMic() {
    if (!supportsSTT()) {
      toast('Voice input is not supported in this browser. Use Chrome or Edge.', 'err');
      return;
    }
    if (opts.isBusy && opts.isBusy()) {
      toast('Wait for the current response to finish.', 'err');
      return;
    }

    if (listening) {
      stopListening();
      return;
    }

    stopSpeaking();
    if (!recognition) recognition = initRecognition();
    if (!recognition) return;

    recognition.lang = lang();
    voiceTranscript = (opts.getInput && opts.getInput().value.trim()) || '';

    try {
      recognition.start();
    } catch (e) {
      toast('Could not start microphone. Check browser permissions.', 'err');
    }
  }

  function pickVoice(utterance) {
    const voices = window.speechSynthesis.getVoices();
    const preferred = lang().toLowerCase();
    const match =
      voices.find(v => v.lang && v.lang.toLowerCase() === preferred) ||
      voices.find(v => v.lang && v.lang.toLowerCase().startsWith(preferred.split('-')[0])) ||
      voices.find(v => v.lang && v.lang.toLowerCase().startsWith('fr')) ||
      voices[0];
    if (match) utterance.voice = match;
  }

  function setSpeakBtnState(btn, state) {
    if (!btn) return;
    btn.classList.remove('speaking', 'paused');
    if (state) btn.classList.add(state);
    const label = btn.querySelector('.speak-label');
    if (label) {
      label.textContent = state === 'speaking' ? 'Stop' : 'Listen';
    }
  }

  function stopSpeaking() {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    speaking = false;
    if (activeSpeakBtn) setSpeakBtnState(activeSpeakBtn, null);
    activeSpeakBtn = null;
  }

  function speak(text, btn) {
    if (!supportsTTS()) {
      toast('Text-to-speech is not supported in this browser.', 'err');
      return;
    }
    const plain = stripForSpeech(text);
    if (!plain) return;

    if (speaking && btn === activeSpeakBtn) {
      stopSpeaking();
      return;
    }

    stopSpeaking();
    const utterance = new SpeechSynthesisUtterance(plain);
    utterance.lang = lang();
    utterance.rate = 1;
    utterance.pitch = 1;

    const start = () => {
      pickVoice(utterance);
      speaking = true;
      activeSpeakBtn = btn || null;
      if (btn) setSpeakBtnState(btn, 'speaking');
    };

    utterance.onstart = start;
    utterance.onend = () => {
      speaking = false;
      if (activeSpeakBtn) setSpeakBtnState(activeSpeakBtn, null);
      activeSpeakBtn = null;
    };
    utterance.onerror = () => {
      speaking = false;
      if (activeSpeakBtn) setSpeakBtnState(activeSpeakBtn, null);
      activeSpeakBtn = null;
    };

    if (window.speechSynthesis.getVoices().length === 0) {
      window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.onvoiceschanged = null;
        pickVoice(utterance);
        window.speechSynthesis.speak(utterance);
      };
    }
    window.speechSynthesis.speak(utterance);
  }

  function speakAnswer(messageId) {
    const mc = document.getElementById('mc-' + messageId);
    const text = (mc && mc.dataset.plainText) || (mc && mc.textContent) || '';
    const btn = document.querySelector(`[data-speak-for="${messageId}"]`);
    speak(text, btn);
  }

  function maybeAutoSpeak(text) {
    if (autoSpeakEnabled()) speak(text, null);
  }

  function savePrefs() {
    const autoSpeak = document.getElementById('autoSpeak');
    const autoSend = document.getElementById('autoSendVoice');
    const voiceLang = document.getElementById('voiceLang');
    if (autoSpeak) localStorage.setItem('autoSpeak', autoSpeak.checked ? '1' : '0');
    if (autoSend) localStorage.setItem('autoSendVoice', autoSend.checked ? '1' : '0');
    if (voiceLang) localStorage.setItem('voiceLang', voiceLang.value);
  }

  function loadPrefs() {
    const autoSpeak = document.getElementById('autoSpeak');
    const autoSend = document.getElementById('autoSendVoice');
    const voiceLang = document.getElementById('voiceLang');
    if (autoSpeak) autoSpeak.checked = localStorage.getItem('autoSpeak') === '1';
    if (autoSend) autoSend.checked = localStorage.getItem('autoSendVoice') !== '0';
    if (voiceLang) {
      const saved = localStorage.getItem('voiceLang');
      if (saved) voiceLang.value = saved;
    }
  }

  function init(options) {
    opts = options || {};
    loadPrefs();

    const micBtn = document.getElementById('micBtn');
    if (micBtn) micBtn.addEventListener('click', toggleMic);

    ['autoSpeak', 'autoSendVoice', 'voiceLang'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', savePrefs);
    });

    if (!supportsSTT() && micBtn) {
      micBtn.disabled = true;
      micBtn.title = 'Voice input not supported in this browser';
    }

    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
    }
  }

  function speakButtonHtml(messageId) {
    return `<button type="button" class="icon-btn speak-btn" data-speak-for="${messageId}"
      onclick="Voice.speakAnswer('${messageId}')" title="Listen to this response">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
        stroke-linecap="round" stroke-linejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
      </svg>
      <span class="speak-label">Listen</span>
    </button>`;
  }

  return {
    init,
    toggleMic,
    speak,
    speakAnswer,
    maybeAutoSpeak,
    stopSpeaking,
    stopListening,
    speakButtonHtml,
    stripForSpeech,
    supportsSTT,
    supportsTTS,
  };
})();
