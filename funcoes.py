import struct
import socket
from crypto import criptografar_mensagem, descriptografar_mensagem

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




def calcular_checksum(dados: bytes) -> int:
    if len(dados) % 2 != 0:
        dados += b'\0'

    soma = 0
    for i in range(0, len(dados), 2):
        palavra = (dados[i] << 8) + dados[i+1]
        soma += palavra

        soma = (soma & 0xFFFF) + (soma >> 16)

    return (~soma) & 0xFFFF
def verificar_checksum(dados: bytes, checksum_recebido: int) -> bool:
    checksum_calculado = calcular_checksum(dados)
    return checksum_calculado == checksum_recebido