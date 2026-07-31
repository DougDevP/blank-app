import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re

# Configuração da página
st.set_page_config(page_title="Extrator de Itens - DANFE", layout="wide")

st.title("📄 Extrator de Itens Faturados (DANFE)")
st.write("Extrai os produtos, quantidades, valores e dados do emissor (incluindo Data) da Nota Fiscal.")

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

        # 2. Captura dos Dados Gerais da Nota (Empresa, CNPJ e Data)
        # Nome da empresa (no canhoto)
        match_empresa = re.search(r'RECEBEMOS\s+DE\s+(.*?)\s+OS\s+PRODUTOS', texto_completo, re.IGNORECASE)
        nome_empresa = match_empresa.group(1).strip() if match_empresa else "Empresa não identificada"
        
        # Primeiro CNPJ encontrado (Emissor)
        match_cnpj = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', texto_completo)
        cnpj_empresa = match_cnpj.group(0) if match_cnpj else "CNPJ não identificado"
        
        # Data de emissão (Busca a primeira data no formato DD/MM/AAAA que aparece na nota)
        match_data = re.search(r'\d{2}/\d{2}/\d{4}', texto_completo)
        data_emissao = match_data.group(0) if match_data else "Data não identificada"

        # 3. Regex Especializada para os Itens do DANFE
        padrao_danfe = re.compile(
            r'(?P<codigo>\d+)\s+'                                  
            r'(?P<descricao>[\s\S]+?)'                             
            r'\s+(?P<ncm>\d{8})\s+'                                
            r'(?P<cst>\d{3,4})\s+'                                 
            r'(?P<cfop>\d[.,]?\d{3})\s+'                           
            r'(?P<unidade>[a-zA-Z]{2,4})\s+'                       
            r'(?P<quantidade>[\d.,]+)\s+'                          
            r'(?P<vlr_unitario>[\d.,]+)\s+'                        
            r'(?P<vlr_total>[\d.,]+)',                             
            re.IGNORECASE
        )

        itens = []
        for match in padrao_danfe.finditer(texto_completo):
            dicionario = match.groupdict()
            
            # Limpeza rápida de quebras de linha na descrição
            dicionario['descricao'] = dicionario['descricao'].replace('\n', ' ').strip()
            
            # Injeta os dados da nota na linha do produto
            dicionario['empresa'] = nome_empresa
            dicionario['cnpj'] = cnpj_empresa
            dicionario['data'] = data_emissao
            
            itens.append(dicionario)

        # 4. Transformação em DataFrame (Pandas)
        if itens:
            st.success(f"Sucesso! Encontramos {len(itens)} produto(s) faturado(s).")
            
            df = pd.DataFrame(itens)
            
            # Reorganiza a ordem das colunas para colocar Empresa, CNPJ e Data no começo
            df = df[['empresa', 'cnpj', 'data', 'codigo', 'descricao', 'ncm', 'cst', 'cfop', 'unidade', 'quantidade', 'vlr_unitario', 'vlr_total']]
            
            # Renomeia as colunas para exibição e exportação
            df.columns = ['Empresa', 'CNPJ', 'Data', 'Código', 'Descrição', 'NCM', 'CST', 'CFOP', 'Unidade', 'Qtd', 'Vlr. Unitário', 'Vlr. Total']
            
            # Exibe o DataFrame na tela
            st.subheader("Tabela de Produtos Faturados")
            st.dataframe(df, use_container_width=True)
            
            # Botão de Download em CSV (Padrão Excel Brasileiro)
            csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            
            st.download_button(
                label="📥 Baixar Planilha em CSV",
                data=csv,
                file_name=f'produtos_{cnpj_empresa.replace("/", "").replace("-", "").replace(".", "")}.csv',
                mime='text/csv',
            )
        else:
            st.warning("Nenhum produto foi mapeado automaticamente.")
            st.info("Expanda o bloco abaixo para ver o texto bruto extraído e analisar a estrutura.")
            
        with st.expander("Ver texto bruto extraído do PDF (Modo Debug)"):
            st.text(texto_completo)
