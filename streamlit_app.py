import streamlit as st
import fitz
import pandas as pd
import json
import requests
from openai import OpenAI

# Inicialize o cliente OpenAI (Certifique-se de configurar sua chave de API)
client = OpenAI(api_key="SUA_CHAVE_API_OPENAI")

# ==========================================
# FUNÇÃO DE EXTRAÇÃO VIA IA
# ==========================================
def extrair_dados_com_ia(texto_pdf):
    prompt = f"""
    Você é um assistente especialista em contabilidade e extração de dados de notas fiscais brasileiras (DANFE e NFS-e).
    Analise o texto da nota fiscal abaixo e extraia os itens faturados (produtos ou serviços).
    
    Retorne APENAS um array JSON válido contendo objetos com as seguintes chaves exatas:
    - "empresa": Nome da empresa emitente/prestadora.
    - "cnpj": CNPJ da empresa emitente.
    - "data": Data de emissão (DD/MM/AAAA).
    - "codigo": Código do produto ou serviço (se não houver, use "N/I").
    - "descricao": Descrição detalhada do produto ou serviço.
    - "ncm": NCM do produto (se não houver, use "N/I").
    - "cst": CST ou CSOSN (se não houver, use "N/I").
    - "cfop": CFOP (se não houver, use "N/I").
    - "unidade": Unidade de medida (ex: UN, KG, PC).
    - "quantidade": Quantidade como string numérica (ex: "1", "10").
    - "vlr_unitario": Valor unitário como string (ex: "27,30").
    - "vlr_total": Valor total do item como string (ex: "1.365,00").
    - "frete": Valor do frete da nota se houver, caso contrário "0,00".

    Texto da Nota Fiscal:
    {texto_pdf}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Ou outro modelo compatível com JSON mode
            messages=[
                {"role": "system", "content": "Você extrai dados estruturados de notas fiscais e responde estritamente em JSON válido."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        conteudo = response.choices[0].message.content
        dados = json.loads(conteudo)
        
        # Garante que a resposta seja tratada como lista
        if isinstance(dados, dict):
            # Procura pela primeira chave que contenha uma lista
            for chave, valor in dados.items():
                if isinstance(valor, list):
                    return valor
            return [dados]
        return dados
    except Exception as e:
        st.error(f"Erro ao processar com a IA: {e}")
        return []

# ==========================================
# NO LOOP DE PROCESSAMENTO DO SEU STREAMLIT
# ==========================================
if arquivos_pdf:
    with st.spinner("Analisando notas fiscais com Inteligência Artificial..."):
        todos_itens = []

        for arquivo_pdf in arquivos_pdf:
            texto_completo = ""
            try:
                arquivo_pdf.seek(0)
                pdf = fitz.open(stream=arquivo_pdf.read(), filetype="pdf")
                for pagina in pdf:
                    texto_completo += pagina.get_text() + "\n"
                pdf.close()
            except Exception as e:
                st.error(f"Erro ao ler o arquivo {arquivo_pdf.name}: {e}")
                continue

            # Chama a IA para extrair os itens sem usar Regex
            itens_extraidos = extrair_dados_com_ia(texto_completo)

            for item in itens_extraidos:
                item["arquivo"] = arquivo_pdf.name
                todos_itens.append(item)

        if len(todos_itens) > 0:
            df = pd.DataFrame(todos_itens)
            # Restante do seu código para exibir o DataFrame, gerar CSV e enviar ao Power Automate...
