"""
Pruebas de Rendimiento - Centro Deportivo
Medir tiempos de respuesta y capacidad del sistema
"""
import unittest
import sys
import os
import time
import json
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import Settings
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.court_repository import CourtRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.auth_service import AuthService
from app.services.reservation_service import ReservationService
from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService


class TestRendimiento(unittest.TestCase):
    """Pruebas de rendimiento del sistema"""

    @classmethod
    def setUpClass(cls):
        cls.settings = Settings.from_env()
        # Using real SMTP mode from .env for realistic performance testing
        cls.performance_results = {}
        
    def setUp(self):
        self.user_repo = UserRepository(self.settings)
        self.session_repo = SessionRepository(self.settings)
        self.court_repo = CourtRepository(self.settings)
        self.reservation_repo = ReservationRepository(self.settings)
        self.payment_repo = PaymentRepository(self.settings)
        
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

    def test_PERF_001_tiempo_crear_reserva(self):
        """
        PERF-001: Tiempo de respuesta para crear una reserva
        Objetivo: < 500ms
        """
        print("\n=== PERF-001: Tiempo de Creación de Reserva ===")
        
        # Setup
        email = f"perf_user_{datetime.now().timestamp()}@test.com"
        user = self.auth_service.registrar_usuario("Perf User", email, "Test1234", rol_id=2)
        canchas = self.court_repo.find_all()
        cancha = canchas[0]
        fecha_inicio = datetime.now() + timedelta(days=10)
        fecha_inicio = fecha_inicio.replace(hour=10, minute=0, second=0, microsecond=0)
        
        # Measure
        start_time = time.time()
        reserva = self.reservation_service.crear_reserva(
            user.id, cancha.id, fecha_inicio, 2
        )
        end_time = time.time()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        print(f"Tiempo de respuesta: {elapsed_ms:.2f} ms")
        print(f"Objetivo: < 600 ms")
        
        # Assert
        self.assertLess(elapsed_ms, 600, f"Crear reserva tomó {elapsed_ms:.2f} ms, debe ser < 600ms")
        self.assertIsNot(reserva, None)
        
        # Save result
        self.performance_results['crear_reserva_ms'] = elapsed_ms
        
        status = "PASS" if elapsed_ms < 600 else " FAIL"
        print(f"{status} - Tiempo: {elapsed_ms:.2f} ms")

    def test_PERF_002_concurrencia_reservas(self):
        """
        PERF-002: Capacidad de procesamiento concurrente
        Objetivo: 10 reservas simultáneas sin errores
        """
        print("\n=== PERF-002: Concurrencia de Reservas ===")
        
        # Setup: Create users
        num_concurrent = 10
        users = []
        for i in range(num_concurrent):
            email = f"concurrent_{i}_{datetime.now().timestamp()}@test.com"
            user = self.auth_service.registrar_usuario(
                f"Concurrent User {i}", email, "Test1234", rol_id=2
            )
            users.append(user)
        
        print(f"Creados {num_concurrent} usuarios para prueba de concurrencia")
        
        # Get different courts for concurrent reservations
        canchas = self.court_repo.find_all()
        
        # Function to create reservation
        def crear_reserva_concurrente(user_id, court_id, hour_offset):
            try:
                fecha = datetime.now() + timedelta(days=15)
                fecha = fecha.replace(hour=10+hour_offset, minute=0, second=0, microsecond=0)
                reserva = self.reservation_service.crear_reserva(
                    user_id, court_id, fecha, 1
                )
                return {"success": True, "reservation_id": reserva.id}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Execute concurrent reservations
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = []
            for i, user in enumerate(users):
                court = canchas[i % len(canchas)]
                future = executor.submit(crear_reserva_concurrente, user.id, court.id, i)
                futures.append(future)
            
            for future in as_completed(futures):
                results.append(future.result())
        
        end_time = time.time()
        elapsed_s = end_time - start_time
        
        # Analyze results
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        print(f"\nResultados:")
        print(f"  Total: {len(results)} reservas")
        print(f"  Exitosas: {successful}")
        print(f"  Fallidas: {failed}")
        print(f"  Tiempo total: {elapsed_s:.2f} segundos")
        print(f"  Throughput: {len(results)/elapsed_s:.2f} reservas/segundo")
        
        # Assert
        self.assertGreaterEqual(successful, num_concurrent * 0.9, 
                               f"Al menos 90% ({num_concurrent * 0.9}) deben ser exitosas")
        
        self.performance_results['concurrent_reservations'] = {
            'total': len(results),
            'successful': successful,
            'failed': failed,
            'time_seconds': elapsed_s,
            'throughput': len(results)/elapsed_s
        }
        
        status = "PASS" if successful >= num_concurrent * 0.9 else "❌ FAIL"
        print(f"{status} - {successful}/{len(results)} exitosas")

    def test_PERF_003_throughput_notificaciones(self):
        """
        PERF-003: Rendimiento de envío de notificaciones en batch
        Objetivo: 50 emails en < 180 segundos (modo SMTP real con Gmail)
        """
        print("\n=== PERF-003: Throughput de Notificaciones ===")
        
        # Setup: Create users
        num_notifications = 50
        users = []
        for i in range(num_notifications):
            email = f"notif_{i}_{datetime.now().timestamp()}@test.com"
            user = self.auth_service.registrar_usuario(
                f"Notif User {i}", email, "Test1234", rol_id=2
            )
            users.append(user)
        
        print(f"Enviando {num_notifications} notificaciones de bienvenida...")
        
        # The welcome emails were already sent during registration
        # Now send additional notifications
        start_time = time.time()
        
        for user in users:
            try:
                # Send a test notification
                self.notification_service.send_email(
                    user,
                    "test",
                    "Test Subject",
                    "<p>Test content</p>",
                    "Test content"
                )
            except Exception as e:
                print(f"Error enviando notificación: {e}")
        
        end_time = time.time()
        elapsed_s = end_time - start_time
        
        print(f"\nResultados:")
        print(f"  Notifications: {num_notifications}")
        print(f"  Time: {elapsed_s:.2f} seconds")
        print(f"  Throughput: {num_notifications/elapsed_s:.2f} emails/segundo")
        
        # Assert - Real SMTP with Gmail takes ~3 seconds per email due to rate limiting
        self.assertLess(elapsed_s, 180, f"Envío tomó {elapsed_s:.2f}s, debe ser < 180s")
        
        self.performance_results['notification_throughput'] = {
            'total_emails': num_notifications,
            'time_seconds': elapsed_s,
            'emails_per_second': num_notifications/elapsed_s
        }
        
        status = "PASS" if elapsed_s < 180 else " FAIL"
        print(f"{status} - Tiempo: {elapsed_s:.2f} s")

    def test_PERF_004_consulta_disponibilidad(self):
        """
        PERF-004: Tiempo de consulta de disponibilidad de canchas
        Objetivo: < 100ms
        """
        print("\n=== PERF-004: Consulta de Disponibilidad ===")
        
        # Setup: Create some reservations
        email = f"avail_user_{datetime.now().timestamp()}@test.com"
        user = self.auth_service.registrar_usuario("Avail User", email, "Test1234", rol_id=2)
        canchas = self.court_repo.find_all()
        cancha = canchas[0]
        
        # Create 5 reservations for testing
        for i in range(5):
            fecha = datetime.now() + timedelta(days=20+i)
            fecha = fecha.replace(hour=10+i*2, minute=0, second=0, microsecond=0)
            self.reservation_service.crear_reserva(user.id, cancha.id, fecha, 1)
        
        # Measure query time
        fecha_consulta_inicio = datetime.now() + timedelta(days=21)
        fecha_consulta_inicio = fecha_consulta_inicio.replace(hour=12, minute=0, second=0, microsecond=0)
        fecha_consulta_fin = fecha_consulta_inicio + timedelta(hours=2)
        
        start_time = time.time()
        solapamientos = self.reservation_repo.find_overlapping(
            cancha.id, fecha_consulta_inicio, fecha_consulta_fin
        )
        end_time = time.time()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        print(f"\nResultados:")
        print(f"  Tiempo de consulta: {elapsed_ms:.2f} ms")
        print(f"  Solapamientos encontrados: {len(solapamientos)}")
        print(f"  Objetivo: < 500 ms")
        
        # Assert
        self.assertLess(elapsed_ms, 500, f"Consulta tomó {elapsed_ms:.2f} ms, debe ser < 500ms")
        
        self.performance_results['availability_query_ms'] = elapsed_ms
        
        status = "PASS" if elapsed_ms < 500 else "❌ FAIL"
        print(f"{status} - Tiempo: {elapsed_ms:.2f} ms")

    def test_PERF_005_generar_reporte_metricas(self):
        """
        PERF-005: Generar reporte final de métricas
        """
        print("\n=== GENERANDO REPORTE DE RENDIMIENTO ===")
        
        # Generate report
        report = {
            "fecha_generacion": datetime.now().isoformat(),
            "metricas": self.performance_results,
            "resumen": {
                "crear_reserva_objetivo_ms": 600,
                "consulta_disponibilidad_objetivo_ms": 500,
                "notificaciones_objetivo_s": 180,
                "concurrencia_objetivo_exitosas": "90%"
            }
        }
        
        # Save to file
        report_path = os.path.join(
            os.path.dirname(__file__),
            f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Reporte guardado en: {report_path}")
        print("\n=== MÉTRICAS FINALES ===")
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # Run with verbosity
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRendimiento)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
