from flask import Flask, render_template, redirect, request
import paramiko
import socket
import logging

app = Flask(__name__)

# Configuración del logger
logging.basicConfig(level=logging.INFO)

# Configura los detalles de conexión SSH para múltiples máquinas
MAQUINAS = {
    'vbox-gateway': {'host': '192.168.0.1', 'username': 'osboxes', 'key': '/home/osboxes/.ssh/id_rsa'},
    'vbox1': {'host': '192.168.0.100', 'username': 'osboxes', 'key': '/home/osboxes/.ssh/id_rsa'},
    'vbox2': {'host': '192.168.0.101', 'username': 'osboxes', 'key': '/home/osboxes/.ssh/id_rsa'},
    'vbox-dns': {'host': '192.168.0.102', 'username': 'osboxes', 'key': '/home/osboxes/.ssh/id_rsa'},
    'vbox-nagios-servidor': {'host': '192.168.0.150', 'username': 'osboxes', 'key': '/home/osboxes/.ssh/id_rsa'}
}

# Lista de comandos predeterminados
COMANDOS_PREDETERMINADOS = {
    'Estado del sistema': 'systemctl status',
    'Espacio en disco': 'df -h',
    'Uso de memoria': 'free -m',
    'Listado de procesos': 'ps aux',
    'Tabla de rutas': 'route -n',
    'Reglas de iptables': 'iptables -L -v -n'
}

def verificar_conexion(host, port=22, timeout=2):
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except Exception as e:
        logging.warning(f"Conexión fallida a {host}:{port} - {e}")
        return False

def maquinas_encendidas():
    encendidas = {}
    for nombre, detalles in MAQUINAS.items():
        if verificar_conexion(detalles['host']):
            encendidas[nombre] = detalles
    return encendidas

def ejecutar_comando_ssh(maquina, comando):
    try:
        detalles_maquina = MAQUINAS.get(maquina)
        if not detalles_maquina:
            logging.error(f"No se encontró la configuración para la máquina: {maquina}")
            return None, f"No se encontró la configuración para la máquina: {maquina}"

        with paramiko.SSHClient() as cliente_ssh:
            cliente_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            clave_privada = paramiko.RSAKey.from_private_key_file(detalles_maquina['key'])
            cliente_ssh.connect(detalles_maquina['host'], 22, detalles_maquina['username'], pkey=clave_privada)
            comando_completo = f"sudo {comando}"
            _, salida, errores = cliente_ssh.exec_command(comando_completo)
            resultado = salida.read().decode("utf-8")
            error = errores.read().decode("utf-8")

        logging.info(f"Comando ejecutado en {maquina}: {comando_completo}")
        return resultado, error

    except Exception as e:
        logging.error(f"Error ejecutando comando SSH: {e}")
        return None, str(e)

@app.route('/')
def index():
    maquinas = maquinas_encendidas()
    return render_template('index.html', maquinas=maquinas.keys(), comandos=COMANDOS_PREDETERMINADOS.keys())

@app.route('/ejecutar', methods=['POST'])
def ejecutar():
    maquina = request.form['maquina']
    comando_personalizado = request.form['comando_personalizado']
    comando_predefinido = request.form.get('comando_predefinido')
    comando = comando_personalizado if comando_personalizado else COMANDOS_PREDETERMINADOS.get(comando_predefinido, '')

    if not comando:
        return render_template('resultado.html', maquina=maquina, comando=comando, resultado='', error='Comando no especificado o inválido.')

    resultado, error = ejecutar_comando_ssh(maquina, comando)
    return render_template('resultado.html', maquina=maquina, comando=comando, resultado=resultado, error=error)

@app.route('/nagios')
def nagios():
    return redirect("http://192.168.0.150/nagios")

if __name__ == '__main__':
    app.run(debug=True)
