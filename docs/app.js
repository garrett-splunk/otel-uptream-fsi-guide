// Theme toggle, reading progress, active sidebar link, and copy buttons. The guide works without JavaScript.
(function () {
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem("otel-lab-theme");
    if (saved) root.setAttribute("data-theme", saved);
  } catch (e) {}

  var toggle = document.getElementById("themeToggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var current = root.getAttribute("data-theme");
      var systemDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
      var next = (current || (systemDark ? "dark" : "light")) === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("otel-lab-theme", next); } catch (e) {}
    });
  }

  var toast = document.getElementById("toast");
  function say(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(function () { toast.classList.remove("show"); }, 1400);
  }

  document.querySelectorAll(".code-block[data-copy]").forEach(function (block) {
    var pre = block.querySelector("pre");
    var btn = block.querySelector(".btn-copy");
    if (!pre || !btn) return;
    btn.addEventListener("click", function () {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(pre.innerText).then(function () { say("Copied"); }, function () {});
      }
    });
  });

  var bar = document.getElementById("progressBar");
  var links = Array.prototype.slice.call(document.querySelectorAll(".sidebar a[href^='#']"));
  var sections = links.map(function (a) { return document.querySelector(a.getAttribute("href")); });
  function onScroll() {
    var h = document.documentElement.scrollHeight - window.innerHeight;
    if (bar && h > 0) bar.style.width = Math.min(100, (window.scrollY / h) * 100) + "%";
    var idx = 0;
    sections.forEach(function (s, i) { if (s && s.getBoundingClientRect().top < 140) idx = i; });
    links.forEach(function (a, i) { a.classList.toggle("active", i === idx); });
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
})();
