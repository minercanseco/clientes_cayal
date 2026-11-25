import unittest
from decimal import Decimal
from types import SimpleNamespace
from ubicacion import extraer_ubicacion, normalizar, enlace_mapa
from formulario_cliente_modelo import FormularioClienteModelo


class UbicacionTests(unittest.TestCase):
    def test_coordenadas_y_precision_opcional(self):
        self.assertEqual(extraer_ubicacion('19.845, -90.523')['Latitude'], Decimal('19.8450000'))
        self.assertIsNone(extraer_ubicacion('0,0')['AccuracyMeters'])
        self.assertEqual(normalizar('0', '0', '2.345')['AccuracyMeters'], Decimal('2.35'))
        self.assertEqual(normalizar(), dict.fromkeys(('Latitude', 'Longitude', 'AccuracyMeters')))

    def test_enlaces_compartidos(self):
        for enlace in ('https://www.google.com/maps?q=19.8%2C-90.5',
                       'https://maps.google.com/?q=19.8,-90.5',
                       'https://www.google.com/maps/search/?api=1&query=19.8%2C-90.5',
                       'Ubicación: https://www.google.com/maps?q=19.8,-90.5\nWhatsApp'):
            self.assertEqual(extraer_ubicacion(enlace)['Longitude'], Decimal('-90.5000000'))

    def test_marcador_prioritario_sobre_centro(self):
        dato = extraer_ubicacion('https://www.google.com/maps/place/x/@20,-91,14z/data=!3d19.8!4d-90.5')
        self.assertEqual(dato['Latitude'], Decimal('19.8000000'))

    def test_centro_sin_marcador_no_es_ubicacion(self):
        with self.assertRaises(ValueError):
            extraer_ubicacion('https://www.google.com/maps/@20,-91,14z')

    def test_resolver_enlace_corto(self):
        dato = extraer_ubicacion('https://maps.app.goo.gl/abc',
                                resolver=lambda _: 'https://www.google.com/maps?q=19.8,-90.5')
        self.assertEqual(dato['Latitude'], Decimal('19.8000000'))

    def test_rechaza_redireccion_a_otro_dominio(self):
        with self.assertRaises(ValueError):
            extraer_ubicacion('https://maps.app.goo.gl/abc', resolver=lambda _: 'https://example.com/?q=1,2')

    def test_rechaza_ambiguos_y_datos_invalidos(self):
        for texto in ('https://example.com/?q=1,2', 'https://www.google.com.evil.test/?q=1,2',
                      'https://www.google.com/maps?q=1,2&q=3,4',
                      'https://www.google.com/maps?q=1,2 https://www.google.com/maps?q=3,4',
                      '91,0', '0,181', 'https://www.google.com/maps?q=Una+calle'):
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                extraer_ubicacion(texto)
        for valores in (('NaN', '0'), ('Infinity', '0'), ('1', None), (None, None, 5), ('1', '2', '-1')):
            with self.subTest(valores=valores), self.assertRaises(ValueError):
                normalizar(*valores)

    def test_enlace_para_previsualizar(self):
        self.assertIn('query=0.0000000%2C0.0000000', enlace_mapa(normalizar('0', '0')))


class PersistenciaTests(unittest.TestCase):
    def modelo(self, direcciones, originales=None, instalado=True):
        modelo = FormularioClienteModelo.__new__(FormularioClienteModelo)
        modelo.cliente = SimpleNamespace(addresses_details=direcciones, business_entity_id=10)
        modelo.user_name = 'Usuario de prueba'
        modelo._ubicaciones_originales = originales or {}
        self.llamadas = []
        modelo.base_de_datos = SimpleNamespace(
            fetchone=lambda _: 1 if instalado else None,
            command=lambda sql, params: self.llamadas.append((sql, params)))
        return modelo

    def test_cliente_nuevo_usa_id_asignado_al_guardar(self):
        detalle = {'AddressDetailID': 0, **normalizar(19, -90)}
        modelo = self.modelo([detalle])
        modelo.validar_guardado_ubicaciones()
        detalle['AddressDetailID'] = 200
        modelo.guardar_ubicaciones()
        sql, params = self.llamadas[0]
        self.assertEqual(params[3:5], (200, 10))
        self.assertEqual(params[-2:], (44, 200))
        self.assertIn('UPDATE D SET Latitude', sql)
        self.assertIn('EXEC dbo.InsertarBitacoraCambiosClientes', sql)
        self.assertNotIn('GuardarUbicacionCliente', sql)
        self.assertIn('BEGIN TRANSACTION', sql)
        self.assertIn('ROLLBACK TRANSACTION', sql)
        self.assertIn('Latitude=(vacío)', params[6])
        modelo.guardar_ubicaciones()
        self.assertEqual(len(self.llamadas), 1)

    def test_eliminar_ubicacion_y_conservar_anterior_para_bitacora(self):
        anterior = normalizar(19, -90, 5)
        modelo = self.modelo([{'AddressDetailID': 3, **normalizar()}], {3: anterior})
        modelo.guardar_ubicaciones()
        params = self.llamadas[0][1]
        self.assertEqual(params[:3], (None, None, None))
        self.assertIn('Latitude=19.0000000', params[6])
        self.assertEqual(params[-2:], (46, 3))

    def test_sin_cambios_no_escribe(self):
        dato = normalizar(19, -90)
        modelo = self.modelo([{'AddressDetailID': 3, **dato}], {3: dato})
        modelo.guardar_ubicaciones()
        self.assertEqual(self.llamadas, [])

    def test_validar_no_necesita_procedimientos_adicionales(self):
        modelo = self.modelo([{'AddressDetailID': 0, **normalizar(19, -90)}], instalado=False)
        modelo.validar_guardado_ubicaciones()
        self.assertEqual(self.llamadas, [])

    def test_actualizar_registra_valores_anteriores_y_nuevos(self):
        modelo = self.modelo([{'AddressDetailID': 3, **normalizar(20, -91)}],
                              {3: normalizar(19, -90)})
        modelo.guardar_ubicaciones()
        params = self.llamadas[0][1]
        self.assertEqual(params[-2:], (45, 3))
        self.assertIn('Latitude=19.0000000', params[6])
        self.assertIn('Latitude=20.0000000', params[7])

    def test_originales_no_comparten_referencia(self):
        modelo = self.modelo([], {3: normalizar(19, -90)})
        dato = modelo.obtener_ubicacion(3)
        dato['Latitude'] = None
        self.assertEqual(modelo.obtener_ubicacion(3)['Latitude'], Decimal(19))

    def test_error_no_confirma_estado_en_memoria(self):
        modelo = self.modelo([{'AddressDetailID': 3, **normalizar(19, -90)}])
        def fallar(*args):
            raise RuntimeError('SQL no disponible')
        modelo.base_de_datos.command = fallar
        with self.assertRaises(RuntimeError):
            modelo.guardar_ubicaciones()
        self.assertIsNone(modelo.obtener_ubicacion(3)['Latitude'])

if __name__ == '__main__':
    unittest.main()
