document.addEventListener('DOMContentLoaded', () => {
  const app = document.getElementById('posApp');
  if (!app) return;
  const state = { carrito: [], productos: [], cliente: null, categoria: '', marca: '', ultimaVentaUrl: '' };
  const $ = (id) => document.getElementById(id);
  const money = (value) => `Q${Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
  const alertBox = $('posAlert');

  function mostrarAlerta(msg, tipo = 'warning') {
    alertBox.innerHTML = `<div class="alert alert-${tipo} shadow">${msg}</div>`;
    setTimeout(() => { alertBox.innerHTML = ''; }, 3200);
  }

  function totales() {
    const subtotal = state.carrito.reduce((acc, item) => acc + item.precio * item.cantidad, 0);
    const cantidad = state.carrito.reduce((acc, item) => acc + item.cantidad, 0);
    const descuentoValor = Math.max(0, Number($('descuentoValor').value || 0));
    const descuentoTipo = $('descuentoTipo').value;
    let descuento = descuentoTipo === 'porcentaje' ? subtotal * descuentoValor / 100 : descuentoValor;
    descuento = Math.min(descuento, subtotal);
    const impuestoPorcentaje = Math.max(0, Number($('impuestoPorcentaje').value || 0));
    const envio = Math.max(0, Number($('envioValor').value || 0));
    const impuesto = (subtotal - descuento) * impuestoPorcentaje / 100;
    const total = subtotal - descuento + impuesto + envio;
    const pagado = Math.max(0, Number($('montoRecibido').value || 0));
    return { subtotal, cantidad, descuento, impuesto, envio, total, pagado, saldo: Math.max(total - pagado, 0) };
  }

  function calcularTotales() {
    const t = totales();
    $('cantidadTotal').textContent = t.cantidad;
    $('subtotalVenta').textContent = money(t.subtotal);
    $('descuentoTotal').textContent = money(t.descuento);
    $('impuestoTotal').textContent = money(t.impuesto);
    $('envioTotal').textContent = money(t.envio);
    $('totalVenta').textContent = money(t.total);
    $('modalTotal').textContent = money(t.total);
    $('modalPagado').textContent = money(0);
    $('modalSaldo').textContent = money(t.total);
    $('pagadoTotal').textContent = money(t.pagado);
    $('saldoTotal').textContent = money(t.saldo);
    $('btnPagar').disabled = state.carrito.length === 0;
    $('btnTopPagar').disabled = state.carrito.length === 0;
    $('btnPendiente').disabled = state.carrito.length === 0;
  }

  function renderCarrito() {
    if (!state.carrito.length) {
      $('carritoItems').innerHTML = '<div class="pos-empty">No hay productos agregados</div>';
      calcularTotales();
      return;
    }
    $('carritoItems').innerHTML = state.carrito.map(item => `
      <div class="pos-cart-line">
        <div><strong>${item.nombre}</strong><br><small>${item.codigo} · ${money(item.precio)} · Stock ${item.stock}</small><br><strong>${money(item.precio * item.cantidad)}</strong></div>
        <div class="pos-qty"><button class="btn btn-sm btn-light" data-action="menos" data-id="${item.id}">-</button><input class="form-control form-control-sm" data-action="cantidad" data-id="${item.id}" type="number" min="1" max="${item.stock}" value="${item.cantidad}"><button class="btn btn-sm btn-light" data-action="mas" data-id="${item.id}">+</button></div>
        <button class="btn btn-sm btn-outline-danger" data-action="quitar" data-id="${item.id}">×</button>
      </div>`).join('');
    calcularTotales();
  }

  function agregarProducto(producto) {
    const existente = state.carrito.find(item => item.id === producto.id);
    if (existente) {
      if (existente.cantidad + 1 > producto.stock) return mostrarAlerta(`Stock insuficiente. Disponible: ${producto.stock} unidades.`);
      existente.cantidad += 1;
    } else {
      if (producto.stock <= 0) return mostrarAlerta('Producto sin stock');
      state.carrito.push({ id: producto.id, nombre: producto.nombre, codigo: producto.codigo, precio: Number(producto.precio), stock: producto.stock, cantidad: 1 });
    }
    renderCarrito();
    $('posSearch').focus();
  }

  async function cargarProductos() {
    const params = new URLSearchParams({ q: $('posSearch').value.trim(), categoria: state.categoria, marca: state.marca });
    const res = await fetch(`${app.dataset.productosUrl}?${params}`);
    const data = await res.json();
    state.productos = data.productos;
    $('productosGrid').innerHTML = data.productos.map(p => `<article class="pos-product-card ${p.stock <= 0 ? 'disabled' : ''}" data-id="${p.id}"><span class="pos-price-badge">${p.precio_formateado}</span><span class="pos-stock-badge" id="stock-${p.id}">${p.stock} pzs</span><div class="pos-product-image">${p.imagen ? `<img src="${p.imagen}" alt="${p.nombre}">` : '<span class="pos-placeholder">▧</span>'}</div><div class="pos-product-name">${p.nombre}</div><div class="pos-product-code">${p.codigo}</div></article>`).join('') || '<div class="text-muted p-3">No se encontraron productos.</div>';
  }

  async function buscarOAgregarProducto() {
    await cargarProductos();
    const q = $('posSearch').value.trim().toLowerCase();
    const exactos = state.productos.filter(p => p.codigo.toLowerCase() === q || p.nombre.toLowerCase() === q);
    if (exactos.length === 1) agregarProducto(exactos[0]);
    else if (!state.productos.length) mostrarAlerta('No encontramos productos con esa búsqueda.');
  }

  function seleccionarCliente(cliente) {
    state.cliente = cliente;
    $('clienteActualNombre').textContent = cliente ? cliente.nombre : 'Cliente mostrador';
    $('clienteActualDetalle').textContent = cliente ? `${cliente.telefono || 'Sin teléfono'} ${cliente.nit ? '· NIT ' + cliente.nit : ''}` : 'Walk-in customer';
  }

  async function buscarClientes() {
    const res = await fetch(`${app.dataset.clientesUrl}?q=${encodeURIComponent($('buscarCliente').value)}`);
    const data = await res.json();
    $('clientesResultados').innerHTML = data.clientes.map(c => `<button type="button" class="list-group-item list-group-item-action" data-cliente='${JSON.stringify(c)}'>${c.nombre}<br><small>${c.telefono || ''} ${c.nit || ''}</small></button>`).join('');
  }

  async function crearCliente() {
    const payload = { nombre: $('clienteNombre').value, telefono: $('clienteTelefono').value, nit: $('clienteNit').value, email: $('clienteEmail').value, direccion: $('clienteDireccion').value };
    const res = await fetch(app.dataset.crearClienteUrl, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body: JSON.stringify(payload) });
    const data = await res.json();
    if (!data.ok) return mostrarAlerta(data.mensaje || 'No se pudo crear el cliente.');
    seleccionarCliente(data.cliente);
    bootstrap.Modal.getOrCreateInstance(document.getElementById('modalCliente')).hide();
    mostrarAlerta('Cliente creado y seleccionado.', 'success');
  }

  function abrirModalPago() {
    if (!state.carrito.length) {
      mostrarAlerta('No hay productos en la venta actual');
      return;
    }
    actualizarResumenPago();
    bootstrap.Modal.getOrCreateInstance(document.getElementById('modalPago')).show();
  }

  function actualizarResumenPago() {
    calcularTotales();
    const t = totales();
    $('modalTotal').textContent = money(t.total);
    $('modalPagado').textContent = money(0);
    $('modalSaldo').textContent = money(t.total);
  }

  function registrarPagoCompleto() {
    const total = totales().total;
    $('montoRecibido').value = total.toFixed(2);
    guardarVentaPOS('completo');
  }

  function registrarPagoParcial() {
    guardarVentaPOS('parcial');
  }

  async function guardarVentaPOS(tipoPago = 'pendiente') {
    const monto = tipoPago === 'completo' ? totales().total : Number($('montoRecibido').value || 0);
    if (!state.carrito.length) return mostrarAlerta('La venta no debe guardarse si el carrito está vacío.');
    const t = totales();
    if (tipoPago === 'parcial' && monto <= 0) return mostrarAlerta('Ingrese un monto válido para pago parcial');
    if (tipoPago === 'completo' && t.total <= 0) return mostrarAlerta('No se pudo determinar el total de la venta');
    if (monto < 0) return mostrarAlerta('No se permiten pagos negativos.');
    if (monto > t.total) return mostrarAlerta('El monto no puede ser mayor al saldo pendiente');
    const payload = { cliente_id: state.cliente?.id || null, items: state.carrito.map(i => ({ producto_id: i.id, cantidad: i.cantidad })), descuento_tipo: $('descuentoTipo').value, descuento_valor: $('descuentoValor').value || '0', impuesto_porcentaje: $('impuestoPorcentaje').value || '0', envio: $('envioValor').value || '0', pago: { tipo: tipoPago, monto, metodo_pago: $('metodoPago').value, referencia: $('referenciaPago').value, observaciones: $('observacionesPago').value } };
    mostrarLoading(true);
    try {
      const res = await fetch(app.dataset.crearVentaUrl, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body: JSON.stringify(payload) });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.mensaje || 'No se pudo guardar la venta.');
      state.ultimaVentaUrl = data.comprobante_url;
      $('btnComprobante').href = data.comprobante_url;
      $('btnComprobante').classList.remove('disabled');
      mostrarAlerta(data.mensaje, 'success');
      if (data.comprobante_url) window.open(data.comprobante_url, '_blank');
      if (tipoPago === 'parcial' && Number(data.saldo || 0) > 0) mostrarAlerta(`Pago parcial registrado. Saldo pendiente: ${money(data.saldo)}`, 'info');
      limpiarCarrito(false);
      limpiarFormularioPago();
      bootstrap.Modal.getOrCreateInstance(document.getElementById('modalPago')).hide();
      await cargarProductos();
    } catch (error) {
      mostrarAlerta(error.message || 'Ocurrió un error al procesar el pago');
    } finally {
      mostrarLoading(false);
    }
  }

  function mostrarLoading(show) {
    $('posLoading').classList.toggle('show', show);
  }

  function limpiarFormularioPago() {
    $('montoRecibido').value = 0;
    $('referenciaPago').value = '';
    $('observacionesPago').value = '';
  }

  function limpiarCarrito(confirmar = true) {
    if (confirmar && state.carrito.length && !confirm('¿Desea reiniciar la venta actual?')) return;
    state.carrito = [];
    $('montoRecibido').value = 0;
    renderCarrito();
    $('posSearch').focus();
  }

  document.addEventListener('click', (e) => {
    const card = e.target.closest('.pos-product-card');
    if (card) agregarProducto(state.productos.find(p => p.id === Number(card.dataset.id)));
    const chip = e.target.closest('.pos-filter-chip');
    if (chip) { document.querySelectorAll(`[data-filter="${chip.dataset.filter}"]`).forEach(c => c.classList.remove('active')); chip.classList.add('active'); state[chip.dataset.filter] = chip.dataset.id; cargarProductos(); }
    const cartAction = e.target.dataset.action;
    if (cartAction) { const item = state.carrito.find(i => i.id === Number(e.target.dataset.id)); if (!item) return; if (cartAction === 'mas') agregarProducto(item); if (cartAction === 'menos') item.cantidad = Math.max(1, item.cantidad - 1); if (cartAction === 'quitar') state.carrito = state.carrito.filter(i => i.id !== item.id); renderCarrito(); }
    const clienteBtn = e.target.closest('[data-cliente]');
    if (clienteBtn) { seleccionarCliente(JSON.parse(clienteBtn.dataset.cliente)); bootstrap.Modal.getOrCreateInstance(document.getElementById('modalCliente')).hide(); }
  });

  $('carritoItems').addEventListener('input', (e) => { if (e.target.dataset.action === 'cantidad') { const item = state.carrito.find(i => i.id === Number(e.target.dataset.id)); item.cantidad = Math.min(item.stock, Math.max(1, Number(e.target.value || 1))); renderCarrito(); } });
  ['descuentoValor', 'descuentoTipo', 'impuestoPorcentaje', 'envioValor', 'montoRecibido'].forEach(id => $(id).addEventListener('input', calcularTotales));
  $('posSearch').addEventListener('input', () => { clearTimeout(window.posSearchTimer); window.posSearchTimer = setTimeout(cargarProductos, 250); });
  $('posSearch').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); buscarOAgregarProducto(); } });
  $('buscarCliente').addEventListener('input', buscarClientes);
  $('btnGuardarCliente').addEventListener('click', crearCliente);
  $('btnReiniciar').addEventListener('click', () => limpiarCarrito(true));
  $('btnNuevaVenta').addEventListener('click', () => limpiarCarrito(true));
  $('btnMantener').addEventListener('click', () => mostrarAlerta('Venta mantenida en pantalla. Use guardar pendiente para conservarla en el sistema.', 'info'));
  $('btnPendiente').addEventListener('click', () => guardarVentaPOS('pendiente'));
  $('btnPagar').addEventListener('click', abrirModalPago);
  $('btnTopPagar').addEventListener('click', abrirModalPago);
  $('btnPagoCompleto').addEventListener('click', registrarPagoCompleto);
  $('btnPagoParcial').addEventListener('click', registrarPagoParcial);
  $('btnFullscreen').addEventListener('click', () => document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen());
  document.addEventListener('keydown', e => { if (e.key === 'F2') { e.preventDefault(); $('posSearch').focus(); } if (e.key === 'F4') { e.preventDefault(); $('btnPagar').click(); } if (e.key === 'F8') { e.preventDefault(); limpiarCarrito(true); } });

  cargarProductos();
  buscarClientes();
  calcularTotales();
  window.abrirModalPago = abrirModalPago;
  window.registrarPagoCompleto = registrarPagoCompleto;
  window.registrarPagoParcial = registrarPagoParcial;
  window.guardarVentaPOS = guardarVentaPOS;
});
