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
    page_title="Extrator de Itens - Notas Fiscais",
    layout="wide"
)

st.title("📄 Extrator de Itens Faturados (DANFE & NFS-e)")
st.write(
    "Extrai produtos, serviços, quantidades, valores, frete e dados gerais de Notas Fiscais."
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
# REGEX PRODUTOS (DANFE)
# ==========================================

padrao_item = re.compile(
    r'(?P<codigo>\d{3,10})\s*\|\s*'                
    r'(?P<descricao>.*?)\s*\|\s*'                 
    r'(?P<ncm>\d{8})\s*\|\s*'                     
    r'(?P<cst>\d{3,4})\s*\|\s*'                   
    r'(?P<cfop>\d\.?\d{3})\s*\|\s*'               
    r'(?P<unidade>[A-Za-z]{2,4})\s*\|\s*'         
    r'(?P<quantidade>[\d.,]+)\s*\|\s*'            
    r'(?P<vlr_unitario>[\d.,]+)\s*\|\s*'          
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
            texto_completo = ""
            try:
                pdf = fitz.open(
                    stream=arquivo_pdf.read(),
                    filetype="pdf"
                )
                for pagina in pdf:
                    texto_completo += pagina.get_text() + "\n"
                pdf.close()
            except Exception as e:
                st.error(f"Erro ao ler o arquivo {arquivo_pdf.name}: {e}")
                continue

            # Detecta se é NFS-e (Serviço) ou DANFE (Produto)
            is_nfse = "NFS-e" in texto_completo or "NOTA FISCAL DE SERVIÇOS" in texto_completo.upper() or "DANFSe" in texto_completo

            if is_nfse:
                # ==========================================
                # EXTRAÇÃO DE NFS-e (Serviços)
                # ==========================================
                match_empresa = re.search(r'(?:Prestador do Serviço|EMITENTE DA NFS-e)\s*[\n\r]+\s*([A-Z0-9\s&_.-]+)', texto_completo, re.IGNORECASE)
                if not match_empresa:
                    linhas = [l.strip() for l in texto_completo.split('\n') if l.strip()]
                    nome_empresa = linhas[0] if linhas else "Prestador não identificado"
                else:
                    nome_empresa = match_empresa.group(1).strip()

                match_cnpj = re.search(r'(?:CNPJ|CPF/CNPJ/NIF)[:\s]*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', texto_completo)
                cnpj_empresa = match_cnpj.group(1) if match_cnpj else "CNPJ não identificado"

                match_data = re.search(r'(?:Emitida em|Data e Hora da emissão da NFS-e|Competência)[^\d]*(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
                data_emissao = match_data.group(1) if match_data else "Data não identificada"

                match_desc = re.search(r'(?:Discriminação do\(s\) Serviço\(s\)|Descrição do Serviço)[:\s]*(.*?)(?:TRIBUTAÇÃO|Código de Tributação|Valor dos serviços|Valor do Serviço|$)', texto_completo, re.DOTALL | re.IGNORECASE)
                descricao_servico = match_desc.group(1).strip() if match_desc else "Serviço prestado conforme nota"
                descricao_servico = re.sub(r'\s+', ' ', descricao_servico)

                match_valor = re.search(r'(?:Valor dos serviços|Valor do Serviço|VALOR TOTAL DA NFS-E)[:\s]*(?:R\$)?\s*([\d.,]+)', texto_completo, re.IGNORECASE)
                vlr_total_servico = match_valor.group(1) if match_valor else "0,00"

                item_servico = {
                    "arquivo": arquivo_pdf.name,
                    "empresa": nome_empresa,
                    "cnpj": cnpj_empresa,
                    "data": data_emissao,
                    "codigo": "N/I",
                    "descricao": descricao_servico,
                    "ncm": "N/I",
                    "cst": "N/I",
                    "cfop": "N/I",
                    "unidade": "UN",
                    "quantidade": "1",
                    "vlr_unitario": vlr_total_servico,
                    "vlr_total": vlr_total_servico,
                    "frete": "0,00"
                }
                todos_itens.append(item_servico)

            else:
                # ==========================================
                # EXTRAÇÃO DE DANFE (Produtos)
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

                # Extração do valor do frete na DANFE
                match_frete = re.search(r'VALOR\s+DO\s+FRETE\s*([\d.,]+)', texto_completo, re.IGNORECASE)
                if not match_frete:
                    match_frete = re.search(r'FRETE\s*[:\s]*([\d.,]+)', texto_completo, re.IGNORECASE)
                
                valor_frete = match_frete.group(1) if match_frete else "0,00"

                padroes_inicio = [
                    r'DADOS\s+DOS\s+PRODUTOS\s*/\s*SERVIÇOS',
                    r'DADOS\s+DOS\s+PRODUTOS/SERVIÇOS',
                    r'Itens\s+da\s+nota\s+fiscal'
                ]

                texto_produtos = ""
                for padrao in padroes_inicio:
                    match = re.search(padrao, texto_completo, re.IGNORECASE)
                    if match:
                        texto_produtos = texto_completo[match.end():]
                        break

                if not texto_produtos:
                    st.warning(f"Não foi possível localizar os itens em {arquivo_pdf.name}")
                    continue

                fim_tabela = re.search(
                    r'(CÁLCULO\s+DO\s+ISSQN|CALCULO\s+DO\s+ISSQN|DADOS\s+ADICIONAIS|INFORMAÇÕES\s+COMPLEMENTARES|INFORMACOES\s+COMPLEMENTARES|RESERVADO\s+AO\s+FISCO)',
                    texto_produtos,
                    re.IGNORECASE
                )
                if fim_tabela:
                    texto_produtos = texto_produtos[:fim_tabela.start()]

                texto_produtos = re.sub(r'\s+', ' ', texto_produtos)

                itens_encontrados_nesta_nota = []

                for match in padrao_item.finditer(texto_produtos):
                    itens_encontrados_nesta_nota.append(match.groupdict())

                if len(itens_encontrados_nesta_nota) == 0:
                    padrao_fallback = re.compile(
                        r'(?P<codigo>\d{2,15})\s+'
                        r'(?P<descricao>.*?)\s+'
                        r'(?P<ncm>\d{8}).*?'
                        r'(?P<unidade>UN|CX|PC|PR|KG|BT|M2|L)\s+'
                        r'(?P<quantidade>[\d.,]+)\s+'
                        r'(?P<vlr_unitario>[\d.,]+).*?'
                        r'(?P<vlr_total>\d{1,3}(?:\.\d{3})*,\d{2})',
                        re.IGNORECASE
                    )
                    try:
                        for match in padrao_fallback.finditer(texto_produtos):
                            dict_item = match.groupdict()
                            dict_item["cst"] = "N/I"
                            dict_item["cfop"] = "N/I"
                            itens_encontrados_nesta_nota.append(dict_item)
                    except Exception as ex:
                        st.warning(f"Falha ao executar o fallback na nota {arquivo_pdf.name}: {ex}")

                for item in itens_encontrados_nesta_nota:
                    item["descricao"] = re.sub(r'\s+', ' ', item.get("descricao", "")).strip()
                    if not item.get("cst"):
                        item["cst"] = "N/I"
                    if not item.get("cfop"):
                        item["cfop"] = "N/I"

                    item["arquivo"] = arquivo_pdf.name
                    item["empresa"] = nome_empresa
                    item["cnpj"] = cnpj_empresa
                    item["data"] = data_emissao
                    item["frete"] = valor_frete

                    todos_itens.append(item)

        # ==========================================
        # RESULTADO FINAL
        # ==========================================
        if len(todos_itens) > 0:
            df = pd.DataFrame(todos_itens)

            df = df[[
                "arquivo", "empresa", "cnpj", "data", "codigo",
                "descricao", "ncm", "cst", "cfop", "unidade",
                "quantidade", "vlr_unitario", "vlr_total", "frete"
            ]]

            df.columns = [
                "Arquivo", "Empresa", "CNPJ", "Data", "Código",
                "Descrição", "NCM", "CST", "CFOP", "Unidade",
                "Quantidade", "Valor Unitário", "Valor Total", "Frete"
            ]

            st.success(f"Foram encontrados {len(df)} item(ns) em {len(arquivos_pdf)} arquivo(s).")
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
            st.warning("Nenhum item encontrado nos arquivos enviados.")
