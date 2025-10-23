import socket
import funcoes
from crypto import gerar_chave

HOST = '127.0.0.1'  
PORT = 65432      
TAMANHO_PAYLOAD_SERVIDOR = 4 
TAMANHO_JANELA = 1           
TAMANHO_MINIMO_MSG = 30    

print("--- Aplicação Servidor ---")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"Servidor pronto e escutando em {HOST}:{PORT}")
    
    conn, addr = s.accept()
    
    with conn:
        print(f"Cliente conectado pelo endereço: {addr}")

        
        chave_simetrica = gerar_chave()
        conn.sendall(chave_simetrica)
        print("Chave de criptografia gerada e enviada para o cliente.")
        
        
        mensagem_handshake = funcoes.receber_mensagem_criptografada(conn, chave_simetrica)
        if mensagem_handshake is None:
            print("Cliente desconectou durante o handshake.")
        else:
            print(f"Mensagem de handshake criptografada recebida: '{mensagem_handshake}'")
        
            try:
                
                partes = mensagem_handshake.split(';')
                modo_operacao_cliente = partes[0].split(':')[1]
                tamanho_maximo_cliente = int(partes[1].split(':')[1])
                
                print(f"\n--- Processando Handshake do Cliente ---")
                print(f"Modo de Operação solicitado: {modo_operacao_cliente}")
                print(f"Tamanho Máximo solicitado: {tamanho_maximo_cliente}")

                
                status = "OK"
                motivo = "N/A"
                
                
                if tamanho_maximo_cliente < TAMANHO_MINIMO_MSG:
                    print(f"Aviso: Tamanho máximo ({tamanho_maximo_cliente}) ajustado para {TAMANHO_MINIMO_MSG}")
                    tamanho_maximo_final = TAMANHO_MINIMO_MSG
                    status = "ADJUSTED"
                    motivo = "MAX_SIZE_TOO_SMALL"
                else:
                    tamanho_maximo_final = tamanho_maximo_cliente
                

                
                modo_operacao_final = modo_operacao_cliente 
                
                print("\n--- Parâmetros Finais Definidos ---")
                print(f"Modo: {modo_operacao_final}")
                print(f"Tamanho Máx.: {tamanho_maximo_final}")
                print(f"Payload: {TAMANHO_PAYLOAD_SERVIDOR}")
                print(f"Janela: {TAMANHO_JANELA}")
                print(f"Status: {status}")

                resposta = (
                    f"HELLO-ACK;"
                    f"MODE={modo_operacao_final};"
                    f"MAX={tamanho_maximo_final};"
                    f"PAYLOAD={TAMANHO_PAYLOAD_SERVIDOR};"
                    f"WINDOW={TAMANHO_JANELA};"
                    f"STATUS={status};"
                    f"REASON={motivo}"
                )
                
                funcoes.mandar_mensagem_criptografada(resposta, conn, chave_simetrica)
                print("Resposta estruturada do handshake enviada.")
                
                while True: 
                    print("\n--- Aguardando nova transmissão do cliente ---")
                    mensagem_completa = []
                    seq_num_esperado = 0

                    while True: 
                        pacote_recebido = funcoes.receber_mensagem_criptografada(conn, chave_simetrica)
                        
                        if pacote_recebido is None: 
                            break
                        
                        if pacote_recebido == "FIM":
                            break

                        
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
                                print(f"Pacote fora de ordem recebido. Esperado: {seq_num_esperado}, Recebido: {seq_num_recebido}.")
                                
                                ack_anterior = f"ACK:{seq_num_esperado - 1}"
                                funcoes.mandar_mensagem_criptografada(ack_anterior, conn, chave_simetrica)

                        except ValueError:
                            print(f"Erro ao processar o pacote: '{pacote_recebido}'")

                    if not mensagem_completa: 
                        break

                    texto_final = "".join(mensagem_completa)
                    print("\n--- Comunicação Completa Recebida ---")
                    print(f"Mensagem reconstruída com sucesso: '{texto_final}'")
            
            except Exception as e:
                print(f"Ocorreu um erro no processamento: {e}")
                
        print("\nFinalizando conexão com este cliente.")

print("Servidor finalizado.")