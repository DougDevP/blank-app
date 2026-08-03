import streamlit as st
import fitz
import pandas as pd
import re

# Configuração da página
st.set_page_config(
    page_title="Extrator de Itens - DANFE",
    layout="wide"
)

st.title("📄 Extrator de Itens Faturados (DANFE)")
st.write(
    "Extrai os produtos, quantidades, valores e dados do emissor da Nota Fiscal."
)

arquivo_pdf = st.file_uploader(
    "Selecione o PDF da Nota Fiscal",
    type=["pdf"]
)

if arquivo_pdf is not None:

    with st.spinner("Analisando a estrutura da nota..."):

        # ==========================
        # LEITURA DO PDF
        # ==========================

        texto_completo = ""

        try:
            documento = fitz.open(
                stream=arquivo_pdf.read(),
                filetype="pdf"
            )

            for pagina in documento:
                texto_completo += pagina.get_text() + "\n"

            documento.close()

        except Exception as e:
            st.error(f"Erro ao ler o PDF: {e}")
            st.stop()

        # ==========================
        # DADOS GERAIS
        # ==========================

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

        # ==========================
        # LOCALIZA TABELA DE PRODUTOS
        # ==========================

        match_produtos = re.search(
            r'(?:DADOS DOS PRODUTOS\s*/\s*SERVIÇOS|'
            r'DADOS DOS PRODUTOS/SERVIÇOS|'
            r'Itens da nota fiscal)([\s\S]*)',
            texto_completo,
            re.IGNORECASE
        )

        texto_produtos = (
            match_produtos.group(1)
            if match_produtos
            else ""
        )

        if not texto_produtos:
            st.warning(
                "Não foi possível localizar a área de produtos da nota."
            )
            st.stop()

        # ==========================
        # REMOVE RODAPÉ DA TABELA
        # ==========================

        match_fim = re.search(
            r'(?:CÁLCULO DO ISSQN|'
            r'INFORMAÇÕES COMPLEMENTARES|'
            r'DADOS ADICIONAIS|'
            r'TRIBUTOS TOTAIS|'
            r'RESERVADO AO FISCO)',
            texto_produtos,
            re.IGNORECASE
        )

        if match_fim:
            texto_produtos = texto_produtos[:match_fim.start()]

        # ==========================
        # DIVIDE PRODUTOS
        # ==========================

        blocos = re.split(
            r'(?=\b\d{3,10}\s+(?:000|010|020|030|040|041|050|051|060|070|090|100|101|102|103|110|200|201|202|203|300|400|500|900)\b)',
            texto_produtos
        )

        itens = []

        # ==========================
        # REGEX FINAL DOS ITENS
        # ==========================

        regex_final = re.compile(
            r'(?P<ncm>\d{8})\s+'
            r'(?P<cfop>\d{4})\s+'
            r'(?P<unidade>[A-Z]{2,4})\s+'
            r'(?P<quantidade>[\d.,]+)\s+'
            r'(?P<vlr_total>[\d.,]+)\s+'
            r'(?P<vlr_unitario>[\d.,]+)',
            re.IGNORECASE
        )

        for bloco in blocos:

            bloco = bloco.strip()

            if not bloco:
                continue

            cabecalho = re.match(
                r'(?P<codigo>\d+)\s+(?P<cst>\d{3})',
                bloco
            )

            if not cabecalho:
                continue

            match_final = regex_final.search(bloco)

            if not match_final:
                continue

            descricao = bloco[
                cabecalho.end():match_final.start()
            ].strip()

            descricao = re.sub(
                r'\s+',
                ' ',
                descricao
            )

            item = {
                "empresa": nome_empresa,
                "cnpj": cnpj_empresa,
                "data": data_emissao,
                "codigo": cabecalho.group("codigo"),
                "descricao": descricao,
                "ncm": match_final.group("ncm"),
                "cst": cabecalho.group("cst"),
                "cfop": match_final.group("cfop"),
                "unidade": match_final.group("unidade"),
                "quantidade": match_final.group("quantidade"),
                "vlr_unitario": match_final.group("vlr_unitario"),
                "vlr_total": match_final.group("vlr_total"),
            }

            itens.append(item)

        # ==========================
        # RESULTADO
        # ==========================

        if itens:

            st.success(
                f"Sucesso! Encontramos {len(itens)} produto(s)."
            )

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
                "Qtd",
                "Vlr. Unitário",
                "Vlr. Total"
            ]

            st.subheader("Tabela de Produtos Faturados")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(
                index=False,
                sep=";",
                encoding="utf-8-sig"
            ).encode("utf-8-sig")

            st.download_button(
                label="📥 Baixar CSV",
                data=csv,
                file_name=f"produtos_{cnpj_empresa.replace('/','').replace('-','').replace('.','')}.csv",
                mime="text/csv"
            )

        else:

            st.warning(
                "Nenhum produto foi encontrado."
            )

            st.write("Trecho analisado:")
            st.text(texto_produtos[:5000])

        with st.expander("Ver texto bruto extraído do PDF"):
            st.text(texto_completo)
