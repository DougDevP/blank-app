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

        # 2. Regex Especializada para DANFE Brasileiro
        # Essa regra mapeia a estrutura padrão das colunas de produtos na nota fiscal
        padrao_danfe = re.compile(
            r'(?P<codigo>[\w.-]+)\s+'                        # 1. Código (Letras/Números)
            r'(?P<descricao>.+?)\s+'                         # 2. Descrição do Produto
            r'(?P<ncm>[\d.]{8,10})\s+'                       # 3. NCM (8 dígitos, com ou sem ponto)
            r'(?P<cst>\d{3,4})\s+'                           # 4. CST ou CSOSN (3 ou 4 dígitos)
            r'(?P<cfop>\d{4})\s+'                            # 5. CFOP (4 dígitos)
            r'(?P<unidade>[A-Za-z]{2,4})\s+'                 # 6. Unidade (UN, PC, KG, LT, etc)
            r'(?P<quantidade>\d+(?:[.,]\d+)?)\s+'            # 7. Quantidade (Ex: 1, 10.50, 2,00)
            r'(?P<vlr_unitario>\d+(?:[.,]\d+)?)\s+'          # 8. Valor Unitário
            r'(?P<vlr_total>\d+(?:[.,]\d+)?)',               # 9. Valor Total
            re.IGNORECASE
        )

        # Procura todos os itens que bateram com a regra acima
        itens = []
        for match in padrao_danfe.finditer(texto_completo):
            itens.append(match.groupdict())

        # 3. Transformação em DataFrame (Pandas)
        if itens:
            st.success(f"Sucesso! Encontramos {len(itens)} produto(s) faturado(s) na nota.")
            
            # Cria o DataFrame com os dados extraídos
            df = pd.DataFrame(itens)
            
            # Organiza os nomes das colunas para ficarem bonitos na tela
            df.columns = ['Código', 'Descrição', 'NCM', 'CST', 'CFOP', 'Unidade', 'Qtd', 'Vlr. Unitário', 'Vlr. Total']
            
            # Exibe o DataFrame na tela
            st.subheader("Tabela de Produtos Faturados")
            st.dataframe(df, use_container_width=True)
            
            # 4. Botão de Download em CSV (Configurado para o Excel brasileiro)
            csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            
            st.download_button(
                label="📥 Baixar Planilha em CSV",
                data=csv,
                file_name='produtos_faturados.csv',
                mime='text/csv',
            )
        else:
            st.warning("Nenhum produto foi mapeado automaticamente.")
            st.info("Isso acontece se a nota for de Serviços (NFS-e) ou tiver colunas fora do padrão DANFE. Expanda o bloco abaixo para ver o texto bruto extraído.")
            
        # Útil para diagnosticar notas com layouts "diferentões"
        with st.expander("Ver texto bruto extraído do PDF (Modo Debug)"):
            st.text(texto_completo)
