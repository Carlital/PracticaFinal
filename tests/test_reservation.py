import unittest
from datetime import datetime, timedelta
from app.models.court import Court
from app.models.reservation import Reservation
from app.services.reservation_service import ReservationService

# Mocks simples para pruebas unitarias sin base de datos
class FakeCourtRepo:
    def find_by_id(self, id):
        if id == 1:
            return Court(1, "Cancha Test", "futbol", 20.0)
        return None

class FakeReservationRepo:
    def __init__(self):
        self.reservations = []

    def create(self, reservation):
        reservation.id = len(self.reservations) + 1
        self.reservations.append(reservation)
        return reservation

    def find_overlapping(self, cancha_id, start, end):
        overlapping = []
        for r in self.reservations:
            if r.cancha_id == cancha_id and r.estado != 'cancelada':
                # Lógica de solapamiento
                if start < r.fecha_fin and end > r.fecha_inicio:
                    overlapping.append(r)
        return overlapping

class ReservationServiceTest(unittest.TestCase):
    def setUp(self):
        self.court_repo = FakeCourtRepo()
        self.res_repo = FakeReservationRepo()
        self.service = ReservationService(self.court_repo, self.res_repo)

    def test_crear_reserva_exitosa(self):
        # Reserva para mañana a las 10am
        fecha = datetime.now() + timedelta(days=1)
        fecha = fecha.replace(hour=10, minute=0, second=0, microsecond=0)
        
        reserva = self.service.crear_reserva(user_id=1, cancha_id=1, fecha_inicio=fecha, duracion_horas=1)
        
        self.assertIsNotNone(reserva.id)
        self.assertEqual(reserva.estado, "pendiente")

    def test_error_doble_reserva(self):
        # Crear primera reserva
        fecha = datetime.now() + timedelta(days=1)
        fecha = fecha.replace(hour=10, minute=0, second=0, microsecond=0)
        self.service.crear_reserva(1, 1, fecha, 2) # 10:00 - 12:00

        # Intentar reservar en horario solapado (11:00 - 13:00)
        fecha_solapada = fecha + timedelta(hours=1)
        with self.assertRaises(ValueError) as cm:
            self.service.crear_reserva(2, 1, fecha_solapada, 2)
        self.assertIn("ya está reservada", str(cm.exception))

    def test_error_horario_invalido(self):
        # Intentar reservar a las 5 AM (fuera de horario 7-22)
        fecha = datetime.now() + timedelta(days=1)
        fecha = fecha.replace(hour=5, minute=0)
        with self.assertRaises(ValueError):
            self.service.crear_reserva(1, 1, fecha, 1)

if __name__ == "__main__":
    unittest.main()