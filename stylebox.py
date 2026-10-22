# StyleBox User Interface for css styling, js scripting, and HTML layout management.
# Provides a graphical interface for managing, creating and editing CSS, JavaScript, and HTML files.

# Supports live preview and real-time updates for web development projects.
# Enables efficient workflow for front-end developers by integrating styling, scripting, and layout tools in a single interface.
# Facilitates collaboration by allowing multiple developers to work on the same project simultaneously.
# Provides version control integration to track changes and manage project history effectively.
# Offers customizable themes and layouts to enhance the user experience and productivity.

# Uses a hacker-friendly interface to streamline coding and debugging processes.

import argparse
import json
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FILES = {"html": "index.html", "css": "style.css", "js": "script.js"}

DEFAULTS = {
    "html": '<!DOCTYPE html>\n<html>\n<head>\n  <link rel="stylesheet" href="style.css">\n</head>\n'
            '<body>\n  <h1>Hello, StyleBox</h1>\n  <script src="script.js"></script>\n</body>\n</html>\n',
    "css": "body {\n  font-family: monospace;\n  background: #0b0f0b;\n  color: #33ff66;\n}\n",
    "js": "console.log('StyleBox ready');\n",
}

PAGE = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>StyleBox</title>
<style>
:root{--bg:#0a0e0a;--panel:#0f160f;--fg:#33ff66;--dim:#1f7a3a;--line:#164d27}
*{box-sizing:border-box}
body{margin:0;height:100vh;display:flex;flex-direction:column;background:var(--bg);color:var(--fg);
font:14px/1.4 "Fira Code",Consolas,monospace}
header{display:flex;align-items:center;gap:12px;padding:8px 14px;border-bottom:1px solid var(--line);background:var(--panel)}
header h1{font-size:16px;margin:0;letter-spacing:2px}
header .spacer{flex:1}
#status{color:var(--dim)}
button{background:transparent;color:var(--fg);border:1px solid var(--dim);padding:4px 12px;font:inherit;cursor:pointer}
button:hover{background:var(--fg);color:var(--bg)}
main{flex:1;display:flex;min-height:0}
.pane{flex:1;display:flex;flex-direction:column;min-width:0}
.pane+.pane{border-left:1px solid var(--line)}
.tabs{display:flex;background:var(--panel);border-bottom:1px solid var(--line)}
.tab{padding:6px 16px;cursor:pointer;color:var(--dim);border-right:1px solid var(--line)}
.tab.active{color:var(--fg);background:var(--bg);box-shadow:inset 0 -2px var(--fg)}
textarea{flex:1;width:100%;resize:none;border:0;outline:0;padding:12px;background:var(--bg);color:var(--fg);
font:inherit;tab-size:2;white-space:pre}
iframe{flex:1;border:0;background:#fff}
.label{padding:6px 14px;background:var(--panel);border-bottom:1px solid var(--line);color:var(--dim)}
</style></head><body>
<header><h1>&gt;_ STYLEBOX</h1><span id="status">loading...</span><span class="spacer"></span>
<button id="save">Save (Ctrl+S)</button><button id="pop">Open in browser</button></header>
<main>
<div class="pane"><div class="tabs" id="tabs"></div><textarea id="ed" spellcheck="false"></textarea></div>
<div class="pane"><div class="label">live preview</div><iframe id="pv" sandbox="allow-scripts"></iframe></div>
</main>
<script>
const names={html:"index.html",css:"style.css",js:"script.js"};
let files={},cur="html",timer;
const $=id=>document.getElementById(id),st=t=>$("status").textContent=t;
function tabs(){$("tabs").innerHTML="";for(const k in names){const d=document.createElement("div");
d.className="tab"+(k==cur?" active":"");d.textContent=names[k];d.onclick=()=>{files[cur]=$("ed").value;cur=k;$("ed").value=files[k];tabs()};
$("tabs").appendChild(d)}}
function preview(){let h=files.html;
h=h.replace(/<link[^>]*href=["']style\.css["'][^>]*>/i,()=>"<style>"+files.css+"</style>");
h=h.replace(/<script[^>]*src=["']script\.js["'][^>]*><\/script>/i,()=>"<script>"+files.js.replace(/<\/script/gi,"<\\/script")+"<\/script>");
$("pv").srcdoc=h}
$("ed").oninput=()=>{files[cur]=$("ed").value;st("unsaved");clearTimeout(timer);timer=setTimeout(preview,250)};
$("ed").onkeydown=e=>{if(e.key=="Tab"){e.preventDefault();document.execCommand("insertText",false,"  ")}};
async function save(){files[cur]=$("ed").value;const r=await fetch("/api/files",{method:"POST",body:JSON.stringify(files)});
st(r.ok?"saved":"save failed")}
$("save").onclick=save;
$("pop").onclick=()=>window.open("/preview/index.html");
addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key=="s"){e.preventDefault();save()}});
fetch("/api/files").then(r=>r.json()).then(j=>{files=j.files;$("ed").value=files[cur];tabs();preview();st("project: "+j.project)});
</script></body></html>"""


def make_handler(project: Path):
    project.mkdir(parents=True, exist_ok=True)
    for key, name in FILES.items():
        path = project / name
        if not path.exists():
            path.write_text(DEFAULTS[key], encoding="utf-8")

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/":
                self._send(200, PAGE, "text/html; charset=utf-8")
            elif self.path == "/api/files":
                files = {k: (project / n).read_text(encoding="utf-8") for k, n in FILES.items()}
                self._send(200, json.dumps({"project": str(project), "files": files}), "application/json")
            elif m := re.fullmatch(r"/preview/(index\.html|style\.css|script\.js)", self.path):
                ctype = {"html": "text/html", "css": "text/css", "js": "text/javascript"}[m[1].rsplit(".", 1)[1]]
                self._send(200, (project / m[1]).read_bytes(), ctype + "; charset=utf-8")
            else:
                self._send(404, "not found", "text/plain")

        def do_POST(self):
            if self.path != "/api/files":
                return self._send(404, "not found", "text/plain")
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length))
                if set(data) != set(FILES) or not all(isinstance(v, str) for v in data.values()):
                    raise ValueError
            except ValueError:
                return self._send(400, "bad request", "text/plain")
            for key, name in FILES.items():
                (project / name).write_text(data[key], encoding="utf-8")
            self._send(200, "ok", "text/plain")

        def log_message(self, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description="StyleBox web development UI")
    parser.add_argument("project", nargs="?", default="stylebox_project", help="project folder")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(Path(args.project).resolve()))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"StyleBox running at {url} (Ctrl+C to quit)")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()

