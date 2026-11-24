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
