import http.cookies
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from string import Template
from urllib.parse import parse_qs, urlparse

from app.core.config import Settings
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "web", "templates")
STATIC_DIR = os.path.join(BASE_DIR, "web", "static")


def load_template(name: str) -> Template:
    path = os.path.join(TEMPLATES_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return Template(f.read())


class SimpleHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        settings = Settings.from_env()
        user_repo = UserRepository(settings)
        session_repo = SessionRepository(settings)
        self.auth_service = AuthService(user_repo, session_repo)
        self.settings = settings
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.redirect("/login")
        elif parsed.path == "/login":
            params = parse_qs(parsed.query)
            msg = params.get("msg", [""])[0]
            self.render_html("login.html", {"message": msg})
        elif parsed.path == "/register":
            params = parse_qs(parsed.query)
            msg = params.get("msg", [""])[0]
            self.render_html("register.html", {"message": msg})
        elif parsed.path in ("/dashboard", "/dashboard/admin", "/dashboard/usuario"):
            self.handle_dashboard(parsed.path)
        elif parsed.path == "/logout":
            self.handle_logout()
        elif parsed.path.startswith("/static/"):
            self.serve_static(parsed.path)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/login":
            self.handle_login()
        elif parsed.path == "/register":
            self.handle_register()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def handle_register(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        data = parse_qs(body)
        nombre = data.get("nombre", [""])[0]
        email = data.get("email", [""])[0]
        password = data.get("password", [""])[0]
        rol = data.get("rol", ["usuario"])[0]
        rol_id = 1 if rol == "admin" else 2  # matches seed order
        try:
            self.auth_service.registrar_usuario(nombre, email, password, rol_id)
            self.redirect("/login?msg=Registro%20exitoso")
        except ValueError as exc:
            self.render_html("register.html", {"message": str(exc)})

    def handle_login(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        data = parse_qs(body)
        email = data.get("email", [""])[0]
        password = data.get("password", [""])[0]
        try:
            user, session = self.auth_service.autenticar(email, password)
            cookie = http.cookies.SimpleCookie()
            cookie["session_token"] = session.token
            cookie["session_token"]["httponly"] = True
            cookie["session_token"]["path"] = "/"
            cookie["session_token"]["samesite"] = "Lax"
            # Expira al mismo tiempo que la sesión
            expires = session.expires_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
            cookie["session_token"]["expires"] = expires
            self.send_response(302)
            self.send_header("Location", "/dashboard")
            # Enviar cookie correctamente formateada
            self.send_header("Set-Cookie", cookie["session_token"].OutputString())
            self.end_headers()
        except ValueError as exc:
            self.render_html("login.html", {"message": str(exc)})

    def handle_dashboard(self, path: str):
        user = self.get_current_user()
        if not user:
            self.redirect("/login")
            return
        # Si entra a /dashboard, redirige al dashboard correspondiente
        if path == "/dashboard":
            target = "/dashboard/admin" if user.rol_id == 1 else "/dashboard/usuario"
            self.redirect(target)
            return
        # Evita acceso cruzado de dashboards
        if path == "/dashboard/admin" and user.rol_id != 1:
            self.redirect("/dashboard/usuario")
            return
        if path == "/dashboard/usuario" and user.rol_id == 1:
            self.redirect("/dashboard/admin")
            return
        template = load_template("dashboard.html")
        role_label = "Administrador" if user.rol_id == 1 else "Usuario"
        html = template.substitute(
            nombre=user.nombre, email=user.email, rol=role_label, message=""
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def handle_logout(self):
        token = self.get_session_token()
        self.auth_service.cerrar_sesion(token)
        cookie = http.cookies.SimpleCookie()
        cookie["session_token"] = ""
        cookie["session_token"]["path"] = "/"
        cookie["session_token"]["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
        self.send_response(302)
        self.send_header("Set-Cookie", cookie["session_token"].OutputString())
        self.send_header("Location", "/login")
        self.end_headers()

    def serve_static(self, path: str):
        filename = path.replace("/static/", "", 1)
        file_path = os.path.join(STATIC_DIR, filename)
        if not os.path.exists(file_path):
            self.send_response(404)
            self.end_headers()
            return
        with open(file_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        if file_path.endswith(".css"):
            self.send_header("Content-Type", "text/css")
        else:
            self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(content)

    def get_session_token(self) -> str:
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return ""
        cookies = http.cookies.SimpleCookie()
        cookies.load(cookie_header)
        morsel = cookies.get("session_token")
        return morsel.value if morsel else ""

    def get_current_user(self):
        token = self.get_session_token()
        return self.auth_service.obtener_usuario_actual(token)

    def render_html(self, template_name: str, context: dict):
        template = load_template(template_name)
        html = template.substitute(**context)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def redirect(self, location: str):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()


def run():
    settings = Settings.from_env()
    server_address = ("", settings.server_port)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"Servidor iniciado en http://localhost:{settings.server_port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
