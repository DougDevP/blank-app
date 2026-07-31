import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re

# Configuração da página
st.set_page_config(page_title="Extrator de Itens - DANFE", layout="wide")

st.title("📄 Extrator de Itens Faturados (DANFE)")
st.write("Extrai os produtos, quantidades e valores da Nota Fiscal e converte em planilha.")

# Upload do arquivo
arquivo_pdf = st.file_uploader("Selecione o PDF da Nota Fiscal", type=["pdf"])

if arquivo_pdf is not None:
    with st.spinner("Analisando a estrutura da nota..."):
        
        # 1. Extração do texto bruto usando PyMuPDF (fitz)
        texto_completo = ""
        try:
            documento = fitz.open(stream=arquivo_pdf.read(), filetype="pdf")
            for pagina in documento:
                texto_completo += pagina.get_text() + "\n"
            documento.close()
        except Exception as e:
            st.error(f"Erro ao ler o PDF: {e}")
            st.stop()

        # 2. Regex Especializada e Flexível baseada nos modelos ExclusivEPI e Tutela
        padrao_danfe = re.compile(
            r'(?P<codigo>\d+)\s+'                                  # 1. Código (Apenas números)
            r'(?P<descricao>[\s\S]+?)'                             # 2. Descrição (Permite quebras de linha e textos longos)
            r'\s+(?P<ncm>\d{8})\s+'                                # 3. NCM (8 dígitos exatos, âncora principal)
            r'(?P<cst>\d{3,4})\s+'                                 # 4. CST/CSOSN (3 a 4 dígitos)
            r'(?P<cfop>\d[.,]?\d{3})\s+'                           # 5. CFOP (Aceita formatos como '6108' ou '5.102')
            r'(?P<unidade>[a-zA-Z]{2,4})\s+'                       # 6. Unidade (Maiúsculas e minúsculas como 'UN', 'un', 'PR')
            r'(?P<quantidade>[\d.,]+)\s+'                          # 7. Quantidade (Aceita vírgula ou ponto)
            r'(?P<vlr_unitario>[\d.,]+)\s+'                        # 8. Valor Unitário (Aceita vírgula ou ponto)
            r'(?P<vlr_total>[\d.,]+)',                             # 9. Valor Total (Aceita vírgula ou ponto)
            re.IGNORECASE
        )

        # Procura todos os itens que bateram com a regra acima
        itens = []
        for match in padrao_danfe.finditer(texto_completo):
            dicionario = match.groupdict()
            
            # Limpeza rápida de quebras de linha na descrição para ficar bonito na planilha
            dicionario['descricao'] = dicionario['descricao'].replace('\n', ' ').strip()
            itens.append(dicionario)

        # 3. Transformação em DataFrame (Pandas)
        if itens:
            st.success(f"Sucesso! Encontramos {len(itens)} produto(s) faturado(s) na nota.")
            
            # Cria o DataFrame com os dados extraídos
            df = pd.DataFrame(itens)
            
            # Organiza os nomes das colunas
            df.columns = ['Código', 'Descrição', 'NCM', 'CST', 'CFOP', 'Unidade', 'Qtd', 'Vlr. Unitário', 'Vlr. Total']
            
            # Exibe o DataFrame na tela
            st.subheader("Tabela de Produtos Faturados")
            st.dataframe(df, use_container_width=True)
            
            # 4. Botão de Download em CSV (Padrão Excel Brasileiro)
            csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            
            st.download_button(
                label="📥 Baixar Planilha em CSV",
                data=csv,
                file_name='produtos_faturados.csv',
                mime='text/csv',
            )
        else:
            st.warning("Nenhum produto foi mapeado automaticamente.")
            st.info("Expanda o bloco abaixo para ver o texto bruto extraído e analisar a estrutura.")
            
        with st.expander("Ver texto bruto extraído do PDF (Modo Debug)"):
            st.text(texto_completo)
