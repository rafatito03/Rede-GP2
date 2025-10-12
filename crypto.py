from cryptography.fernet import Fernet

def gerar_chave():
    return Fernet.generate_key()

def criptografar_mensagem(mensagem_bytes, chave):
    f = Fernet(chave)
    return f.encrypt(mensagem_bytes)

def descriptografar_mensagem(token_criptografado, chave):
    f = Fernet(chave)
    return f.decrypt(token_criptografado)