import os
import uuid
import hmac
import http.server
import socketserver
import urllib.parse

PORT = int(os.environ.get("PORT", 8080))
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")

# In-memory sessions: token → email
_sessions: dict = {}

LOGIN_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BITE Sales Dashboard — Anmelden</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:'Nunito',sans-serif;
  background:#f2f5f9;
  min-height:100vh;
  display:flex;
  align-items:center;
  justify-content:center;
}
.card{
  background:#fff;
  border-radius:20px;
  padding:52px 44px 44px;
  width:420px;
  box-shadow:0 8px 40px rgba(51,144,255,0.12);
}
.logo{text-align:center;margin-bottom:36px}
.logo .brand{
  font-size:32px;font-weight:900;
  background:linear-gradient(90deg,#3390ff,#65bde6);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  letter-spacing:-1px;
}
.logo .sub{font-size:14px;color:#7a8fa6;margin-top:6px;font-weight:600}
.field{margin-bottom:20px}
label{display:block;font-size:13px;font-weight:700;color:#3d4f63;margin-bottom:7px}
input{
  width:100%;padding:13px 16px;
  border:1.5px solid #dde5ef;border-radius:10px;
  font-family:'Nunito',sans-serif;font-size:15px;color:#191919;
  background:#f8fafd;transition:border-color .15s,background .15s;
}
input:focus{outline:none;border-color:#3390ff;background:#fff}
.hint{font-size:12px;color:#9aabbc;margin-top:5px}
.error{
  background:#fff4f4;border:1.5px solid #ffc5c5;border-radius:10px;
  color:#c0392b;font-size:13px;font-weight:700;
  padding:11px 14px;margin-bottom:20px;
}
button{
  width:100%;padding:14px;margin-top:4px;
  background:linear-gradient(90deg,#3390ff,#65bde6);
  border:none;border-radius:10px;color:#fff;
  font-family:'Nunito',sans-serif;font-size:16px;font-weight:800;
  cursor:pointer;letter-spacing:0.2px;transition:opacity .15s;
}
button:hover{opacity:.88}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="brand">BITE</div>
    <div class="sub">Sales Dashboard</div>
  </div>
  <!-- ERROR -->
  <form method="post" action="/login">
    <div class="field">
      <label>E-Mail</label>
      <input type="email" name="email" placeholder="vorname.nachname@b-ite.de" required autofocus>
      <p class="hint">Nur @b-ite.de Adressen</p>
    </div>
    <div class="field">
      <label>Passwort</label>
      <input type="password" name="password" placeholder="••••••••" required>
    </div>
    <button type="submit">Anmelden &rarr;</button>
  </form>
</div>
</body>
</html>"""


def _check_password(password: str) -> bool:
    if not DASHBOARD_PASSWORD:
        return False
    return hmac.compare_digest(password, DASHBOARD_PASSWORD)


def _get_session_token(headers) -> str:
    for part in headers.get("Cookie", "").split(";"):
        part = part.strip()
        if part.startswith("session="):
            return part[8:]
    return ""


class AuthHandler(http.server.SimpleHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress per-request noise

    def _authenticated(self) -> bool:
        token = _get_session_token(self.headers)
        return bool(token) and token in _sessions

    def _send_login(self, error: str = ""):
        error_html = f'<div class="error">{error}</div>' if error else ""
        html = LOGIN_HTML.replace("<!-- ERROR -->", error_html).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def _redirect(self, location: str, clear_cookie: bool = False):
        self.send_response(302)
        self.send_header("Location", location)
        if clear_cookie:
            self.send_header("Set-Cookie", "session=; Max-Age=0; Path=/; HttpOnly")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/login":
            self._send_login()
            return

        if path == "/logout":
            token = _get_session_token(self.headers)
            _sessions.pop(token, None)
            self._redirect("/login", clear_cookie=True)
            return

        if not self._authenticated():
            self._redirect("/login")
            return

        if path in ("/", ""):
            self._redirect("/dashboard.html")
            return

        super().do_GET()

    def do_POST(self):
        if self.path != "/login":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode(errors="replace")
        data = urllib.parse.parse_qs(body)
        email = data.get("email", [""])[0].strip().lower()
        password = data.get("password", [""])[0]

        if not email.endswith("@b-ite.de"):
            self._send_login("Nur @b-ite.de E-Mail-Adressen sind erlaubt.")
            return

        if _check_password(password):
            token = uuid.uuid4().hex
            _sessions[token] = email
            self.send_response(302)
            self.send_header("Location", "/dashboard.html")
            self.send_header(
                "Set-Cookie",
                f"session={token}; Path=/; HttpOnly; SameSite=Lax"
            )
            self.end_headers()
            return

        self._send_login("E-Mail oder Passwort falsch.")


with socketserver.TCPServer(("", PORT), AuthHandler) as httpd:
    httpd.allow_reuse_address = True
    print(f"Server läuft auf Port {PORT}")
    httpd.serve_forever()
