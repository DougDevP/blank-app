import streamlit as st
import fitz
import pandas as pd
import json
import requests
import time
import google.generativeai as genai

# ==========================================
# CONFIGURAÇÃO DA API DO GEMINI (COM PROTEÇÃO)
# ==========================================
try:
    # Tenta carregar dos secrets do Streamlit
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = None

if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ Chave 'GEMINI_API_KEY' não encontrada nos segredos do Streamlit. Certifique-se de configurá-la no painel do Streamlit Cloud ou na pasta .streamlit/secrets.toml")
    st.stop()

# ==========================================
# POWER AUTOMATE
# ==========================================

url = "https://defaultca18acb0331244f2869d5b01ed8bb4.7d.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/31/workflows/c8f13fb65dd8488ab9fc574ba13f6f1a/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=4BLzQi7_7vL1gjLfdAsCzJHkmAZKZc1HtYRLGuFy58s"

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================

st.set_page_config(
    page_title="Extrator de Itens - Notas Fiscais via Gemini",
    layout="wide"
)

st.title("📄 Extrator de Itens Faturados (DANFE & NFS-e via Gemini)")
st.write(
    "Extrai produtos, serviços, quantidades, valores, frete e dados gerais de notas fiscais utilizando o Google Gemini."
)

# ==========================================
# UPLOAD
# ==========================================

arquivos_pdf = st.file_uploader(
    "Selecione uma ou mais Notas Fiscais (PDF)",
    type=["pdf"],
    accept_multiple_files=True
)

# ==========================================
# FUNÇÃO DE EXTRAÇÃO VIA GEMINI
# ==========================================
def extrair_dados_com_gemini(texto_pdf):
    prompt = f"""
    Você é um assistente especialista em contabilidade e extração de dados de notas fiscais brasileiras (DANFE e NFS-e).
    Analise o texto completo da nota fiscal abaixo e extraia todos os itens faturados (produtos ou serviços).
    
    Retorne APENAS um JSON válido contendo uma chave "itens" que seja um array de objetos com as seguintes chaves exatas:
    - "empresa": Nome da empresa emitente/prestadora.
    - "cnpj": CNPJ da empresa emitente.
    - "data": Data de emissão no formato DD/MM/AAAA.
    - "codigo": Código do produto ou serviço (se não houver, use "N/I").
    - "descricao": Descrição detalhada do produto ou serviço.
    - "ncm": NCM do produto (se não houver, use "N/I").
    - "cst": CST ou CSOSN (se não houver, use "N/I").
    - "cfop": CFOP (se não houver, use "N/I").
    - "unidade": Unidade de medida (ex: UN, KG, PC).
    - "quantidade": Quantidade como string numérica (ex: "1", "10", "50").
    - "vlr_unitario": Valor unitário como string formatada (ex: "27,30").
    - "vlr_total": Valor total do item como string formatada (ex: "1.365,00").
    - "frete": Valor total do frete da nota se houver, caso contrário "0,00".

    Texto da Nota Fiscal:
    {texto_pdf}
    """

    try:
        # Corrigido para o modelo padrão estável do Gemini
        model = genai.GenerativeModel('gemini-3.7-flash')
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        dados = json.loads(response.text)
        
        if isinstance(dados, dict):
            for chave, valor in dados.items():
                if isinstance(valor, list):
                    return valor
            return [dados]
        elif isinstance(dados, list):
            return dados
        return []
    except Exception as e:
        st.error(f"Erro ao processar com o Gemini: {e}")
        return []

# ==========================================
# PROCESSAMENTO
# ==========================================

if arquivos_pdf:
    with st.spinner("Analisando notas fiscais com o Google Gemini..."):
        todos_itens = []

        for arquivo_pdf in arquivos_pdf:
            texto_completo = ""
            try:
                arquivo_pdf.seek(0)
                pdf = fitz.open(
                    stream=arquivo_pdf.read(),
                    filetype="pdf"
                )
                for pagina in pdf:
                    texto_completo += pagina.get_text() + "\n"
                pdf.close()
            except Exception as e:
                st.error(f"Erro ao ler o ficheiro {arquivo_pdf.name}: {e}")
                continue

            if not texto_completo.strip():
                st.warning(f"O ficheiro {arquivo_pdf.name} não contém texto legível.")
                continue

            itens_extraidos = extrair_dados_com_gemini(texto_completo)

            for item in itens_extraidos:
                item["arquivo"] = arquivo_pdf.name
                
                for chave_padrao in ["empresa", "cnpj", "data", "codigo", "descricao", "ncm", "cst", "cfop", "unidade", "quantidade", "vlr_unitario", "vlr_total", "frete"]:
                    if chave_padrao not in item or not item[chave_padrao]:
                        item[chave_padrao] = "N/I" if chave_padrao in ["codigo", "ncm", "cst", "cfop"] else "0,00"

                todos_itens.append(item)

            # Pausa de 4 segundos para respeitar o limite gratuito de requisições por minuto (RPM)
            time.sleep(4)

        # ==========================================
        # RESULTADO FINAL
        # ==========================================
        if len(todos_itens) > 0:
            df = pd.DataFrame(todos_itens)

            colunas_desejadas = [
                "arquivo", "empresa", "cnpj", "data", "codigo",
                "descricao", "ncm", "cst", "cfop", "unidade",
                "quantidade", "vlr_unitario", "vlr_total", "frete"
            ]
            
            colunas_existentes = [c for c in colunas_desejadas if c in df.columns]
            df = df[colunas_existentes]

            df.columns = [
                "Arquivo", "Empresa", "CNPJ", "Data", "Código",
                "Descrição", "NCM", "CST", "CFOP", "Unidade",
                "Quantidade", "Valor Unitário", "Valor Total", "Frete"
            ]

            st.success(f"Foram encontrados {len(df)} item(ns) em {len(arquivos_pdf)} ficheiro(s) usando o Gemini.")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")

            st.download_button(
                "📥 Baixar CSV Consolidado",
                csv,
                file_name="produtos_notas_fiscais.csv",
                mime="text/csv"
            )

            if st.button("Enviar para SharePoint"):
                payload = df.to_dict(orient="records")
                try:
                    response = requests.post(url, json=payload, timeout=120)
                    if response.status_code in [200, 201, 202]:
                        st.success(f"{len(df)} registos enviados com sucesso.")
                    else:
                        st.error(f"Erro ao enviar. Estado: {response.status_code}")
                        st.text(response.text)
                except Exception as e:
                    st.error(f"Erro na comunicação: {e}")
        else:
            st.warning("Nenhum item encontrado nos ficheiros enviados.")
