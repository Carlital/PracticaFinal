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
