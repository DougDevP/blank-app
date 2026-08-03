import streamlit as st
import fitz
import pandas as pd
import re

st.set_page_config(page_title="Extrator de Itens - DANFE", layout="wide")

st.title("📄 Extrator de Itens Faturados (DANFE)")

arquivo_pdf = st.file_uploader(
    "Selecione o PDF da Nota Fiscal",
    type=["pdf"]
)

if arquivo_pdf:

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
        st.error(f"Erro ao ler PDF: {e}")
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

    marcadores_inicio = [
        "DADOS DOS PRODUTOS / SERVIÇOS",
        "DADOS DOS PRODUTOS/SERVIÇOS",
        "Itens da nota fiscal"
    ]

    texto_produtos = ""

    for marcador in marcadores_inicio:

        pos = texto_completo.upper().find(
            marcador.upper()
        )

        if pos >= 0:
            texto_produtos = texto_completo[pos:]
            break

    if not texto_produtos:
        st.warning("Seção de produtos não encontrada.")
        st.stop()

    # remove rodapé da tabela

    match_fim = re.search(
        r'(CÁLCULO DO ISSQN|INFORMAÇÕES COMPLEMENTARES|DADOS ADICIONAIS)',
        texto_produtos,
        re.IGNORECASE
    )

    if match_fim:
        texto_produtos = texto_produtos[:match_fim.start()]

    texto_produtos = re.sub(
        r'\s+',
        ' ',
        texto_produtos
    )

    # ==========================
    # IDENTIFICA INÍCIO DOS ITENS
    # ==========================

    padrao_inicio_item = re.compile(
        r'(?=\b\d{3,10}\s+(?:000|010|020|040|041|060|090|100|200|300|400|500|900)\b)'
    )

    posicoes = [
        m.start()
        for m in padrao_inicio_item.finditer(texto_produtos)
    ]

    posicoes.append(len(texto_produtos))

    blocos = []

    for i in range(len(posicoes) - 1):

        inicio = posicoes[i]
        fim = posicoes[i + 1]

        bloco = texto_produtos[inicio:fim].strip()

        if bloco:
            blocos.append(bloco)

    itens = []

    # ==========================
    # EXTRAI CAMPOS
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

        cabecalho = re.match(
            r'(?P<codigo>\d+)\s+(?P<cst>\d{3})\s+',
            bloco
        )

        if not cabecalho:
            continue

        codigo = cabecalho.group("codigo")
        cst = cabecalho.group("cst")

        match_final = regex_final.search(bloco)

        if not match_final:
            continue

        descricao = bloco[
            cabecalho.end():match_final.start()
        ].strip()

        item = {
            "empresa": nome_empresa,
            "cnpj": cnpj_empresa,
            "data": data_emissao,
            "codigo": codigo,
            "descricao": descricao,
            "ncm": match_final.group("ncm"),
            "cst": cst,
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
                "vlr_total",
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
            "Vlr. Total",
        ]

        st.success(
            f"{len(df)} item(ns) encontrado(s)"
        )

        st.dataframe(
            df,
            use_container_width=True
        )

    else:

        st.warning(
            "Nenhum produto encontrado."
        )

    with st.expander("Texto extraído"):

        st.text(texto_completo)
