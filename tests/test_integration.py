"""
Pruebas de Integración - Centro Deportivo
Flujo completo: Registro → Login → Reserva → Pago → Notificaciones
"""
import unittest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import Settings
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.court_repository import CourtRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.auth_service import AuthService
from app.services.reservation_service import ReservationService
from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService


class TestIntegracionCompleta(unittest.TestCase):
    """Pruebas de integración del flujo completo del sistema"""

    @classmethod
    def setUpClass(cls):
        """Configuración única para todas las pruebas"""
        cls.settings = Settings.from_env()
        # Using real SMTP mode from .env for realistic integration testing
        
    def setUp(self):
        """Configuración antes de cada prueba"""
        # Initialize repositories
        self.user_repo = UserRepository(self.settings)
        self.session_repo = SessionRepository(self.settings)
        self.court_repo = CourtRepository(self.settings)
        self.reservation_repo = ReservationRepository(self.settings)
        self.payment_repo = PaymentRepository(self.settings)
        self.notification_repo = NotificationRepository(self.settings)
        
        # Initialize services
        self.notification_service = NotificationService(self.settings)
        self.auth_service = AuthService(
            self.user_repo, 
            self.session_repo, 
            self.notification_service
        )
        self.reservation_service = ReservationService(
            self.court_repo, 
            self.reservation_repo,
            self.user_repo,
            self.notification_service
        )
        self.payment_service = PaymentService(
            self.settings,
            self.user_repo,
            self.notification_service
        )
        
        # Test data
        self.test_email = f"test_integration_{datetime.now().timestamp()}@example.com"
        self.test_password = "Test1234"
        self.test_nombre = "Usuario Test Integración"
    
    def tearDown(self):
        """Limpieza después de cada prueba"""
        # Cleanup: Delete test reservations older than 1 hour to avoid conflicts
        from app.core.db import get_connection
        conn = get_connection(self.settings)
        try:
            with conn.cursor() as cur:
                # Delete old test reservations
                cur.execute("""
                    DELETE FROM reservas 
                    WHERE created_at < NOW() - INTERVAL '1 hour'
                """)
                conn.commit()
        except Exception as e:
            print(f"Cleanup warning: {e}")
        finally:
            conn.close()

    def test_01_flujo_completo_usuario(self):
        """TEST INTEGRACIÓN 001: Flujo completo de usuario nuevo"""
        print("\n=== TEST: Flujo Completo de Usuario ===")
        
        # 1. REGISTRO
        print("1. Registrando usuario...")
        user = self.auth_service.registrar_usuario(
            self.test_nombre,
            self.test_email,
            self.test_password,
            rol_id=2  # usuario
        )
        self.assertIsNot(user, None)
        self.assertEqual(user.email, self.test_email)
        print(f"   ✓ Usuario registrado: {user.email}")
        
        # Verificar notificación de bienvenida
        notifications = self.notification_repo.get_by_user(user.id)
        welcome_notif = [n for n in notifications if n.tipo == "welcome"]
        self.assertGreater(len(welcome_notif), 0, "Debe existir notificación de bienvenida")
        print(f"   ✓ Notificación de bienvenida enviada: {welcome_notif[0].estado}")
        
        # 2. LOGIN
        print("2. Iniciando sesión...")
        user_auth, session = self.auth_service.autenticar(self.test_email, self.test_password)
        self.assertEqual(user_auth.id, user.id)
        self.assertIsNot(session.token, None)
        print(f"   ✓ Sesión creada: {session.token[:20]}...")
        
        # 3. CREAR RESERVA
        print("3. Creando reserva...")
        # Obtener una cancha disponible
        canchas = self.court_repo.find_all()
        self.assertGreater(len(canchas), 0, "Debe haber canchas creadas en la BD")
        cancha = canchas[0]
        
        # Fecha futura para la reserva
        fecha_inicio = datetime.now() + timedelta(days=1, hours=2)
        fecha_inicio = fecha_inicio.replace(hour=10, minute=0, second=0, microsecond=0)
        duracion = 2
        
        reservation = self.reservation_service.crear_reserva(
            user.id, cancha.id, fecha_inicio, duracion
        )
        self.assertIsNot(reservation, None)
        self.assertEqual(reservation.user_id, user.id)
        self.assertEqual(reservation.estado, "pendiente")  # Estado inicial: pendiente
        print(f"   ✓ Reserva creada: ID {reservation.id}, Estado: {reservation.estado}")
        
        # Nota: La notificación de confirmación se envía DESPUÉS del pago
        
        # 4. REALIZAR PAGO
        print("4. Procesando pago...")
        # Calculate amount
        precio_total = float(cancha.precio_hora) * duracion
        
        payment_data = {
            "amount": precio_total,
            "method": "card",
            "currency": "USD"
        }
        payment_result = self.payment_service.process_payment(user_auth, reservation.id, payment_data)
        self.assertTrue(payment_result.get("ok"), "El pago debe ser exitoso")
        print(f"   ✓ Pago procesado: {payment_result.get('gateway_ref')}")
        
        # Verificar que la reserva se actualizó
        reserva_updated = self.reservation_repo.find_by_id(reservation.id)
        self.assertEqual(reserva_updated.estado, "pagada")
        print(f"   ✓ Reserva actualizada a estado: {reserva_updated.estado}")
        
        # Verificar notificación de pago
        notifications = self.notification_repo.get_by_user(user.id)
        payment_notif = [n for n in notifications if n.tipo == "payment_confirmation"]
        self.assertGreater(len(payment_notif), 0, "Debe existir notificación de pago")
        print(f"   ✓ Notificación de pago enviada: {payment_notif[0].estado}")
        
        # Verificar notificación de confirmación de reserva (enviada DESPUÉS del pago)
        reservation_notif = [n for n in notifications if n.tipo == "reservation_confirmation"]
        self.assertGreater(len(reservation_notif), 0, "Debe existir notificación de confirmación de reserva")
        print(f"   ✓ Notificación de confirmación de reserva: {reservation_notif[0].estado}")
        
        # 5. VERIFICAR PERSISTENCIA
        print("5. Verificando persistencia en BD...")
        # User exists
        user_db = self.user_repo.find_by_email(self.test_email)
        self.assertIsNot(user_db, None)
        # Reservation exists
        reservations = self.reservation_repo.find_by_user(user.id)
        self.assertGreater(len(reservations), 0)
        # Payment exists
        payments = self.payment_repo.find_by_user(user.id)
        self.assertGreater(len(payments), 0)
        # Notifications exist (welcome + payment + reservation)
        all_notifications = self.notification_repo.get_by_user(user.id)
        self.assertGreaterEqual(len(all_notifications), 3, "Debe haber al menos 3 notificaciones")
        print(f"   ✓ Datos persistidos: {len(all_notifications)} notificaciones")
        
        print("\n✅ Flujo completo exitoso!")

    def test_02_cancelacion_reserva(self):
        """TEST INTEGRACIÓN 002: Crear y cancelar reserva"""
        print("\n=== TEST: Cancelación de Reserva ===")
        
        # 1. Crear usuario
        email = f"test_cancel_{datetime.now().timestamp()}@example.com"
        user = self.auth_service.registrar_usuario(
            "Usuario Cancelación",
            email,
            self.test_password,
            rol_id=2
        )
        print(f"1. Usuario creado: {user.email}")
        
        # 2. Crear reserva
        canchas = self.court_repo.find_all()
        cancha = canchas[0]
        fecha_inicio = datetime.now() + timedelta(days=2)
        fecha_inicio = fecha_inicio.replace(hour=14, minute=0, second=0, microsecond=0)
        
        reservation = self.reservation_service.crear_reserva(
            user.id, cancha.id, fecha_inicio, 1
        )
        print(f"2. Reserva creada: ID {reservation.id}")
        
        # 3. Cancelar reserva
        self.reservation_service.cancelar_reserva(reservation.id, user.id, is_admin=False)
        print("3. Reserva cancelada")
        
        # 4. Verificar estado
        reserva_cancelada = self.reservation_repo.find_by_id(reservation.id)
        self.assertEqual(reserva_cancelada.estado, "cancelada")
        print(f"   ✓ Estado verificado: {reserva_cancelada.estado}")
        
        # 5. Verificar notificación de cancelación
        notifications = self.notification_repo.get_by_user(user.id)
        cancel_notif = [n for n in notifications if n.tipo == "cancellation"]
        self.assertGreater(len(cancel_notif), 0, "Debe existir notificación de cancelación")
        print(f"   ✓ Notificación de cancelación: {cancel_notif[0].estado}")
        
        print("\n✅ Cancelación exitosa!")

    def test_03_validacion_disponibilidad(self):
        """TEST INTEGRACIÓN 003: Validar que no se permiten reservas solapadas"""
        print("\n=== TEST: Validación de Disponibilidad ===")
        
        # 1. Crear usuario
        email = f"test_availability_{datetime.now().timestamp()}@example.com"
        user = self.auth_service.registrar_usuario(
            "Usuario Disponibilidad",
            email,
            self.test_password,
            rol_id=2
        )
        print(f"1. Usuario creado")
        
        # 2. Crear primera reserva
        canchas = self.court_repo.find_all()
        cancha = canchas[0]
        fecha_inicio = datetime.now() + timedelta(days=3)
        fecha_inicio = fecha_inicio.replace(hour=16, minute=0, second=0, microsecond=0)
        
        reservation1 = self.reservation_service.crear_reserva(
            user.id, cancha.id, fecha_inicio, 2
        )
        print(f"2. Primera reserva creada: {fecha_inicio} por 2 horas")
        
        # 3. Intentar crear reserva solapada (debe fallar)
        with self.assertRaises(ValueError) as context:
            # Misma hora de inicio
            self.reservation_service.crear_reserva(
                user.id, cancha.id, fecha_inicio, 1
            )
        self.assertIn("ya está reservada", str(context.exception))
        print(f"   ✓ Solapamiento detectado correctamente: {context.exception}")
        
        # 4. Crear reserva en horario diferente (debe funcionar)
        fecha_inicio_2 = fecha_inicio + timedelta(hours=3)  # Después de la primera
        reservation2 = self.reservation_service.crear_reserva(
            user.id, cancha.id, fecha_inicio_2, 1
        )
        self.assertIsNot(reservation2, None)
        print(f"   ✓ Reserva en horario diferente creada exitosamente")
        
        print("\n✅ Validación de disponibilidad correcta!")


if __name__ == "__main__":
    # Run with verbosity
    unittest.main(verbosity=2)
