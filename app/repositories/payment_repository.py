from typing import Optional, List
from app.core.config import Settings
from app.core.db import get_connection
from app.models.payment import Payment, Transaction
import psycopg2.extras


class PaymentRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create_payment(self, payment: Payment) -> Payment:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO payments (user_id, reservation_id, amount, currency, estado, created_at, payment_method_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payment.user_id,
                    payment.reservation_id,
                    payment.amount,
                    payment.currency,
                    payment.estado,
                    payment.created_at,
                    payment.payment_method_id,
                ),
            )
            payment.id = cur.fetchone()["id"]
        conn.close()
        return payment

    def update_payment_status(self, payment_id: int, new_status: str):
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute("UPDATE payments SET estado = %s WHERE id = %s", (new_status, payment_id))
        conn.close()

    def get_by_id(self, payment_id: int) -> Optional[dict]:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM payments WHERE id = %s", (payment_id,))
            row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def find_by_user(self, user_id: int) -> List[dict]:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute(
                """
                                SELECT p.*, pm.nombre as metodo_nombre,
                                    (
                                        SELECT t.gateway_ref FROM transactions t WHERE t.payment_id = p.id ORDER BY t.created_at DESC LIMIT 1
                                    ) as gateway_ref
                                FROM payments p
                                LEFT JOIN payment_methods pm ON p.payment_method_id = pm.id
                                WHERE p.user_id = %s AND p.estado IN ('confirmado','fallido')
                                ORDER BY p.created_at DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def find_all_detailed(self) -> List[dict]:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute(
                """
                                SELECT p.*, u.nombre as usuario_nombre, pm.nombre as metodo_nombre,
                                    (
                                        SELECT t.gateway_ref FROM transactions t WHERE t.payment_id = p.id ORDER BY t.created_at DESC LIMIT 1
                                    ) as gateway_ref
                                FROM payments p
                                JOIN users u ON p.user_id = u.id
                                LEFT JOIN payment_methods pm ON p.payment_method_id = pm.id
                                WHERE p.estado IN ('confirmado','fallido')
                                ORDER BY p.created_at DESC
                """
            )
            rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def create_transaction(self, tx: Transaction) -> Transaction:
        conn = get_connection(self.settings)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (payment_id, gateway_ref, status, details, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (tx.payment_id, tx.gateway_ref, tx.status, psycopg2.extras.Json(tx.details), tx.created_at),
            )
            tx.id = cur.fetchone()["id"]
        conn.close()
        return tx
