/* Aviso "Instalar app" (PWA). Só aparece em HTTPS ou localhost, e nunca se a app já está instalada. */
(function () {
  "use strict";
  var CHAVE = "instalar-adiado";
  var ADIAR_DIAS = 7;
  var forcar = /[?&]instalar=ver\b/.test(location.search);

  function instalada() {
    return (window.matchMedia && matchMedia("(display-mode: standalone)").matches) || navigator.standalone === true;
  }
  function adiado() {
    try {
      var t = parseInt(localStorage.getItem(CHAVE) || "0", 10);
      return t && Date.now() - t < ADIAR_DIAS * 864e5;
    } catch (e) { return false; }
  }
  function adiar() {
    try { localStorage.setItem(CHAVE, String(Date.now())); } catch (e) {}
  }
  if (instalada() || (adiado() && !forcar)) return;
  if (!window.isSecureContext && !forcar) return;

  var ua = navigator.userAgent || "";
  var ios = /iphone|ipad|ipod/i.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
  var android = /android/i.test(ua);
  var movel = ios || android;
  var pedido = null;
  var aviso = null;

  function estilos() {
    var s = document.createElement("style");
    s.textContent =
      ".instalar{position:fixed;z-index:60;left:.75rem;right:.75rem;bottom:calc(env(safe-area-inset-bottom,0px) + 4.75rem);max-width:26rem;margin-inline:auto;" +
      "padding:1rem;background:var(--c-surface,#141414);color:var(--c-ink,#f5f5f5);border:1px solid var(--c-line,#2a2a2a);border-left:3px solid var(--c-accent,#76b900);border-radius:2px;" +
      "box-shadow:0 12px 32px -12px rgba(0,0,0,.6);font:14px/1.45 inherit;animation:instalar-entra 320ms cubic-bezier(.2,.7,.2,1) both}" +
      "@media(min-width:768px){.instalar{left:auto;right:1.25rem;bottom:1.25rem;margin:0;width:22rem}}" +
      ".instalar h2{margin:0 0 .25rem;font-size:.9375rem;font-weight:700}" +
      ".instalar p{margin:0;color:var(--c-muted,#a3a3a3);font-size:.8125rem}" +
      ".instalar-acoes{display:flex;gap:.5rem;margin-top:.75rem}" +
      ".instalar button{height:2.25rem;padding:0 .9rem;font:inherit;font-size:.8125rem;font-weight:700;border-radius:2px;cursor:pointer}" +
      ".instalar .i-sim{background:var(--c-accent,#76b900);color:var(--c-accent-ink,#0a0a0a);border:0}" +
      ".instalar .i-nao{background:transparent;color:var(--c-muted,#a3a3a3);border:1px solid var(--c-line,#2a2a2a)}" +
      ".instalar button:focus-visible{outline:2px solid var(--c-accent,#76b900);outline-offset:2px}" +
      "@keyframes instalar-entra{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}" +
      "@media(prefers-reduced-motion:reduce){.instalar{animation:none}}";
    document.head.appendChild(s);
  }

  function mostrar(modo) {
    if (aviso) return;
    estilos();
    aviso = document.createElement("div");
    aviso.className = "instalar";
    aviso.setAttribute("role", "dialog");
    aviso.setAttribute("aria-label", "Instalar a app");
    var texto, botoes;
    if (modo === "nativo") {
      texto = "Abra o painel com um toque, em ecrã inteiro e sem a barra do browser.";
      botoes = '<button type="button" class="i-sim">Instalar</button><button type="button" class="i-nao">Agora não</button>';
    } else {
      texto = ios
        ? "Toque em <b>Partilhar</b> e depois em <b>Adicionar ao ecrã principal</b>."
        : "Abra o menu do browser (<b>⋮</b>) e toque em <b>Instalar app</b> ou <b>Adicionar ao ecrã principal</b>.";
      botoes = '<button type="button" class="i-nao">Percebi</button>';
    }
    aviso.innerHTML = "<h2>Instalar o Painel de renovações</h2><p>" + texto + '</p><div class="instalar-acoes">' + botoes + "</div>";
    document.body.appendChild(aviso);
    var sim = aviso.querySelector(".i-sim"), nao = aviso.querySelector(".i-nao");
    if (sim) sim.addEventListener("click", function () {
      if (!pedido) return;
      pedido.prompt();
      pedido.userChoice.then(function (r) { if (r.outcome !== "accepted") adiar(); fechar(); }, fechar);
      pedido = null;
    });
    nao.addEventListener("click", function () { adiar(); fechar(); });
  }
  function fechar() { if (aviso) { aviso.remove(); aviso = null; } }

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    pedido = e;
    setTimeout(function () { mostrar("nativo"); }, 2500);
  });
  window.addEventListener("appinstalled", function () { pedido = null; fechar(); });

  // Sem evento nativo (iPhone, ou browsers que não o enviam): mostra as instruções no telemóvel.
  window.addEventListener("load", function () {
    setTimeout(function () {
      if (!pedido && !aviso && (movel || forcar)) mostrar("manual");
    }, 5000);
  });
})();
