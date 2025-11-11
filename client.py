import socket
import funcoes
import time

# ===================== CONFIGURAÇÕES =====================
HOST = '127.0.0.1'
PORT = 65432
modo_de_operacao_escolhido = "SR"
tamanho_maximo_da_comunicacao = 500
TIMEOUT_SEGUNDOS = 3

# ===================== FUNÇÕES AUXILIARES =====================


def realizar_handshake(socket_conexao, chave_simetrica):
    """Envia e processa o handshake com o servidor."""
    mensagem_handshake = f"MODO:{modo_de_operacao_escolhido};TAMANHO_MAXIMO:{tamanho_maximo_da_comunicacao}"
    funcoes.mandar_mensagem_criptografada(mensagem_handshake, socket_conexao, chave_simetrica)
    print("[CLIENTE→SERVIDOR] Handshake enviado.")
    
    resposta = funcoes.receber_mensagem_criptografada(socket_conexao, chave_simetrica)
    if resposta is None:
        raise ConnectionError("Servidor fechou a conexão durante o handshake.")
    print(f"[SERVIDOR→CLIENTE] Handshake recebido: '{resposta}'")
    return resposta

def interpretar_handshake(resposta_servidor):
    """Interpreta os parâmetros recebidos no handshake do servidor."""
    parametros = {}
    partes = resposta_servidor.split(';')
    for parte in partes:
        if '=' in parte:
            chave, valor = parte.split('=', 1)
            parametros[chave] = valor
    return parametros

def enviar_segmentos_GBN(segmentos, janela, socket_conexao, chave_simetrica):
    """Implementa o envio Go-Back-N."""
    base = 0
    next_seq_num = 0
    N = janela
    num_segmentos = len(segmentos)

    while base < num_segmentos:
        # Enviar pacotes dentro da janela
        while next_seq_num < base + N and next_seq_num < num_segmentos:
            payload = segmentos[next_seq_num]
            payload_bytes = payload.encode('utf-8')
            checksum = funcoes.calcular_checksum(payload_bytes)
            pacote_para_enviar = f"{next_seq_num}:{checksum}:{payload}"
            funcoes.mandar_mensagem_criptografada(pacote_para_enviar, socket_conexao, chave_simetrica)
            print(f"[CLIENTE→SERVIDOR] Pacote {next_seq_num} enviado [Chk={checksum}, Carga='{payload}']")
            if base == next_seq_num:
                socket_conexao.settimeout(TIMEOUT_SEGUNDOS)
                print(f"[TIMER] Iniciado para base {base}.")
            next_seq_num += 1

        # Esperar ACK/NAK
        try:
            ack_recebido = funcoes.receber_mensagem_criptografada(socket_conexao, chave_simetrica)
            if not ack_recebido:
                raise ConnectionError("Servidor desconectou.")

            print(f"[SERVIDOR→CLIENTE] Recebido: '{ack_recebido}'")

            if ack_recebido.startswith("NAK:"):
                seq_num = int(ack_recebido.split(':')[1])
                print(f"[CONTROLE] NAK para {seq_num}. Retransmitindo janela.")
                socket_conexao.settimeout(None)
                next_seq_num = base
                continue

            elif ack_recebido.startswith("ACK:"):
                seq_num_ack = int(ack_recebido.split(':')[1])
                base = seq_num_ack + 1
                print(f"[CONTROLE] ACK:{seq_num_ack}. Nova base: {base}")

                if base == next_seq_num:
                    socket_conexao.settimeout(None)
                    print("[TIMER] Parado. Janela confirmada.")
                else:
                    socket_conexao.settimeout(TIMEOUT_SEGUNDOS)
                    print(f"[TIMER] Reiniciado para base {base}.")

            else:
                print(f"[AVISO] Formato inesperado de ACK: '{ack_recebido}'")

        except socket.timeout:
            print(f"[ERRO/TIMEOUT] ACK não recebido para base {base}. Retransmitindo janela.")
            socket_conexao.settimeout(None)
            next_seq_num = base


def enviar_segmentos_SR(segmentos, janela, socket_conexao, chave_simetrica):
    """Implementa o envio Selective Repeat."""
    base = 0
    next_seq_num = 0
    N = janela
    num_segmentos = len(segmentos)
    
    # Dicionário de pacotes enviados mas não confirmados
    # Formato: {seq: (timestamp, pacote_str)}
    pacotes_em_transito = {}
    
    # Define um timeout curto para o socket não bloquear o loop
    socket_conexao.settimeout(0.1) # 100ms
    
    while base < num_segmentos:
        agora = time.time()

        # 1. Enviar pacotes novos (se a janela permitir)
        while next_seq_num < base + N and next_seq_num < num_segmentos:
            payload = segmentos[next_seq_num]
            payload_bytes = payload.encode('utf-8')
            checksum = funcoes.calcular_checksum(payload_bytes)
            pacote_para_enviar = f"{next_seq_num}:{checksum}:{payload}"
            
            funcoes.mandar_mensagem_criptografada(pacote_para_enviar, socket_conexao, chave_simetrica)
            print(f"[CLIENTE→SERVIDOR/SR] Pacote {next_seq_num} enviado [Chk={checksum}]")
            
            # Armazena para timer e retransmissão
            pacotes_em_transito[next_seq_num] = (agora, pacote_para_enviar)
            next_seq_num += 1

        # 2. Verificar ACKs/NAKs recebidos
        try:
            resposta = funcoes.receber_mensagem_criptografada(socket_conexao, chave_simetrica)
            if not resposta:
                raise ConnectionError("Servidor desconectou.")

            print(f"[SERVIDOR→CLIENTE/SR] Recebido: '{resposta}'")

            if resposta.startswith("ACK:"):
                seq_ack = int(resposta.split(':')[1])
                
                # Se o ACK é para um pacote em trânsito, remova-o
                if seq_ack in pacotes_em_transito:
                    del pacotes_em_transito[seq_ack]
                    print(f"[CONTROLE/SR] ACK {seq_ack} confirmado.")
                
                # Tenta avançar a base (o ponto inicial da janela)
                if seq_ack == base:
                    # Avança a base para o primeiro pacote ainda não confirmado
                    while base < num_segmentos and base not in pacotes_em_transito:
                        if base >= next_seq_num: break
                        base += 1
                    print(f"[CONTROLE/SR] Nova base: {base}")

            elif resposta.startswith("NAK:"):
                seq_nak = int(resposta.split(':')[1])
                if seq_nak in pacotes_em_transito:
                    print(f"[CONTROLE/SR] NAK para {seq_nak}. Retransmitindo imediatamente.")
                    _, pacote_str = pacotes_em_transito[seq_nak]
                    funcoes.mandar_mensagem_criptografada(pacote_str, socket_conexao, chave_simetrica)
                    # Resetar o timer
                    pacotes_em_transito[seq_nak] = (agora, pacote_str)

        except socket.timeout:
            # Isso é normal e esperado! Significa que não há ACKs/NAKs no buffer.
            pass
        except Exception as e:
            print(f"Erro ao receber ACK: {e}")
            break

        # 3. Verificar timeouts (retransmissão seletiva)
        # É importante usar list() para poder modificar o dicionário durante a iteração
        for seq, (timestamp, pacote_str) in list(pacotes_em_transito.items()):
            if agora - timestamp > TIMEOUT_SEGUNDOS:
                if seq < base + N: # Apenas retransmite se ainda estiver na janela
                    print(f"[ERRO/TIMEOUT/SR] Pacote {seq} estourou. Retransmitindo.")
                    funcoes.mandar_mensagem_criptografada(pacote_str, socket_conexao, chave_simetrica)
                    # Resetar o timer
                    pacotes_em_transito[seq] = (agora, pacote_str)

    # Fim do loop, restaura o timeout normal (bloqueante)
    socket_conexao.settimeout(None)



def main():
    print("--- Aplicação Cliente ---")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            print(f"Conectando ao servidor em {HOST}:{PORT}...")
            s.connect((HOST, PORT))
            print("Conectado com sucesso.")

            chave_simetrica = s.recv(1024)
            if not chave_simetrica:
                raise ConnectionError("Não foi possível receber a chave do servidor.")
            print("Chave de criptografia recebida.")

            resposta = realizar_handshake(s, chave_simetrica)
            parametros = interpretar_handshake(resposta)

            if "STATUS" not in parametros or parametros["STATUS"] not in ("OK", "ADJUSTED"):
                raise ConnectionError(f"Servidor rejeitou o handshake. Motivo: {parametros.get('REASON', 'DESCONHECIDO')}")

            payload_tam = int(parametros["PAYLOAD"])
            max_tam = int(parametros["MAX"])
            janela = int(parametros["WINDOW"])

            print("\n--- Handshake com servidor bem-sucedido ---")
            print(f"Modo: {parametros['MODE']}")
            print(f"Tamanho Máximo: {max_tam}")
            print(f"Payload: {payload_tam}")
            print(f"Janela: {janela}")

            while True:
                msg = input("\nDigite a mensagem (ou 'end' para sair): ")
                if msg.lower() == 'end':
                    print("Encerrando comunicação.")
                    break

                if len(msg) > max_tam:
                    print(f"Mensagem excede o máximo ({len(msg)}>{max_tam}).")
                    continue

                segmentos = [msg[i:i+payload_tam] for i in range(0, len(msg), payload_tam)]
                print(f"Mensagem dividida em {len(segmentos)} pacotes. Enviando...")
                modo_operacao = parametros.get("MODE", "GBN") # Pega o modo do handshake
                
                if modo_operacao == "GBN":
                    enviar_segmentos_GBN(segmentos, janela, s, chave_simetrica)
                elif modo_operacao == "SR":
                    enviar_segmentos_SR(segmentos, janela, s, chave_simetrica)
                else:
                    print(f"ERRO: Modo '{modo_operacao}' desconhecido. Usando GBN por padrão.")
                    enviar_segmentos_GBN(segmentos, janela, s, chave_simetrica)

                funcoes.mandar_mensagem_criptografada("FIM", s, chave_simetrica)
                print("--- Transmissão finalizada ---")

        except Exception as e:
            print(f"Erro: {e}")

    print("Cliente finalizado.")

if __name__ == "__main__":
    main()
