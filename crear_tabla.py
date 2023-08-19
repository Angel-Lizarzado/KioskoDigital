import os
import sqlite3
import hashlib
from datetime import datetime

# Directorio donde se almacenarán las imágenes de los productos
UPLOAD_FOLDER = 'static/uploads'
# Ruta completa al archivo de base de datos SQLite
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kioskodigital.db')

# Función para generar hash MD5 de contraseñas
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

# Conexión a la base de datos SQLite
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

# Crear tabla 'usuarios'
cur.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        rol TEXT NOT NULL,
        code TEXT NOT NULL
    )
''')

# Crear tabla 'productos'
cur.execute('''
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        categoria TEXT NOT NULL,
        stock INTEGER NOT NULL,
        precio REAL NOT NULL,
        disponibilidad TEXT NOT NULL,
        imagen TEXT NOT NULL
    )
''')

# Crear tabla 'pedidos'
cur.execute('''
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT NOT NULL,
        productos TEXT NOT NULL,
        precio REAL NOT NULL,
        estado TEXT NOT NULL,
        responsable TEXT
    )
''')

# Crear tabla 'codes'
cur.execute('''
    CREATE TABLE IF NOT EXISTS codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL,
        create_by TEXT NOT NULL,
        fecha TEXT NOT NULL,
        disponibilidad TEXT NOT NULL
    )
''')

# Insertar el primer usuario
# Asegúrate de que la contraseña sea el hash MD5 de la contraseña real
hashed_password = hash_password("TryHard1998")
cur.execute('''
    INSERT INTO usuarios (username, email, password, rol, code)
    VALUES (?, ?, ?, ?, ?)
''', ('Angel', 'angel.lizarzado98@gmail.com', hashed_password, 'administrador', 'admin'))

# Insertar el código para el primer usuario
current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
cur.execute('''
    INSERT INTO codes (codigo, create_by, fecha, disponibilidad)
    VALUES (?, ?, ?, ?)
''', ('Angel', 'Angel', current_datetime, '1'))

# Importante: Asegúrate de que esta parte esté en el mismo lugar donde creaste las tablas anteriores

# Crear tabla 'categorias'
cur.execute('''
    CREATE TABLE IF NOT EXISTS categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        habilitada INTEGER NOT NULL
    )
''')

# Insertar algunas categorías de ejemplo (puedes agregar más según tus necesidades)
cur.executemany('''
    INSERT INTO categorias (nombre, habilitada)
    VALUES (?, ?)
''', [
    ('Café', 1),  # 1 significa habilitada
    ('Té', 1),
    ('Complementos', 1),
    # Agrega más categorías aquí si es necesario
])
#confirmar los cambios en la base de datos

conn.commit()

# Cerrar la conexión a la base de datos
conn.close()

# Configuración del directorio de subidas de imágenes
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

print("Tablas creadas y primer usuario registrado.")
