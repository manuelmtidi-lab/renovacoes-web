(function () {
  "use strict";

  var reduzir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function formatar(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }

  // Contador: sobe de 0 ao valor final, uma vez (800 ms).
  function contar(el) {
    var texto = el.textContent.trim();
    var alvo = parseInt(texto.replace(/\D/g, ""), 10);
    if (isNaN(alvo) || alvo === 0) return;
    var inicio = null;
    var duracao = 800;
    function passo(t) {
      if (inicio === null) inicio = t;
      var p = Math.min((t - inicio) / duracao, 1);
      var e = p === 1 ? 1 : 1 - Math.pow(2, -10 * p);
      if (p < 1) {
        el.textContent = formatar(Math.round(alvo * e));
        requestAnimationFrame(passo);
      } else {
        el.textContent = texto;
      }
    }
    requestAnimationFrame(passo);
  }

  function iniciar() {
    if (!reduzir) {
      document.querySelectorAll("[data-contador]").forEach(contar);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }

  // Brilho que segue o rato (só com rato, não em ecrã tátil).
  if (!reduzir) {
    document.addEventListener("pointermove", function (e) {
      if (e.pointerType !== "mouse") return;
      var c = e.target.closest ? e.target.closest(".cartao") : null;
      if (!c) return;
      var r = c.getBoundingClientRect();
      c.style.setProperty("--mx", e.clientX - r.left + "px");
      c.style.setProperty("--my", e.clientY - r.top + "px");
    }, { passive: true });
  }
})();
