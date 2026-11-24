(function () {
  "use strict";

  var canvas = document.getElementById("fundo");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  if (!ctx) return;

  var reduzir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var COLUNAS = 80;        // colunas da grelha (mais uma)
  var LINHAS = 32;         // linhas da grelha (mais uma)
  var DX = 0.4;            // distância entre colunas
  var DZ = 0.5;            // distância entre linhas
  var Z_PERTO = 1.2;       // linha mais próxima da câmara
  var ALTURA_CAMERA = 1.0;
  var HORIZONTE = 0.4;     // 40% da altura do ecrã (igual ao CSS)

  var N = COLUNAS + 1;
  var px = new Float32Array((LINHAS + 1) * N);
  var py = new Float32Array((LINHAS + 1) * N);

  var W = 0, H = 0, dpr = 1;
  var cor = "118,185,0";
  var forca = 1;
  var rato = { x: 0, y: 0, ax: 0, ay: 0 };
  var t = 2;
  var deslocamento = 0;
  var ultimo = 0;
  var pulsos = [];

  function lerCor() {
    var raiz = document.documentElement;
    var v = (getComputedStyle(raiz).getPropertyValue("--c-accent") || "").trim();
    var m = /^#([0-9a-f]{6})$/i.exec(v);
    if (m) {
      var n = parseInt(m[1], 16);
      cor = ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255);
    }
    forca = raiz.classList.contains("dark") ? 1 : 0.55;
  }

  function medir() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function desenhar() {
    ctx.clearRect(0, 0, W, H);

    var horizonte = H * HORIZONTE;
    var foco = Math.min(W, H * 1.6) * 0.6;
    var camX = rato.ax * 1.4;
    var amp = 0.3 + rato.ay * 0.1;
    var desvio = deslocamento % DZ;
    var i, j, k, zv, zm, s, x, y, calma, a, b, p, d, idade, onda;

    // 1) Projecção de todos os pontos (ondas no relevo)
    for (i = 0; i <= LINHAS; i++) {
      zv = Z_PERTO + i * DZ - desvio;       // distância à câmara
      zm = zv + deslocamento;               // posição no mundo (o relevo fica parado)
      s = foco / zv;
      calma = Math.min(1, Math.max(0, (zv - 1.4) / 3.5)); // ondas mais calmas perto
      onda = 0;                             // onda que rola ao clicar
      for (p = 0; p < pulsos.length; p++) {
        idade = t - pulsos[p];
        d = zv - (Z_PERTO + idade * 7);
        onda += 0.32 * Math.exp(-d * d / 0.5) * Math.max(0, 1 - idade / 3.2);
      }
      for (j = 0; j < N; j++) {
        x = (j - COLUNAS / 2) * DX;
        y = amp * calma * (
          0.6 * Math.sin(x * 0.9 + zm * 0.95 + t * 1.1) +
          0.4 * Math.sin(x * 0.35 - zm * 1.4 + t * 0.7)
        ) + onda;
        k = i * N + j;
        px[k] = W / 2 + (x - camX) * s;
        py[k] = horizonte + (ALTURA_CAMERA - y) * s;
      }
    }

    // 2) Uma linha de cada vez (do perto ao longe), com mais transparência ao longe
    ctx.lineWidth = 1;
    for (i = 0; i <= LINHAS; i++) {
      a = Math.pow(1 - i / (LINHAS + 1), 1.7) * 0.9 * forca;
      ctx.strokeStyle = "rgba(" + cor + "," + a.toFixed(3) + ")";
      ctx.beginPath();
      k = i * N;
      ctx.moveTo(px[k], py[k]);
      for (j = 1; j < N; j++) ctx.lineTo(px[k + j], py[k + j]);
      if (i < LINHAS) {
        for (j = 0; j < N; j++) {
          ctx.moveTo(px[k + j], py[k + j]);
          ctx.lineTo(px[k + N + j], py[k + N + j]);
        }
      }
      ctx.stroke();
    }

    // 3) Pontos que brilham nos cruzamentos
    for (i = 1; i < LINHAS; i += 3) {
      a = Math.pow(1 - i / (LINHAS + 1), 1.7) * forca;
      for (j = 2; j < N; j += 5) {
        b = 0.5 + 0.5 * Math.sin(t * 2.2 + i * 0.9 + j * 1.7);
        ctx.fillStyle = "rgba(" + cor + "," + (a * b).toFixed(3) + ")";
        k = i * N + j;
        ctx.fillRect(px[k] - 1.5, py[k] - 1.5, 3, 3);
      }
    }
  }

  function ciclo(agora) {
    var dt = (agora - ultimo) / 1000;
    if (!(dt > 0) || dt > 0.05) dt = 0.016;
    ultimo = agora;
    t += dt;
    while (pulsos.length && t - pulsos[0] > 3.5) pulsos.shift();
    deslocamento += dt * 0.9;
    var k = 1 - Math.exp(-dt * 4);
    rato.ax += (rato.x - rato.ax) * k;
    rato.ay += (rato.y - rato.ay) * k;
    desenhar();
    window.requestAnimationFrame(ciclo);
  }

  lerCor();
  medir();

  window.addEventListener("resize", function () {
    medir();
    if (reduzir) desenhar();
  });

  if (reduzir) {
    desenhar();            // uma imagem parada
  } else {
    window.addEventListener("pointermove", function (e) {
      rato.x = (e.clientX / W) * 2 - 1;
      rato.y = (e.clientY / H) * 2 - 1;
    }, { passive: true });
    window.addEventListener("pointerdown", function () {
      pulsos.push(t);
      if (pulsos.length > 3) pulsos.shift();
    }, { passive: true });
    pulsos.push(t);
    window.requestAnimationFrame(ciclo);
  }
})();
