import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime
import plotly.express as px

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="TI Saúde - Aquidauana", layout="wide")

# 1. BIBLIOTECA PADRÃO (ESTÁTICA)
biblioteca_padrao = {
    "🛠️ MANUTENÇÃO E LABORATÓRIO": {
        "Estação de Solda e Retrabalho": "Digital, com soprador de ar quente e controle ESD.",
        "Microscópio Digital USB 1000x": "Para inspeção de trilhas e soldas SMD.",
        "Multímetro Digital True RMS": "Auto-range, medição de capacitância e temperatura."
    },
    "💻 HARDWARE E UPGRADE": {
        "SSD NVMe M.2 500GB": "Interface PCIe Gen3 x4, alta performance.",
        "Memória RAM DDR4 16GB": "Frequência 3200MHz corporativa."
    },
    "🌐 REDES E INFRAESTRUTURA": {
        "Switch 24p Gigabit Rack": "10/100/1000 Mbps, padrão 19 polegadas.",
        "Cabo de Rede CAT6 (305m)": "100% Cobre, homologado Anatel."
    },
    "🔌 ELÉTRICA E ENERGIA": {
        "Nobreak Senoidal 1500VA": "Ideal para servidores e racks de rede.",
        "Filtro de Linha DPS iClamper": "Proteção real contra surtos elétricos."
    }
}

# 2. FUNÇÕES PARA GERENCIAR A "MEMÓRIA" DO SISTEMA (BIBLIOTECA CUSTOM)
def carregar_biblioteca_custom():
    if not os.path.exists('minha_biblioteca.csv'):
        return pd.DataFrame(columns=['Categoria', 'Item', 'Especificacao'])
    return pd.read_csv('minha_biblioteca.csv')

def salvar_na_biblioteca(cat, item, espec):
    df_custom = carregar_biblioteca_custom()
    # Evita duplicados
    if not ((df_custom['Categoria'] == cat) & (df_custom['Item'] == item)).any():
        novo_item = pd.DataFrame([[cat, item, espec]], columns=['Categoria', 'Item', 'Especificacao'])
        novo_item.to_csv('minha_biblioteca.csv', mode='a', header=not os.path.exists('minha_biblioteca.csv'), index=False)

# Mescla a biblioteca padrão com a que você alimentou
df_bib_custom = carregar_biblioteca_custom()
biblioteca_ativa = biblioteca_padrao.copy()

for _, row in df_bib_custom.iterrows():
    if row['Categoria'] not in biblioteca_ativa:
        biblioteca_ativa[row['Categoria']] = {}
    biblioteca_ativa[row['Categoria']][row['Item']] = row['Especificacao']

# 3. GESTÃO DE COTAÇÕES
COLUNAS_COTACAO = ['Data', 'Categoria', 'Item', 'Qtd', 'Unitário', 'Total', 'Especificação']
def carregar_cotacoes():
    if not os.path.exists('cotacoes.csv'): return pd.DataFrame(columns=COLUNAS_COTACAO)
    try: return pd.read_csv('cotacoes.csv')
    except: return pd.DataFrame(columns=COLUNAS_COTACAO)

df_cotacao = carregar_cotacoes()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🏢 SMS Aquidauana")
    
    opcoes_categorias = list(biblioteca_ativa.keys()) + ["🆕 ADICIONAR NOVA CATEGORIA"]
    cat_sel = st.selectbox("Categoria", opcoes_categorias)
    
    # Lógica para Nova Categoria ou Categoria Existente
    if cat_sel == "🆕 ADICIONAR NOVA CATEGORIA":
        cat_final = st.text_input("Nome da Nova Categoria")
        nome_sel = st.text_input("Nome do Material")
        espec_sel = st.text_area("Especificação Técnica")
    else:
        cat_final = cat_sel
        itens_da_cat = list(biblioteca_ativa[cat_sel].keys()) + ["+ Adicionar Novo Item nesta Categoria"]
        prod_sel = st.selectbox("Produto", itens_da_cat)
        
        if prod_sel == "+ Adicionar Novo Item nesta Categoria":
            nome_sel = st.text_input("Nome do Novo Material")
            espec_sel = st.text_area("Especificação Técnica")
        else:
            nome_sel = prod_sel
            espec_sel = st.text_area("Especificação", value=biblioteca_ativa[cat_sel][prod_sel])

    qtd_sel = st.number_input("Quantidade", min_value=1, value=1)
    preco_sel = st.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f")
    
    salvar_fixo = st.checkbox("💾 Salvar este item permanentemente na biblioteca", value=False)
    
    if st.button("📥 Registrar na Cotação"):
        hoje = datetime.now().strftime("%d/%m/%Y")
        
        # 1. Salva na Biblioteca se o checkbox estiver marcado
        if salvar_fixo:
            salvar_na_biblioteca(cat_final, nome_sel, espec_sel)
            
        # 2. Salva na Cotação Atual
        nova_linha = pd.DataFrame([[hoje, cat_final, nome_sel, qtd_sel, preco_sel, qtd_sel*preco_sel, espec_sel]], columns=COLUNAS_COTACAO)
        nova_linha.to_csv('cotacoes.csv', mode='a', header=not os.path.exists('cotacoes.csv'), index=False)
        
        st.success("Registrado!")
        st.rerun()

# --- DASHBOARD (Mantendo a lógica que você já aprovou) ---
st.title("🛡️ Sistema de Gestão TI - Aquidauana")

if not df_cotacao.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Investimento Total", f"R$ {df_cotacao['Total'].sum():,.2f}")
    m2.metric("Itens na Lista", int(df_cotacao['Qtd'].sum()))
    m3.metric("Categorias", len(df_cotacao['Categoria'].unique()))

    # Gráficos
    g1, g2 = st.columns(2)
    with g1:
        fig_pie = px.pie(df_cotacao, values='Total', names='Categoria', hole=0.4, title="Divisão de Custos")
        st.plotly_chart(fig_pie, use_container_width=True)
    with g2:
        resumo = df_cotacao.groupby('Categoria')['Total'].sum().reset_index()
        fig_bar = px.bar(resumo, x='Categoria', y='Total', color='Categoria', title="Custo por Grupo")
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- FUNÇÃO DO PDF DUAL (MAPA E FINAL) ---
    def gerar_pdf_dual(data, modo="final"):
        pdf = FPDF()
        pdf.add_page()
        def limpar_texto(txt): return txt.encode('ascii', 'ignore').decode('ascii').strip()
        pdf.set_font("helvetica", 'B', 14)
        pdf.cell(190, 10, "SECRETARIA MUNICIPAL DE SAUDE - AQUIDAUANA", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.set_font("helvetica", 'B', 12)
        titulo = "MAPA DE COTACAO" if modo == "mapa" else "RELATORIO FINAL DE ESTIMATIVA"
        pdf.cell(190, 7, titulo, new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(10)

        for categoria in data['Categoria'].unique():
            pdf.set_font("helvetica", 'B', 11)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(190, 8, f" CATEGORIA: {limpar_texto(categoria)}", border=1, new_x="LMARGIN", new_y="NEXT", fill=True)
            itens = data[data['Categoria'] == categoria]
            for _, r in itens.iterrows():
                pdf.set_font("helvetica", 'B', 9)
                pdf.cell(100, 7, f" {limpar_texto(r['Item'])}", border='LTR')
                pdf.cell(20, 7, str(r['Qtd']), border='LTR', align='C')
                v_u = " RS .........." if modo == "mapa" else f" RS {r['Unitário']:,.2f}"
                v_t = " RS .........." if modo == "mapa" else f" RS {r['Total']:,.2f}"
                pdf.cell(35, 7, v_u, border='LTR', align='R')
                pdf.cell(35, 7, v_t, border='LTR', new_x="LMARGIN", new_y="NEXT", align='R')
                pdf.set_font("helvetica", 'I', 8)
                pdf.multi_cell(190, 5, f" Especificacao: {limpar_texto(r['Especificação'])}", border='LBR')
            pdf.ln(3)
        
        if modo == "final":
            pdf.ln(5)
            pdf.set_font("helvetica", 'B', 12)
            pdf.cell(190, 10, f"TOTAL GERAL: RS {data['Total'].sum():,.2f}", border=1, align='R')
        return pdf.output()

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📄 Baixar Mapa de Cotação", data=bytes(gerar_pdf_dual(df_cotacao, "mapa")), file_name="Mapa_SMS.pdf")
    with c2:
        st.download_button("💰 Baixar Relatório Final", data=bytes(gerar_pdf_dual(df_cotacao, "final")), file_name="Relatorio_SMS.pdf")
    with c3:
        if st.button("🗑️ Resetar Cotação Atual"):
            if os.path.exists('cotacoes.csv'): os.remove('cotacoes.csv')
            st.rerun()

    st.dataframe(df_cotacao, use_container_width=True)
else:
    st.info("👋 Comece a lançar os itens. Marque 'Salvar permanentemente' para alimentar seu banco de dados.")