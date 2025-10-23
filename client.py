import socket
import funcoes

HOST = '127.0.0.1'  
PORT = 65432      
modo_de_operacao_escolhido = "GBN"
tamanho_maximo_da_comunicacao = 500 

print("--- Aplicação Cliente ---")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        print(f"Conectando ao servidor em {HOST}:{PORT}...")
        s.connect((HOST, PORT))
        print("Conectado")
        
        chave_simetrica = s.recv(1024)
        if not chave_simetrica:
            raise ConnectionError("Não foi possível receber a chave do servidor.")
        print("Chave de criptografia recebida do servidor.")

        mensagem_handshake = f"MODO:{modo_de_operacao_escolhido};TAMANHO_MAXIMO:{tamanho_maximo_da_comunicacao}"
        funcoes.mandar_mensagem_criptografada(mensagem_handshake, s, chave_simetrica)
        print(f"Mensagem de handshake criptografada enviada para o servidor.")
        
        resposta_servidor = funcoes.receber_mensagem_criptografada(s, chave_simetrica)
        print(f"Resposta de handshake recebida: '{resposta_servidor}'")

        
        parametros_servidor = {}
        try:
            partes = resposta_servidor.split(';')
            for parte in partes:
                if '=' in parte:
                    chave, valor = parte.split('=', 1)
                    parametros_servidor[chave] = valor
        except Exception as e:
            raise ValueError(f"Falha ao parsear resposta do servidor: {e}")
        if "STATUS" not in parametros_servidor or parametros_servidor["STATUS"] not in ("OK", "ADJUSTED"):
            motivo = parametros_servidor.get("REASON", "DESCONHECIDO")
            raise ConnectionError(f"Servidor rejeitou o handshake. Status: {parametros_servidor.get('STATUS')}, Motivo: {motivo}")

        tamanho_payload_negociado = int(parametros_servidor["PAYLOAD"])
        tamanho_maximo_negociado = int(parametros_servidor["MAX"])
        tamanho_janela_negociado = int(parametros_servidor["WINDOW"])
        
        print("\n--- Handshake com servidor BEM-SUCEDIDO ---")
        print(f"Modo: {parametros_servidor['MODE']}")
        print(f"Tamanho Máx. (Final): {tamanho_maximo_negociado}")
        print(f"Tamanho Payload (Definido pelo Servidor): {tamanho_payload_negociado}")
        print(f"Tamanho Janela (Definido pelo Servidor): {tamanho_janela_negociado}")
        if parametros_servidor["STATUS"] == "ADJUSTED":
            print(f"Aviso do Servidor: {parametros_servidor['REASON']}")


        while True:
            mensagem_original = input("\nDigite a mensagem completa para enviar (ou 'end' para sair): ")
            if mensagem_original.lower() == 'end':
                print("Encerrando a comunicação.")
                break

            if len(mensagem_original) > tamanho_maximo_negociado:
                print(f"Erro: A mensagem é muito longa ({len(mensagem_original)} caracteres). O máximo negociado foi {tamanho_maximo_negociado}.")
                continue 

            segmentos = [mensagem_original[i:i+tamanho_payload_negociado] for i in range(0, len(mensagem_original), tamanho_payload_negociado)]
            print(f"Mensagem dividida em {len(segmentos)} pacotes (Payload: {tamanho_payload_negociado}). Iniciando transmissão...")

            for i, payload in enumerate(segmentos):
                numero_sequencia = i 
                pacote_para_enviar = f"{numero_sequencia}:{payload}"

                funcoes.mandar_mensagem_criptografada(pacote_para_enviar, s, chave_simetrica)
                print(f"--> Pacote {numero_sequencia} enviado com dados: '{payload}'")

                ack_recebido = funcoes.receber_mensagem_criptografada(s, chave_simetrica)
                print(f"<-- Confirmação recebida do servidor: '{ack_recebido}'") 
            
            funcoes.mandar_mensagem_criptografada("FIM", s, chave_simetrica)
            print("--- Transmissão da mensagem completa finalizada ---")


    except ConnectionRefusedError:
        print("Falha na conexão. O servidor parece estar offline ou recusou a conexão.")
    except Exception as error:
        print(f"Ocorreu um erro inesperado: {error}")

print("Cliente finalizado.")