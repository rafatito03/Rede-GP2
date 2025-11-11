import socket
import funcoes
from crypto import gerar_chave

# ===================== CONFIGURAÇÕES =====================
HOST = '127.0.0.1'
PORT = 65432
TAMANHO_PAYLOAD_SERVIDOR = 4
TAMANHO_JANELA = 5
TAMANHO_MINIMO_MSG = 30

# ===================== FUNÇÕES AUXILIARES =====================



def processar_handshake(mensagem, chave, conn):
    """Processa a mensagem de handshake do cliente."""
    partes = mensagem.split(';')
    modo = partes[0].split(':')[1]
    tamanho = int(partes[1].split(':')[1])
    print(f"[HANDSHAKE] Cliente solicitou modo {modo}, tamanho máximo {tamanho}")

    status = "OK"
    motivo = "N/A"

    if tamanho < TAMANHO_MINIMO_MSG:
        tamanho_final = TAMANHO_MINIMO_MSG
        status = "ADJUSTED"
        motivo = "MAX_SIZE_TOO_SMALL"
        print(f"[HANDSHAKE] Tamanho ajustado para {tamanho_final}")
    else:
        tamanho_final = tamanho

    resposta = (
        f"HELLO-ACK;"
        f"MODE={modo};"
        f"MAX={tamanho_final};"
        f"PAYLOAD={TAMANHO_PAYLOAD_SERVIDOR};"
        f"WINDOW={TAMANHO_JANELA};"
        f"STATUS={status};"
        f"REASON={motivo}"
    )
    funcoes.mandar_mensagem_criptografada(resposta, conn, chave)
    print("[SERVIDOR→CLIENTE] Resposta de handshake enviada.")
    return modo, tamanho_final

def processar_pacote_gbn(seq, payload, seq_esperado, chave, conn):
    """Processa um pacote GBN (checksum JÁ VALIDADO).
    Retorna (novo_seq_esperado, payload_pronto)."""
    
    print(f"[PROCESSAR/GBN] Pacote {seq}, esperando {seq_esperado}")
    
    if seq == seq_esperado:
        # Pacote esperado, envia ACK cumulativo
        funcoes.mandar_mensagem_criptografada(f"ACK:{seq}", conn, chave)
        print(f"[SERVIDOR→CLIENTE] ACK (GBN) enviado para {seq}")
        # Avança a base e retorna o payload para entrega
        return seq_esperado + 1, payload
    else:
        # Pacote fora de ordem, descarta
        print(f"[AVISO/GBN] Pacote fora de ordem. Esperado {seq_esperado}, recebido {seq}.")
        if seq_esperado > 0:
            # Re-envia ACK do último pacote correto
            funcoes.mandar_mensagem_criptografada(f"ACK:{seq_esperado-1}", conn, chave)
            print(f"[SERVIDOR→CLIENTE] ACK (GBN) reenviado para {seq_esperado-1}")
        # Base não avança, nada é entregue
        return seq_esperado, None

def processar_pacote_sr(seq, payload, seq_esperado, buffer_pacotes, chave, conn):
    """Processa um pacote SR (checksum JÁ VALIDADO).
    Retorna (novo_seq_esperado, lista_payloads_prontos)."""
    
    print(f"[PROCESSAR/SR] Pacote {seq}, esperando {seq_esperado}")

    # 1. Envia ACK individual para CADA pacote válido recebido
    # (Mesmo que seja duplicado, a especificação SR geralmente re-ACK)
    funcoes.mandar_mensagem_criptografada(f"ACK:{seq}", conn, chave)
    print(f"[SERVIDOR→CLIENTE] ACK (SR) enviado para {seq}")

    payloads_prontos = []

    if seq == seq_esperado:
        # Pacote esperado. Entrega ele e verifica o buffer.
        payloads_prontos.append(payload)
        seq_esperado += 1
        
        # Libera pacotes do buffer
        while seq_esperado in buffer_pacotes:
            print(f"[BUFFER/SR] Liberando pacote {seq_esperado} do buffer.")
            payloads_prontos.append(buffer_pacotes[seq_esperado])
            del buffer_pacotes[seq_esperado]
            seq_esperado += 1
        
        return seq_esperado, payloads_prontos

    elif seq > seq_esperado:
        # Pacote fora de ordem (adiantado). Armazena no buffer.
        if seq not in buffer_pacotes:
            print(f"[BUFFER/SR] Pacote {seq} armazenado (esperando {seq_esperado}).")
            buffer_pacotes[seq] = payload
        # Base não avança, mas retorna lista vazia
        return seq_esperado, [] 

    else: # seq < seq_esperado
        # Pacote antigo, já foi confirmado. O ACK já foi enviado.
        print(f"[AVISO/SR] Pacote {seq} duplicado recebido.")
        return seq_esperado, []

def main():
    print("--- Aplicação Servidor ---")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor escutando em {HOST}:{PORT}")

        conn, addr = s.accept()
        with conn:
            print(f"Cliente conectado: {addr}")

            chave = gerar_chave()
            conn.sendall(chave)
            print("Chave de criptografia enviada.")

            handshake = funcoes.receber_mensagem_criptografada(conn, chave)
            if handshake is None:
                print("Cliente desconectou no handshake.")
                return

            modo, tamanho_final = processar_handshake(handshake, chave, conn)

            while True:
                print(f"\n[Aguardando nova transmissão no modo: {modo}]")
                mensagem_final_ordenada = []
                buffer_pacotes = {} # Usado apenas por SR
                seq_esperado = 0

                while True:
                    pacote = funcoes.receber_mensagem_criptografada(conn, chave)
                    if pacote is None:
                        return
                    if pacote == "FIM":
                        break

                    # --- 1. Bloco de Validação Comum ---
                    partes = pacote.split(':', 2)
                    if len(partes) != 3:
                        print(f"[ERRO] Pacote mal formatado: '{pacote}'")
                        continue # Pede o próximo pacote

                    seq, chk, payload = int(partes[0]), int(partes[1]), partes[2]
                    payload_bytes = payload.encode('utf-8')

                    if not funcoes.verificar_checksum(payload_bytes, chk):
                        print(f"[ERRO] Checksum inválido no pacote {seq}.")
                        # Envia NAK (comum a GBN e SR)
                        funcoes.mandar_mensagem_criptografada(f"NAK:{seq}", conn, chave)
                        print(f"[SERVIDOR→CLIENTE] NAK enviado para {seq}")
                        continue # Pede o próximo pacote
                    
                    # --- 2. Delegação da Lógica do Protocolo ---
                    
                    payloads_prontos = []
                    
                    if modo == "GBN":
                        seq_esperado, payload_pronto = processar_pacote_gbn(
                            seq, payload, seq_esperado, chave, conn
                        )
                        if payload_pronto:
                            payloads_prontos.append(payload_pronto)
                    
                    elif modo == "SR":
                        seq_esperado, payloads_prontos_sr = processar_pacote_sr(
                            seq, payload, seq_esperado, buffer_pacotes, chave, conn
                        )
                        payloads_prontos.extend(payloads_prontos_sr)

                    # --- 3. Entrega na Aplicação ---
                    if payloads_prontos:
                        mensagem_final_ordenada.extend(payloads_prontos)

                if mensagem_final_ordenada:
                    texto_final = "".join(mensagem_final_ordenada)
                    print("\n--- Comunicação completa recebida ---")
                    print(f"Mensagem reconstruída: '{texto_final}'")
                    if modo == "SR":
                        print(f"Buffer restante (deve estar vazio): {buffer_pacotes}")

            print("Conexão encerrada.")

if __name__ == "__main__":
    main()
