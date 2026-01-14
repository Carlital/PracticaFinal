import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta

from app.services.payment_service import PaymentService

def make_settings():
    class S: pass
    s = S()
    # Crear atributos mínimos que pueden usar los repositorios / servicios
    s.db_host = None
    s.db_port = None
    s.db_name = None
    s.db_user = None
    s.db_password = None
    s.server_port = 8003
    return s

def test_process_payment_sandbox_success(monkeypatch):
    settings = make_settings()
    svc = PaymentService(settings)
    # mock repos
    svc.payment_repo = MagicMock()
    svc.reservation_repo = MagicMock()
    # prepare a fake reservation that belongs to the test user and is "pendiente"
    start = datetime.now()
    end = start + timedelta(hours=1)
    fake_reserva = MagicMock()
    fake_reserva.user_id = 1
    fake_reserva.estado = "pendiente"
    fake_reserva.cancha_id = 1
    fake_reserva.fecha_inicio = start
    fake_reserva.fecha_fin = end
    svc.reservation_repo.find_by_id.return_value = fake_reserva
    # mock court repo to provide a price per hour
    svc.court_repo = MagicMock()
    fake_court = MagicMock()
    fake_court.precio_hora = "10.00"
    svc.court_repo.find_by_id.return_value = fake_court
    # method repo (optional) to avoid DB lookups
    svc.method_repo = MagicMock()
    # force sandbox path
    settings.PAYMENTS_ALWAYS_SUCCESS = True
    result = svc.process_payment(user=MagicMock(id=1), reservation_id=1, payment_data={"amount":"10.00","method":"card"})
    assert result["ok"] is True
    # verify repo called to create payment/transaction
    svc.payment_repo.create_payment.assert_called()