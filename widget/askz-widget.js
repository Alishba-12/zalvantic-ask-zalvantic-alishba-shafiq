/* Ask Zalvantic chat widget. One file. Usage:
   <script src="askz-widget.js" data-api="https://your-api"></script>
   If data-api is missing, the widget talks to the server it was loaded from. */
(function () {
  var script = document.currentScript;
  var API = (script.getAttribute("data-api") || new URL(script.src).origin).replace(/\/$/, "");

  var css = ".askz-btn{position:fixed;right:20px;bottom:20px;width:56px;height:56px;border-radius:50%;border:0;background:#1a56db;color:#fff;font-size:24px;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.25);z-index:99999}" +
    ".askz-box{position:fixed;right:20px;bottom:88px;width:340px;max-width:calc(100vw - 40px);height:460px;background:#fff;border:1px solid #ddd;border-radius:12px;display:none;flex-direction:column;font-family:system-ui,sans-serif;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,.2);z-index:99999}" +
    ".askz-box.open{display:flex}.askz-head{padding:12px;background:#1a56db;color:#fff;border-radius:12px 12px 0 0;font-weight:600}" +
    ".askz-msgs{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px}" +
    ".askz-m{padding:8px 10px;border-radius:10px;max-width:85%;white-space:pre-wrap;word-wrap:break-word}" +
    ".askz-u{align-self:flex-end;background:#e8f0fe}.askz-b{align-self:flex-start;background:#f3f4f6}" +
    ".askz-src{font-size:12px;color:#555;margin-top:4px}" +
    ".askz-form{display:flex;border-top:1px solid #ddd}.askz-form input{flex:1;border:0;padding:12px;font-size:14px;outline:none;border-radius:0 0 0 12px}" +
    ".askz-form button{border:0;background:#1a56db;color:#fff;padding:0 16px;border-radius:0 0 12px 0;cursor:pointer}";
  var style = document.createElement("style"); style.textContent = css; document.head.appendChild(style);

  var btn = document.createElement("button"); btn.className = "askz-btn"; btn.textContent = "\u{1F4AC}"; btn.setAttribute("aria-label", "Open chat");
  var box = document.createElement("div"); box.className = "askz-box";
  box.innerHTML = '<div class="askz-head">Ask Zalvantic</div><div class="askz-msgs"></div>' +
    '<form class="askz-form"><input placeholder="Ask a question..." maxlength="500" required><button type="submit">Send</button></form>';
  document.body.appendChild(btn); document.body.appendChild(box);

  var msgs = box.querySelector(".askz-msgs"), form = box.querySelector("form"), input = box.querySelector("input");
  var busy = false;

  function add(cls, text) {
    var d = document.createElement("div"); d.className = "askz-m " + cls; d.textContent = text;
    msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight; return d;
  }

  btn.onclick = function () {
    box.classList.toggle("open");
    if (!msgs.children.length) add("askz-b", "Hi! Ask me anything about what Zalvantic does.");
    input.focus();
  };

  form.onsubmit = async function (e) {
    e.preventDefault();
    var q = input.value.trim(); if (!q || busy) return;
    input.value = ""; busy = true; add("askz-u", q);
    var bubble = add("askz-b", "..."), started = false;
    try {
      var res = await fetch(API + "/chat", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q })
      });
      if (res.status === 429) { bubble.textContent = "Too many questions, please wait a minute."; return; }
      if (!res.ok) { bubble.textContent = "Sorry, something went wrong."; return; }
      var reader = res.body.getReader(), dec = new TextDecoder(), buf = "";
      while (true) {
        var r = await reader.read(); if (r.done) break;
        buf += dec.decode(r.value, { stream: true });
        var parts = buf.split("\n\n"); buf = parts.pop();
        parts.forEach(function (block) {
          var ev = "message", data = "";
          block.split("\n").forEach(function (l) {
            if (l.indexOf("event:") === 0) ev = l.slice(6).trim();
            else if (l.indexOf("data:") === 0) data += l.slice(5).trim();
          });
          if (!data) return;
          var val = JSON.parse(data);
          if (ev === "token") { if (!started) { bubble.textContent = ""; started = true; } bubble.textContent += val; }
          else if (ev === "sources" && val.length) { var s = document.createElement("div"); s.className = "askz-src"; s.textContent = "Sources: " + val.join(", "); bubble.appendChild(s); }
          else if (ev === "error") { bubble.textContent = val; }
          msgs.scrollTop = msgs.scrollHeight;
        });
      }
    } catch (err) {
      bubble.textContent = "Cannot reach the server.";
    } finally { busy = false; }
  };
})();
