from datetime import datetime, timedelta
from typing import Optional
from app.models.reservation import Reservation
from app.repositories.court_repository import CourtRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService

class ReservationService:
    def __init__(self, court_repo: CourtRepository, reservation_repo: ReservationRepository, user_repo: Optional[UserRepository] = None, notification_service: Optional[NotificationService] = None):
        self.court_repo = court_repo
        self.reservation_repo = reservation_repo
        self.user_repo = user_repo
        self.notification_service = notification_service

    def crear_reserva(self, user_id: int, cancha_id: int, fecha_inicio: datetime, duracion_horas: int) -> Reservation:
        # 1. Validar existencia de cancha
        cancha = self.court_repo.find_by_id(cancha_id)
        if not cancha:
            raise ValueError("La cancha seleccionada no existe.")

        # 2. Validar duración (1 a 3 horas)
        if duracion_horas < 1 or duracion_horas > 3:
            raise ValueError("La duración de la reserva debe ser entre 1 y 3 horas.")

        # 3. Calcular fecha fin
        fecha_fin = fecha_inicio + timedelta(hours=duracion_horas)

        # 4. Validar fecha pasada
        if fecha_inicio < datetime.now():
            raise ValueError("No se puede reservar en una fecha u hora pasada.")

        # 5. Validar reglas de horario laboral (07:00 - 22:00)
        inicio_jornada = fecha_inicio.replace(hour=7, minute=0, second=0, microsecond=0)
        fin_jornada = fecha_inicio.replace(hour=22, minute=0, second=0, microsecond=0)

        if fecha_inicio < inicio_jornada or fecha_fin > fin_jornada:
             raise ValueError("El horario de atención es de 07:00 a 22:00.")

        # 6. Validar disponibilidad (Evitar doble reserva)
        solapamientos = self.reservation_repo.find_overlapping(cancha_id, fecha_inicio, fecha_fin)
        if solapamientos:
            raise ValueError("La cancha ya está reservada en ese horario.")

        # 7. Crear reserva
        nueva_reserva = Reservation(
            user_id=user_id,
            cancha_id=cancha_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado="pendiente"  # Pendiente hasta que se pague
        )
        
        created_reservation = self.reservation_repo.create(nueva_reserva)
        
        # NOTE: La notificación de confirmación se envía DESPUÉS del pago exitoso
        # No enviamos email aquí porque la reserva aún está pendiente de pago
        
        return created_reservation

    def cancelar_reserva(self, reservation_id: int, user_id: int, is_admin: bool):
        reserva = self.reservation_repo.find_by_id(reservation_id)
        if not reserva:
            raise ValueError("Reserva no encontrada.")
        
        # Validar permisos (si no es admin, debe ser el dueño)
        if not is_admin and reserva.user_id != user_id:
            raise ValueError("No tienes permiso para cancelar esta reserva.")
            
        # Validar que no sea una reserva pasada
        if reserva.fecha_inicio < datetime.now():
             raise ValueError("No se puede cancelar una reserva que ya pasó.")

        self.reservation_repo.update_status(reservation_id, 'cancelada')
        
        # Send cancellation notification
        if self.notification_service and self.user_repo:
            try:
                user = self.user_repo.find_by_id(reserva.user_id)
                cancha = self.court_repo.find_by_id(reserva.cancha_id)
                if user and cancha:
                    reservation_data = {
                        "cancha": cancha.nombre,
                        "fecha_inicio": reserva.fecha_inicio.strftime("%d/%m/%Y %H:%M")
                    }
                    self.notification_service.send_cancellation_notification(user, reservation_data)
            except Exception as e:
                print(f"[WARNING] Error sending cancellation notification email: {e}")