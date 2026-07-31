import streamlit as st
import fitz
import pandas as pd
import re

# Configuração inicial da página
st.set_page_config(page_title="Leitor de Nota Fiscal", layout="wide")

st.title("📄 Extrator de Itens de Nota Fiscal")
st.write("Faça o upload do PDF da Nota Fiscal para processar os itens e valores (utilizando PyMuPDF).")

# Componente de upload no navegador
arquivo_pdf = st.file_uploader("Selecione o arquivo PDF", type=["pdf"])

if arquivo_pdf is not None:
    st.success("Arquivo carregado com sucesso!")
    
    with st.spinner("Lendo o documento..."):
        # 1. Extração de Texto do PDF com PyMuPDF
        texto_completo = ""
        
        # O fitz (PyMuPDF) lê o PDF diretamente da memória a partir do upload
        documento = fitz.open(stream=arquivo_pdf.read(), filetype="pdf")
        
        for pagina in documento:
            texto_completo += pagina.get_text() + "\n"
            
        documento.close()
        
        # 2. Lógica de Captura dos Itens (Regex)
        padrao_item = re.compile(
            r'(?P<codigo>\d+)\s+'                          # Código
            r'(?P<descricao>[A-Za-z0-9\s\.\-\/]+?)\s+'     # Descrição
            r'(?P<qtd>\d+(?:,\d+)?)\s+'                    # Quantidade
            r'(?P<unid>[A-Z]{2,4})\s+'                     # Unidade de medida
            r'(?P<vlr_unit>\d+(?:[.,]\d+)?)\s+'            # Valor Unitário
            r'(?P<vlr_total>\d+(?:[.,]\d+)?)$',            # Valor Total
            re.MULTILINE
        )
        
        itens = []
        for match in padrao_item.finditer(texto_completo):
            itens.append(match.groupdict())
        
        # 3. Exibição dos Dados na Interface
        if itens:
            st.subheader("Itens Encontrados na Nota")
            df = pd.DataFrame(itens)
            
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False, sep=';').encode('utf-8')
            st.download_button(
                label="📥 Baixar dados em CSV",
                data=csv,
                file_name='itens_nota_fiscal.csv',
                mime='text/csv',
            )
        else:
            st.warning("Nenhum item foi mapeado de forma automática.")
            st.info("Verifique o texto bruto abaixo para ajustar a extração da Regex.")
            
        with st.expander("Ver texto bruto extraído do PDF (Modo Debug)"):
            st.text(texto_completo)
