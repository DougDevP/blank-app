import streamlit as st
import fitz
import pandas as pd
import re
import requests

# ==========================================
# POWER AUTOMATE
# ==========================================

url = "https://defaultca18acb0331244f2869d5b01ed8bb4.7d.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/31/workflows/c8f13fb65dd8488ab9fc574ba13f6f1a/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=4BLzQi7_7vL1gjLfdAsCzJHkmAZKZc1HtYRLGuFy58s"

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================

st.set_page_config(
    page_title="Extrator de Itens - DANFE",
    layout="wide"
)

st.title("📄 Extrator de Itens Faturados (DANFE)")
st.write(
    "Extrai produtos, quantidades, valores e dados gerais de uma ou mais notas fiscais."
)

# ==========================================
# UPLOAD
# ==========================================

arquivos_pdf = st.file_uploader(
    "Selecione uma ou mais Notas Fiscais",
    type=["pdf"],
    accept_multiple_files=True
)

# ==========================================
# REGEX PRODUTOS (Linha a Linha)
# ==========================================
padrao_item = re.compile(
    r'^(?P<codigo>\d{3,10})\s+'
    r'(?P<descricao>.*?)\s+'
    r'(?P<ncm>\d{8})\s+'
    r'(?P<cst>\d{2,4})?\s*'
    r'(?P<cfop>\d\.?\d{3})\s+'
    r'(?P<unidade>[A-Za-z]{2,4})\s+'
    r'(?P<quantidade>[\d.,]+)\s+'
    r'(?P<vlr_unitario>[\d.,]+)\s+'
    r'(?P<vlr_total>[\d.,]+)',
    re.IGNORECASE
)

# ==========================================
# PROCESSAMENTO
# ==========================================

if arquivos_pdf:
    with st.spinner("Analisando notas fiscais..."):
        todos_itens = []

        for arquivo_pdf in arquivos_pdf:
            try:
                pdf = fitz.open(
                    stream=arquivo_pdf.read(),
                    filetype="pdf"
                )
                
                linhas_texto = []
                for pagina in pdf:
                    # Extrai linha por linha mantendo a estrutura vertical
                    texto_pagina = pagina.get_text("text")
                    for linha in texto_pagina.split("\n"):
                        linhas_texto.append(linha.strip())
                        
                pdf.close()
            except Exception as e:
                st.error(f"Erro ao ler o arquivo {arquivo_pdf.name}: {e}")
                continue

            # Junta tudo em um texto com quebras de linha preservadas para os dados gerais
            texto_completo = "\n".join(linhas_texto)

            # ==========================================
            # DADOS GERAIS
            # ==========================================
            match_empresa = re.search(
                r'RECEBEMOS\s+DE\s+(.*?)\s+OS\s+PRODUTOS',
                texto_completo,
                re.IGNORECASE
            )
            nome_empresa = match_empresa.group(1).strip() if match_empresa else "Empresa não identificada"

            match_cnpj = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', texto_completo)
            cnpj_empresa = match_cnpj.group(0) if match_cnpj else "CNPJ não identificado"

            match_data = re.search(r'\d{2}/\d{2}/\d{4}', texto_completo)
            data_emissao = match_data.group(0) if match_data else "Data não identificada"

            # ==========================================
            # EXTRAÇÃO LINHA A LINHA DOS PRODUTOS
            # ==========================================
            capturando_produtos = False
            
            for linha in linhas_texto:
                # Detecta início da tabela
                if any(p in linha.upper() for p in ["DADOS DOS PRODUTOS", "DADOS DOS PRODUTOS/SERVIÇOS", "ITENS DA NOTA FISCAL"]):
                    capturando_produtos = True
                    continue
                
                # Detecta fim da tabela
                if any(f in linha.upper() for f in ["CÁLCULO DO ISSQN", "CALCULO DO ISSQN", "DADOS ADICIONAIS", "INFORMAÇÕES COMPLEMENTARES", "RESERVADO AO FISCO"]):
                    capturando_produtos = False
                    
                if capturando_produtos:
                    match = padrao_item.match(linha)
                    if match:
                        item = match.groupdict()
                        if not item.get("cst"):
                            item["cst"] = "N/I"
                        
                        item["arquivo"] = arquivo_pdf.name
                        item["empresa"] = nome_empresa
                        item["cnpj"] = cnpj_empresa
                        item["data"] = data_emissao

                        todos_itens.append(item)

        # ==========================================
        # RESULTADO FINAL
        # ==========================================
        if len(todos_itens) > 0:
            df = pd.DataFrame(todos_itens)
            
            # Garante colunas essenciais
            colunas_desejadas = [
                "arquivo", "empresa", "cnpj", "data", "codigo", 
                "descricao", "ncm", "cst", "cfop", "unidade", 
                "quantidade", "vlr_unitario", "vlr_total"
            ]
            
            # Filtra apenas as que existem
            df = df[[c for c in colunas_desejadas if c in df.columns]]

            df.columns = [
                "Arquivo", "Empresa", "CNPJ", "Data", "Código", 
                "Descrição", "NCM", "CST", "CFOP", "Unidade", 
                "Quantidade", "Valor Unitário", "Valor Total"
            ]

            st.success(f"Foram encontrados {len(df)} produto(s) em {len(arquivos_pdf)} arquivo(s).")
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
                        st.success(f"{len(df)} registros enviados com sucesso.")
                    else:
                        st.error(f"Erro ao enviar. Status: {response.status_code}")
                        st.text(response.text)
                except Exception as e:
                    st.error(f"Erro na comunicação: {e}")
        else:
            st.warning("Nenhum produto encontrado nos arquivos enviados. Verifique o layout do PDF.")
