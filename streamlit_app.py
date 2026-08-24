import streamlit as st
import pdfplumber
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
    "Extrai produtos, quantidades, valores e dados gerais de notas fiscais usando leitura estruturada."
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
# PROCESSAMENTO
# ==========================================
if arquivos_pdf:
    with st.spinner("Analisando notas fiscais..."):
        todos_itens = []

        for arquivo_pdf in arquivos_pdf:
            texto_completo = ""
            tabelas_encontradas = []

            try:
                with pdfplumber.open(arquivo_pdf) as pdf:
                    for pagina in pdf.pages:
                        # Extrai texto para dados gerais
                        t = pagina.extract_text()
                        if t:
                            texto_completo += t + "\n"
                        
                        # Extrai tabelas visuais da página
                        tables = pagina.extract_tables()
                        if tables:
                            tabelas_encontradas.extend(tables)

            except Exception as e:
                st.error(f"Erro ao ler o arquivo {arquivo_pdf.name}: {e}")
                continue

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
            # EXTRAÇÃO INTELIGENTE DAS TABELAS
            # ==========================================
            produto_encontrado = False
            
            for tabela in tabelas_encontradas:
                for linha in tabela:
                    # Filtra linhas vazias ou cabeçalhos comuns de DANFE
                    linha_txt = " ".join([str(celula) for celula in linha if celula])
                    
                    if any(c in linha_txt.upper() for c in ["CÓDIGO", "CODIGO", "DESCRIÇÃO", "NCM", "CFOP", "VALOR"]):
                        continue # Pula o cabeçalho da tabela
                    
                    # Tenta identificar se a linha parece um item (procurando NCM com 8 dígitos ou valores numéricos consistentes)
                    # Uma linha de produto geralmente tem vários elementos preenchidos
                    elementos_validos = [cel for cel in linha if cel and cel.strip()]
                    if len(elementos_validos) >= 5: # Linhas com dados suficientes para ser um item
                        # Tentativa de mapear colunas por heurística ou ordem comum em DANFEs
                        # Geralmente: [Codigo, Descricao, NCM, CST, CFOP, Unidade, Qtd, VlUnit, VlTotal]
                        # Como os layouts mudam, pegamos os campos principais com base na estrutura da linha
                        
                        try:
                            # Tentamos extrair valores numéricos nas últimas posições e texto nas primeiras
                            codigo = elementos_validos[0]
                            descricao = elementos_validos[1]
                            
                            # Varre os elementos para achar o NCM (8 dígitos)
                            ncm = "N/I"
                            cst = "N/I"
                            cfop = "N/I"
                            unidade = "UN"
                            quantidade = "1"
                            vlr_unitario = "0,00"
                            vlr_total = "0,00"
                            
                            # Heurística para preencher colunas baseada no conteúdo das células da linha
                            for item_cel in elementos_validos:
                                item_cel_limpo = item_cel.strip()
                                if re.match(r'^\d{8}$', item_cel_limpo):
                                    ncm = item_cel_limpo
                                elif re.match(r'^\d\.?\d{3}$', item_cel_limpo):
                                    cfop = item_cel_limpo
                                elif re.match(r'^[A-Za-z]{2,4}$', item_cel_limpo) and len(item_cel_limpo) <= 4:
                                    unidade = item_cel_limpo

                            # Os últimos elementos da linha costumam ser Quantidade, Vlr Unit e Vl Total
                            if len(elementos_validos) >= 3:
                                vlr_total = elementos_validos[-1]
                                vlr_unitario = elementos_validos[-2] if len(elementos_validos) >= 4 else "0,00"
                                quantidade = elementos_validos[-3] if len(elementos_validos) >= 5 else "1"

                            item = {
                                "arquivo": arquivo_pdf.name,
                                "empresa": nome_empresa,
                                "cnpj": cnpj_empresa,
                                "data": data_emissao,
                                "codigo": codigo,
                                "descricao": descricao,
                                "ncm": ncm,
                                "cst": cst,
                                "cfop": cfop,
                                "unidade": unidade,
                                "quantidade": quantidade,
                                "vlr_unitario": vlr_unitario,
                                "vlr_total": vlr_total
                            }
                            
                            todos_itens.append(item)
                            produto_encontrado = True
                        except Exception:
                            continue

        # ==========================================
        # RESULTADO FINAL
        # ==========================================
        if len(todos_itens) > 0:
            df = pd.DataFrame(todos_itens)

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
            st.warning("Nenhum produto foi extraído automaticamente. Como as notas não seguem um padrão, verifique se o PDF é digital ou escaneado (imagem).")
