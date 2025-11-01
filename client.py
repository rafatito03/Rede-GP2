import socket
import funcoes

# ===================== CONFIGURAÇÕES =====================
HOST = '127.0.0.1'
PORT = 65432
modo_de_operacao_escolhido = "GBN"
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
                enviar_segmentos_GBN(segmentos, janela, s, chave_simetrica)

                funcoes.mandar_mensagem_criptografada("FIM", s, chave_simetrica)
                print("--- Transmissão finalizada ---")

        except Exception as e:
            print(f"Erro: {e}")

    print("Cliente finalizado.")

if __name__ == "__main__":
    main()
