import streamlit as st
import fitz
import pandas as pd
import re
import requests
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
    "Extrai produtos, quantidades, valores e dados gerais da NF."
)

# ==========================================
# UPLOAD
# ==========================================

arquivo_pdf = st.file_uploader(
    "Selecione o PDF da Nota Fiscal",
    type=["pdf"]
)

# ==========================================
# PROCESSAMENTO
# ==========================================

if arquivo_pdf is not None:

    with st.spinner("Analisando nota fiscal..."):

        # --------------------------
        # LEITURA PDF
        # --------------------------

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

            st.error(f"Erro ao ler PDF: {e}")
            st.stop()

        # --------------------------
        # DADOS GERAIS
        # --------------------------

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

        # --------------------------
        # LOCALIZA TABELA PRODUTOS
        # --------------------------

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
                "Não foi possível localizar a seção de produtos."
            )

            st.stop()

        # --------------------------
        # REMOVE RODAPÉ
        # --------------------------

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

        # normaliza espaços

        texto_produtos = re.sub(
            r'\s+',
            ' ',
            texto_produtos
        )

        # --------------------------
        # REGEX PRODUTOS
        # --------------------------

        padrao_item = re.compile(

            r'(?P<codigo>\d{3,10})\s+'

            r'(?P<descricao>.*?)'

            r'\s+(?P<ncm>\d{8})'

            r'(?:\s+(?P<cst>\d{3}))?'

            r'\s+(?P<cfop>\d\.?\d{3})'

            r'\s+(?P<unidade>[A-Za-z]{2,4})'

            r'\s+(?P<quantidade>[\d.,]+)'

            r'\s+(?P<vlr_unitario>[\d.,]+)'

            r'\s+(?P<vlr_total>[\d.,]+)',

            re.IGNORECASE
        )

        itens = []

        # --------------------------
        # EXTRAÇÃO
        # --------------------------

        for match in padrao_item.finditer(
            texto_produtos
        ):

            item = match.groupdict()

            descricao = re.sub(
                r'\s+',
                ' ',
                item["descricao"]
            ).strip()

            item["descricao"] = descricao

            if not item["cst"]:
                item["cst"] = "N/I"

            item["empresa"] = nome_empresa
            item["cnpj"] = cnpj_empresa
            item["data"] = data_emissao

            itens.append(item)

        # --------------------------
        # RESULTADO
        # --------------------------

        if len(itens) > 0:

            df = pd.DataFrame(itens)

            df = df[
                [
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
                f"Foram encontrados {len(df)} produto(s)."
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
                "📥 Baixar CSV",
                csv,
                file_name="produtos_nota_fiscal.csv",
                mime="text/csv"
            )

            if st.button("Enviar para Sharepoint"):
                requests.post(url)

        else:

            st.warning(
                "Nenhum produto encontrado."
            )

            st.subheader(
                "Debug da área de produtos"
            )

            st.text(
                texto_produtos[:5000]
            )

        # --------------------------
        # DEBUG COMPLETO
        # --------------------------

        with st.expander(
            "Ver texto completo extraído"
        ):
            st.text(texto_completo)



