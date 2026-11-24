/* Animações do painel e do login (parte 1). Ver DESIGN.md. */
(function () {
  "use strict";

  var reduzir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var comRato = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  var raiz = document.documentElement;

  // Luz ambiente que segue o rato
  if (!reduzir && comRato) {
    var pendente = false, mx = 0, my = 0;
    window.addEventListener("pointermove", function (e) {
      if (e.pointerType !== "mouse") return;
      mx = e.clientX;
      my = e.clientY;
      if (pendente) return;
      pendente = true;
      requestAnimationFrame(function () {
        pendente = false;
        raiz.style.setProperty("--sx", mx + "px");
        raiz.style.setProperty("--sy", my + "px");
      });
    }, { passive: true });
  }

  // Barra lateral: o bloco verde desliza entre os itens
  var nav = document.querySelector(".vt-lateral nav");
  if (nav) {
    var itens = [].slice.call(nav.querySelectorAll(".nav-item"));
    var activo = nav.querySelector('.nav-item[aria-current="page"]');
    var pilula = document.createElement("span");
    pilula.className = "nav-pill";
    pilula.setAttribute("aria-hidden", "true");
    nav.insertBefore(pilula, nav.firstChild);
    nav.classList.add("nav-js");

    var ir = function (el, animar) {
      if (!el || !el.offsetHeight) { pilula.style.opacity = "0"; return; }
      if (!animar) pilula.style.transition = "none";
      pilula.style.opacity = "1";
      pilula.style.height = el.offsetHeight + "px";
      pilula.style.transform = "translateY(" + el.offsetTop + "px)";
      if (!animar) {
        void pilula.offsetHeight;
        pilula.style.transition = "";
      }
    };

    ir(activo, false);
    itens.forEach(function (a) {
      a.addEventListener("pointerenter", function () { ir(a, true); });
      a.addEventListener("focus", function () { ir(a, true); });
    });
    nav.addEventListener("pointerleave", function () { ir(activo, true); });
    window.addEventListener("resize", function () { ir(activo, false); });
  }
})();

/* parte-2: página de login */
(function () {
  "use strict";

  var reduzir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var comRato = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  var cartao = document.querySelector(".login-cartao");
  if (!cartao || reduzir) return;

  // Título: cada palavra vira um elemento para entrar em cascata
  var h = cartao.querySelector("h1");
  if (h && !h.dataset.palavras) {
    var texto = h.textContent.trim();
    h.dataset.palavras = "1";
    h.setAttribute("aria-label", texto);
    h.textContent = "";
    texto.split(/\s+/).forEach(function (p, i) {
      if (i) h.appendChild(document.createTextNode(" "));
      var s = document.createElement("span");
      s.className = "pal";
      s.setAttribute("aria-hidden", "true");
      s.style.setProperty("--w", i);
      s.textContent = p;
      h.appendChild(s);
    });
  }

  // Cartão: inclina a seguir o rato (parado enquanto escreves)
  if (!comRato) return;
  cartao.addEventListener("pointermove", function (e) {
    if (e.pointerType !== "mouse") return;
    var r = cartao.getBoundingClientRect();
    var x = (e.clientX - r.left) / r.width;
    var y = (e.clientY - r.top) / r.height;
    cartao.style.setProperty("--gx", (x * 100).toFixed(1) + "%");
    cartao.style.setProperty("--gy", (y * 100).toFixed(1) + "%");
    if (cartao.matches(":focus-within")) {
      cartao.style.transform = "";
      return;
    }
    cartao.classList.add("inclinando");
    cartao.style.transform = "perspective(900px) rotateX(" + ((0.5 - y) * 7).toFixed(2) + "deg) rotateY(" + ((x - 0.5) * 9).toFixed(2) + "deg)";
  });
  cartao.addEventListener("pointerleave", function () {
    cartao.classList.remove("inclinando");
    cartao.style.transform = "";
  });
})();

/* parte-3: abertura v3 (5,2 s) e boas-vindas depois do login */
(function () {
  "use strict";

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var noLogin = !!document.querySelector(".login-cartao");
  var modo;
  try {
    if (!noLogin && sessionStorage.getItem("boasvindas")) {
      sessionStorage.removeItem("boasvindas");
      sessionStorage.setItem("abertura", "1");
      modo = "bv";
    } else if (!sessionStorage.getItem("abertura")) {
      sessionStorage.setItem("abertura", "1");
      modo = "abertura";
    } else {
      return;
    }
  } catch (e) { return; }

  var raiz = document.documentElement;
  var tela = document.createElement("div");
  tela.setAttribute("aria-hidden", "true");

  function criar(tag, classe, texto) {
    var el = document.createElement(tag);
    el.className = classe;
    if (texto) el.textContent = texto;
    return el;
  }

  if (modo === "abertura") {
    var modelo = document.querySelector(".logo-marca");
    if (!modelo) return;
    tela.className = "abertura-tela";
    var logo = modelo.cloneNode(true);
    logo.setAttribute("width", "120");
    logo.setAttribute("height", "120");
    tela.appendChild(logo);
    var nome = criar("p", "abertura-nome");
    "Renovações".split("").forEach(function (c, i) {
      var sp = criar("span", "", c);
      sp.style.setProperty("--l", i);
      nome.appendChild(sp);
    });
    tela.appendChild(nome);
    var barra = criar("div", "abertura-barra");
    barra.appendChild(document.createElement("i"));
    tela.appendChild(barra);
  } else {
    tela.className = "bv-tela";
    var h = new Date().getHours();
    var saudacao = h < 12 ? "Bom dia" : (h < 19 ? "Boa tarde" : "Boa noite");
    var bruto = (document.body.getAttribute("data-nome") || "").trim().split(/[\s@]/)[0];
    var primeiro = bruto ? bruto.charAt(0).toUpperCase() + bruto.slice(1) : "";

    tela.appendChild(criar("div", "bv-metade bv-esq"));
    tela.appendChild(criar("div", "bv-metade bv-dir"));
    tela.appendChild(criar("div", "bv-fenda"));

    var conteudo = criar("div", "bv-conteudo");
    conteudo.appendChild(criar("p", "bv-saudacao", saudacao));
    var grande = criar("h2", "bv-nome");
    (primeiro || "Bem-vindo").split("").forEach(function (c, i) {
      var sp = criar("span", "", c);
      sp.style.setProperty("--l", i);
      grande.appendChild(sp);
    });
    conteudo.appendChild(grande);
    conteudo.appendChild(criar("div", "bv-linha"));
    conteudo.appendChild(criar("p", "bv-frase", "O teu painel está pronto."));
    tela.appendChild(conteudo);
  }

  var fim = function () {
    if (!tela.parentNode) return;
    tela.parentNode.removeChild(tela);
    raiz.classList.remove("a-abrir");
    document.removeEventListener("keydown", fim);
  };

  raiz.classList.add("a-abrir");
  document.body.appendChild(tela);
  tela.addEventListener("click", fim);
  document.addEventListener("keydown", fim);
  tela.addEventListener("animationend", function (e) {
    if (e.animationName === "abertura-sai" || e.animationName === "bv-esq") fim();
  });
  setTimeout(fim, 3400);
})();

/* parte-7: logout repõe a abertura */
(function () {
  "use strict";
  document.addEventListener("submit", function (e) {
    var f = e.target;
    var acao = (f && f.getAttribute && f.getAttribute("action")) || "";
    if (acao.indexOf("logout") === -1 && acao.indexOf("sair") === -1) return;
    try {
      sessionStorage.removeItem("abertura");
      sessionStorage.removeItem("boasvindas");
    } catch (err) {}
  });
})();

/* parte-8: universo (fundo animado do painel) */
(function () {
  "use strict";

  if (document.getElementById("fundo") || !document.querySelector(".vt-lateral")) return;

  var reduzir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var comRato = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  var raiz = document.documentElement;

  var caixa = document.createElement("div");
  caixa.className = "universo";
  caixa.setAttribute("aria-hidden", "true");
  var tela = document.createElement("canvas");
  caixa.appendChild(tela);
  document.body.insertBefore(caixa, document.body.firstChild);
  var ctx = tela.getContext("2d");
  if (!ctx) return;

  var dpr = Math.min(window.devicePixelRatio || 1, 1.5);
  var w = 0, h = 0, estrelas = [];
  var ink = "#ffffff", acc = "#76b900", claro = false;
  var px = 0, py = 0, alvoX = 0, alvoY = 0;
  var offset = 0;
  try { offset = (parseFloat(sessionStorage.getItem("universo-t")) || 0) * 1000; } catch (e) {}

  function semente(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function cores() {
    var cs = getComputedStyle(raiz);
    ink = cs.getPropertyValue("--c-ink").trim() || "#ffffff";
    acc = cs.getPropertyValue("--c-accent").trim() || "#76b900";
    claro = !raiz.classList.contains("dark");
  }

  function medir() {
    w = window.innerWidth;
    h = window.innerHeight;
    tela.width = Math.round(w * dpr);
    tela.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var n = Math.max(60, Math.min(w < 700 ? 110 : 240, Math.round(w * h / 8000)));
    var rnd = semente(20261124);
    estrelas = [];
    for (var i = 0; i < n; i++) {
      var d = 0.2 + rnd() * 0.8;
      estrelas.push({
        x: rnd(), y: rnd(), d: d,
        r: 0.35 + d * 1.1,
        a: 0.25 + d * 0.6,
        f: 0.5 + rnd() * 1.8,
        p: rnd() * 6.283,
        ac: rnd() < 0.12
      });
    }
  }

  function mod(a, m) { return ((a % m) + m) % m; }

  var cadente = null, proxima = 7;

  function desenhar(t) {
    ctx.clearRect(0, 0, w, h);
    var fator = claro ? 0.55 : 1;
    for (var i = 0; i < estrelas.length; i++) {
      var s = estrelas[i];
      var v = 3 + s.d * 11;
      var x = mod(s.x * w - t * v + px * s.d * 22, w);
      var y = mod(s.y * h - t * v * 0.4 + py * s.d * 22, h);
      var brilho = reduzir ? 1 : 0.55 + 0.45 * Math.sin(t * s.f + s.p);
      ctx.globalAlpha = s.a * brilho * fator;
      ctx.fillStyle = s.ac ? acc : ink;
      ctx.beginPath();
      ctx.arc(x, y, s.r, 0, 6.283);
      ctx.fill();
    }

    if (!reduzir) {
      if (!cadente && t > proxima) {
        var ang = 0.5 + Math.random() * 0.4;
        cadente = { x: Math.random() * w * 0.8 + w * 0.2, y: Math.random() * h * 0.4, vx: -Math.cos(ang), vy: Math.sin(ang), vida: 0 };
        proxima = t + 7 + Math.random() * 8;
      }
      if (cadente) {
        cadente.vida += 1 / 30;
        var k = cadente.vida / 1.1;
        if (k >= 1) { cadente = null; }
        else {
          var hx = cadente.x + cadente.vx * k * 520;
          var hy = cadente.y + cadente.vy * k * 520;
          var tx = hx - cadente.vx * 110;
          var ty = hy - cadente.vy * 110;
          var g = ctx.createLinearGradient(tx, ty, hx, hy);
          g.addColorStop(0, "transparent");
          g.addColorStop(1, acc);
          ctx.globalAlpha = (1 - k) * 0.8 * fator;
          ctx.strokeStyle = g;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(tx, ty);
          ctx.lineTo(hx, hy);
          ctx.stroke();
        }
      }
    }
    ctx.globalAlpha = 1;
  }

  cores();
  medir();

  var ultimo = 0, quadro = 0, tempo = 0;
  function passo(agora) {
    quadro = requestAnimationFrame(passo);
    if (agora - ultimo < 32) return;
    ultimo = agora;
    px += (alvoX - px) * 0.06;
    py += (alvoY - py) * 0.06;
    tempo = (agora + offset) / 1000;
    desenhar(tempo);
  }

  if (reduzir) {
    desenhar(offset / 1000);
  } else {
    quadro = requestAnimationFrame(passo);
    document.addEventListener("visibilitychange", function () {
      cancelAnimationFrame(quadro);
      if (!document.hidden) quadro = requestAnimationFrame(passo);
    });
    if (comRato) {
      window.addEventListener("pointermove", function (e) {
        if (e.pointerType !== "mouse") return;
        alvoX = (e.clientX / w - 0.5) * 2;
        alvoY = (e.clientY / h - 0.5) * 2;
      }, { passive: true });
    }
  }

  window.addEventListener("resize", function () {
    medir();
    if (reduzir) desenhar(offset / 1000);
  });

  new MutationObserver(function () {
    cores();
    if (reduzir) desenhar(offset / 1000);
  }).observe(raiz, { attributes: true, attributeFilter: ["class"] });

  window.addEventListener("pagehide", function () {
    try { sessionStorage.setItem("universo-t", String(Math.floor(tempo))); } catch (e) {}
  });
})();
