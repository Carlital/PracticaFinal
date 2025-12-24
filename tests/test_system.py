import unittest
import http.client
import urllib.parse
import time
import random
from datetime import datetime, timedelta

# Configuración
SERVER_HOST = "localhost"
SERVER_PORT = 8003
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

class SystemTest(unittest.TestCase):
    def setUp(self):
        self.conn = http.client.HTTPConnection(SERVER_HOST, SERVER_PORT)
        # Generar usuario único para cada prueba
        self.email = f"test_sys_{random.randint(1000,9999)}@example.com"
        self.password = "Password123"
        self.nombre = "System Tester"

    def tearDown(self):
        self.conn.close()

    def get_cookie(self, headers):
        # Extraer token de sesión de los headers
        for header, value in headers:
            if header == 'Set-Cookie':
                return value.split(';')[0]
        return None

    def test_flujo_completo_reserva(self):
        print(f"\nEjecutando prueba de sistema con usuario: {self.email}")

        # 1. REGISTRO
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        params = urllib.parse.urlencode({
            'nombre': self.nombre,
            'email': self.email,
            'password': self.password,
            'rol': 'usuario'
        })
        self.conn.request("POST", "/register", params, headers)
        response = self.conn.getresponse()
        response.read() # Consumir respuesta
        self.assertEqual(response.status, 302, "El registro debería redirigir (302)")

        # 2. LOGIN
        params = urllib.parse.urlencode({
            'email': self.email,
            'password': self.password
        })
        self.conn.request("POST", "/login", params, headers)
        response = self.conn.getresponse()
        response.read()
        self.assertEqual(response.status, 302, "El login debería redirigir (302)")
        
        cookie = self.get_cookie(response.getheaders())
        self.assertIsNotNone(cookie, "El login debería devolver una cookie de sesión")
        
        # Headers autenticados
        auth_headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "Cookie": cookie
        }

        # 3. CREAR RESERVA
        # Reservar para un día futuro y hora aleatoria para evitar colisiones si se corre el test varias veces
        dias_futuros = random.randint(1, 7)
        hora_inicio = random.randint(7, 20) # Horario laboral 7-22, duración 1h
        fecha_reserva = datetime.now() + timedelta(days=dias_futuros)
        fecha_str = fecha_reserva.strftime(f"%Y-%m-%dT{hora_inicio:02d}:00")
        
        params = urllib.parse.urlencode({
            'cancha_id': 1, # Asumimos que existe la cancha ID 1 (seed)
            'fecha_inicio': fecha_str,
            'duracion': 1
        })
        self.conn.request("POST", "/reservar", params, auth_headers)
        response = self.conn.getresponse()
        response.read()
        
        # Si es exitoso, redirige al dashboard
        self.assertEqual(response.status, 302, "La reserva debería redirigir al dashboard")
        self.assertIn("/dashboard/usuario", response.getheader("Location"), "Debe redirigir al dashboard de usuario")
        print("✅ Flujo de sistema completado exitosamente.")

    def test_seguridad_acceso_admin(self):
        print(f"\nEjecutando prueba de seguridad (Acceso Denegado) con usuario: {self.email}")

        # 1. REGISTRO (Usuario normal)
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        params = urllib.parse.urlencode({
            'nombre': self.nombre,
            'email': self.email,
            'password': self.password,
            'rol': 'usuario'
        })
        self.conn.request("POST", "/register", params, headers)
        self.conn.getresponse().read()

        # 2. LOGIN
        params = urllib.parse.urlencode({'email': self.email, 'password': self.password})
        self.conn.request("POST", "/login", params, headers)
        response = self.conn.getresponse()
        response.read()
        cookie = self.get_cookie(response.getheaders())
        auth_headers = {"Cookie": cookie}

        # 3. INTENTAR ACCEDER A ADMIN
        self.conn.request("GET", "/dashboard/admin", headers=auth_headers)
        response = self.conn.getresponse()
        response.read()
        
        self.assertEqual(response.status, 302, "El acceso a admin por un usuario normal debería redirigir")
        self.assertIn("/dashboard/usuario", response.getheader("Location"), "Debe redirigir al dashboard de usuario")
        print("✅ Prueba de seguridad completada: Acceso a admin bloqueado correctamente.")

if __name__ == "__main__":
    unittest.main()