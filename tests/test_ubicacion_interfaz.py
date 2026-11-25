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

    def test_vacio_no_borra_la_ubicacion(self):
        captura = self.dialogo('', normalizar(19, -90))
        self.procesar(captura)
        captura._aceptar.assert_not_called()
        captura.master.after.assert_not_called()

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
