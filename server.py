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

def processar_pacote(pacote, seq_esperado, chave, conn):
    """Valida o pacote recebido e retorna o novo número esperado."""
    partes = pacote.split(':', 2)
    if len(partes) != 3:
        print(f"[ERRO] Pacote mal formatado: '{pacote}'")
        return seq_esperado

    seq, chk, payload = int(partes[0]), int(partes[1]), partes[2]
    payload_bytes = payload.encode('utf-8')

    print(f"[CLIENTE→SERVIDOR] Pacote recebido [Seq={seq}, Chk={chk}, Carga='{payload}']")

    if not funcoes.verificar_checksum(payload_bytes, chk):
        print(f"[ERRO] Checksum inválido no pacote {seq}.")
        funcoes.mandar_mensagem_criptografada(f"NAK:{seq}", conn, chave)
        print(f"[SERVIDOR→CLIENTE] NAK enviado para {seq}")
        return seq_esperado

    if seq == seq_esperado:
        funcoes.mandar_mensagem_criptografada(f"ACK:{seq}", conn, chave)
        print(f"[SERVIDOR→CLIENTE] ACK enviado para {seq}")
        return seq_esperado + 1
    else:
        print(f"[AVISO] Pacote fora de ordem. Esperado {seq_esperado}, recebido {seq}.")
        if seq_esperado > 0:
            funcoes.mandar_mensagem_criptografada(f"ACK:{seq_esperado-1}", conn, chave)
            print(f"[SERVIDOR→CLIENTE] ACK reenviado para {seq_esperado-1}")
        return seq_esperado

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
                print("\n[Aguardando nova transmissão]")
                mensagem = []
                seq_esperado = 0

                while True:
                    pacote = funcoes.receber_mensagem_criptografada(conn, chave)
                    if pacote is None:
                        return
                    if pacote == "FIM":
                        break

                    seq_esperado = processar_pacote(pacote, seq_esperado, chave, conn)
                    mensagem.append(pacote.split(':', 2)[2])

                if mensagem:
                    texto_final = "".join(mensagem)
                    print("\n--- Comunicação completa recebida ---")
                    print(f"Mensagem reconstruída: '{texto_final}'")

            print("Conexão encerrada.")

if __name__ == "__main__":
    main()
