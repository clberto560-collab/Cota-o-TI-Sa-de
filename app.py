import streamlit as st
import pandas as pd
import os
import unicodedata
from fpdf import FPDF
from datetime import datetime

# --- FUNÇÃO MESTRE DE TRATAMENTO DE TEXTO ---
def tratar_texto(texto):
    if texto is None: return " "
    texto = str(texto)
    
    # 1. Remove emojis específicos que costumam travar a fonte Helvetica
    emojis = ["🛠", "🌐", "💾", "📥", "📄", "💰", "🚨", "🏢", "🔐", "🛡️"]
    for e in emojis:
        texto = texto.replace(e, "")
    
    # 2. Converte para Latin-1 (padrão do PDF) ignorando símbolos incompatíveis
    # Isso mantém acentos (á, é, í, ó, ú, ç, ã) e remove o que causa "???"
    try:
        return texto.encode('iso-8859-1', 'ignore').decode('iso-8859-1').strip()
    except:
        return texto.strip()

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="TI Saúde - Aquidauana", layout="wide")

# --- SISTEMA DE LOGIN ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.markdown("<h1 style='text-align: center;'>🔐 Acesso Restrito - TI SMS</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            senha = st.text_input("Digite a senha:", type="password")
            if st.button("Entrar"):
                if senha == "1234":
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
        return False
    return True

if check_password():
    # BIBLIOTECA PADRÃO
    biblioteca_padrao = {
        "MANUTENCAO": {"SSD 500GB": "SSD NVMe M.2 500GB alta performance."},
        "REDES": {"Switch 24p": "Switch Gigabit Rack 19 polegadas."}
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

    df_bib_custom = carregar_biblioteca_custom()
    biblioteca_ativa = biblioteca_padrao.copy()
    for _, row in df_bib_custom.iterrows():
        cat = str(row['Categoria'])
        if cat not in biblioteca_ativa: biblioteca_ativa[cat] = {}
        biblioteca_ativa[cat][str(row['Item'])] = str(row['Especificacao'])

    COLUNAS_COTACAO = ['ID', 'Data', 'Categoria', 'Item', 'Qtd', 'Unitário', 'Total', 'Especificação']
    def carregar_cotacoes():
        if not os.path.exists('cotacoes.csv'): return pd.DataFrame(columns=COLUNAS_COTACAO)
        df = pd.read_csv('cotacoes.csv')
        # Garante que as colunas numéricas sejam tratadas como tal
        df['Unitário'] = pd.to_numeric(df['Unitário'], errors='coerce').fillna(0.0)
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0.0)
        return df

    df_cotacao = carregar_cotacoes()

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🏢 SMS Aquidauana")
        if st.button("Sair/Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        opcoes_categorias = list(biblioteca_ativa.keys()) + ["NOVA CATEGORIA"]
        cat_sel = st.selectbox("Categoria", opcoes_categorias)
        
        if cat_sel == "NOVA CATEGORIA":
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
            pdf.cell(190, 12, tratar_texto("PREFEITURA MUNICIPAL DE AQUIDAUANA"), align='C', fill=True, new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("helvetica", 'B', 11)
            pdf.cell(190, 8, tratar_texto("SECRETARIA MUNICIPAL DE SAÚDE - SMS"), align='C', new_x="LMARGIN", new_y="NEXT")
            
            titulo = "MAPA DE COTAÇÃO" if modo == "mapa" else "RELATÓRIO DE ESTIMATIVA"
            pdf.set_font("helvetica", 'I', 10)
            pdf.cell(190, 7, tratar_texto(titulo), align='C', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

            for categoria in data['Categoria'].unique():
                # Título do Grupo (Limpa Emojis)
                pdf.set_font("helvetica", 'B', 10)
                pdf.set_fill_color(240, 240, 240)
                cat_txt = f" GRUPO: {categoria.upper()}"
                pdf.cell(190, 7, tratar_texto(cat_txt), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
                
                # Cabeçalho da Tabela
                pdf.set_font("helvetica", 'B', 8)
                pdf.cell(110, 7, tratar_texto("DESCRIÇÃO"), border=1, align='C')
                pdf.cell(15, 7, "QTD", border=1, align='C')
                pdf.cell(30, 7, tratar_texto("UNIT. (R$)"), border=1, align='C')
                pdf.cell(35, 7, tratar_texto("TOTAL (R$)"), border=1, align='C', new_x="LMARGIN", new_y="NEXT")

                itens = data[data['Categoria'] == categoria]
                for _, r in itens.iterrows():
                    # Formatação de Moeda e Mapa
                    v_u = "........" if modo == "mapa" else f"{float(r['Unitário']):,.2f}"
                    v_t = "........" if modo == "mapa" else f"{float(r['Total']):,.2f}"
                    
                    pdf.set_font("helvetica", '', 8)
                    desc_item = f"{r['Item']} - {r['Especificação']}"
                    
                    x, y = pdf.get_x(), pdf.get_y()
                    pdf.multi_cell(110, 6, tratar_texto(desc_item), border=1)
                    final_y = pdf.get_y()
                    altura = final_y - y
                    
                    pdf.set_xy(x + 110, y)
                    pdf.cell(15, altura, str(int(r['Qtd'])), border=1, align='C')
                    pdf.cell(30, altura, v_u, border=1, align='R')
                    pdf.cell(35, altura, v_t, border=1, align='R', new_x="LMARGIN", new_y="NEXT")
            
            pdf.ln(5)
            if modo == "final":
                pdf.set_font("helvetica", 'B', 11)
                total_geral = data['Total'].sum()
                pdf.cell(155, 10, tratar_texto("TOTAL GERAL R$ "), border=1, align='R')
                pdf.cell(35, 10, f"{total_geral:,.2f}", border=1, align='R', new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.set_font("helvetica", 'I', 9)
                pdf.cell(190, 10, tratar_texto("VALIDADE DA PROPOSTA: _____ DIAS  |  PRAZO DE ENTREGA: _____ DIAS"), new_x="LMARGIN", new_y="NEXT")
                pdf.ln(10)
                pdf.cell(190, 5, "__________________________________________________", align='C', new_x="LMARGIN", new_y="NEXT")
                pdf.cell(190, 5, tratar_texto("ASSINATURA E CARIMBO DO PROPONENTE (CNPJ)"), align='C', new_x="LMARGIN", new_y="NEXT")
            
            return bytes(pdf.output())

        with st.expander("❌ Remover Itens Específicos"):
            col_exc, col_btn = st.columns([3, 1])
            item_para_remover = col_exc.selectbox("Selecione o ID", options=df_cotacao['ID'].tolist())
            if col_btn.button("🗑️ Excluir"):
                df_novo = df_cotacao[df_cotacao['ID'] != item_para_remover]
                df_novo.to_csv('cotacoes.csv', index=False)
                st.rerun()

        c1, c2, c3 = st.columns(3)
        with c1: st.download_button("📄 Baixar Mapa", data=gerar_pdf_dual(df_cotacao, "mapa"), file_name="Mapa.pdf")
        with c2: st.download_button("💰 Baixar Relatório", data=gerar_pdf_dual(df_cotacao, "final"), file_name="Relatorio.pdf")
        with c3:
            if st.button("🚨 Resetar Tudo"):
                if os.path.exists('cotacoes.csv'): os.remove('cotacoes.csv')
                st.rerun()

        st.dataframe(df_cotacao, width="stretch")
    else:
        st.info("Adicione itens para começar.")
