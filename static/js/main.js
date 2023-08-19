(function () {
let productos = [];

fetch("/api/productos")
.then(response => response.json())
.then(data => {
  console.log("Datos recibidos:", data);

  const productosConInfoCategoria = data.filter(producto => producto.categoria);
  if (productosConInfoCategoria.length !== data.length) {
    console.error("Error: No todos los productos tienen una categoría válida.", data);
  } else {
    productos = productosConInfoCategoria;
    cargarProductos(productos);
  }
})
.catch(error => {
  console.error("Error obteniendo productos:", error);
});


  // Función para filtrar los productos según la categoría seleccionada
  function filtrarProductosPorCategoria(categoria) {
    if (!categoria) {
      return productos;
    } else {
      const productosFiltrados = productos.filter(producto => producto.categoria === categoria);
      return productosFiltrados;
    }
  }


  const contenedorProductos = document.querySelector("#contenedor-productos");
  const botonesCategorias = document.querySelectorAll(".boton-categoria");
  const tituloPrincipal = document.querySelector("#titulo-principal");
  let botonesAgregar = document.querySelectorAll(".producto-agregar");
  const numerito = document.querySelector("#numerito");


  botonesCategorias.forEach(boton => boton.addEventListener("click", () => {
      aside.classList.remove("aside-visible");
  }))


  function cargarProductos(productosElegidos) {
    contenedorProductos.innerHTML = "";

    productosElegidos.forEach(producto => {
        const div = document.createElement("div");
        div.classList.add("producto");
        div.innerHTML = `
        <img class="producto-imagen" src="${producto.imagen}" alt="${producto.titulo}">
            <div class="producto-detalles">
                <h3 class="producto-titulo">${producto.titulo}</h3>
                <p class="producto-precio">$${producto.precio}</p>
                <button class="producto-agregar" id="${producto.id}">Agregar</button>
            </div>
        `;

        contenedorProductos.append(div);
    });

    actualizarBotonesAgregar();
  }




  botonesCategorias.forEach(boton => {
    boton.addEventListener("click", (e) => {
      botonesCategorias.forEach(boton => boton.classList.remove("active"));
      e.currentTarget.classList.add("active");

      if (e.currentTarget.id !== "todos") {
        const categoriaIdSeleccionada = e.currentTarget.id;
        const nombreCategoriaSeleccionada = e.currentTarget.innerText;
        tituloPrincipal.innerText = nombreCategoriaSeleccionada ? nombreCategoriaSeleccionada : "Todos los productos";
        const productosBoton = filtrarProductosPorCategoria(categoriaIdSeleccionada);
        cargarProductos(productosBoton);
      } else {
        tituloPrincipal.innerText = "Todos los productos";
        cargarProductos(productos);
      }
    });
  });


  function actualizarBotonesAgregar() {
      botonesAgregar = document.querySelectorAll(".producto-agregar");

      botonesAgregar.forEach(boton => {
          boton.addEventListener("click", agregarAlCarrito);
      });
  }

  let productosEnCarrito;

  let productosEnCarritoLS = localStorage.getItem("productos-en-carrito");

  if (productosEnCarritoLS) {
      productosEnCarrito = JSON.parse(productosEnCarritoLS);
      actualizarNumerito();
  } else {
      productosEnCarrito = [];
  }

  function agregarAlCarrito(e) {
    Toastify({
      text: "Producto agregado",
      duration: 3000,
      close: true,
      gravity: "top",
      position: "right",
      stopOnFocus: true,
      style: {
          background: "linear-gradient(to right, #4b33a8, #785ce9)",
          borderRadius: "2rem",
          textTransform: "uppercase",
          fontSize: ".75rem"
      },
      offset: {
          x: '1.5rem',
          y: '1.5rem'
      },
      onClick: function () { }
  }).showToast();

    const idBoton = e.currentTarget.id;
    const productoAgregado = productos.find(producto => producto.id === parseInt(idBoton));

    if (productosEnCarrito.some(producto => producto.id === productoAgregado.id)) {
        const index = productosEnCarrito.findIndex(producto => producto.id === productoAgregado.id);
        productosEnCarrito[index].cantidad++;
    } else {
        productoAgregado.cantidad = 1;
        productosEnCarrito.push(productoAgregado);
    }

    actualizarNumerito();

    localStorage.setItem("productos-en-carrito", JSON.stringify(productosEnCarrito));
}

function actualizarNumerito() {
    let nuevoNumerito = productosEnCarrito.reduce((acc, producto) => acc + producto.cantidad, 0);
    numerito.innerText = nuevoNumerito;
}
})();