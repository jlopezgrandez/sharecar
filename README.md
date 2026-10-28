# ShareCar - Aplicación de Coche Compartido para Empresas y Colectivos

Aplicación web desarrollada con **Python y Django** para gestionar y optimizar el uso compartido del coche para acudir al trabajo.

---

## Características Principales

1. **Gestión de Usuarios y Vehículos**:
   - Registro de usuarios, coches asociados y capacidad útil de plazas (incluido conductor y plazas de pasajeros).
   - Posibilidad de marcar vehículos temporalmente "no disponibles" (taller, revisión) sin alterar el registro.
2. **Control Semanal de Disponibilidad (Check-in Pre-planificación)**:
   - Los usuarios indican de lunes a viernes si viajan o no, y si pueden conducir.
   - Registro de motivos de ausencia (teletrabajo, vacaciones, médico, etc.).
3. **Motor de Optimización Matemática y Equidad**:
   - **Minimización de vehículos (*Bin Packing*)**: Calcula la menor cantidad de coches necesarios según las personas que asisten cada día (por ejemplo, para 9 personas prefiere dos coches de 5 plazas antes que tres de 4 plazas).
   - **Reparto equitativo**: Lleva un registro del ratio histórico de días conducidos vs días viajados para priorizar a los conductores que "deben" viajes al colectivo.
   - **Rotación semanal**: Penaliza que una misma persona conduzca varios días en la misma semana si hay otros candidatos disponibles.
4. **Visualización Web Responsive**:
   - Cuadrante semanal intuitivo (compatible con móvil y escritorio) con los coches asignados y pasajeros de cada vehículo.
5. **Listo para Despliegue Gratuito en Render**:
   - Configurado con WhiteNoise, Gunicorn, `render.yaml` y soporte dual para SQLite (local) y PostgreSQL (producción).

---

## Puesta en Marcha Local

### 1. Requisitos
* Python 3.10 o superior instalado.

### 2. Instalación del entorno virtual
```bash
# Crear entorno virtual
python -m venv venv

# Activar en Windows PowerShell:
.\venv\Scripts\Activate.ps1
# (o en Git Bash / Linux: source venv/bin/activate)

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Migraciones y Base de Datos
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Cargar datos de prueba y superusuario
Hemos creado un comando que crea automáticamente el superusuario administrador (`admin / admin123`), 9 usuarios con distintos coches y plazas, sus disponibilidades y el primer plan optimizado:
```bash
python manage.py crear_datos_prueba
```

### 5. Iniciar el servidor de desarrollo
```bash
python manage.py runserver
```
Abre tu navegador en `http://127.0.0.1:8000/`.

---

## Cuentas de Acceso de Prueba

| Usuario | Contraseña | Rol / Coche |
| :--- | :--- | :--- |
| **admin** | `admin123` | Administrador total (acceso a `/admin/`) |
| **carlos** | `demo1234` | Conductor (Peugeot 308 - 5 plazas) |
| **ana** | `demo1234` | Conductora (Toyota Corolla - 5 plazas) |
| **david** | `demo1234` | Conductor (Seat Ibiza - 4 plazas) |
| **lucia** | `demo1234` | Pasajera sin coche |

---

## Despliegue Gratuito en Render

1. Sube este proyecto a tu repositorio de **GitHub**.
2. Entra en [Render.com](https://render.com) y crea una cuenta gratuita.
3. En el panel de Render, pulsa **New +** > **Blueprint** (o **Web Service**):
   * Si eliges **Blueprint**, Render detectará automáticamente el archivo `render.yaml` incluido en el repositorio.
   * Si creas un **Web Service manual**:
     * **Build Command**: `./build.sh`
     * **Start Command**: `gunicorn sharecar_project.wsgi:application`
     * Añade las variables de entorno indicadas en `.env.example`.
4. Para la base de datos PostgreSQL gratuita y persistente, puedes crear una en [Neon.tech](https://neon.tech) y pegar la cadena de conexión en la variable `DATABASE_URL` de Render.
