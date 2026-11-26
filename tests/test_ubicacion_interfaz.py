import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from ubicacion import normalizar, enlace_mapa
from ubicacion_interfaz import CapturaUbicacion


class CapturaTests(unittest.TestCase):
    def dialogo(self, texto, original=None):
        captura = CapturaUbicacion.__new__(CapturaUbicacion)
        original = original or normalizar()
        captura._ubicacion_original = original
        captura._enlace_original = enlace_mapa(original) if original['Latitude'] is not None else ''
        captura._pendiente = False
        captura._aceptar = Mock()
        captura.master = SimpleNamespace(winfo_exists=lambda: True, destroy=Mock(), after=Mock())
        captura.ventanas = SimpleNamespace(
            obtener_input_componente=lambda _: texto,
            componentes_forma={n: Mock() for n in ('btn_aceptar', 'btn_mapa')},
            bloquear_componente=Mock(), desbloquear_componente=Mock(), mostrar_mensaje=Mock())
        return captura

    def procesar(self, captura):
        # Ejecutar trabajo y sondeo de manera determinista sin abrir una ventana.
        with patch('ubicacion_interfaz.threading.Thread') as hilo:
            hilo.side_effect = lambda target, daemon: SimpleNamespace(start=target)
            captura._guardar()
        if captura.master.after.called:
            captura.master.after.call_args.args[1]()

    def test_aceptar_analiza_y_guarda_solo_datos_internos(self):
        captura = self.dialogo('https://maps.google.com/?q=19,-90')
        self.procesar(captura)
        captura._aceptar.assert_called_once_with(normalizar(19, -90))
        captura.master.destroy.assert_called_once()

    def test_enlace_invalido_no_modifica_ubicacion(self):
        captura = self.dialogo('texto inválido', normalizar(19, -90))
        self.procesar(captura)
        captura._aceptar.assert_not_called()
        captura.master.destroy.assert_not_called()
        captura.ventanas.mostrar_mensaje.assert_called_once()

    def test_vacio_elimina_la_ubicacion_al_aceptar(self):
        captura = self.dialogo('', normalizar(19, -90, 5))
        self.procesar(captura)
        captura._aceptar.assert_called_once_with(normalizar())
        captura.master.destroy.assert_called_once()
        captura.master.after.assert_not_called()

    def test_borrar_enlace_actualiza_null_y_registra_eliminacion(self):
        from formulario_cliente_modelo import FormularioClienteModelo
        anterior = normalizar(19, -90, 5)
        detalle = {'AddressDetailID': 7, **anterior}
        modelo = FormularioClienteModelo.__new__(FormularioClienteModelo)
        modelo.cliente = SimpleNamespace(addresses_details=[detalle], business_entity_id=10)
        modelo.user_name = 'Usuario de prueba'
        modelo._ubicaciones_originales = {7: dict(anterior)}
        modelo.base_de_datos = SimpleNamespace(command=Mock())
        captura = self.dialogo('   ', anterior)
        captura._aceptar = detalle.update
        self.procesar(captura)
        modelo.validar_guardado_ubicaciones()
        modelo.guardar_ubicaciones()
        sql, parametros = modelo.base_de_datos.command.call_args.args
        self.assertEqual(parametros[:3], (None, None, None))
        self.assertEqual(parametros[3:5], (7, 10))
        self.assertEqual(parametros[5], 'ELIMINACIÓN DE UBICACIÓN DE DIRECCIÓN')
        self.assertIn('Latitude=19.0000000', parametros[6])
        self.assertIn('AccuracyMeters=5.00', parametros[6])
        self.assertIn('Latitude=(vacío)', parametros[7])
        self.assertEqual(parametros[-2:], (46, 7))
        self.assertIn('UPDATE D SET Latitude = ?, Longitude = ?, AccuracyMeters = ?', sql)
        self.assertIn('EXEC dbo.InsertarBitacoraCambiosClientes', sql)
        self.assertEqual(modelo.obtener_ubicacion(7), normalizar())
        modelo.guardar_ubicaciones()
        modelo.base_de_datos.command.assert_called_once()

    def test_vacio_sin_ubicacion_previa_se_acepta(self):
        captura = self.dialogo('')
        self.procesar(captura)
        captura._aceptar.assert_called_once_with(normalizar())
        captura.master.destroy.assert_called_once()

    def test_aceptar_sin_cambio_conserva_precision_interna(self):
        original = normalizar(19, -90, 5)
        captura = self.dialogo(enlace_mapa(original), original)
        self.procesar(captura)
        captura._aceptar.assert_called_once_with(original)

    def test_ver_maps_usa_texto_actual_sin_aceptar(self):
        enlace = 'https://maps.app.goo.gl/nuevo'
        captura = self.dialogo(enlace, normalizar(19, -90))
        with patch('ubicacion_interfaz.webbrowser.open') as abrir:
            captura._ver_mapa()
            abrir.assert_called_once_with(enlace)
        captura._aceptar.assert_not_called()

    def test_cancelar_durante_resolucion_no_aplica_resultado(self):
        captura = self.dialogo('https://maps.google.com/?q=19,-90')
        captura.master.winfo_exists = lambda: False
        self.procesar(captura)
        captura._aceptar.assert_not_called()

if __name__ == '__main__':
    unittest.main()
