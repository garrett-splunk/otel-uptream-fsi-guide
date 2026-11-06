// Adds a Copy button to every code block marked data-copy. Page works without it.
document.querySelectorAll("pre[data-copy]").forEach(function (pre) {
  var text = pre.innerText; // captured before the button is added
  var btn = document.createElement("button");
  btn.className = "copy";
  btn.type = "button";
  btn.textContent = "Copy";
  btn.addEventListener("click", function () {
    var done = function () {
      btn.textContent = "Copied";
      setTimeout(function () { btn.textContent = "Copy"; }, 1500);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () {});
    }
  });
  pre.appendChild(btn);
});
