import http.cookies
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from string import Template
from urllib.parse import parse_qs, urlparse

from app.core.config import Settings
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.court_repository import CourtRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.admin_repository import AdminRepository
from app.models.court import Court
from app.services.auth_service import AuthService
from app.services.reservation_service import ReservationService

# Forzar salida sin buffer para ver los logs
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "web", "templates")
STATIC_DIR = os.path.join(BASE_DIR, "web", "static")
IMG_DIR = os.path.join(BASE_DIR, "web", "img")


def load_template(name: str) -> Template:
    path = os.path.join(TEMPLATES_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return Template(f.read())


class SimpleHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        settings = Settings.from_env()
        user_repo = UserRepository(settings)
        session_repo = SessionRepository(settings)
        court_repo = CourtRepository(settings)
        reservation_repo = ReservationRepository(settings)
        self.admin_repo = AdminRepository(settings)
        
        self.auth_service = AuthService(user_repo, session_repo)
        self.reservation_service = ReservationService(court_repo, reservation_repo)
        self.settings = settings
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.render_html("welcome.html", {})
        elif parsed.path == "/login":
            params = parse_qs(parsed.query)
            msg = params.get("msg", [""])[0]
            self.render_html("login.html", {"message": msg})
        elif parsed.path == "/register":
            params = parse_qs(parsed.query)
            msg = params.get("msg", [""])[0]
            self.render_html("register.html", {"message": msg})
        elif parsed.path.startswith("/dashboard/admin"):
            self.handle_admin_dashboard(parsed)
        elif parsed.path in ("/dashboard", "/dashboard/usuario"):
            self.handle_dashboard(parsed.path)
        elif parsed.path == "/logout":
            self.handle_logout()
        elif parsed.path == "/reservar":
            self.render_booking_form()
        elif parsed.path == "/canchas/edit":
            self.render_court_edit(parsed)
        elif parsed.path.startswith("/static/"):
            self.serve_static(parsed.path)
        elif parsed.path.startswith("/img/"):
            self.serve_image(parsed.path)
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
        elif parsed.path == "/reservar":
            self.handle_booking()
        elif parsed.path == "/canchas/create":
            self.handle_court_create()
        elif parsed.path == "/canchas/delete":
            self.handle_court_delete()
        elif parsed.path == "/canchas/edit":
            self.handle_court_update()
        elif parsed.path == "/reservas/cancel":
            self.handle_reservation_cancel()
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
            return
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
            
            # Construir cookie manualmente en formato correcto
            cookie_value = f"session_token={session.token}; Path=/; Max-Age=3600; HttpOnly; SameSite=Lax"
            
            self.send_response(302)
            self.send_header("Set-Cookie", cookie_value)
            self.send_header("Location", "/dashboard")
            self.end_headers()
            return
        except ValueError as exc:
            self.render_html("login.html", {"message": str(exc)})

    def render_booking_form(self, message=""):
        user = self.get_current_user()
        if not user:
            self.redirect("/login")
            return
        # En un caso real, cargaríamos las canchas dinámicamente en el HTML
        # Por simplicidad, renderizamos un HTML básico o usamos un template si existe
        # Aquí asumiremos que existe 'booking.html' o reutilizamos dashboard con mensaje
        try:
            # Listar canchas para el formulario (simplificado)
            canchas = self.reservation_service.court_repo.find_all()
            # Usamos data-price para que JS lo lea. El texto visible es más limpio.
            options = "".join([f'<option value="{c.id}" data-price="{c.precio_hora}">{c.nombre} ({c.deporte})</option>' for c in canchas])
            
            # Generar HTML del mensaje si existe
            message_html = ""
            if message:
                message_html = f"<div class='message-box message-error'>{message}</div>"

            role_label = "Administrador" if user.rol_id == 1 else "Usuario"
            template = load_template("booking.html")
            html = template.safe_substitute(
                options=options,
                nombre=user.nombre,
                rol=role_label,
                year=datetime.now().year,
                message=message_html
            )
            
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode("utf-8"))

    def handle_booking(self):
        user = self.get_current_user()
        if not user:
            self.redirect("/login")
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        data = parse_qs(body)
        
        try:
            cancha_id = int(data.get("cancha_id")[0])
            fecha_str = data.get("fecha_inicio")[0] # Viene como '2023-10-27T10:00'
            duracion = int(data.get("duracion")[0])
            
            # Parsear fecha
            fecha_inicio = datetime.strptime(fecha_str, "%Y-%m-%dT%H:%M")
            
            self.reservation_service.crear_reserva(user.id, cancha_id, fecha_inicio, duracion)
            self.redirect("/dashboard/usuario?msg=Reserva%20Exitosa")
        except Exception as e:
            self.render_booking_form(message=f"Error: {str(e)}")

    def handle_court_create(self):
        user = self.get_current_user()
        if not user or user.rol_id != 1: # Solo admin
            self.send_response(403)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        data = parse_qs(body)
        try:
            nombre = data.get("nombre")[0]
            deporte = data.get("deporte")[0]
            precio = float(data.get("precio")[0])
            new_court = Court(id=0, nombre=nombre, deporte=deporte, precio_hora=precio)
            self.reservation_service.court_repo.create(new_court)
            self.redirect("/dashboard/admin?msg=Cancha%20Creada")
        except Exception as e:
            self.redirect(f"/dashboard/admin?msg=Error:{str(e)}")

    def handle_court_delete(self):
        user = self.get_current_user()
        if not user or user.rol_id != 1:
            self.send_response(403)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        data = parse_qs(body)
        cancha_id = int(data.get("id")[0])
        self.reservation_service.court_repo.delete(cancha_id)
        self.redirect("/dashboard/admin?msg=Cancha%20Eliminada")

    def render_court_edit(self, parsed):
        user = self.get_current_user()
        if not user or user.rol_id != 1:
            self.redirect("/dashboard")
            return
        
        query = parse_qs(parsed.query)
        cancha_id = int(query.get("id", [0])[0])
        cancha = self.reservation_service.court_repo.find_by_id(cancha_id)
        
        if not cancha:
            self.redirect("/dashboard/admin?msg=Cancha%20no%20encontrada")
            return

        # Generar opciones de deporte seleccionando el actual
        deportes = ["futbol", "tenis", "basquet"]
        options_html = ""
        for d in deportes:
            selected = "selected" if d == cancha.deporte else ""
            options_html += f'<option value="{d}" {selected}>{d.capitalize()}</option>'

        template = load_template("admin_cancha_edit.html")
        content_html = template.safe_substitute(
            id=cancha.id,
            nombre=cancha.nombre,
            precio=cancha.precio_hora,
            options_deporte=options_html
        )
        self.render_dashboard_layout(user, "Administrador", "", content_html)

    def handle_court_update(self):
        user = self.get_current_user()
        if not user or user.rol_id != 1:
            self.send_response(403); return
        
        length = int(self.headers.get("Content-Length", "0"))
        data = parse_qs(self.rfile.read(length).decode())
        
        try:
            cancha = Court(
                id=int(data.get("id")[0]),
                nombre=data.get("nombre")[0],
                deporte=data.get("deporte")[0],
                precio_hora=float(data.get("precio")[0])
            )
            self.reservation_service.court_repo.update(cancha)
            self.redirect("/dashboard/admin?msg=Cancha%20Actualizada")
        except Exception as e:
            self.redirect(f"/dashboard/admin?msg=Error:{str(e)}")

    def handle_reservation_cancel(self):
        user = self.get_current_user()
        if not user:
            self.redirect("/login")
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        data = parse_qs(body)
        reservation_id = int(data.get("id")[0])
        is_admin = (user.rol_id == 1)
        try:
            self.reservation_service.cancelar_reserva(reservation_id, user.id, is_admin)
            target = "/dashboard/admin" if is_admin else "/dashboard/usuario"
            self.redirect(f"{target}?msg=Reserva%20Cancelada")
        except ValueError as e:
            target = "/dashboard/admin" if is_admin else "/dashboard/usuario"
            self.redirect(f"{target}?msg=Error:%20{str(e)}")

    def handle_admin_dashboard(self, parsed):
        user = self.get_current_user()
        if not user:
            self.redirect("/login")
            return
        if user.rol_id != 1:
            self.redirect("/dashboard/usuario")
            return

        path = parsed.path
        query = parse_qs(parsed.query)
        msg = query.get("msg", [""])[0]

        # Lógica para el Dashboard de Admin
        
        # 1. Vista de Detalle (Se mantiene separada por claridad)
        if path == "/dashboard/admin/reservas/detalle":
            # Detalle de Reserva
            res_id = int(query.get("id", [0])[0])
            reserva = self.reservation_service.reservation_repo.find_detailed_by_id(res_id)
            if not reserva:
                self.redirect("/dashboard/admin/reservas?msg=Reserva%20no%20encontrada")
                return
            
            acciones = ""
            if reserva['estado'] == 'pendiente':
                acciones = f"<form action='/reservas/cancel' method='POST'><input type='hidden' name='id' value='{reserva['id']}'><button type='submit' class='btn btn-danger'>Cancelar Reserva</button></form>"
            else:
                acciones = "<p style='color:#666;'>No hay acciones disponibles para este estado.</p>"

            template = load_template("admin_reserva_detalle.html")
            content_html = template.safe_substitute(**reserva, acciones=acciones)
            self.render_dashboard_layout(user, "Administrador", msg, content_html)
            return

        # 2. Dashboard Principal (Consolidado: Canchas + Usuarios + Reservas)
        
        # Datos Canchas
        canchas = self.reservation_service.court_repo.find_all()
        canchas_rows = "".join([
            f"<tr><td>{c.id}</td><td>{c.nombre}</td><td>{c.deporte}</td><td>${c.precio_hora}</td>"
            f"<td><a href='/canchas/edit?id={c.id}' class='btn btn-secondary' style='padding:5px 10px; font-size:0.8rem; margin-right:5px; width:auto;'>Editar</a>"
            f"<form action='/canchas/delete' method='POST' style='display:inline'><input type='hidden' name='id' value='{c.id}'><button type='submit' class='btn btn-danger' style='padding:5px 10px; font-size:0.8rem; width:auto;'>Eliminar</button></form></td></tr>" 
            for c in canchas
        ])

        # Datos Usuarios
        users = self.admin_repo.get_all_users()
        users_rows = "".join([f"<tr><td>{u['id']}</td><td>{u['nombre']}</td><td>{u['email']}</td><td>{u['rol']}</td></tr>" for u in users])

        # Datos Reservas
        reservas = self.reservation_service.reservation_repo.find_all_detailed()
        reservas_rows = ""
        for r in reservas:
            # Acción: Ver Detalle
            accion = f"<a href='/dashboard/admin/reservas/detalle?id={r['id']}' class='btn btn-secondary' style='padding:5px 10px; font-size:0.8rem;'>Ver Detalle</a>"
            reservas_rows += f"<tr><td>{r['id']}</td><td>{r['usuario']}</td><td>{r['cancha']}</td><td>{r['fecha_inicio']}</td><td>{r['estado']}</td><td>{accion}</td></tr>"

        # Renderizar todo en dashboard_admin.html
        template = load_template("dashboard_admin.html")
        content_html = template.safe_substitute(
            canchas_rows=canchas_rows,
            users_rows=users_rows,
            reservas_rows=reservas_rows
        )
        self.render_dashboard_layout(user, "Administrador", msg, content_html)

    def handle_dashboard(self, path: str):
        user = self.get_current_user()
        if not user:
            self.redirect("/login")
            return
        if path == "/dashboard":
            target = "/dashboard/admin" if user.rol_id == 1 else "/dashboard/usuario"
            self.redirect(target)
            return
        role_label = "Administrador" if user.rol_id == 1 else "Usuario"
        
        # Capturar mensaje de query param si existe
        query = urlparse(self.path).query
        msg = parse_qs(query).get("msg", [""])[0]
        
        # Generar contenido dinámico según el rol
        content_html = ""
        if path == "/dashboard/usuario": # Vista de Usuario (accesible para admin también)
            # Tabla de mis reservas
            mis_reservas = self.reservation_service.reservation_repo.find_by_user(user.id)
            if not mis_reservas:
                reservas_rows = "<tr><td colspan='5' style='text-align:center; padding:20px;'>No tienes reservas activas.</td></tr>"
            else:
                reservas_rows = ""
                for r in mis_reservas:
                    # Definir colores según estado
                    if r['estado'] == 'confirmada':
                        estado_color, bg_color = "#2e7d32", "#e8f5e9" # Verde
                    elif r['estado'] == 'pendiente':
                        estado_color, bg_color = "#ef6c00", "#fff3e0" # Naranja
                    else:
                        estado_color, bg_color = "#d32f2f", "#ffebee" # Rojo

                    accion = ""
                    if r['estado'] == 'pendiente':
                        accion = f"<button type='button' class='btn' style='padding:5px 10px; font-size:0.8rem; width:auto; margin-right:5px; background-color:#1976d2; cursor:pointer;' title='Función de pago próximamente'>Pagar</button>"
                        accion += f"<form action='/reservas/cancel' method='POST' style='display:inline'><input type='hidden' name='id' value='{r['id']}'><button type='submit' class='btn btn-danger' style='padding:5px 10px; font-size:0.8rem; width:auto; margin:0;'>Cancelar</button></form>"
                    elif r['estado'] == 'confirmada':
                        accion = f"<form action='/reservas/cancel' method='POST' style='display:inline'><input type='hidden' name='id' value='{r['id']}'><button type='submit' class='btn btn-danger' style='padding:5px 10px; font-size:0.8rem; width:auto; margin:0;'>Cancelar</button></form>"
                    else:
                        accion = "<span style='color:#999; font-size:0.9rem;'>-</span>"
                    
                    reservas_rows += f"<tr><td>{r['cancha']}</td><td>{r['fecha_inicio']}</td><td>{r['fecha_fin']}</td><td><span class='badge' style='background:{bg_color}; color:{estado_color};'>{r['estado']}</span></td><td>{accion}</td></tr>"
            
            # Si es admin viendo como usuario, agregar botón para volver
            admin_controls = ""
            if user.rol_id == 1:
                admin_controls = "<div style='background:#fff3e0; padding:10px; border:1px solid #ffe0b2; border-radius:8px; margin-bottom:20px; text-align:center;'>👀 Estás viendo la vista de Usuario. <a href='/dashboard/admin' style='font-weight:bold;'>Volver al Panel de Admin</a></div>"

            # Cargar plantilla parcial de usuario
            template_user = load_template("dashboard_user.html")
            content_html = template_user.safe_substitute(
                nombre=user.nombre + (" (Admin)" if user.rol_id == 1 else ""),
                reservas_rows=reservas_rows
            )
            content_html = admin_controls + content_html
        
        self.render_dashboard_layout(user, role_label, msg, content_html)

    def render_dashboard_layout(self, user, role_label, msg, content_html):
        # Inyectamos el contenido en el mensaje o concatenamos
        # Como el template usa $message, vamos a poner todo el HTML ahí.
        # Si hay un mensaje de error/exito (msg), lo ponemos arriba.
        full_message = ""
        if msg:
            msg_class = "message-error" if "Error" in msg else "message-success"
            full_message += f"<div class='message-box {msg_class}'>{msg}</div>"
        full_message += content_html

        template = load_template("dashboard.html")
        html = template.substitute(
            nombre=user.nombre,
            email=user.email,
            rol=role_label,
            content=full_message,
            year=datetime.now().year
        )
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def handle_logout(self):
        token = self.get_session_token()
        self.auth_service.cerrar_sesion(token)
        expires = "Thu, 01 Jan 1970 00:00:00 GMT"
        cookie_header = (
            f"session_token=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0; Expires={expires}"
        )
        self.send_response(302)
        self.send_header("Set-Cookie", cookie_header)
        self.send_header("Location", "/")
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

    def serve_image(self, path: str):
        filename = path.replace("/img/", "", 1)
        file_path = os.path.join(IMG_DIR, filename)
        if not os.path.exists(file_path):
            self.send_response(404)
            self.end_headers()
            return
        with open(file_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        # Tipos de contenido básicos para imágenes
        if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
            self.send_header("Content-Type", "image/jpeg")
        elif filename.lower().endswith(".png"):
            self.send_header("Content-Type", "image/png")
        self.end_headers()
        self.wfile.write(content)

    def get_session_token(self) -> str:
        cookie_header = self.headers.get("Cookie")
        print(f"[DEBUG] Cookie header: {cookie_header}")
        if not cookie_header:
            print("[DEBUG] No cookie header found")
            return ""
        cookies = http.cookies.SimpleCookie()
        cookies.load(cookie_header)
        morsel = cookies.get("session_token")
        return morsel.value if morsel else ""

    def get_current_user(self):
        token = self.get_session_token()
        user = self.auth_service.obtener_usuario_actual(token)
        print(f"[DEBUG] User from token: {user.email if user else 'None'}")
        return user

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
