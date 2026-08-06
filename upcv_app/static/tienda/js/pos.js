document.addEventListener('DOMContentLoaded', () => {
  const app = document.getElementById('posApp');
  if (!app) return;
  const state = { carrito: [], productos: [], cliente: null, categoria: '', marca: '', ultimaVentaUrl: '' };
  const $ = (id) => document.getElementById(id);
  const money = (value) => `Q${Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  function obtenerCSRFToken() {
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (input) return input.value;
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
  }
  const csrf = obtenerCSRFToken;
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
    const pagado = Math.max(0, Number($('monto_recibido').value || 0));
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
    $('btnGuardarCotizacion').disabled = state.carrito.length === 0;
  }

  function renderCarrito() {
    if (!state.carrito.length) {
      $('carritoItems').innerHTML = '<div class="pos-empty-cart">No hay productos agregados</div>';
      calcularTotales();
      return;
    }
    $('carritoItems').innerHTML = state.carrito.map(item => `
      <div class="pos-cart-item">
        <div>
          <div class="pos-cart-item-name">${item.nombre}</div>
          <div class="pos-cart-item-meta">${item.codigo || ''} · ${money(item.precio)} · Stock ${item.stock}</div>
          <div class="pos-qty-controls">
            <button type="button" class="pos-qty-btn" data-action="menos" data-id="${item.id}">-</button>
            <input class="pos-qty-input" data-action="cantidad" data-id="${item.id}" type="number" min="1" max="${item.stock}" value="${item.cantidad}">
            <button type="button" class="pos-qty-btn" data-action="mas" data-id="${item.id}">+</button>
            <button type="button" class="pos-remove-btn" data-action="quitar" data-id="${item.id}">×</button>
          </div>
        </div>
        <div class="pos-cart-item-total">${money(item.precio * item.cantidad)}</div>
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

  function renderClientes(clientes) {
    const contenedor = $('clientesResultados');
    contenedor.replaceChildren();
    if (!clientes.length) {
      contenedor.innerHTML = '<div class="text-muted p-2">No se encontraron clientes.</div>';
      return;
    }
    clientes.forEach(cliente => {
      const boton = document.createElement('button');
      boton.type = 'button';
      boton.className = 'list-group-item list-group-item-action';
      boton.dataset.cliente = JSON.stringify(cliente);
      const nombre = document.createElement('span');
      nombre.textContent = cliente.nombre;
      const detalle = document.createElement('small');
      detalle.className = 'd-block';
      detalle.textContent = `${cliente.telefono || 'Sin teléfono'}${cliente.nit ? ` · NIT ${cliente.nit}` : ''}`;
      boton.append(nombre, detalle);
      contenedor.appendChild(boton);
    });
  }

  async function buscarClientes(query = $('buscarCliente').value) {
    try {
      const url = `${window.POS_URLS.buscarClientes}?q=${encodeURIComponent(query || '')}`;
      const response = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' } });
      const text = await response.text();
      let data;
      try { data = JSON.parse(text); } catch (error) {
        console.error('Respuesta no JSON al buscar clientes:', text);
        throw new Error('El servidor no devolvió JSON al buscar clientes. Verifique la sesión y la URL en Network.');
      }
      if (!response.ok || !data.ok) throw new Error(data.mensaje || 'No se pudieron cargar los clientes.');
      renderClientes(data.clientes || []);
    } catch (error) {
      mostrarAlerta(error.message || 'No se pudieron cargar los clientes.');
    }
  }

  async function crearCliente() {
    const payload = { nombre: $('cliente_nombre')?.value.trim() || '', telefono: $('cliente_telefono')?.value.trim() || '', nit: $('cliente_nit')?.value.trim() || '', dpi: $('cliente_dpi')?.value.trim() || '', email: $('cliente_email')?.value.trim() || '', direccion: $('cliente_direccion')?.value.trim() || '' };
    if (!payload.nombre) return mostrarAlerta('Ingrese el nombre del cliente.');
    mostrarLoading(true);
    try {
      const response = await fetch(window.POS_URLS.crearCliente, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': obtenerCSRFToken(), 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' }, body: JSON.stringify(payload) });
      const text = await response.text();
      let data;
      try { data = JSON.parse(text); } catch (error) {
        console.error('Respuesta no JSON al crear cliente:', text);
        throw new Error('El servidor no devolvió JSON al crear cliente. Verifique CSRF, sesión y URL en Network.');
      }
      if (!response.ok || !data.ok) throw new Error(data.mensaje || 'No se pudo crear el cliente.');
      seleccionarCliente(data.cliente);
      bootstrap.Modal.getOrCreateInstance(document.getElementById('modalCliente')).hide();
      mostrarAlerta(data.mensaje || 'Cliente creado y seleccionado correctamente.', 'success');
      await buscarClientes('');
    } catch (error) {
      mostrarAlerta(error.message || 'No se pudo crear el cliente.');
    } finally {
      mostrarLoading(false);
    }
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
    $('monto_recibido').value = total.toFixed(2);
    guardarVentaPOS('completo');
  }

  function registrarPagoParcial() {
    guardarVentaPOS('parcial');
  }

  function registrarPagoCredito() {
    if (!state.carrito.length) {
      mostrarAlerta('No hay productos en la venta actual.');
      return;
    }
    const montoInput = $('monto_recibido');
    if (montoInput) montoInput.value = '0.00';
    guardarVentaPOS('credito');
  }

  async function guardarVentaPOS(tipoPago = 'credito') {
    let monto = Number($('monto_recibido')?.value || 0);
    if (!state.carrito.length) return mostrarAlerta('No hay productos en la venta actual.');
    const t = totales();
    if (tipoPago === 'completo') monto = t.total;
    if (tipoPago === 'credito') monto = 0;
    if (tipoPago === 'parcial' && monto <= 0) return mostrarAlerta('Ingrese un monto válido para pago parcial.');
    if (tipoPago === 'parcial' && monto >= t.total) return mostrarAlerta('Para pagar el total use el botón de pago completo.');
    if (tipoPago === 'completo' && t.total <= 0) return mostrarAlerta('No se pudo determinar el total de la venta');
    if (!['credito', 'completo', 'parcial'].includes(tipoPago)) return mostrarAlerta('Tipo de pago no válido.');
    if (monto < 0) return mostrarAlerta('No se permiten pagos negativos.');
    if (monto > t.total) return mostrarAlerta('El monto no puede ser mayor al saldo pendiente');
    const payload = { cliente_id: state.cliente?.id || null, items: state.carrito.map(i => ({ producto_id: i.id, cantidad: i.cantidad })), descuento_tipo: $('descuentoTipo').value, descuento_valor: $('descuentoValor').value || '0', impuesto_porcentaje: $('impuestoPorcentaje').value || '0', envio: $('envioValor').value || '0', pago: { tipo: tipoPago, monto: monto.toFixed(2), metodo_pago: tipoPago === 'credito' ? '' : $('metodo_pago')?.value || '', referencia: tipoPago === 'credito' ? '' : $('referencia_pago')?.value || '', observaciones: tipoPago === 'credito' ? 'Venta registrada al crédito' : $('observaciones_pago')?.value || '' } };
    mostrarLoading(true);
    try {
      const res = await fetch(window.POS_URLS.crearVenta, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' }, body: JSON.stringify(payload) });
      const responseText = await res.text();
      let data;
      try {
        data = JSON.parse(responseText);
      } catch (error) {
        console.error('Respuesta no JSON del servidor:', responseText);
        throw new Error('El servidor no devolvió JSON válido. Revisa consola, CSRF, URL o error 500.');
      }
      if (!res.ok || !data.ok) throw new Error(data.mensaje || 'No se pudo guardar la venta.');
      state.ultimaVentaUrl = data.comprobante_url;
      $('btnComprobante').href = data.comprobante_url;
      $('btnComprobante').classList.remove('disabled', 'd-none');
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

  async function guardarComoCotizacion() {
    if (!state.carrito.length) return mostrarAlerta('No hay productos para cotizar.');
    const payload = {
      cliente_id: state.cliente?.id || null,
      items: state.carrito.map(i => ({ producto_id: i.id, cantidad: i.cantidad })),
      descuento_tipo: $('descuentoTipo').value,
      descuento_valor: $('descuentoValor').value || '0',
      impuesto_porcentaje: $('impuestoPorcentaje').value || '0',
      envio: $('envioValor').value || '0',
      observaciones: $('observaciones_pago')?.value || ''
    };
    mostrarLoading(true);
    try {
      const res = await fetch(window.POS_URLS.crearCotizacion, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' }, body: JSON.stringify(payload) });
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch (error) { console.error('Respuesta no JSON:', text); throw new Error('El servidor no devolvió JSON válido.'); }
      if (!res.ok || !data.ok) throw new Error(data.mensaje || 'No se pudo guardar la cotización.');
      mostrarAlerta(data.mensaje || 'Cotización guardada correctamente.', 'success');
      if (data.imprimir_url) window.open(data.imprimir_url, '_blank');
      limpiarCarrito(false);
    } catch (error) {
      mostrarAlerta(error.message || 'No se pudo guardar la cotización.');
    } finally {
      mostrarLoading(false);
    }
  }


  function mostrarLoading(show) {
    $('posLoading').classList.toggle('show', show);
  }

  function limpiarFormularioPago() {
    $('monto_recibido').value = 0;
    $('referencia_pago').value = '';
    $('observaciones_pago').value = '';
  }

  function limpiarCarrito(confirmar = true) {
    if (confirmar && state.carrito.length && !confirm('¿Desea reiniciar la venta actual?')) return;
    state.carrito = [];
    $('monto_recibido').value = 0;
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
  ['descuentoValor', 'descuentoTipo', 'impuestoPorcentaje', 'envioValor', 'monto_recibido'].forEach(id => $(id).addEventListener('input', calcularTotales));
  $('posSearch').addEventListener('input', () => { clearTimeout(window.posSearchTimer); window.posSearchTimer = setTimeout(cargarProductos, 250); });
  $('posSearch').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); buscarOAgregarProducto(); } });
  $('buscarCliente').addEventListener('input', buscarClientes);
  $('btnGuardarCliente').addEventListener('click', crearCliente);
  $('btnReiniciar').addEventListener('click', () => limpiarCarrito(true));
  $('btnNuevaVenta').addEventListener('click', () => limpiarCarrito(true));
  $('btnMantener').addEventListener('click', () => mostrarAlerta('Venta mantenida en pantalla. Use Venta al crédito para registrarla sin pago inicial.', 'info'));
  $('btnPendiente').addEventListener('click', registrarPagoCredito);
  $('btnGuardarCotizacion').addEventListener('click', guardarComoCotizacion);
  $('btnPagar').addEventListener('click', abrirModalPago);
  $('btnTopPagar').addEventListener('click', abrirModalPago);
  $('btnPagoCompleto').addEventListener('click', registrarPagoCompleto);
  $('btnPagoParcial').addEventListener('click', registrarPagoParcial);
  const btnPagoCredito = $('btnPagoCredito');
  if (btnPagoCredito) {
    btnPagoCredito.addEventListener('click', registrarPagoCredito);
  } else {
    console.warn('No se encontró el botón btnPagoCredito');
  }
  $('btnFullscreen').addEventListener('click', () => document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen());
  document.addEventListener('keydown', e => { if (e.key === 'F2') { e.preventDefault(); $('posSearch').focus(); } if (e.key === 'F4') { e.preventDefault(); $('btnPagar').click(); } if (e.key === 'F8') { e.preventDefault(); limpiarCarrito(true); } });

  cargarProductos();
  buscarClientes();
  calcularTotales();
  window.abrirModalPago = abrirModalPago;
  window.registrarPagoCompleto = registrarPagoCompleto;
  window.registrarPagoParcial = registrarPagoParcial;
  window.registrarPagoCredito = registrarPagoCredito;
  window.guardarVentaPOS = guardarVentaPOS;
  window.guardarComoCotizacion = guardarComoCotizacion;
});
