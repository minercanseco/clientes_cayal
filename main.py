import ttkbootstrap as ttk
from cayal.parametros_contpaqi import ParametrosContpaqi
from formulario_cliente import FormularioCliente
from cayal.cliente import Cliente
from panel_principal_cliente import PanelPrincipal
from cayal.comandos_base_datos import ComandosBaseDatos
from buscar_clientes import BuscarClientes
from cayal.util import Utilerias


if __name__ == '__main__':
    parametros = ParametrosContpaqi()

    # parametros de prueba
    #parametros.cadena_conexion = 'Mac'
    # parametros.base_de_datos ='ComercialSP'
    # parametros.id_principal = 6930 #kambul
    #parametros.id_principal = 5636  # anaid
    # parametros.id_principal = 8106  # gess
    # parametros.id_principal = 8907  # gess
    # parametros.id_principal = 18728
    #parametros.id_principal = -1
    #parametros.id_usuario = 64

    base_de_datos = ComandosBaseDatos(parametros.cadena_conexion)
    utilerias = Utilerias()
    id_principal = parametros.id_principal

    ventana = ttk.Window()
    if not (id_principal in (9277, 8179, 6211) and parametros.id_usuario not in (64, 1)):
        if id_principal == -1:
            instancia = PanelPrincipal(ventana, parametros, base_de_datos, utilerias)

        elif id_principal == 0:
            BuscarClientes(ventana, base_de_datos, parametros, utilerias)

        else:
            info_cliente = base_de_datos.fetchall("""
                        SELECT * FROM [dbo].[zvwBuscarInfoCliente-BusinessEntityID](?)
                """, (id_principal))

            instancia_cliente = Cliente()
            instancia_cliente.consulta = info_cliente
            instancia_cliente.settear_valores_consulta()

            tipo_captura = 'Remisión' if instancia_cliente.official_number == 'XAXX010101000' else 'Factura'
            parametros_cliente = {'TipoCaptura': tipo_captura}

            formulario_cliente = FormularioCliente(ventana, parametros, parametros_cliente, instancia_cliente)

        ventana.mainloop()
