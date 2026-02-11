import streamlit as st
import pandas as pd
import os
import unicodedata
from fpdf import FPDF
from datetime import datetime
import plotly.express as px


    # --- FUNÇÃO PARA LIMPAR TUDO QUE TRAVA O PDF (Acentos e Emojis) ---
def remover_acentos(texto):
    if not isinstance(texto, str): return str(texto)
    # Remove emojis e símbolos especiais antes de normalizar
    texto_limpo = "".join(c for c in texto if c.isalnum() or c in " /-.(),:")
    # Remove acentos (ex: á -> a)
    nfkd_form = unicodedata.normalize('NFKD', texto_limpo)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="TI Saúde - Aquidauana", layout="wide")

# BIBLIOTECA PADRÃO (Mesma lógica anterior)
biblioteca_padrao = {
    "🛠️ MANUTENCAO": {"SSD 500GB": "SSD NVMe M.2 500GB alta performance."},
    "🌐 REDES": {"Switch 24p": "Switch Gigabit Rack 19 polegadas."}
}

def carregar_biblioteca_custom():
    if not os.path.exists('minha_biblioteca.csv'):
        return pd.DataFrame(columns=['Categoria', 'Item', 'Especificacao'])
    return pd.read_csv('minha_biblioteca.csv')

def salvar_na_biblioteca(cat, item, espec):
    df_custom = carregar_biblioteca_custom()
    if not ((df_custom['Categoria'] == cat) & (df_custom['Item'] == item)).any():
        novo_item = pd.DataFrame([[cat, item, espec]], columns=['Categoria', 'Item', 'Especificacao'])
        novo_item.to_csv('minha_biblioteca.csv', mode='a', header=not os.path.exists('minha_biblioteca.csv'), index=False)

# Mesclagem
df_bib_custom = carregar_biblioteca_custom()
biblioteca_ativa = biblioteca_padrao.copy()
for _, row in df_bib_custom.iterrows():
    if row['Categoria'] not in biblioteca_ativa: biblioteca_ativa[row['Categoria']] = {}
    biblioteca_ativa[row['Categoria']][row['Item']] = row['Especificacao']

# GESTÃO DE COTAÇÕES
COLUNAS_COTACAO = ['ID', 'Data', 'Categoria', 'Item', 'Qtd', 'Unitário', 'Total', 'Especificação']
def carregar_cotacoes():
    if not os.path.exists('cotacoes.csv'): return pd.DataFrame(columns=COLUNAS_COTACAO)
    return pd.read_csv('cotacoes.csv')

df_cotacao = carregar_cotacoes()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🏢 SMS Aquidauana")
    opcoes_categorias = list(biblioteca_ativa.keys()) + ["🆕 NOVA CATEGORIA"]
    cat_sel = st.selectbox("Categoria", opcoes_categorias)
    
    if cat_sel == "🆕 NOVA CATEGORIA":
        cat_final = st.text_input("Nome da Nova Categoria")
        nome_sel = st.text_input("Nome do Material")
        espec_sel = st.text_area("Especificação")
    else:
        cat_final = cat_sel
        itens = list(biblioteca_ativa[cat_sel].keys()) + ["+ Novo Item"]
        prod_sel = st.selectbox("Produto", itens)
        if prod_sel == "+ Novo Item":
            nome_sel = st.text_input("Nome do Novo Material")
            espec_sel = st.text_area("Especificação")
        else:
            nome_sel = prod_sel
            espec_sel = st.text_area("Especificação", value=biblioteca_ativa[cat_sel][prod_sel])

    qtd_sel = st.number_input("Qtd", min_value=1, value=1)
    preco_sel = st.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f")
    salvar_fixo = st.checkbox("💾 Salvar na biblioteca", value=False)
    
    if st.button("📥 Registrar na Cotação"):
        hoje = datetime.now().strftime("%d/%m/%Y")
        if salvar_fixo: salvar_na_biblioteca(cat_final, nome_sel, espec_sel)
        
        # Gera um ID único simples para facilitar a exclusão
        novo_id = int(df_cotacao['ID'].max() + 1) if not df_cotacao.empty else 1
        nova_linha = pd.DataFrame([[novo_id, hoje, cat_final, nome_sel, qtd_sel, preco_sel, qtd_sel*preco_sel, espec_sel]], columns=COLUNAS_COTACAO)
        nova_linha.to_csv('cotacoes.csv', mode='a', header=not os.path.exists('cotacoes.csv'), index=False)
        st.rerun()

# --- PAINEL PRINCIPAL ---
st.title("🛡️ TI Gestão - SMS Aquidauana")

if not df_cotacao.empty:
    def gerar_pdf_dual(data, modo="final"):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Cabeçalho Institucional
        pdf.set_fill_color(0, 51, 102) 
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("helvetica", 'B', 14)
        pdf.cell(190, 12, remover_acentos("PREFEITURA MUNICIPAL DE AQUIDAUANA"), ln=True, align='C', fill=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("helvetica", 'B', 11)
        pdf.cell(190, 8, "SECRETARIA MUNICIPAL DE SAÚDE - SMS", ln=True, align='C')
        
        titulo = "MAPA DE COTACÃO" if modo == "mapa" else "RELATORIO DE ESTIMATIVA"
        pdf.set_font("helvetica", 'I', 10)
        pdf.cell(190, 7, titulo, ln=True, align='C')
        pdf.ln(5)

        for categoria in data['Categoria'].unique():
            # Título do Grupo
            pdf.set_font("helvetica", 'B', 10)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(190, 7, f" GRUPO: {remover_acentos(categoria).upper()}", border=1, ln=True, fill=True)
            
            # --- CABEÇALHO DA TABELA (O que estava faltando!) ---
            pdf.set_font("helvetica", 'B', 8)
            pdf.cell(110, 7, "DESCRICÃO", border=1, align='C')
            pdf.cell(15, 7, "QTD", border=1, align='C')
            pdf.cell(30, 7, "UNIT. (RS)", border=1, align='C')
            pdf.cell(35, 7, "TOTAL (RS)", border=1, ln=True, align='C')

            itens = data[data['Categoria'] == categoria]
            for _, r in itens.iterrows():
                v_u = "........" if modo == "mapa" else f"{r['Unitário']:,.2f}"
                v_t = "........" if modo == "mapa" else f"{r['Total']:,.2f}"
                
                pdf.set_font("helvetica", '', 8)
                desc = remover_acentos(f"{r['Item']} - {r['Especificação']}")
                
                # Cálculo de altura dinâmica para a descrição
                x, y = pdf.get_x(), pdf.get_y()
                pdf.multi_cell(110, 6, desc, border=1)
                final_y = pdf.get_y()
                altura = final_y - y
                
                # Preenche as colunas de valores mantendo a altura da descrição
                pdf.set_xy(x + 110, y)
                pdf.cell(15, altura, str(int(r['Qtd'])), border=1, align='C')
                pdf.cell(30, altura, v_u, border=1, align='R')
                pdf.cell(35, altura, v_t, border=1, ln=True, align='R')
        
        # Rodapé de Totais ou Assinatura
        pdf.ln(5)
        if modo == "final":
            pdf.set_font("helvetica", 'B', 11)
            pdf.cell(155, 10, "TOTAL GERAL RS ", border=1, align='R')
            pdf.cell(35, 10, f"{data['Total'].sum():,.2f}", border=1, align='R')
        else:
            pdf.set_font("helvetica", 'I', 9)
            pdf.cell(190, 10, remover_acentos("VALIDADE DA PROPOSTA: _____ DIAS  |  PRAZO DE ENTREGA: _____ DIAS"), ln=True)
            pdf.ln(10)
            pdf.cell(190, 5, "__________________________________________________", ln=True, align='C')
            pdf.cell(190, 5, "ASSINATURA E CARIMBO DO PROPONENTE (CNPJ)", ln=True, align='C')
            
        return pdf.output()
    
    # --- ÁREA DE EXCLUSÃO ---
    with st.expander("❌ Remover Itens Específicos"):
        col_exc, col_btn = st.columns([3, 1])
        item_para_remover = col_exc.selectbox("Selecione o item para excluir", 
                                              options=df_cotacao['ID'].tolist(),
                                              format_func=lambda x: f"ID {x} - {df_cotacao[df_cotacao['ID']==x]['Item'].values[0]}")
        if col_btn.button("🗑️ Excluir Item"):
            df_novo = df_cotacao[df_cotacao['ID'] != item_para_remover]
            df_novo.to_csv('cotacoes.csv', index=False)
            st.success("Item removido!")
            st.rerun()

    # Botões de PDF (Mesma lógica)
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("📄 Baixar Mapa", data=bytes(gerar_pdf_dual(df_cotacao, "mapa")), file_name="Mapa.pdf")
    with c2: st.download_button("💰 Baixar Relatório", data=bytes(gerar_pdf_dual(df_cotacao, "final")), file_name="Relatorio.pdf")
    with c3:
        if st.button("🚨 Resetar Tudo"):
            if os.path.exists('cotacoes.csv'): os.remove('cotacoes.csv')
            st.rerun()

    st.dataframe(df_cotacao, use_container_width=True)
else:
    st.info("Adicione itens para começar.")

