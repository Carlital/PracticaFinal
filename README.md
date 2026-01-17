# Sistema de Gestión de Reservas - Módulo Auth (Python + PostgreSQL)

Módulo inicial de autenticación y roles para un centro deportivo usando Python estándar + `psycopg2` y un servidor HTTP sencillo.

## Requisitos previos
- Python 3.11+ instalado y agregado al PATH.
- PostgreSQL 13+ en local y usuario con permisos para crear base de datos/tablas.
- Visual Studio Code con la extensión de Python.

## Pasos en VS Code (Windows)
1. **Crear carpeta del proyecto**  
   ```
   mkdir centro_deportivo_reservas
   cd centro_deportivo_reservas
   ```
2. **Clonar/copiar el contenido** en esta carpeta (ya presente si lees este archivo).
3. **Crear y activar entorno virtual**  
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
4. **Instalar dependencias**  
   ```
   pip install -r requirements.txt
   ```
5. **Configurar variables de entorno**  
   Copia `.env.example` a `.env` y ajusta valores:
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=centro_deportivo
   DB_USER=centro_user
   DB_PASSWORD=tu_password
   SECRET_KEY=una_clave_secreta
   SERVER_PORT=8000
   ```
6. **Crear BD y usuario en PostgreSQL** (desde `psql`):
   ```sql
   CREATE DATABASE centro_deportivo;
   CREATE USER centro_user WITH ENCRYPTED PASSWORD 'tu_password';
   GRANT ALL PRIVILEGES ON DATABASE centro_deportivo TO centro_user;
   ```
7. **Ejecutar migración inicial**  
   ```
   python scripts/init_db.py
   ```
8. **Levantar servidor local**  
   ```
   python -m app.server
   ```
   Abrir navegador en `http://localhost:8000`.
9. **Probar endpoints**  
   - `GET /register` -> formulario de registro  
   - `POST /register` -> crea usuario (elige rol usuario/admin)  
   - `GET /login` -> formulario de login  
   - `POST /login` -> autenticación, setea cookie de sesión  
   - `GET /dashboard` -> dashboard según rol  
   - `GET /logout` -> cierre de sesión
10. **Ejecutar pruebas unitarias**  
    ```
    python -m unittest tests.test_auth
    ```

## Estructura del proyecto
```
app/
  core/ (configuración, seguridad, conexión DB)
  models/ (clases User, Role, Session)
  repositories/ (UserRepository, SessionRepository)
  services/ (AuthService)
  web/
    templates/ (HTML)
    static/ (CSS)
  server.py (servidor HTTP)
scripts/
  schema.sql
  init_db.py
tests/
  test_auth.py
requirements.txt
.env.example
README.md
```

## Notas de seguridad y validaciones
- Contraseñas se almacenan con PBKDF2 (`hashlib.pbkdf2_hmac`) con salt aleatorio e iteraciones altas.
- Sesiones se guardan en tabla `sessions` con token seguro y expiración (60 min por defecto).
- Validaciones: email con formato, contraseña mínima 8 caracteres con letras y números, campos obligatorios, unicidad de email en DB.

## Convenciones
- Estilo OO con separación de capas (modelos, repositorios, servicios, servidor).
- Manejo de errores mediante `ValueError` con mensajes claros para UI.
- Agregar nuevas rutas siguiendo el patrón en `app/server.py`.
- Notificaciones se envían de forma asíncrona y no bloquean la operación principal.

##  Módulo de Notificaciones 📧

### Configuración SMTP

El sistema soporta notificaciones por email usando SMTP:

**Outlook/Hotmail (Recomendado):**
```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=tu_email@outlook.com
SMTP_PASSWORD=tu_contraseña
SMTP_FROM_EMAIL=tu_email@outlook.com
SMTP_FROM_NAME=Centro Deportivo
NOTIFICATION_MODE=smtp
```

**Modo Simulado (Testing):**
```env
NOTIFICATION_MODE=simulated
```

### Tipos de Notificaciones
1. **Bienvenida**: Al registrar nuevo usuario
2. **Confirmación de Reserva**: Al crear una reserva
3. **Confirmación de Pago**: Al procesar un pago exitoso
4. **Cancelación**: Al cancelar una reserva

## Pruebas 🧪

### Ejecutar Pruebas
```bash
# Todas las pruebas
python -m pytest tests/ -v

# Pruebas de integración
python -m pytest tests/test_integration.py -v

# Pruebas de aceptación (UAT)
python -m pytest tests/test_acceptance.py -v

# Pruebas de rendimiento (genera reporte JSON)
python -m pytest tests/test_performance.py -v
```

### Cobertura de Pruebas
- **Integración**: Flujo completo registro → reserva → pago → notificación
- **Aceptación**: 7 criterios UAT desde perspectiva de usuario
- **Rendimiento**: Tiempos de respuesta y capacidad concurrente

## Próximos pasos sugeridos
- Añadir flujo de renovación de sesión y CSRF tokens.
- Implementar retry logic para notificaciones fallidas.
- Extender con más tipos de notificaciones (recordatorios, promociones).
