# Rede-GP2

Instruções para configurar e executar o projeto.

---

## 1. Pré-requisitos

* Python 3.x instalado.

---

## 2. Configuração do Ambiente

Siga os passos abaixo no seu terminal:

1.  **Acesse o diretório do projeto:**
    ```bash
    cd Rede-GP2
    ```

2.  **Crie um ambiente virtual (venv):**
    * Use `python3` (recomendado para Linux/macOS):
        ```bash
        python3 -m venv venv
        ```
    * Ou `python` (comum no Windows):
        ```bash
        python -m venv venv
        ```

3.  **Ative o ambiente virtual:**
    * **No Windows (CMD/PowerShell):**
        ```bash
        .\venv\Scripts\activate
        ```
    * **No macOS ou Linux (bash/zsh):**
        ```bash
        source venv/bin/activate
        ```
    *Seu terminal deve agora mostrar `(venv)` antes do prompt.*

4.  **Instale as dependências necessárias:**
    ```bash
    pip install cryptography
    ```

---

## 3. Como Executar

Para rodar a aplicação, você precisará de **dois terminais separados**, ambos com o ambiente virtual ativado (como no passo 2.3).

1.  **Terminal 1 (Servidor):**
    Inicie o servidor primeiro.
    ```bash
    python server.py
    ```

2.  **Terminal 2 (Cliente):**
    Com o servidor rodando, inicie o cliente no outro terminal.
    ```bash
    python client.py
    ```
