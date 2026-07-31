import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configuração inicial da página
st.set_page_config(page_title="Leitor de Nota Fiscal", layout="wide")

st.title("📄 Extrator de Itens de Nota Fiscal")
st.write("Faça o upload do PDF da Nota Fiscal para processar os itens e valores.")

# Componente de upload no navegador
arquivo_pdf = st.file_uploader("Selecione o arquivo PDF", type=["pdf"])

if arquivo_pdf is not None:
    st.success("Arquivo carregado com sucesso!")
    
    with st.spinner("Lendo o documento..."):
        # 1. Extração de Texto do PDF
        texto_completo = ""
        with pdfplumber.open(arquivo_pdf) as pdf:
            for pagina in pdf.pages:
                texto_extraido = pagina.extract_text()
                if texto_extraido:
                    texto_completo += texto_extraido + "\n"
        
        # 2. Lógica de Captura dos Itens (Regex)
        # Atenção: Esta Regex é um modelo genérico para capturar linhas no formato:
        # [Código] [Descrição] [Qtd] [UN] [Vlr Unitário] [Vlr Total]
        # Ex: "1234 TECLADO MECANICO 2,00 UN 150,00 300,00"
        padrao_item = re.compile(
            r'(?P<codigo>\d+)\s+'                          # Código (números)
            r'(?P<descricao>[A-Za-z0-9\s\.\-\/]+?)\s+'     # Descrição do produto
            r'(?P<qtd>\d+(?:,\d+)?)\s+'                    # Quantidade (ex: 1 ou 1,00)
            r'(?P<unid>[A-Z]{2,4})\s+'                     # Unidade de medida (UN, PC, CX)
            r'(?P<vlr_unit>\d+(?:[.,]\d+)?)\s+'            # Valor Unitário
            r'(?P<vlr_total>\d+(?:[.,]\d+)?)$',            # Valor Total no fim da linha
            re.MULTILINE
        )
        
        itens = []
        # Procura as correspondências no texto extraído
        for match in padrao_item.finditer(texto_completo):
            itens.append(match.groupdict())
        
        # 3. Exibição dos Dados na Interface
        if itens:
            st.subheader("Itens Encontrados na Nota")
            df = pd.DataFrame(itens)
            
            # Exibe os dados como uma tabela interativa
            st.dataframe(df, use_container_width=True)
            
            # Botão para baixar os resultados em CSV
            csv = df.to_csv(index=False, sep=';').encode('utf-8')
            st.download_button(
                label="📥 Baixar dados em CSV",
                data=csv,
                file_name='itens_nota_fiscal.csv',
                mime='text/csv',
            )
        else:
            st.warning("Nenhum item foi mapeado de forma automática.")
            st.info("Isso acontece quando a estrutura do PDF é diferente da regra (Regex) configurada. Verifique o texto bruto abaixo para ajustar a extração.")
            
        # Área de Debug: Muito útil durante o desenvolvimento para ver como o pdfplumber "enxerga" o texto
        with st.expander("Ver texto bruto extraído do PDF (Modo Debug)"):
            st.text(texto_completo)
