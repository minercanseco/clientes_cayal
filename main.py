import ttkbootstrap as ttk
from cayal.parametros_contpaqi import ParametrosContpaqi
from formulario_cliente import FormularioCliente
from cayal.cliente import Cliente

if __name__ == '__main__':
    parametros = ParametrosContpaqi()
    ventana = ttk.Window()
    parametros_cliente = {}
    instancia_cliente = Cliente()
    instancia = FormularioCliente(ventana,parametros, parametros_cliente, instancia_cliente)
    ventana.mainloop()

