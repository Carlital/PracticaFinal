import os
import uuid
from decimal import Decimal
from typing import Dict
import stripe

from app.models.payment import Payment, Transaction
from app.repositories.payment_repository import PaymentRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.court_repository import CourtRepository
from app.repositories.payment_method_repository import PaymentMethodRepository


class PaymentService:
    def __init__(self, settings):
        self.settings = settings
        self.payment_repo = PaymentRepository(settings)
        self.reservation_repo = ReservationRepository(settings)
        self.court_repo = CourtRepository(settings)
        self.method_repo = PaymentMethodRepository(settings)

    def process_payment(self, user, reservation_id: int, payment_data: Dict) -> Dict:
        """Procesa un pago: valida la reserva, crea payment, simula gateway, crea transaction y actualiza estados.

        payment_data debe contener al menos: `method` y `amount` (string/number)
        """
        reserva = self.reservation_repo.find_by_id(reservation_id)
        if not reserva:
            raise ValueError("Reserva no encontrada.")
        if reserva.user_id != user.id:
            raise ValueError("No tienes permiso para pagar esta reserva.")
        if reserva.estado != "pendiente":
            raise ValueError("Solo se puede pagar una reserva en estado 'pendiente'.")

        # Calcular monto esperado
        cancha = self.court_repo.find_by_id(reserva.cancha_id)
        if not cancha:
            raise ValueError("Cancha no encontrada.")
        dur_horas = (reserva.fecha_fin - reserva.fecha_inicio).total_seconds() / 3600
        expected_amount = Decimal(cancha.precio_hora) * Decimal(dur_horas)

        try:
            provided_amount = Decimal(str(payment_data.get("amount")))
        except Exception:
            raise ValueError("Monto inválido para el pago.")

        if provided_amount < expected_amount:
            raise ValueError(f"El monto es insuficiente. Se requiere {expected_amount}")

        # Determinar método de pago (si viene por id o por tipo)
        method = payment_data.get("method")
        method_obj = None
        payment_method_id = None
        try:
            # si el frontend envía id numérico
            if isinstance(method, str) and method.isdigit():
                # buscar por id
                all_methods = self.method_repo.find_all()
                for m in all_methods:
                    if m['id'] == int(method):
                        method_obj = m
                        payment_method_id = m['id']
                        break
            else:
                method_obj = self.method_repo.find_by_name(method)
                payment_method_id = method_obj['id'] if method_obj else None
        except Exception:
            payment_method_id = None

        # Crear registro de pago (pendiente)
        payment = Payment(user_id=user.id, reservation_id=reservation_id, amount=float(provided_amount), currency=payment_data.get("currency", "USD"), payment_method_id=payment_method_id)
        payment = self.payment_repo.create_payment(payment)

        # Simular gateway (sandbox configurable por env PAYMENTS_SANDBOX)
        sandbox = os.environ.get("PAYMENTS_SANDBOX", "true").lower() in ("1", "true", "yes")
        always_ok = os.environ.get("PAYMENTS_ALWAYS_SUCCESS", "false").lower() in ("1", "true", "yes")
        gateway_ref = str(uuid.uuid4())
        if always_ok:
            success = True
        elif sandbox:
            # simulación simple: si gateway_ref termina en dígito par => success
            success = gateway_ref[-1] in "02468"
        else:
            # En producción integrar con verdadero gateway aquí
            success = True

        # Log para depuración local
        print(f"[PAYMENTS] gateway_ref={gateway_ref} sandbox={sandbox} always_ok={always_ok} success={success}")

        tx_status = "success" if success else "failed"
        tx = Transaction(payment_id=payment.id, gateway_ref=gateway_ref, status=tx_status, details={"method": payment_data.get("method")})
        tx = self.payment_repo.create_transaction(tx)

        if success:
            self.payment_repo.update_payment_status(payment.id, "confirmado")
            # Actualizar reserva a pagada
            self.reservation_repo.update_status(reservation_id, "pagada")
            return {"ok": True, "payment_id": payment.id, "transaction_id": tx.id, "gateway_ref": gateway_ref}
        else:
            self.payment_repo.update_payment_status(payment.id, "fallido")
            return {"ok": False, "payment_id": payment.id, "transaction_id": tx.id, "gateway_ref": gateway_ref}

    def create_checkout_session(self, user, reservation_id: int) -> Dict:
        """Crea un Checkout Session en Stripe y devuelve la URL para redirigir al usuario.

        Crea primero un registro de pago en la base de datos con estado 'pendiente'.
        """
        reserva = self.reservation_repo.find_by_id(reservation_id)
        if not reserva:
            raise ValueError("Reserva no encontrada.")
        if reserva.user_id != user.id:
            raise ValueError("No tienes permiso para pagar esta reserva.")
        if reserva.estado != "pendiente":
            raise ValueError("Solo se puede pagar una reserva en estado 'pendiente'.")

        cancha = self.court_repo.find_by_id(reserva.cancha_id)
        if not cancha:
            raise ValueError("Cancha no encontrada.")
        dur_horas = (reserva.fecha_fin - reserva.fecha_inicio).total_seconds() / 3600
        amount = Decimal(cancha.precio_hora) * Decimal(dur_horas)

        # Configurar Stripe
        stripe_api_key = os.environ.get("STRIPE_API_KEY")
        if not stripe_api_key:
            raise RuntimeError("Stripe no configurado. Configure STRIPE_API_KEY en .env")
        # pequeño chequeo de formato para evitar pasar claves incorrectas
        if not (stripe_api_key.startswith("sk_") or stripe_api_key.startswith("rk_")):
            raise RuntimeError("Clave de Stripe inválida (formato incorrecto)")
        stripe.api_key = stripe_api_key

        # Use Stripe placeholder to receive the session id in the success redirect
        success_url = f"http://localhost:{self.settings.server_port}/pagos/checkout/success?session_id={'{CHECKOUT_SESSION_ID}'}"
        cancel_url = f"http://localhost:{self.settings.server_port}/dashboard/usuario?msg=Pago%20Cancelado"

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"Reserva {reservation_id} - Cancha {cancha.nombre}"},
                        "unit_amount": int(amount * 100),
                    },
                    "quantity": 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                # Do NOT create a DB payment here to avoid storing 'pendiente' when user cancels.
                metadata={"reservation_id": str(reservation_id), "user_id": str(user.id)},
            )
        except Exception:
            # En caso de error con Stripe, no creamos pagos locales aquí
            raise

        return {"url": session.url, "id": session.id}

    def finalize_checkout_session(self, session_id: str) -> dict:
        """Confirma una sesión de Checkout recuperando la sesión desde Stripe y actualizando BD.

        Esto es un fallback cuando el webhook no llega; también permite confirmar inmediatamente
        tras la redirección de éxito.
        """
        stripe_api_key = os.environ.get("STRIPE_API_KEY")
        if not stripe_api_key:
            raise RuntimeError("Stripe no configurado. Configure STRIPE_API_KEY en .env")
        stripe.api_key = stripe_api_key

        # Recuperar la sesión (expandimos payment_intent si es posible)
        session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
        metadata = session.get("metadata", {}) or {}
        payment_id = int(metadata.get("payment_id")) if metadata.get("payment_id") else None
        reservation_id = int(metadata.get("reservation_id")) if metadata.get("reservation_id") else None

        # Determinar referencia y estado
        gateway_ref = None
        status = None
        pi = session.get("payment_intent")
        if pi:
            if isinstance(pi, dict):
                gateway_ref = pi.get("id")
                status = pi.get("status")
            else:
                pi_obj = stripe.PaymentIntent.retrieve(pi)
                gateway_ref = pi_obj.get("id")
                status = pi_obj.get("status")
        else:
            gateway_ref = session.get("id")
            status = session.get("payment_status")

        success = (status == "succeeded") or (session.get("payment_status") == "paid")

        # If a payment record was not created earlier, create it now based on the session and metadata.
        if not payment_id:
            # Recompute amount from reservation to store accurate value
            reserva = self.reservation_repo.find_by_id(reservation_id) if reservation_id else None
            if not reserva:
                # nothing to do
                return {"ok": False, "handled": False}
            cancha = self.court_repo.find_by_id(reserva.cancha_id)
            if not cancha:
                return {"ok": False, "handled": False}
            dur_horas = (reserva.fecha_fin - reserva.fecha_inicio).total_seconds() / 3600
            amount = Decimal(cancha.precio_hora) * Decimal(dur_horas)

            estado = "confirmado" if success else "fallido"
            user_id = int(metadata.get("user_id", 0))
            # Asignar payment_method_id para pagos con tarjeta
            method_obj = self.method_repo.find_by_name('card')
            payment_method_id = method_obj['id'] if method_obj else None
            payment = Payment(user_id=user_id, reservation_id=reservation_id, amount=float(amount), currency="USD", estado=estado, payment_method_id=payment_method_id)
            payment = self.payment_repo.create_payment(payment)
            payment_id = payment.id

            tx_status = "success" if success else "failed"
            tx = Transaction(payment_id=payment_id, gateway_ref=str(gateway_ref), status=tx_status, details={"stripe_session": session})
            self.payment_repo.create_transaction(tx)

            if success:
                if reservation_id:
                    self.reservation_repo.update_status(reservation_id, "pagada")
                return {"ok": True, "handled": True}
            else:
                return {"ok": False, "handled": True}

        # If payment_id existed, handle as before
        existing = self.payment_repo.get_by_id(payment_id)
        if existing and existing.get("estado") == "confirmado":
            return {"ok": True, "handled": False, "already_confirmed": True}

        tx_status = "success" if success else "failed"
        tx = Transaction(payment_id=payment_id, gateway_ref=str(gateway_ref), status=tx_status, details={"stripe_session": session})
        self.payment_repo.create_transaction(tx)
        if success:
            self.payment_repo.update_payment_status(payment_id, "confirmado")
            if reservation_id:
                self.reservation_repo.update_status(reservation_id, "pagada")
            return {"ok": True, "handled": True}
        else:
            self.payment_repo.update_payment_status(payment_id, "fallido")
            return {"ok": False, "handled": True}

    def handle_stripe_event(self, payload: bytes, sig_header: str) -> Dict:
        """Procesa un webhook de Stripe (verifica firma y actualiza payment/transaction).

        Devuelve un dict con resultado.
        """
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET no configurada en .env")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except Exception as e:
            raise

        # Manejar evento de checkout.session.completed
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            metadata = session.get("metadata", {})
            payment_id = int(metadata.get("payment_id")) if metadata.get("payment_id") else None
            reservation_id = int(metadata.get("reservation_id")) if metadata.get("reservation_id") else None

            # Obtener referencia de pago (payment_intent)
            gateway_ref = session.get("payment_intent") or session.get("id")

            # Crear transacción y actualizar estados. Si no existe payment_id, crear pago ahora.
            if not payment_id:
                # Recompute amount from reservation
                reserva = self.reservation_repo.find_by_id(reservation_id) if reservation_id else None
                if reserva:
                    cancha = self.court_repo.find_by_id(reserva.cancha_id)
                    if cancha:
                        dur_horas = (reserva.fecha_fin - reserva.fecha_inicio).total_seconds() / 3600
                        amount = Decimal(cancha.precio_hora) * Decimal(dur_horas)
                        # find card method id
                        method_obj = self.method_repo.find_by_name('card')
                        payment_method_id = method_obj['id'] if method_obj else None
                        payment = Payment(user_id=int(metadata.get("user_id", reserva.user_id)), reservation_id=reservation_id, amount=float(amount), currency="USD", estado="confirmado", payment_method_id=payment_method_id)
                        payment = self.payment_repo.create_payment(payment)
                        payment_id = payment.id

            if payment_id:
                tx = Transaction(payment_id=payment_id, gateway_ref=str(gateway_ref), status="success", details={"stripe_session": session})
                self.payment_repo.create_transaction(tx)
                self.payment_repo.update_payment_status(payment_id, "confirmado")
                if reservation_id:
                    self.reservation_repo.update_status(reservation_id, "pagada")

            return {"ok": True, "handled": True}

        return {"ok": True, "handled": False}
