import socket

HOST = '127.0.0.1'  
PORT = 65432        
# Escolha do modo de operação (será usado na próxima entrega)
modo_de_operacao_escolhido = "GBN"

# Definição do tamanho máximo de caracteres para toda a comunicação
tamanho_maximo_da_comunicacao = 500

# Texto a ser enviado para o servidor
texto_para_enviar = "Este eh um teste de comunicacao para a segunda entrega do trabalho."
tamanho_payload = 4 # Carga útil de no máximo 4 caracteres por pacote

print("--- Aplicação Cliente ---")

# 1. Segmentar a mensagem em pacotes com carga útil de 4 caracteres
segmentos = [texto_para_enviar[i:i+tamanho_payload] for i in range(0, len(texto_para_enviar), tamanho_payload)]
print(f"Mensagem original foi dividida em {len(segmentos)} pacotes.")

# Cria o socket do cliente com o padrão IPv4 e TCP
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        # Tenta estabelecer a conexão com o servidor
        print(f"Conectando ao servidor em {HOST}:{PORT}...")
        s.connect((HOST, PORT))
        print("Conectado.")
            
        # --- HANDSHAKE INICIAL ---
        mensagem_handshake = f"MODO:{modo_de_operacao_escolhido};TAMANHO_MAXIMO:{tamanho_maximo_da_comunicacao}"
        s.sendall(mensagem_handshake.encode())
        print(f"Mensagem de handshake enviada para o servidor: '{mensagem_handshake}'")
        
        # Recebe a confirmação do handshake
        dados_recebidos = s.recv(1024)
        print(f"Resposta do servidor: '{dados_recebidos.decode()}'")

        # --- TROCA DE MENSAGENS (ENTREGA 27/10) ---
        print("\n--- Iniciando a transmissão da mensagem em pacotes ---")
        
        # iterando aqui pela quantidade de segmentos
        for i, payload in enumerate(segmentos):
            # 2. Monta o pacote com número de sequência e carga útil (formato: "SEQ:PAYLOAD")
            numero_sequencia = i
            pacote = f"{numero_sequencia}:{payload}"
            
            # Envia o pacote para o servidor
            s.sendall(pacote.encode())
            print(f"--> Pacote {numero_sequencia} enviado com dados: '{payload}'")
            
            # 3. Aguarda o recebimento do ACK do servidor
            ack_recebido = s.recv(1024).decode()
            print(f"<-- Metadados de confirmação recebidos: '{ack_recebido}'")
        
        s.sendall("FIM".encode())
        print("\n--- Transmissão finalizada com sucesso! ---")

    except ConnectionRefusedError:
        print("Falha na conexão. O servidor parece estar offline ou recusou a conexão.")
    except Exception as error:
        print(f"Ocorreu um erro inesperado: {error}")

print("Cliente finalizado.")