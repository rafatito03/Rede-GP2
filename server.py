import socket

# Configurações do servidor
HOST = '127.0.0.1'  
PORT = 65432        

print("--- Aplicação Servidor ---")

# Cria o socket do servidor com o padrão TCP/IP
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # Vincula o socket ao endereço e porta definidos
    s.bind((HOST, PORT))
    
    # Coloca o servidor em modo de escuta
    s.listen()
    print(f"Servidor pronto e escutando em {HOST}:{PORT}")
    
    # Aguarda a conexão de um cliente
    conn, addr = s.accept()
    
    with conn:
        print(f"Cliente conectado pelo endereço: {addr}")
        
        # --- HANDSHAKE INICIAL ---
        dados_recebidos = conn.recv(1024)
        mensagem_handshake = dados_recebidos.decode()
        print(f"Mensagem de handshake recebida do cliente: '{mensagem_handshake}'")
        
        try:
            # Processa o handshake
            partes = mensagem_handshake.split(';')
            modo_operacao = partes[0].split(':')[1]
            tamanho_maximo = int(partes[1].split(':')[1])
            
            print("\n--- Handshake processado com sucesso! ---")
            print(f"Modo de Operação acordado: {modo_operacao}")
            print(f"Tamanho Máximo da Comunicação: {tamanho_maximo} caracteres")
            
            # Envia a confirmação do handshake
            resposta = "CONFIRMADO: Handshake recebido e parâmetros definidos."
            conn.sendall(resposta.encode())

        except (IndexError, ValueError):
            print("Erro: A mensagem de handshake do cliente está em um formato inválido.")
            resposta_erro = "ERRO: Formato de handshake inválido."
            conn.sendall(resposta_erro.encode())
            
        print("\n--- Aguardando recebimento de pacotes de dados ---")
        
        mensagem_completa = []
        seq_num_esperado = 0
        
        while True:
            # Fica em um loop aguardando os pacotes
            pacote_recebido = conn.recv(1024).decode()
            
            # Se a mensagem for "FIM", encerra o loop
            if pacote_recebido == "FIM":
                break
            
            try:
                # desmonntando o payload e o numero de sequencia
                seq_num_str, payload = pacote_recebido.split(':', 1)
                seq_num_recebido = int(seq_num_str)
                
                # Imprime os metadados do pacote recebido
                print(f"<-- Pacote recebido. Metadados: [Seq={seq_num_recebido}, Carga='{payload}']")
                
                # Para este cenário de canal perfeito, o número de sequência sempre será o esperado
                if seq_num_recebido == seq_num_esperado:
                    # 6. Armazena a carga útil para remontar a mensagem depois
                    mensagem_completa.append(payload)
                    
                    # 5. Envia o reconhecimento positivo (ACK) para o cliente
                    ack = f"ACK:{seq_num_recebido}"
                    conn.sendall(ack.encode())
                    print(f"--> Confirmação enviada: '{ack}'")
                    
                    # Atualiza o próximo número de sequência esperado
                    seq_num_esperado += 1
                else:
                    print(f"recebido um pacote fora de ordem. Esperado: {seq_num_esperado}, Recebido: {seq_num_recebido}. Descartando.")
                    # Reenvia o ACK do último pacote recebido em ordem
                    ack_anterior = f"ACK:{seq_num_esperado - 1}"
                    conn.sendall(ack_anterior.encode())

            except ValueError:
                print(f"Erro ao processar o pacote: '{pacote_recebido}'")

        texto_final = "".join(mensagem_completa)
        print("\n--- Comunicação Completa ---")
        print(f"Mensagem reconstruída com sucesso: '{texto_final}'")
            
        print("\nFinalizando conexão com este cliente.")

print("Servidor finalizado.")