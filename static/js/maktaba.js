// المكتبة السرية — سلوك الواجهة (بدون مكتبات خارجية)
(function () {
  "use strict";

  // ------------------------------------------------------------ theme
  var root = document.documentElement;
  function storedTheme() {
    try {
      return localStorage.getItem("theme");
    } catch (e) {
      return null;
    }
  }
  function applyTheme(theme) {
    if (theme === "light" || theme === "dark") {
      root.setAttribute("data-theme", theme);
    } else {
      root.removeAttribute("data-theme");
    }
  }
  applyTheme(storedTheme());

  document.addEventListener("DOMContentLoaded", function () {
    var toggle = document.getElementById("theme-toggle");
    if (toggle) {
      toggle.addEventListener("click", function () {
        var current = root.getAttribute("data-theme");
        if (!current) {
          current = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        }
        var next = current === "dark" ? "light" : "dark";
        applyTheme(next);
        try {
          localStorage.setItem("theme", next);
        } catch (e) {
          /* ignore */
        }
      });
    }

    // ---------------------------------------------------------- search suggestions
    document.querySelectorAll("[data-suggest]").forEach(function (form) {
      var input = form.querySelector('input[type="search"]');
      var box = form.querySelector(".suggestions");
      var url = form.getAttribute("data-suggest");
      if (!input || !box || !url) return;
      var timer = null;
      var controller = null;

      function hide() {
        box.hidden = true;
        input.setAttribute("aria-expanded", "false");
      }

      function render(results) {
        box.replaceChildren();
        if (!results.length) {
          var empty = document.createElement("p");
          empty.className = "s-empty";
          empty.textContent = "لا اقتراحات. اضغط Enter للبحث الكامل.";
          box.appendChild(empty);
        }
        results.forEach(function (item) {
          var a = document.createElement("a");
          a.href = item.url;
          a.setAttribute("role", "option");
          a.textContent = item.title;
          if (item.author) {
            var s = document.createElement("span");
            s.className = "s-author";
            s.textContent = item.author;
            a.appendChild(s);
          }
          box.appendChild(a);
        });
        box.hidden = false;
        input.setAttribute("aria-expanded", "true");
      }

      input.addEventListener("input", function () {
        var q = input.value.trim();
        clearTimeout(timer);
        if (q.length < 2) {
          hide();
          return;
        }
        timer = setTimeout(function () {
          if (controller) controller.abort();
          controller = new AbortController();
          fetch(url + "?q=" + encodeURIComponent(q), {
            headers: { Accept: "application/json" },
            signal: controller.signal,
          })
            .then(function (r) {
              return r.ok ? r.json() : { results: [] };
            })
            .then(function (data) {
              render(data.results || []);
            })
            .catch(function () {});
        }, 220);
      });
      input.addEventListener("keydown", function (e) {
        if (e.key === "Escape") hide();
      });
      document.addEventListener("click", function (e) {
        if (!form.contains(e.target)) hide();
      });
    });

    // ---------------------------------------------------------- save toggle (يعمل أيضًا بدون JS كنموذج عادي)
    document.querySelectorAll("form[data-save-toggle]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var button = form.querySelector("button");
        fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: { Accept: "application/json" },
          credentials: "same-origin",
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (data) {
            button.textContent = data.saved ? "محفوظ ✓" : "احفظ";
            button.setAttribute("aria-pressed", data.saved ? "true" : "false");
          })
          .catch(function () {
            form.submit();
          });
      });
    });
  });
})();
