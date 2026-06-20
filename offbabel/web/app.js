// OffBabel UI client. Talks to the Python backend over a localhost WebSocket. No network.
(function () {
  "use strict";

  var ws;
  var lang = "es";
  var demoWord = "HELLO";
  var wordIndex = 0;

  var $ = function (sel) { return document.querySelector(sel); };
  var statusbar = $("#statusbar");

  // ---- screens ----
  function show(screen) {
    document.querySelectorAll(".screen").forEach(function (s) {
      s.classList.toggle("active", s.dataset.screen === screen);
    });
    if (screen === "progress") send({ type: "get_progress" });
    if (screen === "sign") resetWord();
    send({ type: "set_mode", mode: screen });
  }

  document.querySelectorAll("[data-go]").forEach(function (el) {
    el.addEventListener("click", function () { show(el.dataset.go); });
  });

  $("#lang-select").addEventListener("change", function (e) {
    lang = e.target.value;
    send({ type: "set_language", language: lang });
  });

  // ---- WebSocket ----
  function connect() {
    ws = new WebSocket("ws://" + location.host + "/ws");
    ws.onopen = function () { statusbar.textContent = "connected (offline, on-device)"; };
    ws.onclose = function () {
      statusbar.textContent = "disconnected. retrying...";
      setTimeout(connect, 1000);
    };
    ws.onmessage = function (ev) { handle(JSON.parse(ev.data)); };
  }

  function send(msg) {
    if (ws && ws.readyState === 1) ws.send(JSON.stringify(msg));
  }

  function handle(m) {
    switch (m.type) {
      case "status":
        var badge = $("#offline-badge");
        badge.classList.toggle("online", !m.offline);
        badge.textContent = m.offline ? "On-device · No internet" : "ONLINE (not offline!)";
        if (m.stats) renderStats(m.stats);
        break;
      case "transcript": addBubble(m.role, m.text); break;
      case "correction": showCorrection(m); break;
      case "emote": setEmote(m.emotion); break;
      case "sign_detect": onSignDetect(m); break;
      case "progress": renderStats(m.stats); renderReview(m.review); break;
    }
  }

  // ---- Speak ----
  function addBubble(role, text) {
    var t = $("#transcript");
    var b = document.createElement("div");
    b.className = "bubble " + (role === "user" ? "user" : "tutor");
    b.textContent = text;
    t.appendChild(b);
    t.scrollTop = t.scrollHeight;
  }
  function showCorrection(c) {
    var el = $("#correction");
    el.classList.remove("hidden");
    el.innerHTML = "you said <span class='wrong'></span> &rarr; try <span class='right'></span>" +
      (c.note ? "<div class='note'></div>" : "");
    el.querySelector(".wrong").textContent = c.wrong || "";
    el.querySelector(".right").textContent = c.right || "";
    if (c.note) el.querySelector(".note").textContent = c.note;
  }
  function setEmote(emotion) {
    ["#avatar", "#avatar-sign"].forEach(function (sel) {
      var a = $(sel);
      if (!a) return;
      a.className = "avatar " + (emotion || "idle");
      var label = a.querySelector("span");
      if (label) label.textContent = emotion || "idle";
    });
  }

  var ptt = $("#ptt");
  ptt.addEventListener("mousedown", function () { ptt.classList.add("active"); send({ type: "speak_ptt_start" }); });
  ["mouseup", "mouseleave"].forEach(function (evt) {
    ptt.addEventListener(evt, function () {
      if (!ptt.classList.contains("active")) return;
      ptt.classList.remove("active");
      send({ type: "speak_ptt_stop" });
    });
  });
  $("#text-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var input = $("#text-input");
    if (!input.value.trim()) return;
    send({ type: "speak_text", text: input.value.trim(), language: lang });
    input.value = "";
  });

  // ---- Sign ----
  function resetWord() {
    wordIndex = 0;
    var strip = $("#word-strip");
    strip.innerHTML = "";
    demoWord.split("").forEach(function (ch, i) {
      var d = document.createElement("div");
      d.className = "ltr" + (i === 0 ? " current" : "");
      d.textContent = ch;
      strip.appendChild(d);
    });
    $("#now-letter").textContent = demoWord[0];
    buildDemoKeys();
  }
  function onSignDetect(m) {
    $("#detect-overlay").textContent = m.label || "--";
    $("#conf-line").textContent = "confidence: " + (m.confidence != null ? m.confidence.toFixed(2) : "--");
    if (m.stable && m.label === demoWord[wordIndex]) advanceLetter();
  }
  function advanceLetter() {
    var letters = document.querySelectorAll("#word-strip .ltr");
    if (letters[wordIndex]) { letters[wordIndex].classList.remove("current"); letters[wordIndex].classList.add("done"); }
    wordIndex++;
    if (wordIndex >= demoWord.length) {
      send({ type: "celebrate" });
      return;
    }
    if (letters[wordIndex]) letters[wordIndex].classList.add("current");
    $("#now-letter").textContent = demoWord[wordIndex];
  }
  // click-test keys (drop once the live classifier streams sign_detect)
  function buildDemoKeys() {
    var box = $("#demo-keys");
    box.innerHTML = "";
    Array.from(new Set(demoWord.split(""))).forEach(function (ch) {
      var b = document.createElement("button");
      b.textContent = ch;
      b.addEventListener("click", function () { send({ type: "sign_demo_letter", label: ch }); });
      box.appendChild(b);
    });
  }

  // ---- Progress ----
  function renderStats(s) {
    if (!s) return;
    $("#stats").innerHTML =
      "<div class='stat'><div class='n'>" + (s.words || 0) + "</div><div class='l'>words</div></div>" +
      "<div class='stat'><div class='n'>" + (s.signs || 0) + "</div><div class='l'>signs</div></div>";
  }
  function renderReview(items) {
    var ul = $("#review");
    ul.innerHTML = "";
    (items || []).forEach(function (it) {
      var li = document.createElement("li");
      li.innerHTML = "<span>" + it.value + " <small>(" + it.type + ", " + it.language + ")</small></span>" +
        "<span class='miss'>missed " + it.miss_count + "x</span>";
      ul.appendChild(li);
    });
    if (!items || !items.length) ul.innerHTML = "<li>Nothing to review yet. Go practice!</li>";
  }

  connect();
})();
