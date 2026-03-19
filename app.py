import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime

# --- FUNÇÃO DE TRATAMENTO DE TEXTO (Padrão Aquidauana) ---
def tratar_texto(texto):
    if texto is None: return ""
    texto = str(texto).replace('\xa0', ' ')
    emojis = ["🛠", "🌐", "💾", "📥", "📄", "💰", "🚨", "🏢", "🔐", "🛡️", "🏛️", "⚙️"]
    for e in emojis:
        texto = texto.replace(e, "")
    try:
        return texto.encode('iso-8859-1', 'ignore').decode('iso-8859-1').strip()
    except:
        return texto.strip()

# --- CONFIGURAÇÕES E BANCO ---
st.set_page_config(page_title="TI Gestão - Aquidauana", page_icon="🏛️", layout="wide")

def carregar_bib():
    if not os.path.exists('minha_biblioteca.csv'):
        return pd.DataFrame(columns=['Categoria', 'Item', 'Especificacao'])
    return pd.read_csv('minha_biblioteca.csv')

def salvar_item_bib(cat, item, espec):
    df = carregar_bib()
    # Atualiza se já existir
    df = df[~((df['Categoria'] == cat) & (df['Item'] == item))]
    nova_linha = pd.DataFrame([[cat, item, espec]], columns=['Categoria', 'Item', 'Especificacao'])
    df = pd.concat([df, nova_linha], ignore_index=True)
    df.to_csv('minha_biblioteca.csv', index=False)

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🔐 TI SMS - Aquidauana</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if senha == "1234": 
                st.session_state.auth = True
                st.rerun()
            else: st.error("Senha incorreta")
    st.stop()

# --- INTERFACE ---
tab1, tab2, tab3 = st.tabs(["📝 Gerar Cotação", "📚 Biblioteca", "⚙️ Adicionar Itens"])

# --- ABA 1: GERAÇÃO DE COTAÇÃO ---
with tab1:
    df_bib = carregar_bib()
    if df_bib.empty:
        st.warning("Biblioteca vazia! Vá em 'Adicionar Itens' para cadastrar seus produtos.")
    else:
        with st.sidebar:
            if os.path.exists('brasao.png'): st.image('brasao.png', width=100)
            st.header("Nova Cotação")
            
            cat_sel = st.selectbox("Categoria", sorted(df_bib['Categoria'].unique().tolist()))
            prod_sel = st.selectbox("Produto", df_bib[df_bib['Categoria'] == cat_sel]['Item'].tolist())
            
            espec_db = df_bib[(df_bib['Item'] == prod_sel)]['Especificacao'].values[0]
            espec_final = st.text_area("Revisar Especificação", value=espec_db, height=200)
            
            qtd = st.number_input("Qtd", min_value=1, value=1)
            preco = st.number_input("Preço Unitário", min_value=0.0, format="%.2f")
            
            if st.button("📥 Adicionar à Cotação"):
                if not os.path.exists('cotacoes.csv'):
                    df_c = pd.DataFrame(columns=['ID','Data','Categoria','Item','Qtd','Unitário','Total','Especificação'])
                    df_c.to_csv('cotacoes.csv', index=False)
                
                df_c = pd.read_csv('cotacoes.csv')
                n_id = int(df_c['ID'].max() + 1) if not df_c.empty else 1
                nova = pd.DataFrame([[n_id, datetime.now().strftime("%d/%m/%Y"), cat_sel, prod_sel, qtd, preco, qtd*preco, espec_final]], columns=df_c.columns)
                nova.to_csv('cotacoes.csv', mode='a', header=False, index=False)
                st.rerun()

        st.title("🏛️ Mapa de Preços")
        if os.path.exists('cotacoes.csv'):
            df_atual = pd.read_csv('cotacoes.csv')
            st.dataframe(df_atual, use_container_width=True)
            
            if st.button("🗑️ Limpar Itens da Cotação Atual"): 
                os.remove('cotacoes.csv')
                st.rerun()

# --- ABA 2: BIBLIOTECA (COM BOTÃO DE ZERAR) ---
with tab2:
    st.header("📚 Itens Cadastrados na Base")
    df_visualizar = carregar_bib()
    st.dataframe(df_visualizar, use_container_width=True)
    
    st.divider()
    st.subheader("🚨 Zona de Perigo")
    if st.button("🔥 ZERAR BIBLIOTECA COMPLETA"):
        if os.path.exists('minha_biblioteca.csv'):
            os.remove('minha_biblioteca.csv')
            st.success("Biblioteca apagada com sucesso!")
            st.rerun()

# --- ABA 3: ADICIONAR ITENS  ---
with tab3:
    st.header("⚙️ Cadastro de Itens ")
    st.write("Insira os dados técnicos para alimentar sua biblioteca permanente.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        nova_cat = st.selectbox("Categoria", ["HARDWARE", "REDES", "INFRAESTRUTURA", "FERRAMENTAS", "PERIFÉRICOS", "OUTROS"])
    with col_b:
        novo_nome = st.text_input("Nome do Equipamento (Ex: Desktop Tipo 01)")
    
    texto_word = st.text_area("Especificação Técnica (Cole aqui o texto do Word)", height=300)
    
    if st.button("💾 Salvar na Biblioteca"):
        if novo_nome and texto_word:
            salvar_item_bib(nova_cat, novo_nome, texto_word)
            st.success(f"Item '{novo_nome}' salvo com sucesso!")
            st.rerun()
        else:
            st.error("Por favor, preencha o Nome e a Especificação.")
