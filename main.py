from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import secrets
import os
from datetime import datetime, timedelta

app = FastAPI(title="API Faturamento Segura")

# --- CONFIGURAÇÕES (Use variáveis de ambiente na vida real) ---
MEU_EMAIL = "seu_email@gmail.com"  # <--- COLOQUE SEU EMAIL AQUI
MINHA_SENHA_APP = "sua_senha_de_app_aqui"  # <--- COLOQUE A SENHA DE APP AQUI
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Onde vamos salvar o CSV que chegar da sua máquina
ARQUIVO_TEMPORARIO = "faturamento_nuvem.csv"

# --- BANCO DE DADOS EM MEMÓRIA ---
usuarios_db = {}       # {email: senha}
codigos_otp = {}       # {email: codigo_1234}
tokens_ativos = {}     # {token: email}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- FUNÇÕES DE EMAIL ---
def enviar_email_codigo(para_email, codigo):
    msg = MIMEText(f"Seu código de acesso é: {codigo}")
    msg['Subject'] = "Código de Verificação API"
    msg['From'] = MEU_EMAIL
    msg['To'] = para_email

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(MEU_EMAIL, MINHA_SENHA_APP)
        server.sendmail(MEU_EMAIL, para_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False

# --- ROTAS DE AUTENTICAÇÃO ---

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

@app.post("/1-login-senha")
def passo1_login(dados: LoginRequest):
    # Aqui você pode colocar uma senha fixa para só você acessar, 
    # ou verificar no usuarios_db se quiser multi-usuários.
    if dados.senha != "senha_da_empresa_123": # Senha mestra simples
        raise HTTPException(status_code=401, detail="Senha incorreta")
    
    # Gera código de 6 dígitos
    codigo = secrets.token_hex(3).upper()
    codigos_otp[dados.email] = codigo
    
    # Envia email
    sucesso = enviar_email_codigo(dados.email, codigo)
    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao enviar email. Veja os logs.")
        
    return {"mensagem": f"Código enviado para {dados.email}. Vá para o passo 2."}

@app.post("/2-validar-codigo")
def passo2_validar(email: str, codigo: str):
    if email not in codigos_otp or codigos_otp[email] != codigo:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado")
    
    # Gera o Token Final (Bearer)
    token_final = secrets.token_hex(16)
    tokens_ativos[token_final] = email
    
    # Limpa o código usado
    del codigos_otp[email]
    
    return {"access_token": token_final, "token_type": "bearer"}

# Validador de Token para as rotas protegidas
def pegar_usuario_logado(token: str = Depends(oauth2_scheme)):
    if token not in tokens_ativos:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    return tokens_ativos[token]

# --- ROTA DE ATUALIZAÇÃO (Onde seu PC vai jogar os dados) ---
# Protegemos com uma senha especial de "admin" no header para o script local usar
@app.post("/atualizar-dados-sistema")
def receber_csv_local(file: UploadFile = File(...), senha_admin: str = Form(...)):
    if senha_admin != "senha_super_secreta_do_script":
        raise HTTPException(status_code=401, detail="Não autorizado")
    
    # Salva o arquivo que veio do upload
    with open(ARQUIVO_TEMPORARIO, "wb") as buffer:
        buffer.write(file.file.read())
        
    return {"status": "Dados atualizados com sucesso na nuvem!"}

# --- ROTA DE LEITURA (Pública para quem tem token) ---
@app.get("/dados-faturamento")
def ler_dados(usuario: str = Depends(pegar_usuario_logado)):
    if not os.path.exists(ARQUIVO_TEMPORARIO):
        return {"aviso": "Nenhum dado enviado pelo sistema local ainda."}
    
    try:
        df = pd.read_csv(ARQUIVO_TEMPORARIO, sep=";", encoding="utf-8-sig")
        return df.to_dict(orient="records")
    except Exception as e:
        return {"erro": str(e)}