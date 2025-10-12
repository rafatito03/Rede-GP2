import socket
import funcoes
from crypto import gerar_chave

# Configurações do servidor
HOST = '127.0.0.1'  
PORT = 65432      

print("--- Aplicação Servidor ---")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"Servidor pronto e escutando em {HOST}:{PORT}")
    
    conn, addr = s.accept()
    
    with conn:
        print(f"Cliente conectado pelo endereço: {addr}")

        # 1. Gerar e enviar a chave de criptografia
        chave_simetrica = gerar_chave()
        conn.sendall(chave_simetrica)
        print("Chave de criptografia gerada e enviada para o cliente.")
        
        # 2. Receber e processar o handshake criptografado
        mensagem_handshake = funcoes.receber_mensagem_criptografada(conn, chave_simetrica)
        if mensagem_handshake is None:
            print("Cliente desconectou durante o handshake.")
        else:
            print(f"Mensagem de handshake criptografada recebida: '{mensagem_handshake}'")
        
            try:
                partes = mensagem_handshake.split(';')
                modo_operacao = partes[0].split(':')[1]
                tamanho_maximo = int(partes[1].split(':')[1])
                
                print("\n--- Handshake processado com sucesso! ---")
                print(f"Modo de Operação acordado: {modo_operacao}")
                print(f"Tamanho Máximo da Comunicação: {tamanho_maximo} caracteres")
                
                resposta = "CONFIRMADO: Handshake recebido e parâmetros definidos."
                funcoes.mandar_mensagem_criptografada(resposta, conn, chave_simetrica)
                
                # --- LÓGICA DE RECEBIMENTO E MONTAGEM DE PACOTES ---
                while True: # Loop principal para receber múltiplas mensagens completas
                    print("\n--- Aguardando nova transmissão do cliente ---")
                    mensagem_completa = []
                    seq_num_esperado = 0

                    while True: # Loop para receber os pacotes de uma única transmissão
                        pacote_recebido = funcoes.receber_mensagem_criptografada(conn, chave_simetrica)
                        
                        if pacote_recebido is None: # Conexão fechada
                            break
                        
                        if pacote_recebido == "FIM":
                            break

                        # Processa o pacote recebido
                        try:
                            seq_num_str, payload = pacote_recebido.split(':', 1)
                            seq_num_recebido = int(seq_num_str)
                            
                            print(f"<-- Pacote recebido. Metadados: [Seq={seq_num_recebido}, Carga='{payload}']")
                            
                            if seq_num_recebido == seq_num_esperado:
                                mensagem_completa.append(payload)
                                
                                ack = f"ACK:{seq_num_recebido}"
                                funcoes.mandar_mensagem_criptografada(ack, conn, chave_simetrica)
                                print(f"--> Confirmação enviada para pacote {seq_num_recebido}")
                                
                                seq_num_esperado += 1
                            else:
                                print(f"Pacote fora de ordem recebido. Esperado: {seq_num_esperado}, Recebido: {seq_num_recebido}. (Ação de descarte/NACK será implementada na próxima entrega)")
                                ack_anterior = f"ACK:{seq_num_esperado - 1}"
                                funcoes.mandar_mensagem_criptografada(ack_anterior, conn, chave_simetrica)

                        except ValueError:
                            print(f"Erro ao processar o pacote: '{pacote_recebido}'")

                    if not mensagem_completa: # Se a conexão foi fechada sem receber FIM
                        break

                    texto_final = "".join(mensagem_completa)
                    print("\n--- Comunicação Completa Recebida ---")
                    print(f"Mensagem reconstruída com sucesso: '{texto_final}'")
            
            except Exception as e:
                print(f"Ocorreu um erro no processamento: {e}")
                
        print("\nFinalizando conexão com este cliente.")

print("Servidor finalizado.")