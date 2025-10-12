import struct
import socket
from crypto import criptografar_mensagem, descriptografar_mensagem

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

def mandar_mensagem_criptografada(mensagem: str, conexao_socket: socket.socket, chave: bytes):
    """Criptografa a mensagem e a envia com um cabeçalho de tamanho."""
    mensagem_bytes = mensagem.encode('utf-8')
    # Criptografa a mensagem
    mensagem_criptografada = criptografar_mensagem(mensagem_bytes, chave)
    
    # tamanho da mensagem CRIPTOGRAFADA tem que esta no cabeçalho
    tamanho_mensagem = len(mensagem_criptografada)
    cabecalho = struct.pack('!I', tamanho_mensagem)
    
    print(f"Mensagem criptografada: {mensagem_criptografada}\n")
    # envia o cabeçalho e depois a mensagem
    conexao_socket.sendall(cabecalho)
    conexao_socket.sendall(mensagem_criptografada)

def receber_mensagem_criptografada(conexao_socket: socket.socket, chave: bytes) -> str:
    """Recebe uma mensagem criptografada, a descriptografa e retorna como string."""
    # Recebe o cabeçalho
    cabecalho = conexao_socket.recv(4)
    if not cabecalho:
        return None
    tamanho_mensagem_criptografada = struct.unpack('!I', cabecalho)[0]
    
    # o restante da mensagem
    chunks = []
    bytes_recebidos = 0
    while bytes_recebidos < tamanho_mensagem_criptografada:
        bytes_restantes = tamanho_mensagem_criptografada - bytes_recebidos
        chunk = conexao_socket.recv(min(bytes_restantes, 4096))
        if not chunk:
            raise RuntimeError("Conexão interrompida durante a recepção da mensagem criptografada")
        chunks.append(chunk)
        bytes_recebidos += len(chunk)
        
    mensagem_criptografada_bytes = b''.join(chunks)

    print(f"\Verificando criptografia da mensagem: {mensagem_criptografada_bytes}\n")
    
    mensagem_descriptografada_bytes = descriptografar_mensagem(mensagem_criptografada_bytes, chave)
    
    return mensagem_descriptografada_bytes.decode('utf-8')