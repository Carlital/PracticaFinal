"""
Pruebas de Aceptación (UAT) - Centro Deportivo
Criterios de aceptación desde la perspectiva del usuario
"""
import unittest
import sys
import os
from datetime import datetime, timedelta

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


class TestAceptacionUsuario(unittest.TestCase):
    """Pruebas de aceptación desde la perspectiva del usuario"""

    @classmethod
    def setUpClass(cls):
        cls.settings = Settings.from_env()
        cls.settings.notification_mode = "simulated"
        
    def setUp(self):
        self.user_repo = UserRepository(self.settings)
        self.session_repo = SessionRepository(self.settings)
        self.court_repo = CourtRepository(self.settings)
        self.reservation_repo = ReservationRepository(self.settings)
        self.payment_repo = PaymentRepository(self.settings)
        self.notification_repo = NotificationRepository(self.settings)
        
        self.notification_service = NotificationService(self.settings)
        self.auth_service = AuthService(
            self.user_repo, self.session_repo, self.notification_service
        )
        self.reservation_service = ReservationService(
            self.court_repo, self.reservation_repo, self.user_repo, self.notification_service
        )
        self.payment_service = PaymentService(
            self.settings, self.user_repo, self.notification_service
        )

    def test_UAT_001_registro_y_email_bienvenida(self):
        """
        UAT-001: Como usuario nuevo,
        quiero registrarme en el sistema y recibir un email de bienvenida,
        para confirmar que mi cuenta fue creada exitosamente.
        """
        print("\n=== UAT-001: Registro y Email de Bienvenida ===")
        
        # DADO que soy un usuario nuevo
        email = f"nuevo_usuario_{datetime.now().timestamp()}@example.com"
        nombre = "Juan Pérez"
        password = "Segura123"
        
        # CUANDO me registro en el sistema
        user = self.auth_service.registrar_usuario(nombre, email, password, rol_id=2)
        
        # ENTONCES mi cuenta debe ser creada
        self.assertIsNot(user, None)
        self.assertEqual(user.email, email)
        self.assertEqual(user.nombre, nombre)
        print(f"✓ Usuario registrado: {user.nombre} ({user.email})")
        
        # Y debo recibir un email de bienvenida
        notifications = self.notification_repo.get_by_user(user.id)
        welcome_emails = [n for n in notifications if n.tipo == "welcome"]
        self.assertEqual(len(welcome_emails), 1, "Debe recibir exactamente 1 email de bienvenida")
        self.assertEqual(welcome_emails[0].estado, "enviado")
        print(f"✓ Email de bienvenida enviado: {welcome_emails[0].asunto}")
        
        print("✅ UAT-001 PASSED")

    def test_UAT_002_visualizar_canchas_disponibles(self):
        """
        UAT-002: Como usuario autenticado,
        quiero visualizar las canchas disponibles,
        para elegir dónde hacer mi reserva.
        """
        print("\n=== UAT-002: Visualizar Canchas Disponibles ===")
        
        # DADO que soy un usuario autenticado
        email = f"user_courts_{datetime.now().timestamp()}@example.com"
        user = self.auth_service.registrar_usuario("Maria Lopez", email, "Pass1234", rol_id=2)
        
        # CUANDO consulto las canchas disponibles
        canchas = self.court_repo.find_all()
        
        # ENTONCES debo ver la lista de canchas con su información
        self.assertGreater(len(canchas), 0, "Debe haber canchas disponibles")
        
        for cancha in canchas:
            self.assertIsNot(cancha.nombre, None)
            self.assertIsNot(cancha.deporte, None)
            self.assertGreater(cancha.precio_hora, 0)
            print(f"✓ Cancha: {cancha.nombre} - {cancha.deporte} - ${cancha.precio_hora}/hora")
        
        print(f"✅ UAT-002 PASSED - {len(canchas)} canchas disponibles")

    def test_UAT_003_hacer_reserva_y_recibir_confirmacion(self):
        """
        UAT-003: Como usuario autenticado,
        quiero hacer una reserva y recibir confirmación por email,
        para asegurar mi espacio deportivo.
        """
        print("\n=== UAT-003: Hacer Reserva y Recibir Confirmación ===")
        
        # DADO que soy un usuario autenticado
        email = f"user_booking_{datetime.now().timestamp()}@example.com"
        user = self.auth_service.registrar_usuario("Carlos Ruiz", email, "Test1234", rol_id=2)
        
        # Y hay canchas disponibles
        canchas = self.court_repo.find_all()
        cancha = canchas[0]
        
        # CUANDO hago una reserva
        fecha_inicio = datetime.now() + timedelta(days=1)
        fecha_inicio = fecha_inicio.replace(hour=15, minute=0, second=0, microsecond=0)
        duracion = 2
        
        reserva = self.reservation_service.crear_reserva(
            user.id, cancha.id, fecha_inicio, duracion
        )
        
        # ENTONCES la reserva debe ser confirmada
        self.assertIsNot(reserva, None)
        self.assertEqual(reserva.estado, "confirmada")
        self.assertEqual(reserva.user_id, user.id)
        print(f"✓ Reserva creada: {cancha.nombre} del {fecha_inicio.strftime('%d/%m/%Y %H:%M')}")
        
        # Y debo recibir un email de confirmación
        notifications = self.notification_repo.get_by_user(user.id)
        conf_emails = [n for n in notifications if n.tipo == "reservation_confirmation"]
        self.assertEqual(len(conf_emails), 1, "Debe recibir email de confirmación de reserva")
        self.assertEqual(conf_emails[0].estado, "enviado")
        self.assertIn(cancha.nombre, conf_emails[0].contenido)
        print(f"✓ Email de confirmación enviado: {conf_emails[0].asunto}")
        
        print("✅ UAT-003 PASSED")

    def test_UAT_004_pagar_reserva_y_recibir_recibo(self):
        """
        UAT-004: Como usuario con una reserva,
        quiero pagar mi reserva y recibir un recibo por email,
        para completar mi transacción.
        """
        print("\n=== UAT-004: Pagar Reserva y Recibir Recibo ===")
        
        # DADO que tengo una reserva pendiente
        email = f"user_payment_{datetime.now().timestamp()}@example.com"
        user = self.auth_service.registrar_usuario("Ana Torres", email, "Secure123", rol_id=2)
        
        canchas = self.court_repo.find_all()
        cancha = canchas[0]
        fecha_inicio = datetime.now() + timedelta(days=2)
        fecha_inicio = fecha_inicio.replace(hour=10, minute=0, second=0, microsecond=0)
        duracion = 1
        
        reserva = self.reservation_service.crear_reserva(
            user.id, cancha.id, fecha_inicio, duracion
        )
        
        # Change to pendiente for payment
        self.reservation_repo.update_status(reserva.id, 'pendiente')
        
        # CUANDO realizo el pago
        monto = float(cancha.precio_hora) * duracion
        payment_data = {"amount": monto, "method": "card", "currency": "USD"}
        
        result = self.payment_service.process_payment(user, reserva.id, payment_data)
        
        # ENTONCES el pago debe ser exitoso
        self.assertTrue(result.get("ok"), "El pago debe ser procesado exitosamente")
        print(f"✓ Pago procesado: ${monto} USD")
        
        # Y la reserva debe cambiar a estado 'pagada'
        reserva_pagada = self.reservation_repo.find_by_id(reserva.id)
        self.assertEqual(reserva_pagada.estado, "pagada")
        print(f"✓ Reserva actualizada a: {reserva_pagada.estado}")
        
        # Y debo recibir un email con el recibo
        notifications = self.notification_repo.get_by_user(user.id)
        payment_emails = [n for n in notifications if n.tipo == "payment_confirmation"]
        self.assertEqual(len(payment_emails), 1, "Debe recibir email de confirmación de pago")
        self.assertEqual(payment_emails[0].estado, "enviado")
        self.assertIn(str(monto), payment_emails[0].contenido)
        print(f"✓ Recibo enviado por email: {payment_emails[0].asunto}")
        
        print("✅ UAT-004 PASSED")

    def test_UAT_005_cancelar_reserva_y_recibir_notificacion(self):
        """
        UAT-005: Como usuario con una reserva,
        quiero cancelarla y recibir notificación,
        para liberar el espacio si no puedo asistir.
        """
        print("\n=== UAT-005: Cancelar Reserva ===")
        
        # DADO que tengo una reserva activa
        email = f"user_cancel_{datetime.now().timestamp()}@example.com"
        user = self.auth_service.registrar_usuario("Luis Gomez", email, "Pass9876", rol_id=2)
        
        canchas = self.court_repo.find_all()
        cancha = canchas[0]
        fecha_inicio = datetime.now() + timedelta(days=5)
        fecha_inicio = fecha_inicio.replace(hour=18, minute=0, second=0, microsecond=0)
        
        reserva = self.reservation_service.crear_reserva(
            user.id, cancha.id, fecha_inicio, 2
        )
        print(f"✓ Reserva creada: ID {reserva.id}")
        
        # CUANDO cancelo mi reserva
        self.reservation_service.cancelar_reserva(reserva.id, user.id, is_admin=False)
        
        # ENTONCES la reserva debe cambiar a estado 'cancelada'
        reserva_cancelada = self.reservation_repo.find_by_id(reserva.id)
        self.assertEqual(reserva_cancelada.estado, "cancelada")
        print(f"✓ Reserva cancelada: {reserva_cancelada.estado}")
        
        # Y debo recibir notificación de cancelación
        notifications = self.notification_repo.get_by_user(user.id)
        cancel_emails = [n for n in notifications if n.tipo == "cancellation"]
        self.assertEqual(len(cancel_emails), 1, "Debe recibir email de cancelación")
        self.assertEqual(cancel_emails[0].estado, "enviado")
        print(f"✓ Notificación de cancelación enviada: {cancel_emails[0].asunto}")
        
        print("✅ UAT-005 PASSED")

    def test_UAT_006_admin_ver_todas_reservas(self):
        """
        UAT-006: Como administrador,
        quiero ver todas las reservas del sistema,
        para gestionar las operaciones del centro deportivo.
        """
        print("\n=== UAT-006: Admin Ver Todas las Reservas ===")
        
        # DADO que soy un administrador
        admin_email = f"admin_{datetime.now().timestamp()}@example.com"
        admin = self.auth_service.registrar_usuario(
            "Admin Sistema", admin_email, "Admin123", rol_id=1
        )
        
        # Y hay múltiples reservas en el sistema
        # Crear algunos usuarios y reservas
        for i in range(3):
            user = self.auth_service.registrar_usuario(
                f"User {i}", f"user{i}_{datetime.now().timestamp()}@test.com", "Pass123", rol_id=2
            )
            canchas = self.court_repo.find_all()
            fecha = datetime.now() + timedelta(days=i+1)
            fecha = fecha.replace(hour=10+i, minute=0, second=0, microsecond=0)
            self.reservation_service.crear_reserva(user.id, canchas[0].id, fecha, 1)
        
        # CUANDO consulto todas las reservas
        all_reservas = self.reservation_repo.find_all_detailed()
        
        # ENTONCES debo ver todas las reservas del sistema
        self.assertGreaterEqual(len(all_reservas), 3, "Debe haber al menos 3 reservas")
        
        for reserva in all_reservas[:3]:
            self.assertIn('usuario', reserva)
            self.assertIn('cancha', reserva)
            self.assertIn('estado', reserva)
            print(f"✓ Reserva: {reserva['usuario']} - {reserva['cancha']} - {reserva['estado']}")
        
        print(f"✅ UAT-006 PASSED - {len(all_reservas)} reservas visibles")

    def test_UAT_007_validacion_conflictos_horarios(self):
        """
        UAT-007: Como usuario,
        el sistema debe prevenir reservas en horarios ocupados,
        para evitar conflictos de programación.
        """
        print("\n=== UAT-007: Validación de Conflictos ===")
        
        # DADO que existe una reserva en un horario específico
        email1 = f"user1_conflict_{datetime.now().timestamp()}@example.com"
        user1 = self.auth_service.registrar_usuario("User Uno", email1, "Test123", rol_id=2)
        
        canchas = self.court_repo.find_all()
        cancha = canchas[0]
        fecha_reserva = datetime.now() + timedelta(days=7)
        fecha_reserva = fecha_reserva.replace(hour=14, minute=0, second=0, microsecond=0)
        
        reserva1 = self.reservation_service.crear_reserva(
            user1.id, cancha.id, fecha_reserva, 2
        )
        print(f"✓ Reserva 1 creada: {fecha_reserva.strftime('%d/%m/%Y %H:%M')} por 2 horas")
        
        # CUANDO otro usuario intenta reservar en el mismo horario
        email2 = f"user2_conflict_{datetime.now().timestamp()}@example.com"
        user2 = self.auth_service.registrar_usuario("User Dos", email2, "Test456", rol_id=2)
        
        # ENTONCES el sistema debe rechazar la reserva
        with self.assertRaises(ValueError) as context:
            self.reservation_service.crear_reserva(
                user2.id, cancha.id, fecha_reserva, 1
            )
        
        self.assertIn("ya está reservada", str(context.exception))
        print(f"✓ Conflicto detectado correctamente: {context.exception}")
        
        # Y debe permitir reservar en otro horario
        fecha_libre = fecha_reserva + timedelta(hours=3)
        reserva2 = self.reservation_service.crear_reserva(
            user2.id, cancha.id, fecha_libre, 1
        )
        self.assertIsNot(reserva2, None)
        print(f"✓ Reserva en horario libre permitida: {fecha_libre.strftime('%H:%M')}")
        
        print("✅ UAT-007 PASSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
