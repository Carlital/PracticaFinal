-- Schema for sports center reservation auth module
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    nombre_rol VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol_id INTEGER NOT NULL REFERENCES roles(id),
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_rol ON users (rol_id);

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions (token);

-- Módulo de Reservas
CREATE TABLE IF NOT EXISTS canchas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    deporte VARCHAR(50) NOT NULL, -- futbol, tenis, basquet
    precio_hora DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS reservas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    cancha_id INTEGER NOT NULL REFERENCES canchas(id),
    fecha_inicio TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    fecha_fin TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'confirmada', -- pendiente, confirmada, cancelada
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reservas_cancha_fecha ON reservas (cancha_id, fecha_inicio);
CREATE INDEX IF NOT EXISTS idx_reservas_user ON reservas (user_id);

-- Seed roles
INSERT INTO roles (nombre_rol)
VALUES ('admin'), ('usuario')
ON CONFLICT (nombre_rol) DO NOTHING;

-- Seed canchas (Datos de prueba iniciales)
INSERT INTO canchas (nombre, deporte, precio_hora)
VALUES 
    ('Cancha Sintética 1', 'futbol', 25.00),
    ('Cancha Tenis A', 'tenis', 15.00),
    ('Coliseo Principal', 'basquet', 20.00)
ON CONFLICT (nombre) DO NOTHING;

-- Módulo de Pagos
CREATE TABLE IF NOT EXISTS payment_methods (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    tipo VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    reservation_id INTEGER NOT NULL REFERENCES reservas(id) ON DELETE CASCADE,
    amount NUMERIC(10,2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    payment_method_id INTEGER NOT NULL REFERENCES payment_methods(id) ON DELETE CASCADE,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente', -- pendiente, confirmado, fallido
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    payment_id INTEGER NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    gateway_ref VARCHAR(255),
    status VARCHAR(20) NOT NULL, -- success, failed
    details JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_user ON payments (user_id);
CREATE INDEX IF NOT EXISTS idx_payments_reservation ON payments (reservation_id);
CREATE INDEX IF NOT EXISTS idx_transactions_payment ON transactions (payment_id);

-- Métodos de pago
INSERT INTO payment_methods (nombre, tipo)
VALUES ('Tarjeta', 'card'), ('Efectivo', 'cash')
ON CONFLICT (nombre) DO NOTHING;

-- Módulo de Notificaciones
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL, -- welcome, reservation_confirmation, payment_confirmation, cancellation
    asunto VARCHAR(255) NOT NULL,
    contenido TEXT NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente', -- pendiente, enviado, fallido
    sent_at TIMESTAMP WITHOUT TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_estado ON notifications (estado);
CREATE INDEX IF NOT EXISTS idx_notifications_tipo ON notifications (tipo);

