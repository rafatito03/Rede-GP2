import socket

# Configurações do servidor
HOST = '127.0.0.1'  
PORT = 65432        

print("--- Aplicação Servidor ---")

# Cria o socket do servidor com o padrão TCP/IP
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # Vincula o socket ao endereço e porta definidos
    s.bind((HOST, PORT))
    
    # Coloca o servidor em modo de await
    s.listen()
    print(f"Servidor pronto e escutando em {HOST}:{PORT}")
    
    # O programa fica parado aqui até um cliente se conectar.
    conn, addr = s.accept()
    
    with conn:
        print(f"Cliente conectado pelo endereço: {addr}")
        
        dados_recebidos = conn.recv(1024)
        mensagem_handshake = dados_recebidos.decode()
        print(f"Mensagem de handshake recebida do cliente: '{mensagem_handshake}'")
        
        try:
            partes = mensagem_handshake.split(';')
            modo_operacao = partes[0].split(':')[1]
            tamanho_maximo = int(partes[1].split(':')[1])
            
            print("\n--- Handshake processado com sucesso! ---")
            print(f"Modo de Operação acordado: {modo_operacao}")
            print(f"Tamanho Máximo da Comunicação: {tamanho_maximo} caracteres")
            
            resposta = "CONFIRMADO: Handshake recebido e parâmetros definidos."
            conn.sendall(resposta.encode())

        except (IndexError, ValueError):
            print("Erro: A mensagem de handshake do cliente está em um formato inválido.")
            resposta_erro = "ERRO: Formato de handshake inválido."
            conn.sendall(resposta_erro.encode())
            
        print("Finalizando conexão com este cliente.")

print("Servidor finalizado.")
