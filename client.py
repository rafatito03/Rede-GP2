import socket
import funcoes

HOST = '127.0.0.1'  
PORT = 65432      
modo_de_operacao_escolhido = "GBN"
tamanho_maximo_da_comunicacao = 500
TAMANHO_PAYLOAD = 4

print("--- Aplicação Cliente ---")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        print(f"Conectando ao servidor em {HOST}:{PORT}...")
        s.connect((HOST, PORT))
        print("Conectado")
        
        # 1. Receber a chave de criptografia do servidor
        chave_simetrica = s.recv(1024)
        if not chave_simetrica:
            raise ConnectionError("Não foi possível receber a chave do servidor.")
        print("Chave de criptografia recebida do servidor.")

        mensagem_handshake = f"MODO:{modo_de_operacao_escolhido};TAMANHO_MAXIMO:{tamanho_maximo_da_comunicacao}"
        funcoes.mandar_mensagem_criptografada(mensagem_handshake, s, chave_simetrica)
        print(f"Mensagem de handshake criptografada enviada para o servidor.")
        
        resposta_servidor = funcoes.receber_mensagem_criptografada(s, chave_simetrica)
        print(f"Resposta criptografada recebida: '{resposta_servidor}'")

        # --- LÓGICA DE ENVIO DE PACOTES IMPLEMENTADA ---
        while True:
            mensagem_original = input("\nDigite a mensagem completa para enviar (ou 'end' para sair): ")
            if mensagem_original.lower() == 'end':
                print("Encerrando a comunicação.")
                break

            #  Segmentar a mensagem em pacotes com carga útil de 4 caracteres 
            segmentos = [mensagem_original[i:i+TAMANHO_PAYLOAD] for i in range(0, len(mensagem_original), TAMANHO_PAYLOAD)]
            print(f"Mensagem dividida em {len(segmentos)} pacotes. Iniciando transmissão...")

            # Enviar cada pacote individualmente e aguardar ACK
            for i, payload in enumerate(segmentos):
                numero_sequencia = i 
                pacote_para_enviar = f"{numero_sequencia}:{payload}"

                funcoes.mandar_mensagem_criptografada(pacote_para_enviar, s, chave_simetrica)
                print(f"--> Pacote {numero_sequencia} enviado com dados: '{payload}'")

                ack_recebido = funcoes.receber_mensagem_criptografada(s, chave_simetrica)
                print(f"<-- Confirmação recebida do servidor: '{ack_recebido}'") 
            
            # Enviar mensagem de finalização para o servidor saber que a transmissão acabou
            funcoes.mandar_mensagem_criptografada("FIM", s, chave_simetrica)
            print("--- Transmissão da mensagem completa finalizada ---")


    except ConnectionRefusedError:
        print("Falha na conexão. O servidor parece estar offline ou recusou a conexão.")
    except Exception as error:
        print(f"Ocorreu um erro inesperado: {error}")

print("Cliente finalizado.")