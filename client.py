import socket
import funcoes
import time

# ===================== CONFIGURAÇÕES =====================
HOST = '127.0.0.1'
PORT = 65432
TIMEOUT_SEGUNDOS = 3

# ===================== FUNÇÕES DE ENVIO (GBN e SR) =====================

def enviar_segmentos_GBN(segmentos, janela, socket_conexao, chave_simetrica, seq_erro_chk=-1, seq_erro_perda=-1):
    """Implementa Go-Back-N com injeção de falhas (Checksum e Perda)."""
    base = 0
    next_seq_num = 0
    N = janela
    num_segmentos = len(segmentos)

    # Controle para que o erro ocorra apenas na primeira tentativa
    erros_chk_pendentes = {seq_erro_chk}
    erros_perda_pendentes = {seq_erro_perda}

    while base < num_segmentos:
        # 1. Enviar pacotes dentro da janela
        while next_seq_num < base + N and next_seq_num < num_segmentos:
            payload = segmentos[next_seq_num]
            payload_bytes = payload.encode('utf-8')
            checksum = funcoes.calcular_checksum(payload_bytes)
            
            # --- SIMULAÇÃO DE ERRO DE CHECKSUM ---
            if next_seq_num in erros_chk_pendentes:
                print(f"[SIMULAÇÃO] Corrompendo checksum do pacote {next_seq_num}!")
                checksum += 1337
                erros_chk_pendentes.remove(next_seq_num)
            
            pacote_para_enviar = f"{next_seq_num}:{checksum}:{payload}"
            
            # --- SIMULAÇÃO DE PERDA DE PACOTE ---
            if next_seq_num in erros_perda_pendentes:
                print(f"[SIMULAÇÃO] PACOTE {next_seq_num} PERDIDO NA REDE (Não enviado)!")
                erros_perda_pendentes.remove(next_seq_num)
                # Não enviamos o socket.sendall, mas a lógica continua como se tivesse enviado
            else:
                funcoes.mandar_mensagem_criptografada(pacote_para_enviar, socket_conexao, chave_simetrica)
                print(f"[CLIENTE→SERVIDOR] Pacote {next_seq_num} enviado.")

            # Lógica do Timer do GBN
            if base == next_seq_num:
                socket_conexao.settimeout(TIMEOUT_SEGUNDOS)
                # Se perdemos o pacote base, o timer começa mesmo assim
                print(f"[TIMER] Iniciado para base {base}.")
                
            next_seq_num += 1

        # 2. Esperar ACK/NAK
        try:
            ack_recebido = funcoes.receber_mensagem_criptografada(socket_conexao, chave_simetrica)
            if not ack_recebido:
                raise ConnectionError("Servidor desconectou.")

            print(f"[SERVIDOR→CLIENTE] Recebido: '{ack_recebido}'")

            if ack_recebido.startswith("NAK:"):
                seq_num = int(ack_recebido.split(':')[1])
                print(f"[CONTROLE] NAK recebido para {seq_num}. Retransmitindo janela.")
                socket_conexao.settimeout(None)
                next_seq_num = base # Go-Back-N: volta tudo
                continue

            elif ack_recebido.startswith("ACK:"):
                seq_num_ack = int(ack_recebido.split(':')[1])
                base = seq_num_ack + 1
                print(f"[CONTROLE] ACK:{seq_num_ack}. Nova base: {base}")

                if base == next_seq_num:
                    socket_conexao.settimeout(None)
                else:
                    socket_conexao.settimeout(TIMEOUT_SEGUNDOS)

        except socket.timeout:
            print(f"[ERRO/TIMEOUT] ACK não recebido para base {base}. Retransmitindo janela.")
            socket_conexao.settimeout(None)
            next_seq_num = base


def enviar_segmentos_SR(segmentos, janela, socket_conexao, chave_simetrica, seq_erro_chk=-1, seq_erro_perda=-1):
    """Implementa Selective Repeat com injeção de falhas."""
    base = 0
    next_seq_num = 0
    N = janela
    num_segmentos = len(segmentos)
    
    pacotes_em_transito = {} # {seq: (timestamp, pacote_pronto, payload_orig)}
    erros_chk_pendentes = {seq_erro_chk}
    erros_perda_pendentes = {seq_erro_perda}
    
    socket_conexao.settimeout(0.1) 
    
    while base < num_segmentos:
        agora = time.time()

        # 1. Enviar pacotes novos
        while next_seq_num < base + N and next_seq_num < num_segmentos:
            payload = segmentos[next_seq_num]
            payload_bytes = payload.encode('utf-8')
            checksum = funcoes.calcular_checksum(payload_bytes)

            # Simulação Checksum
            if next_seq_num in erros_chk_pendentes:
                print(f"[SIMULAÇÃO] Corrompendo checksum do pacote {next_seq_num}!")
                checksum += 1337
                erros_chk_pendentes.remove(next_seq_num)

            pacote_para_enviar = f"{next_seq_num}:{checksum}:{payload}"
            
            # Guardamos no buffer de trânsito ANTES de enviar (para o timer funcionar mesmo se perder)
            pacotes_em_transito[next_seq_num] = (agora, pacote_para_enviar, payload)

            # Simulação Perda
            if next_seq_num in erros_perda_pendentes:
                print(f"[SIMULAÇÃO] PACOTE {next_seq_num} PERDIDO NA REDE (Não enviado)!")
                erros_perda_pendentes.remove(next_seq_num)
            else:
                funcoes.mandar_mensagem_criptografada(pacote_para_enviar, socket_conexao, chave_simetrica)
                print(f"[CLIENTE→SERVIDOR/SR] Pacote {next_seq_num} enviado.")
            
            next_seq_num += 1

        # 2. Verificar ACKs/NAKs
        try:
            resposta = funcoes.receber_mensagem_criptografada(socket_conexao, chave_simetrica)
            if resposta:
                print(f"[SERVIDOR→CLIENTE/SR] Recebido: '{resposta}'")

                if resposta.startswith("ACK:"):
                    seq_ack = int(resposta.split(':')[1])
                    if seq_ack in pacotes_em_transito:
                        del pacotes_em_transito[seq_ack]
                    
                    # Avança a base
                    if seq_ack == base:
                        while base < num_segmentos and base not in pacotes_em_transito:
                            if base >= next_seq_num: break
                            base += 1

                elif resposta.startswith("NAK:"):
                    seq_nak = int(resposta.split(':')[1])
                    print(f"[CONTROLE/SR] NAK para {seq_nak}. Retransmitindo corrigido.")
                    if seq_nak in pacotes_em_transito:
                        # Reconstrói pacote limpo
                        _, _, pl_orig = pacotes_em_transito[seq_nak]
                        chk_new = funcoes.calcular_checksum(pl_orig.encode('utf-8'))
                        pkt_new = f"{seq_nak}:{chk_new}:{pl_orig}"
                        
                        funcoes.mandar_mensagem_criptografada(pkt_new, socket_conexao, chave_simetrica)
                        pacotes_em_transito[seq_nak] = (agora, pkt_new, pl_orig)

        except socket.timeout:
            pass

        # 3. Verificar timeouts
        for seq, (timestamp, _, payload_orig) in list(pacotes_em_transito.items()):
            if agora - timestamp > TIMEOUT_SEGUNDOS:
                print(f"[ERRO/TIMEOUT/SR] Pacote {seq} expirou timer. Retransmitindo.")
                
                # Sempre retransmite LIMPO após timeout
                chk_clean = funcoes.calcular_checksum(payload_orig.encode('utf-8'))
                pkt_clean = f"{seq}:{chk_clean}:{payload_orig}"
                
                if seq < base + N:
                    funcoes.mandar_mensagem_criptografada(pkt_clean, socket_conexao, chave_simetrica)
                    pacotes_em_transito[seq] = (agora, pkt_clean, payload_orig)

    socket_conexao.settimeout(None)

# ===================== FUNÇÕES AUXILIARES =====================

def realizar_handshake(socket_conexao, chave_simetrica, modo_escolhido, tamanho_max):
    """Faz o handshake com o modo escolhido pelo usuário."""
    print(f"\n--- Iniciando Handshake ({modo_escolhido}) ---")
    msg = f"MODO:{modo_escolhido};TAMANHO_MAXIMO:{tamanho_max}"
    funcoes.mandar_mensagem_criptografada(msg, socket_conexao, chave_simetrica)
    
    resposta = funcoes.receber_mensagem_criptografada(socket_conexao, chave_simetrica)
    return resposta, interpretar_handshake(resposta)

def interpretar_handshake(resposta_servidor):
    parametros = {}
    if not resposta_servidor: return parameters
    partes = resposta_servidor.split(';')
    for parte in partes:
        if '=' in parte:
            chave, valor = parte.split('=', 1)
            parametros[chave] = valor
    return parametros

# ===================== MAIN =====================

def main():
    print("--- Aplicação Cliente ---")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            print(f"Conectando ao servidor em {HOST}:{PORT}...")
            s.connect((HOST, PORT))
            chave_simetrica = s.recv(1024)
            print("Conectado e chave recebida.")

            # --- ETAPA 1: ESCOLHA DO MODO (Handshake) ---
            print("\nSelecione o Protocolo de Transporte:")
            print("1 - Go-Back-N (GBN)")
            print("2 - Selective Repeat (SR)")
            opcao_modo = input("Opção: ")
            
            modo_str = "SR" if opcao_modo == "2" else "GBN"
            
            # Realiza o handshake com o modo escolhido
            resposta_hs, parametros = realizar_handshake(s, chave_simetrica, modo_str, 500)
            
            if "STATUS" not in parametros or parametros["STATUS"] not in ("OK", "ADJUSTED"):
                raise ConnectionError("Handshake falhou.")

            payload_tam = int(parametros["PAYLOAD"])
            janela = int(parametros["WINDOW"])
            
            print(f"Servidor aceitou modo: {parametros['MODE']}")
            print(f"Tamanho Payload: {payload_tam} | Janela: {janela}")

            # --- ETAPA 2: LOOP DE MENSAGENS ---
            while True:
                print("\n" + "="*40)
                msg = input("Digite a mensagem (ou 'end' para sair): ")
                if msg.lower() == 'end': break

                segmentos = [msg[i:i+payload_tam] for i in range(0, len(msg), payload_tam)]
                qtd_pcts = len(segmentos)
                print(f"Mensagem terá {qtd_pcts} pacotes (IDs 0 a {qtd_pcts-1}).")

                # --- ESCOLHA DE FALHAS ---
                seq_erro_chk = -1
                seq_erro_perda = -1
                
                print("\nDeseja simular falha nesta transmissão?")
                print("0 - Nenhuma (Envio Perfeito)")
                print("1 - Erro de Checksum (Integridade)")
                print("2 - Perda de Pacote (Timeout)")
                opcao_erro = input("Opção: ")

                if opcao_erro == "1":
                    try:
                        seq_erro_chk = int(input(f"Qual ID corromper (0-{qtd_pcts-1})? "))
                    except: pass
                elif opcao_erro == "2":
                    try:
                        seq_erro_perda = int(input(f"Qual ID perder (0-{qtd_pcts-1})? "))
                    except: pass

                # --- ENVIO ---
                print(f"\nIniciando envio via {modo_str}...")
                
                if modo_str == "GBN":
                    enviar_segmentos_GBN(segmentos, janela, s, chave_simetrica, 
                                         seq_erro_chk=seq_erro_chk, 
                                         seq_erro_perda=seq_erro_perda)
                else:
                    enviar_segmentos_SR(segmentos, janela, s, chave_simetrica, 
                                        seq_erro_chk=seq_erro_chk, 
                                        seq_erro_perda=seq_erro_perda)

                funcoes.mandar_mensagem_criptografada("FIM", s, chave_simetrica)
                print("--- Transmissão Finalizada ---")

        except Exception as e:
            print(f"Erro fatal: {e}")

if __name__ == "__main__":
    main()