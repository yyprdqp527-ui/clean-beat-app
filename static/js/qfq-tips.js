/* ================================
   QFQ TIPS — Système bulles d'aide
   ================================ */

// CSS injecté dynamiquement
var QFQ_TIPS_CSS = `
.qfq-tip {
  position: fixed;
  z-index: 9999;
  max-width: 260px;
  padding: 14px 16px 10px;
  border-radius: 20px;
  background: rgba(255,255,255,0.92) !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.45);
  box-shadow: 0 6px 20px rgba(21,48,54,0.2),
              0 0 0 1px rgba(255,255,255,0.5);
  font-family: 'Montserrat', sans-serif;
  cursor: pointer;
  animation: qfqTipIn 0.3s ease;
  color: #153036 !important;
}
@keyframes qfqTipIn {
  0% { opacity:0; transform:scale(0.85); }
  100% { opacity:1; transform:scale(1); }
}
.qfq-tip-text {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.45;
  color: #153036 !important;
}
.qfq-tip-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  gap: 6px;
}
.qfq-tip-prev,
.qfq-tip-next {
  background: rgba(21,48,54,0.12);
  border: 1px solid rgba(21,48,54,0.2);
  border-radius: 20px;
  color: #153036 !important;
  font-size: 13px;
  font-weight: 600;
  padding: 4px 10px;
  cursor: pointer;
}
.qfq-tip-prev:disabled {
  opacity: 0.3;
  cursor: default;
}
.qfq-tip-counter {
  font-size: 11px;
  color: rgba(21,48,54,0.5) !important;
  font-weight: 500;
}
/* Triangle rouge pointeur */
.qfq-tip::before {
  content: '';
  position: absolute;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
}
.qfq-tip.pos-bottom::before {
  top: -18px;
  left: var(--arrow-left, 50%);
  transform: translateX(-50%);
  border-bottom: 18px solid #ff4757;
}
.qfq-tip.pos-top::before {
  bottom: -18px;
  left: var(--arrow-left, 50%);
  transform: translateX(-50%);
  border-top: 18px solid #ff4757;
}
/* Overlay semi-transparent derrière la cible */
.qfq-tip-highlight {
  position: fixed;
  z-index: 9998;
  border-radius: 12px;
  box-shadow: 0 0 0 9999px rgba(0,0,0,0.35);
  pointer-events: none;
  transition: all 0.3s ease;
}
`;

// Fonctions partagées
window.QfqTips = {

  _currentIndex: 0,
  _tips: [],
  _tipEl: null,
  _highlightEl: null,
  _doneKey: null,
  _doneCallback: null,

  init: function(tips, doneKey, doneCallback) {
    // Injecte le CSS si pas encore fait
    if (!document.getElementById('qfq-tips-style')) {
      var style = document.createElement('style');
      style.id = 'qfq-tips-style';
      style.textContent = QFQ_TIPS_CSS;
      document.head.appendChild(style);
    }
    this._tips = tips;
    this._doneKey = doneKey;
    this._doneCallback = doneCallback;
    this._currentIndex = 0;
    // Crée overlay bloquant
    var overlay = document.createElement('div');
    overlay.id = 'qfq-tips-overlay';
    overlay.style.cssText =
      'position:fixed;inset:0;' +
      'z-index:9997;' +
      'background:rgba(0,0,0,0.5);' +
      'backdrop-filter:blur(2px);' +
      '-webkit-backdrop-filter:blur(2px);';
    document.body.appendChild(overlay);
    this.show(0);
  },

  show: function(index) {
    this.remove();
    if (index >= this._tips.length) {
      this.done();
      return;
    }
    var tip = this._tips[index];
    var target = document.querySelector(tip.target);
    if (!target) {
      this.show(index + 1);
      return;
    }

    // Highlight de la cible
    var rect = target.getBoundingClientRect();
    this._highlightEl = document.createElement('div');
    this._highlightEl.className = 'qfq-tip-highlight';
    this._highlightEl.style.cssText =
      'top:' + (rect.top - 6) + 'px;' +
      'left:' + (rect.left - 6) + 'px;' +
      'width:' + (rect.width + 12) + 'px;' +
      'height:' + (rect.height + 12) + 'px;';
    document.body.appendChild(this._highlightEl);

    // Bulle
    this._tipEl = document.createElement('div');
    this._tipEl.className = 'qfq-tip pos-' +
      (tip.position || 'bottom');

    var total = this._tips.length;
    this._tipEl.innerHTML =
      '<div class="qfq-tip-text">' +
        tip.text +
      '</div>' +
      '<div class="qfq-tip-nav">' +
        '<button class="qfq-tip-prev"' +
          (index === 0 ? ' disabled' : '') +
          '>←</button>' +
        '<span class="qfq-tip-counter">' +
          (index + 1) + '/' + total +
        '</span>' +
        '<button class="qfq-tip-next">→</button>' +
      '</div>';

    document.body.appendChild(this._tipEl);

    // Attend le rendu pour que offsetHeight soit correct
    var self2 = this;
    var tgt2 = target;
    var pos2 = tip.position || 'bottom';
    requestAnimationFrame(function() {
      self2._position(tgt2, pos2);
    });

    // Navigation
    var self = this;
    this._tipEl.querySelector('.qfq-tip-next')
      .addEventListener('click', function(e) {
        e.stopPropagation();
        self._currentIndex++;
        self.show(self._currentIndex);
      });
    this._tipEl.querySelector('.qfq-tip-prev')
      .addEventListener('click', function(e) {
        e.stopPropagation();
        self._currentIndex--;
        self.show(self._currentIndex);
      });
  },

  _position: function(target, position) {
    var rect = target.getBoundingClientRect();
    var tipW = 260;
    var tipH = this._tipEl.offsetHeight || 100;
    var margin = 22;

    var left = rect.left + rect.width / 2 - tipW / 2;
    left = Math.max(10,
      Math.min(left, window.innerWidth - tipW - 10));

    var top;
    if (position === 'bottom') {
      top = rect.bottom + margin;
    } else {
      top = rect.top - tipH - margin;
    }
    // Clamping vertical : jamais hors viewport
    top = Math.max(10, Math.min(top, window.innerHeight - tipH - 10));

    // Position flèche rouge sur la cible
    var arrowLeft = rect.left + rect.width / 2 - left;
    arrowLeft = Math.max(20,
      Math.min(arrowLeft, tipW - 20));

    this._tipEl.style.top = top + 'px';
    this._tipEl.style.left = left + 'px';
    this._tipEl.style.setProperty(
      '--arrow-left', arrowLeft + 'px');
  },

  remove: function() {
    if (this._tipEl) {
      this._tipEl.remove();
      this._tipEl = null;
    }
    if (this._highlightEl) {
      this._highlightEl.remove();
      this._highlightEl = null;
    }
  },

  done: function() {
    this.remove();
    // Supprime l'overlay bloquant
    var overlay = document.getElementById('qfq-tips-overlay');
    if (overlay) overlay.remove();
    if (this._doneKey) {
      localStorage.setItem(this._doneKey, '1');
    }
    window.dispatchEvent(new Event('qfq_tips_done'));
    if (typeof this._doneCallback === 'function') {
      this._doneCallback();
    }
  }
};
