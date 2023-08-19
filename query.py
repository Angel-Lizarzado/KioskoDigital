import sqlite3

db_conn = {
    'dbname': 'kioskodigital.db',  # Nombre de la base de datos SQLite3
}

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

# Consulta para actualizar el nombre de la categoría de "Café" a "Cafe"
update_query = "UPDATE categorias SET nombre = ? WHERE nombre = ?;"
execute_query(update_query, ("Café", "Cafe"))
