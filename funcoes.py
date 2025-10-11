import struct
import socket
def mandar_mensagem(mensagem,conexao_socket:socket.socket):
    mensagem_bytes = mensagem.encode('utf-8')
    tamanho_mensagem = len(mensagem_bytes)
    cabecalho = struct.pack('!I', tamanho_mensagem)
    conexao_socket.sendall(cabecalho)
    conexao_socket.sendall(mensagem_bytes)

def receber_mensagem(conexao_socket: socket.socket):
    """Recebe uma mensagem completa, lendo o cabeçalho de tamanho primeiro."""
    cabecalho = conexao_socket.recv(4)
    if not cabecalho:
        return None # Conexão fechada
    
    tamanho_mensagem = struct.unpack('!I', cabecalho)[0]
    
    
    chunks = []
    bytes_recebidos = 0
    while bytes_recebidos < tamanho_mensagem:
        bytes_restantes = tamanho_mensagem - bytes_recebidos
        chunk = conexao_socket.recv(min(bytes_restantes, 4096))
        if not chunk:
            raise RuntimeError("Conexão interrompida") #se cair no meio da transmissão
        chunks.append(chunk)
        bytes_recebidos += len(chunk)
        
    mensagem_bytes = b''.join(chunks)
    return mensagem_bytes.decode('utf-8')
