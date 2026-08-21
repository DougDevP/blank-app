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
# REGEX PRODUTOS
# ==========================================

padrao_item = re.compile(
    r'(?P<codigo>\d{3,10})\s+'
    r'(?P<descricao>.*?)'
    r'\s+(?P<ncm>\d{8})'
    r'(?:\s+(?P<cst>\d{3,4}))?'          # ATUALIZADO: Aceita CST (3) ou CSOSN (4)
    r'\s+(?P<cfop>\d\.?\d{3})'
    r'\s+(?P<unidade>[A-Za-z]{2,4})'
    r'\s+(?P<quantidade>[\d.,]+)'
    r'\s+(?P<vlr_unitario>[\d.,]+)'
    r'(?:\s+(?P<vlr_desconto>[\d.,]+))?' # NOVO: Captura o valor de desconto opcional
    r'\s+(?P<vlr_total>[\d.,]+)',
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

                st.error(
                    f"Erro ao ler o arquivo {arquivo_pdf.name}: {e}"
                )
                continue

            # ==========================================
            # DADOS GERAIS
            # ==========================================

            match_empresa = re.search(
                r'RECEBEMOS\s+DE\s+(.*?)\s+OS\s+PRODUTOS',
                texto_completo,
                re.IGNORECASE
            )

            nome_empresa = (
                match_empresa.group(1).strip()
                if match_empresa
                else "Empresa não identificada"
            )

            match_cnpj = re.search(
                r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}',
                texto_completo
            )

            cnpj_empresa = (
                match_cnpj.group(0)
                if match_cnpj
                else "CNPJ não identificado"
            )

            match_data = re.search(
                r'\d{2}/\d{2}/\d{4}',
                texto_completo
            )

            data_emissao = (
                match_data.group(0)
                if match_data
                else "Data não identificada"
            )

            # ==========================================
            # ENCONTRA TABELA DE PRODUTOS
            # ==========================================

            padroes_inicio = [
                r'DADOS\s+DOS\s+PRODUTOS\s*/\s*SERVIÇOS',
                r'DADOS\s+DOS\s+PRODUTOS/SERVIÇOS',
                r'Itens\s+da\s+nota\s+fiscal'
            ]

            texto_produtos = ""

            for padrao in padroes_inicio:

                match = re.search(
                    padrao,
                    texto_completo,
                    re.IGNORECASE
                )

                if match:
                    texto_produtos = texto_completo[
                        match.end():
                    ]
                    break

            if not texto_produtos:

                st.warning(
                    f"Não foi possível localizar os produtos em {arquivo_pdf.name}"
                )
                continue

            # ==========================================
            # REMOVE RODAPÉ
            # ==========================================

            fim_tabela = re.search(
                r'(CÁLCULO\s+DO\s+ISSQN|'
                r'CALCULO\s+DO\s+ISSQN|'
                r'DADOS\s+ADICIONAIS|'
                r'INFORMAÇÕES\s+COMPLEMENTARES|'
                r'INFORMACOES\s+COMPLEMENTARES|'
                r'RESERVADO\s+AO\s+FISCO)',
                texto_produtos,
                re.IGNORECASE
            )

            if fim_tabela:
                texto_produtos = texto_produtos[
                    :fim_tabela.start()
                ]

            texto_produtos = re.sub(
                r'\s+',
                ' ',
                texto_produtos
            )

            # ==========================================
            # EXTRAÇÃO DOS ITENS
            # ==========================================

            for match in padrao_item.finditer(
                texto_produtos
            ):

                item = match.groupdict()

                item["descricao"] = re.sub(
                    r'\s+',
                    ' ',
                    item["descricao"]
                ).strip()

                if not item["cst"]:
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

            df = df[
                [
                    "arquivo",
                    "empresa",
                    "cnpj",
                    "data",
                    "codigo",
                    "descricao",
                    "ncm",
                    "cst",
                    "cfop",
                    "unidade",
                    "quantidade",
                    "vlr_unitario",
                    "vlr_total"
                ]
            ]

            df.columns = [
                "Arquivo",
                "Empresa",
                "CNPJ",
                "Data",
                "Código",
                "Descrição",
                "NCM",
                "CST",
                "CFOP",
                "Unidade",
                "Quantidade",
                "Valor Unitário",
                "Valor Total"
            ]

            st.success(
                f"Foram encontrados {len(df)} produto(s) em {len(arquivos_pdf)} arquivo(s)."
            )

            st.dataframe(
                df,
                use_container_width=True
            )

            csv = df.to_csv(
                index=False,
                sep=";",
                encoding="utf-8-sig"
            ).encode(
                "utf-8-sig"
            )

            st.download_button(
                "📥 Baixar CSV Consolidado",
                csv,
                file_name="produtos_notas_fiscais.csv",
                mime="text/csv"
            )

            # ==========================================
            # ENVIO SHAREPOINT / POWER AUTOMATE
            # ==========================================

            if st.button("Enviar para SharePoint"):

                payload = df.to_dict(
                    orient="records"
                )

                try:

                    response = requests.post(
                        url,
                        json=payload,
                        timeout=120
                    )

                    if response.status_code in [
                        200,
                        201,
                        202
                    ]:

                        st.success(
                            f"{len(df)} registros enviados com sucesso."
                        )

                    else:

                        st.error(
                            f"Erro ao enviar. Status: {response.status_code}"
                        )

                        st.text(response.text)

                except Exception as e:

                    st.error(
                        f"Erro na comunicação: {e}"
                    )

        else:

            st.warning(
                "Nenhum produto encontrado nos arquivos enviados."
            )
