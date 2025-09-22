import socket
HOST = '127.0.0.1'  
PORT = 65432        
# Escolha do modo de operação 
modo_de_operacao_escolhido = "GBN"

# Definição do tamanho máximo de caracteres para toda a comunicação
tamanho_maximo_da_comunicacao = 500

print("--- Aplicação Cliente ---")

# Cria o socket do cliente com o padrão IPv4 e TCP
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        # Tenta estabelecer a conexão com o servidor
        print(f"conectando ao servidor em {HOST}:{PORT}...")
        s.connect((HOST, PORT))
        print("Conectado")
            
        # Monta a mensagem de handshake no formato "CHAVE:VALOR;CHAVE:VALOR"
        mensagem_handshake = f"MODO:{modo_de_operacao_escolhido};TAMANHO_MAXIMO:{tamanho_maximo_da_comunicacao}"
    
        s.sendall(mensagem_handshake.encode())
        print(f"Mensagem de handshake enviada para o servidor: '{mensagem_handshake}'")
        
        dados_recebidos = s.recv(1024)
        
        print(f"Resposta recebida: '{dados_recebidos.decode()}'")

    except ConnectionRefusedError:
        print("Falha na conexão. O servidor parece estar offline ou recusou a conexão.")
    except Exception as error:
        print(f"Ocorreu um erro inesperado: {error}")

print("Cliente finalizado.")
