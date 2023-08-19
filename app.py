import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from email.message import EmailMessage
from datetime import datetime
import smtplib
import ssl
import json
import hashlib
import random
import string

import os

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
app = Flask(__name__)

app.secret_key = os.urandom(24)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuración de la base de datos PostgreSQL
db_conn = {
    'dbname': 'kioskodigital.db',  # Nombre de la base de datos SQLite3
}

# Crear la base de datos SQLite3 y las tablas necesarias al inicio
conn = sqlite3.connect(db_conn['dbname'])
cur = conn.cursor()

# Función para ejecutar consultas en la base de datos SQLite3
def execute_query(query, args=None):
    conn = sqlite3.connect(db_conn['dbname'])
    cur = conn.cursor()
    try:
        if args:
            cur.execute(query, args)
        else:
            cur.execute(query)
        if query.lower().startswith("select"):
            result = cur.fetchall()
            return result
        else:
            conn.commit()
    except sqlite3.Error as e:
        # Manejar errores de la base de datos
        print("Error en la consulta:", e)
        raise  # Re-lanza la excepción para que sea manejada por el código que llama a esta función
    finally:
        conn.close()



def registrar_usuario(username, email, password):
    query = "INSERT INTO usuarios (username, email, password) VALUES (?, ?, ?);"
    args = (username, email, password)
    try:
        execute_query(query, args)
        conn.commit()
    except sqlite3.Error as e:
        # Manejar el error y realizar un rollback si es necesario
        conn.rollback()
        print("Error al registrar usuario:", str(e))




    


@app.route('/')
def index():
    # Verifica si el usuario está logueado y tiene el rol de administrador en la sesión
    if 'username' in session and session.get('rol') == 'administrador':
        mostrar_opcion_admin = True
    else:
        mostrar_opcion_admin = False
    
    # Conexión a la base de datos SQLite (creada dentro de la función)
    db_conn = {
        'dbname': 'kioskodigital.db',  # Nombre de la base de datos SQLite3
    }

    # Obtener categorías habilitadas
    conn = sqlite3.connect(db_conn['dbname'])
    cur = conn.cursor()
    cur.execute("SELECT * FROM categorias WHERE habilitada = 1")
    categorias_habilitadas = cur.fetchall()
    print(categorias_habilitadas)

    # Cerrar la conexión a la base de datos
    conn.close()

    return render_template('index.html', mostrar_opcion_admin=mostrar_opcion_admin, categorias_habilitadas=categorias_habilitadas)


@app.route('/carrito')
def mostrar_carrito():  
    return render_template('carrito.html')


@app.route('/api/productos', methods=['GET'])
def obtener_productos():
    try:
        # Consulta SQL para obtener los productos con disponibilidad igual a 1 (True en SQLite3)
        query = "SELECT * FROM productos WHERE disponibilidad = 1 AND categoria IN (SELECT nombre FROM categorias WHERE habilitada = 1);"
        productos = execute_query(query)
        
        # Crear una lista de diccionarios con los datos de los productos
        productos_json = []

        for row in productos:
            producto = {
                'id': row[0],
                'categoria': row[2],
                'titulo': row[1],
                'stock': row[3],
                'precio': row[4],
                'disponibilidad': row[5],
                'imagen': f"/static/uploads/{row[6]}",  # Agregar la ruta de la imagen
            }
            productos_json.append(producto)
        
        # Devolver la respuesta JSON con los datos de los productos
        return jsonify(productos_json)
    except sqlite3.Error as e:
        # En caso de error en la consulta, devolver una respuesta JSON con el mensaje de error de SQLite3
        return jsonify({'error': str(e)})
    except Exception as e:
        # Capturar cualquier otro tipo de excepción y devolver una respuesta JSON con el mensaje de error genérico
        return jsonify({'error': "Error inesperado: " + str(e)})





 

@app.route('/admin')
def admin_login():
    # Renderiza la plantilla para el inicio de sesión del administrador
    return render_template('admin/login.html')

@app.route('/login', methods=['POST'])
def login_view():
    # Obtén el nombre de usuario y la contraseña desde el formulario
    username = request.form['username']
    password = request.form['password']

    # Verificar las credenciales en la base de datos
    conn = sqlite3.connect(db_conn['dbname'])
    cur = conn.cursor()
    query = "SELECT * FROM usuarios WHERE username = ?;"
    cur.execute(query, (username,))
    user = cur.fetchone()
    conn.close()

    # Verificar las credenciales del usuario
    if user and user[3] == hashlib.md5(password.encode()).hexdigest():
        # Si las credenciales son válidas, iniciar sesión y redirigir al panel de administración
        session['username'] = username
        session['rol'] = user[4]  # Suponiendo que el rol es el quinto campo en la tabla usuarios
        return redirect('/admin/dashboard')
    else:
        # Si las credenciales son inválidas, mostrar un mensaje
        flash('Credenciales invalidas', 'danger')
        return redirect('/admin')


@app.route('/registrar', methods=['POST'])
def registrar():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    code = request.form['code']
    rol = 'administrador'  # Cambia esto según tu diseño de roles

    try:
        # Verificar si el usuario ya existe en la base de datos
        query = "SELECT * FROM usuarios WHERE username = ?;"
        existing_user = execute_query(query, (username,))
        if existing_user:
            # Si el usuario ya existe, mostrar un mensaje de error
            flash("Usuario ya registrado", "danger")
            return render_template("admin/login.html")

        # Verificar si el código existe y está disponible en la base de datos
        query = "SELECT * FROM codes WHERE codigo = ? AND disponibilidad = 'disponible';"
        code_info = execute_query(query, (code,))

        if not code_info:
            # Si el código no es válido o no está disponible, mostrar un mensaje de error
            flash("Código inválido o no disponible", "danger")
            return render_template("admin/login.html")

        # Obtener el valor de 'create_by' del código usado en el registro
        create_by_query = "SELECT create_by FROM codes WHERE codigo = ? AND disponibilidad = 'disponible';"
        create_by_result = execute_query(create_by_query, (code,))

        if create_by_result and create_by_result[0]:
            create_by = create_by_result[0][0]  # Obtenemos el primer resultado
        else:
            create_by = ''  # Si no se encuentra, ponemos un valor por defecto

        # Insertar el nuevo usuario en la base de datos
        query = "INSERT INTO usuarios (username, email, password, rol, code) VALUES (?, ?, ?, ?, ?);"
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        execute_query(query, (username, email, hashed_password, rol, create_by))

        # Actualizar la disponibilidad del código a 'no disponible'
        update_query = "UPDATE codes SET disponibilidad = 'no disponible' WHERE codigo = ?;"
        execute_query(update_query, (code,))  # Usamos el valor del código aquí

        flash("Registrado exitosamente, puedes loguear", "success")
        return render_template("admin/login.html")
    except Exception as e:
        # Manejar cualquier error en la consulta o proceso
        flash("Error en el registro", "danger")
        return render_template("admin/login.html")








@app.route('/admin/dashboard')
def admin_dashboard():
    # Verificar si el usuario está logueado como administrador
    if 'username' in session and session['rol'] == 'administrador':
        try:
            # Obtener el conteo de productos, usuarios, pedidos y pedidos confirmados
            conteo_productos = execute_query("SELECT COUNT(*) FROM productos;")[0][0]
            conteo_usuarios = execute_query("SELECT COUNT(*) FROM usuarios;")[0][0]
            conteo_pedidos = execute_query("SELECT COUNT(*) FROM pedidos WHERE estado NOT LIKE ?;", ('%confirmado%',))[0][0]
            conteo_confirmados = execute_query("SELECT COUNT(*) FROM pedidos WHERE estado LIKE ?;", ('%confirmado%',))[0][0]

            # Pasar el conteo de productos, usuarios, pedidos y pedidos confirmados como contexto a la plantilla
            return render_template('admin/dashboard.html', username=session['username'], conteo_productos=conteo_productos, conteo_usuarios=conteo_usuarios, conteo_pedidos=conteo_pedidos, conteo_confirmados=conteo_confirmados)
        except Exception as e:
            # Manejar cualquier error en la consulta o proceso
            flash("Error al cargar el dashboard: " + str(e), "danger")
            return render_template("admin/login.html")
    else:
        # Si el usuario no está logueado como administrador, redirigir al formulario de login de administrador
        flash("Acceso no autorizado", "danger")
        return render_template("admin/login.html")


@app.route('/admin/pedidos')
def pedidos():
    # Verificar si el usuario está logueado como administrador
    if 'username' in session and session['rol'] == 'administrador':
        try:
            # Obtener el nombre de usuario de la sesión
            session_username = session['username']
            
            # Conectar a la base de datos SQLite3
            conn = sqlite3.connect(db_conn['dbname'])
            cur = conn.cursor()
            
            # Obtener los pedidos pendientes (no confirmados) de la base de datos
            query = "SELECT * FROM pedidos WHERE estado NOT LIKE '%confirmado%';"
            cur.execute(query)
            pedidos = cur.fetchall()
            
            # Cerrar la conexión a la base de datos
            conn.close()
            
            # Pasar la lista de pedidos pendientes como contexto a la plantilla
            return render_template('admin/pedidos.html', username=session_username, pedidos=pedidos)
        except Exception as e:
            # Manejar cualquier error en la consulta o proceso
            flash("Error al cargar los pedidos: " + str(e), "danger")
            return render_template("admin/login.html")
    else:
        # Si el usuario no está logueado como administrador, redirigir al formulario de login de administrador
        flash("Acceso no autorizado", "danger")
        return render_template("admin/login.html")

@app.route('/admin/confirmados')
def pedidos_completados():
    # Verificar si el usuario está logueado como administrador
    if 'username' in session and session['rol'] == 'administrador':
        try:
            # Obtener el nombre de usuario de la sesión
            session_username = session['username']
            
            # Conectar a la base de datos SQLite3
            conn = sqlite3.connect(db_conn['dbname'])
            cur = conn.cursor()
            
            # Obtener los pedidos completados de la base de datos
            query = "SELECT * FROM pedidos WHERE estado LIKE '%confirmado%';"
            cur.execute(query)
            pedidos = cur.fetchall()
            
            # Cerrar la conexión a la base de datos
            conn.close()
            
            # Pasar la lista de pedidos completados como contexto a la plantilla
            return render_template('admin/pedidosCompletados.html', username=session_username, pedidos=pedidos)
        except Exception as e:
            # Manejar cualquier error en la consulta o proceso
            flash("Error al cargar los pedidos completados: " + str(e), "danger")
            return render_template("admin/login.html")
    else:
        # Si el usuario no está logueado como administrador, redirigir al formulario de login de administrador
        flash("Acceso no autorizado", "danger")
        return render_template("admin/login.html")


@app.route('/admin/tomar_pedido/<int:pedido_id>', methods=['POST'])
def tomar_pedido(pedido_id):
    # Verificar si el usuario está logueado como administrador
    if 'username' in session and session['rol'] == 'administrador':
        try:
            # Obtener el nombre de usuario del que está tomando el pedido
            usuario_tomador = session['username']
            
            # Definir el nuevo estado del pedido con el nombre del tomador
            nuevo_estado = f'Tomado por {usuario_tomador}'
            
            # Actualizar el estado y responsable del pedido en la base de datos SQLite3
            conn = sqlite3.connect(db_conn['dbname'])
            cur = conn.cursor()
            query = "UPDATE pedidos SET estado = ?, responsable = ? WHERE id = ?;"
            cur.execute(query, (nuevo_estado, usuario_tomador, pedido_id))
            conn.commit()
            conn.close()
            
            # Mostrar un mensaje de éxito y redirigir a la lista de pedidos pendientes
            flash(f'Pedido tomado exitosamente por {usuario_tomador}', "success")
            return redirect(url_for('pedidos'))
        except Exception as e:
            # Manejar cualquier error en la consulta o proceso
            flash("Error al tomar el pedido: " + str(e), "danger")
            return redirect(url_for('pedidos'))
    else:
        # Si el usuario no está logueado como administrador, devolver un mensaje de error en formato JSON
        flash('Acceso no autorizado', "danger")
        return render_template('admin/login.html')
    
@app.route('/admin/confirmar_pedido/<int:pedido_id>', methods=['POST'])
def confirmar_pedido(pedido_id):
    # Verificar si el usuario está logueado como administrador
    if 'username' in session and session['rol'] == 'administrador':
        try:
            # Obtener el nombre de usuario del confirmador
            usuario_confirmador = session['username']
            nuevo_estado = f'Confirmado por {usuario_confirmador}'
            
            # Actualizar el estado del pedido en la base de datos SQLite3
            conn = sqlite3.connect(db_conn['dbname'])
            cur = conn.cursor()
            query = "UPDATE pedidos SET estado = ? WHERE id = ? AND responsable = ?;"
            cur.execute(query, (nuevo_estado, pedido_id, usuario_confirmador))
            conn.commit()
            conn.close()
            
            # Mostrar un mensaje de éxito y redirigir a la lista de pedidos
            flash('Pedido confirmado exitosamente', "success")
            return redirect(url_for('pedidos'))
        except Exception as e:
            # Manejar cualquier error en la consulta o proceso
            flash("Error al confirmar el pedido: " + str(e), "danger")
            return redirect(url_for('pedidos'))
    else:
        # Si el usuario no está logueado como administrador, mostrar un mensaje de error y redirigir al login del administrador
        flash('Acceso no autorizado', "danger")
        return render_template('admin/login.html')


@app.route('/procesar_compra', methods=['POST'])
def procesar_compra():
    try:
        # Obtener los datos del formulario
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        productos_json = request.form.get('productos')
        productos = json.loads(productos_json) if productos_json else []

        # Extraer los nombres de los productos con sus cantidades
        nombres_cantidades_formateados = [f"{producto['titulo']} x{producto['cantidad']}" for producto in productos]
        # Concatenar los nombres de los productos en una cadena
        nombres_productos_text = ', '.join(nombres_cantidades_formateados)

        # Calcular el precio total sumando los subtotales de cada producto
        precio_total = calcular_precio_total(productos)

        # Insertar el pedido en la base de datos
        insertar_pedido(nombre, telefono, nombres_productos_text, precio_total)

        # Enviar correos electrónicos a los usuarios notificando del nuevo pedido
        enviar_correos_pedidos()

        # Mostrar un mensaje de éxito y redirigir a donde sea necesario
        flash("El pedido ha sido procesado, se te contactará en breve", "success")  
        return redirect(url_for('mostrar_carrito'))  # Cambia 'mostrar_carrito' por la ruta adecuada
    except Exception as e:
        # Mostrar un mensaje de error en caso de excepción
        print("Error:", str(e))
        return f"Error al procesar el pedido: {str(e)}"




        return redirect(url_for('mostrar_carrito'))
    except Exception as e:
        # Mostrar un mensaje de error en caso de excepción
        print("Error:", str(e))
        return f"Error al procesar la compra: {str(e)}"


# Función para calcular el precio total de los productos
def calcular_precio_total(productos):
    precio_total = 0
    for producto in productos:
        cantidad = producto.get('cantidad', 0)
        precio = float(producto.get('precio', 0))
        subtotal = cantidad * precio
        precio_total += subtotal
    return precio_total

def insertar_pedido(nombre, telefono, nombres_productos_text, precio_total):
    query = '''
        INSERT INTO pedidos (nombre, telefono, productos, precio, estado)
        VALUES (?, ?, ?, ?, ?)
    '''
    # En la siguiente línea, pasamos directamente nombres_productos_text como un valor en la tupla de argumentos
    execute_query(query, (nombre, telefono, nombres_productos_text, precio_total, 'pendiente'))


# Función para enviar correos a los usuarios
def enviar_correos_pedidos():
    try:
        # Obtener la lista de correos de usuarios
        usuarios = execute_query("SELECT email FROM usuarios;")

        # Enviar un correo a cada usuario registrado
        for usuario in usuarios:
            email_destinatario = usuario[0]
            subject = "Nuevo pedido en KioskoLaRedoma Digital"
            message_body = (
                "Hola,\n\nSe ha generado un nuevo pedido en KioskoLaRedoma Digital y está pendiente de ser atendido. "
                "Por favor, revisa el sistema y toma las acciones necesarias.\n\nGracias,\nEquipo de KioskoLaRedoma Digital"
            )
            email_sender = 'kioskolaredomadigital@gmail.com'
            password = 'qvqzxaljjcdhxqmo'
            
            # Crear el mensaje de correo electrónico
            em = EmailMessage()
            em["From"] = email_sender
            em["To"] = usuario[0]
            em["subject"] = subject
            em.set_content(message_body)

            # Enviar el correo utilizando SSL
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
                smtp.login(email_sender, password)
                smtp.sendmail(email_sender, email_destinatario, em.as_string())
        # return redirect(url_for('mostrar_carrito'))
    except Exception as e:
        # Mostrar un mensaje de error en caso de excepción
        print("Error:", str(e))
        return f"Error al enviar los correos de los pedidos: {str(e)}"




@app.route('/borrar_pedido/<int:pedido_id>', methods=['POST'])
def borrar_pedido(pedido_id):
    try:
        # Realizar la lógica para borrar el pedido con el pedido_id proporcionado
        query = "DELETE FROM pedidos WHERE id = ?;"
        execute_query(query, (pedido_id,))

        # Mostrar mensaje de éxito
        flash("Pedido borrado exitosamente", "success")
    except Exception as e:
        # En caso de error, mostrar un mensaje de error
        print("Error:", str(e))
        flash("Error al borrar el pedido", "danger")

    # Redirigir a la página de pedidos (independientemente de éxito o error)
    return redirect(url_for('pedidos'))


@app.route('/admin/usuarios_registrados')
def usuarios_registrados():
    if 'username' in session and session['rol'] == 'administrador':
        try:
            # Obtener el nombre de usuario de la sesión
            session_username = session['username']
            
            # Obtener los usuarios registrados desde la base de datos
            query = "SELECT * FROM usuarios"
            usuarios = execute_query(query)
            
            # Renderizar la plantilla y pasar la lista de usuarios como contexto
            return render_template('admin/usuarios-registrados.html', username=session_username, usuarios=usuarios)
        except Exception as e:
            # En caso de error, mostrar un mensaje de error
            print("Error:", str(e))
            flash("Error al obtener la lista de usuarios", "danger")

        # Redirigir a la página de login en caso de error o falta de autorización
        return render_template("admin/login.html")
    else:
        # Redirigir a la página de login si el usuario no está autorizado
        return render_template("admin/login.html")


@app.route('/admin/registrar_usuarios')
def registrar_usuarios():
    if 'username' in session and session['rol'] == 'administrador':
        try:
            # Obtener el nombre de usuario de la sesión
            session_username = session['username']
            
            # Obtener los códigos de la base de datos
            query = "SELECT * FROM codes"
            codes = execute_query(query)
            
            # Renderizar la plantilla y pasar la lista de códigos como contexto
            return render_template('admin/registrar-usuarios.html', username=session_username, codes=codes)
        except Exception as e:
            # En caso de error, mostrar un mensaje de error
            print("Error:", str(e))
            flash("Error al obtener la lista de códigos", "danger")

        # Redirigir a la página de login en caso de error o falta de autorización
        return render_template("admin/login.html")
    else:
        # Redirigir a la página de login si el usuario no está autorizado
        return render_template("admin/login.html")

@app.route('/borrar_codigo/<int:codigo_id>', methods=['POST'])
def borrar_codigo(codigo_id):
    try:
        # Realizar la lógica para borrar el pedido con el pedido_id proporcionado
        query = "DELETE FROM codes WHERE id = ?;"
        execute_query(query, (codigo_id,))

        # Mostrar mensaje de éxito
        flash("Codigo borrado exitosamente", "success")
    except Exception as e:
        # En caso de error, mostrar un mensaje de error
        print("Error:", str(e))
        flash("Error al borrar codigo", "danger")

    # Redirigir a la página de pedidos (independientemente de éxito o error)
    return redirect(url_for('registrar_usuarios'))

@app.route('/borrar_usuario/<int:usuario_id>', methods=['POST'])
def borrar_usuario(usuario_id):
    try:
        # Realizar la lógica para borrar el pedido con el pedido_id proporcionado
        query = "DELETE FROM usuarios WHERE id = ?;"
        execute_query(query, (usuario_id,))

        # Mostrar mensaje de éxito
        flash("Usuario borrado exitosamente", "success")
    except Exception as e:
        # En caso de error, mostrar un mensaje de error
        print("Error:", str(e))
        flash("Error al borrar usuario", "danger")

    # Redirigir a la página de pedidos (independientemente de éxito o error)
    return redirect(url_for('usuarios_registrados'))


@app.route('/admin/registrar_codigo', methods=['GET', 'POST'])
def registrar_codigo():
    if request.method == 'POST':
        # Generar un código aleatorio de 6 dígitos
        codigo = generate_random_code(6)
        creado_por = session['username']
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Obtener la fecha y hora actual

        try:
            # Insertar el código en la base de datos
            query = "INSERT INTO codes (codigo, create_by, fecha, disponibilidad) VALUES (?, ?, ?, ?);"
            execute_query(query, (codigo, creado_por, fecha_actual, 'disponible'))
            flash("Código registrado exitosamente.", "success")
        except Exception as e:
            # Manejar errores al registrar el código en la base de datos
            print("Error al registrar el código:", str(e))
            flash("No se ha podido generar el código.", "danger")

        # Redirigir a la página de registro de usuarios
        return redirect(url_for('registrar_usuarios'))

# Generar código aleatorio
def generate_random_code(length):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


@app.route('/admin/productos_registrados')
def productos_registrados():
    if 'username' in session and session['rol'] == 'administrador':
        # Obtener el nombre de usuario de la sesión
        session_username = session['username']
        
        # Obtener los productos de la base de datos
        try:
            query = "SELECT * FROM productos"
            productos = execute_query(query)
            
            query_categorias = "SELECT * FROM categorias"
            categorias = execute_query(query_categorias)

            # Renderizar la plantilla con la lista de productos
            return render_template('admin/productos-registrados.html', username=session_username, productos=productos, categorias=categorias)
        except Exception as e:
            # Manejar errores si ocurre un problema al obtener los productos
            print("Error al obtener la lista de productos:", str(e))
            flash("Error al obtener la lista de productos.", "danger")
            return render_template("admin/login.html")
    else:
        # Redirigir a la página de login si el usuario no está autorizado
        return render_template("admin/login.html")


import os

@app.route('/registrar_producto', methods=['POST'])
def registrar_producto():
    try:
        titulo = request.form['titulo']
        categoria = request.form['categoria']
        stock = int(request.form['stock'])
        precio = float(request.form['precio'])
        disponibilidad = 1 if request.form['disponibilidad'] == '1' else 1  # 0 si es verdadero, 1 si es falso

        imagen = request.files['imagen']
        imagen_filename = secure_filename(imagen.filename)
        
        # Verificar si el nombre del archivo ya existe
        while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], imagen_filename)):
            # Si el nombre existe, agregar un número al final antes de la extensión
            nombre_base, extension = os.path.splitext(imagen_filename)
            imagen_filename = f"{nombre_base}_1{extension}"
        
        imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], imagen_filename)
        imagen.save(imagen_path)

        # Insertar el nuevo producto en la base de datos
        query = "INSERT INTO productos (titulo, categoria, stock, precio, disponibilidad, imagen) VALUES (?, ?, ?, ?, ?, ?);"
        execute_query(query, (titulo, categoria, stock, precio, disponibilidad, imagen_filename))

        flash("Producto registrado exitosamente.", "success")
        return redirect(url_for('productos_registrados'))
    except sqlite3.Error as e:
        flash("Error al registrar el producto. Detalles: " + str(e), "danger")
    except Exception as e:
        flash("Error inesperado al registrar el producto. Detalles: " + str(e), "danger")

    return redirect(url_for('productos_registrados'))



@app.route('/editar_producto/<int:producto_id>', methods=['POST'])
def editar_producto(producto_id):
    try:
        nuevo_titulo = request.form['nuevo_titulo']
        nueva_categoria = request.form['nueva_categoria']
        nuevo_stock = int(request.form['nuevo_stock'])
        nuevo_precio = float(request.form['nuevo_precio'])
        nueva_disponibilidad = request.form['nueva_disponibilidad']

        # Actualizar el producto en la base de datos
        query = "UPDATE productos SET titulo = ?, categoria = ?, stock = ?, precio = ?, disponibilidad = ? WHERE id = ?;"
        execute_query(query, (nuevo_titulo, nueva_categoria, nuevo_stock, nuevo_precio, nueva_disponibilidad, producto_id))

        flash("Producto actualizado exitosamente.", "success")
    except sqlite3.Error as e:
        flash("Error al actualizar el producto. Detalles: " + str(e), "danger")
    except Exception as e:
        flash("Error inesperado al actualizar el producto. Detalles: " + str(e), "danger")

    return redirect(url_for('productos_registrados'))


    
@app.route('/borrar_producto/<int:producto_id>', methods=['POST'])
def borrar_producto(producto_id):
    try:
        conn = sqlite3.connect(db_conn['dbname'])
        cur = conn.cursor()
        
        # Obtener el nombre de la imagen antes de eliminar el producto
        cur.execute("SELECT imagen FROM productos WHERE id = ?;", (producto_id,))
        imagen_filename = cur.fetchone()[0]
        # Eliminar el producto
        query = "DELETE FROM productos WHERE id = ?;"
        cur.execute(query, (producto_id,))
        conn.commit()
        conn.close()

        # Borrar la imagen del sistema de archivos
        if imagen_filename:
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], imagen_filename)
            if os.path.exists(imagen_path):
                os.remove(imagen_path)

        flash("Producto borrado exitosamente.", "success")
    except sqlite3.Error as e:
        flash("Error al borrar el producto. Detalles: " + str(e), "danger")
    except Exception as e:
        flash("Error inesperado al borrar el producto. Detalles: " + str(e), "danger")

    return redirect(url_for('productos_registrados'))


@app.route('/admin/categorias_registradas')
def categorias_registradas():
    if 'username' in session and session['rol'] == 'administrador':
        # Obtener el nombre de usuario de la sesión
        session_username = session['username']
        
        # Obtener las categorias de la base de datos
        try:
            query = "SELECT * FROM categorias"
            categorias = execute_query(query)
            # Renderizar la plantilla con la lista de productos
            return render_template('admin/categorias-registradas.html', username=session_username, categorias=categorias)
        except Exception as e:
            # Manejar errores si ocurre un problema al obtener los productos
            print("Error al obtener la lista de categorias:", str(e))
            flash("Error al obtener la lista de categorias.", "danger")
            return render_template("admin/login.html")
    else:
        # Redirigir a la página de login si el usuario no está autorizado
        return render_template("admin/login.html")


@app.route('/editar_categoria/<int:categoria_id>', methods=['POST'])
def editar_categoria(categoria_id):
    try:
        nuevo_titulo = request.form['nuevo_titulo']
        nueva_disponibilidad = request.form['nueva_disponibilidad']

        # Actualizar el producto en la base de datos
        query = "UPDATE categorias SET nombre = ?, habilitada = ? WHERE id = ?;"
        execute_query(query, (nuevo_titulo, nueva_disponibilidad, categoria_id))

        flash("Categoria actualizada exitosamente.", "success")
    except sqlite3.Error as e:
        flash("Error al actualizar la categoria. Detalles: " + str(e), "danger")
    except Exception as e:
        flash("Error inesperado al actualizar la categoria: " + str(e), "danger")

    return redirect(url_for('categorias_registradas'))


@app.route('/borrar_categoria/<int:categoria_id>', methods=['POST'])
def borrar_categoria(categoria_id):
    try:
        # Realizar la lógica para borrar la categoría con el categoria_id proporcionado
        query = "DELETE FROM categorias WHERE id = ?;"
        execute_query(query, (categoria_id,))

        # Mostrar mensaje de éxito
        flash("Categoría borrada exitosamente", "success")
    except Exception as e:
        # En caso de error, mostrar un mensaje de error
        print("Error:", str(e))
        flash("Error al borrar la categoría", "danger")

    # Redirigir a la página de categorías registradas (independientemente de éxito o error)
    return redirect(url_for('categorias_registradas'))


@app.route('/registrar_categoria', methods=['POST'])
def registrar_categoria():
    try:
        titulo = request.form['titulo']
        habilitada = 1 if request.form['disponibilidad'] == '1' else 0  # 1 si es verdadero, 0 si es falso

        # Insertar la nueva categoría en la base de datos
        query = "INSERT INTO categorias (nombre, habilitada) VALUES (?, ?);"
        execute_query(query, (titulo, habilitada))

        flash("Categoría registrada exitosamente.", "success")
        return redirect(url_for('categorias_registradas'))
    except sqlite3.Error as e:
        flash("Error al registrar la categoría. Detalles: " + str(e), "danger")
    except Exception as e:
        flash("Error inesperado al registrar la categoría. Detalles: " + str(e), "danger")

    return redirect(url_for('categorias_registradas'))


@app.route('/logout')
def logout():
    # Borrar la información de la sesión
    session.pop('username', None)
    session.pop('rol', None)
    
    flash('Cierre de sesión exitoso.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()

