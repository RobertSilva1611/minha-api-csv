from fastapi import FastAPI, HTTPException
import pandas as pd
import os

app = FastAPI(title="API Leitora de CSV")

# --- CONFIGURAÇÃO ---
# Defina aqui o caminho da pasta e o nome do arquivo
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))  # Exemplo: pasta 'dados' no mesmo local do script
NOME_ARQUIVO = "Dados_API.csv"

def obter_caminho_completo():
    return os.path.join(PASTA_ATUAL, NOME_ARQUIVO)

@app.get("/")
def home():
    return {"mensagem": "API Online! Acesse /dados para ver o CSV."}

@app.get("/dados")
def ler_csv():
    caminho = obter_caminho_completo()
    
    if not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado em: {caminho}")
    
    try:
        # Lê o CSV usando Pandas
        df = pd.read_csv(caminho, sep=";", encoding="utf-8-sig")
        
        # Converte para dicionário (JSON)
        # 'records' cria uma lista de objetos: [{col1: val1}, {col1: val2}...]
        dados_json = df.to_dict(orient="records")
        return dados_json
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler o CSV: {str(e)}")

# Endpoint para filtrar (Opcional)
@app.get("/dados/{coluna}/{valor}")
def filtrar_csv(coluna: str, valor: str):
    caminho = obter_caminho_completo()
    df = pd.read_csv(caminho, sep=";", encoding="utf-8-sig")
    
    if coluna not in df.columns:
        raise HTTPException(status_code=400, detail="Coluna não existe")
    
    # Filtra o dataframe
    df_filtrado = df[df[coluna].astype(str) == valor]
    return df_filtrado.to_dict(orient="records")