import os
import re
import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st
from fpdf import FPDF
from pandas.errors import EmptyDataError, ParserError


BIBLIOTECA_ARQ = "minha_biblioteca.csv"
COTACOES_ARQ = "cotacoes.csv"
BRASAO_ARQ = "brasao.png"

BIB_COLS = ["Categoria", "Item", "Especificacao"]
COTACAO_COLS = ["ID", "Data", "Categoria", "Item", "Qtd", "Unitário", "Total", "Especificação"]


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Compatibiliza nomes antigos/sem acento com os nomes usados no app."""
    mapa = {
        "Unitario": "Unitário",
        "unitario": "Unitário",
        "Preço Unitário": "Unitário",
        "Preco Unitario": "Unitário",
        "Especificacao": "Especificação",
        "especificacao": "Especificação",
    }
    df = df.rename(columns={col: mapa.get(col, col) for col in df.columns})
    return df


def carregar_csv_seguro(caminho: str, colunas: list[str]) -> pd.DataFrame:
    if not os.path.exists(caminho):
        return pd.DataFrame(columns=colunas)

    try:
        df = pd.read_csv(caminho, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(caminho, encoding="latin-1")
    except (EmptyDataError, ParserError):
        st.warning(f"O arquivo {caminho} está vazio ou com formato inválido. Ele será tratado como vazio.")
        return pd.DataFrame(columns=colunas)

    if "Especificação" in colunas:
        df = normalizar_colunas(df)
    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = ""
    return df[colunas]


def salvar_csv_seguro(df: pd.DataFrame, caminho: str) -> None:
    df.to_csv(caminho, index=False, encoding="utf-8-sig")


def carregar_bib() -> pd.DataFrame:
    df = carregar_csv_seguro(BIBLIOTECA_ARQ, BIB_COLS)
    # A biblioteca usa "Especificacao" sem acento para manter compatibilidade com a base atual.
    if "Especificação" in df.columns and "Especificacao" not in df.columns:
        df = df.rename(columns={"Especificação": "Especificacao"})
    for coluna in BIB_COLS:
        if coluna not in df.columns:
            df[coluna] = ""
    return df[BIB_COLS].dropna(how="all")


def carregar_cotacoes() -> pd.DataFrame:
    df = carregar_csv_seguro(COTACOES_ARQ, COTACAO_COLS)
    if df.empty:
        return df

    df["Qtd"] = pd.to_numeric(df["Qtd"], errors="coerce").fillna(0).astype(int)
    df["Unitário"] = pd.to_numeric(df["Unitário"], errors="coerce").fillna(0.0)
    df["Total"] = df["Qtd"] * df["Unitário"]
    return df


def salvar_item_bib(cat: str, item: str, espec: str) -> None:
    df = carregar_bib()
    df = df[~((df["Categoria"] == cat) & (df["Item"] == item))]
    nova_linha = pd.DataFrame([[cat, item, espec]], columns=BIB_COLS)
    salvar_csv_seguro(pd.concat([df, nova_linha], ignore_index=True), BIBLIOTECA_ARQ)


def limpar_texto_pdf(texto) -> str:
    """Remove caracteres que quebram fontes padrão do FPDF e preserva acentos latinos."""
    if texto is None or pd.isna(texto):
        return ""

    texto = str(texto).replace("\xa0", " ")
    substituicoes = {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "-",
        "\u00b5": "u",
        "\u2122": "",
        "\u00ae": "",
    }
    for original, novo in substituicoes.items():
        texto = texto.replace(original, novo)

    texto = unicodedata.normalize("NFC", texto)
    texto = re.sub(r"[\U00010000-\U0010ffff]", "", texto)
    texto = texto.encode("latin-1", "ignore").decode("latin-1")
    return texto.strip()


def formatar_moeda(valor) -> str:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        numero = 0.0
    texto = f"R$ {numero:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def linhas_texto(pdf: FPDF, texto: str, largura: float) -> list[str]:
    texto = limpar_texto_pdf(texto)
    largura_util = max(largura - 2, 10)
    linhas = []

    for bloco in texto.splitlines() or [""]:
        palavras = bloco.split(" ")
        atual = ""
        for palavra in palavras:
            tentativa = palavra if not atual else f"{atual} {palavra}"
            if pdf.get_string_width(tentativa) <= largura_util:
                atual = tentativa
            else:
                if atual:
                    linhas.append(atual)
                # Quebra palavras muito longas.
                while pdf.get_string_width(palavra) > largura_util and len(palavra) > 1:
                    corte = len(palavra)
                    while corte > 1 and pdf.get_string_width(palavra[:corte]) > largura_util:
                        corte -= 1
                    linhas.append(palavra[:corte])
                    palavra = palavra[corte:]
                atual = palavra
        linhas.append(atual)
    return linhas or [""]


def adicionar_cabecalho_pdf(pdf: FPDF) -> None:
    if os.path.exists(BRASAO_ARQ):
        pdf.image(BRASAO_ARQ, x=10, y=9, w=18)
        pdf.image(BRASAO_ARQ, x=182, y=9, w=18)

    # A faixa azul fica entre os dois brasões para não cobrir as imagens.
    pdf.set_xy(32, 10)
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(146, 11, limpar_texto_pdf("PREFEITURA MUNICIPAL DE AQUIDAUANA"), ln=True, align="C", fill=True)

    pdf.set_x(10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 7, limpar_texto_pdf("SECRETARIA MUNICIPAL DE SAÚDE - SMS"), ln=True, align="C")
    pdf.set_font("Arial", "I", 10)
    pdf.cell(190, 7, limpar_texto_pdf("MAPA DE COTAÇÃO DE PREÇOS"), ln=True, align="C")
    pdf.set_font("Arial", "", 8)
    pdf.cell(190, 5, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="R")
    pdf.ln(4)


def adicionar_cabecalho_tabela(pdf: FPDF) -> None:
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(110, 7, limpar_texto_pdf("DESCRIÇÃO / ESPECIFICAÇÃO"), border=1, align="C", fill=True)
    pdf.cell(15, 7, "QTD", border=1, align="C", fill=True)
    pdf.cell(30, 7, "UNIT. (R$)", border=1, align="C", fill=True)
    pdf.cell(35, 7, "TOTAL (R$)", border=1, ln=True, align="C", fill=True)


def garantir_espaco(pdf: FPDF, altura: float, categoria: str | None = None) -> None:
    if pdf.get_y() + altura > pdf.page_break_trigger:
        pdf.add_page()
        adicionar_cabecalho_pdf(pdf)
        if categoria:
            adicionar_grupo(pdf, categoria)
            adicionar_cabecalho_tabela(pdf)


def adicionar_grupo(pdf: FPDF, categoria: str) -> None:
    garantir_espaco(pdf, 10)
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 8, limpar_texto_pdf(f" GRUPO: {str(categoria).upper()}"), border=1, ln=True, fill=True)


def adicionar_linha_item(pdf: FPDF, row: pd.Series, categoria: str) -> None:
    desc = f"{row['Item']} - {row['Especificação']}"
    pdf.set_font("Arial", "", 7.6)
    linhas = linhas_texto(pdf, desc, 110)
    line_h = 4.2
    altura = max(8, len(linhas) * line_h + 2)

    garantir_espaco(pdf, altura, categoria)

    x = pdf.get_x()
    y = pdf.get_y()

    pdf.rect(x, y, 110, altura)
    pdf.set_xy(x + 1, y + 1)
    for linha in linhas:
        pdf.cell(108, line_h, linha, ln=True)

    pdf.set_xy(x + 110, y)
    pdf.set_font("Arial", "", 8)
    pdf.cell(15, altura, str(int(row["Qtd"])), border=1, align="C")
    pdf.cell(30, altura, formatar_moeda(row["Unitário"]), border=1, align="R")
    pdf.cell(35, altura, formatar_moeda(row["Total"]), border=1, ln=True, align="R")


def gerar_pdf_cotacao(df: pd.DataFrame) -> bytes:
    if df.empty:
        raise ValueError("Não há itens na cotação para gerar PDF.")

    df = normalizar_colunas(df.copy())
    df["Qtd"] = pd.to_numeric(df["Qtd"], errors="coerce").fillna(0).astype(int)
    df["Unitário"] = pd.to_numeric(df["Unitário"], errors="coerce").fillna(0.0)
    df["Total"] = df["Qtd"] * df["Unitário"]

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    adicionar_cabecalho_pdf(pdf)

    for categoria in df["Categoria"].dropna().unique():
        adicionar_grupo(pdf, categoria)
        adicionar_cabecalho_tabela(pdf)
        itens = df[df["Categoria"] == categoria]
        for _, row in itens.iterrows():
            adicionar_linha_item(pdf, row, categoria)
        pdf.ln(2)

    garantir_espaco(pdf, 38)
    pdf.ln(4)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(155, 9, "TOTAL GERAL DO MAPA", border=1, align="R")
    pdf.cell(35, 9, formatar_moeda(df["Total"].sum()), border=1, ln=True, align="R")

    pdf.ln(8)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(190, 5, limpar_texto_pdf("VALIDADE DA PROPOSTA: _____ DIAS  |  PRAZO DE ENTREGA: _____ DIAS"), ln=True, align="C")
    pdf.ln(12)
    pdf.cell(190, 5, "__________________________________________________", ln=True, align="C")
    pdf.cell(190, 5, limpar_texto_pdf("ASSINATURA E CARIMBO DO PROPONENTE"), ln=True, align="C")

    saida = pdf.output(dest="S")
    if isinstance(saida, str):
        return saida.encode("latin-1", "ignore")
    return bytes(saida)


def obter_senha_configurada() -> str:
    try:
        return st.secrets.get("APP_PASSWORD", "@quidauana")
    except Exception:
        return "@quidauana"


st.set_page_config(page_title="TI Gestão - Aquidauana", page_icon="🏛️", layout="wide")


# --- LOGIN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🔐 TI SMS - Aquidauana</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        senha = st.text_input("Senha de Acesso", type="password")
        if st.button("Entrar"):
            if senha == obter_senha_configurada():
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Senha incorreta")
    st.stop()


# --- INTERFACE ---
tab1, tab2, tab3 = st.tabs(["📝 Gerar Cotação", "📚 Biblioteca", "⚙️ Adicionar Itens"])


# --- ABA 1: GERAÇÃO DE COTAÇÃO ---
with tab1:
    df_bib = carregar_bib()
    df_atual = carregar_cotacoes()

    if df_bib.empty:
        st.warning("Biblioteca vazia! Vá em 'Adicionar Itens' para cadastrar seus produtos.")
    else:
        with st.sidebar:
            st.header("Nova Cotação")
            categorias = sorted(df_bib["Categoria"].dropna().unique().tolist())
            cat_sel = st.selectbox("Categoria", categorias)
            produtos = df_bib[df_bib["Categoria"] == cat_sel]["Item"].dropna().tolist()
            prod_sel = st.selectbox("Produto", produtos)

            item_bib = df_bib[(df_bib["Categoria"] == cat_sel) & (df_bib["Item"] == prod_sel)]
            espec_db = item_bib["Especificacao"].iloc[0] if not item_bib.empty else ""
            espec_final = st.text_area("Revisar Especificação", value=espec_db, height=200)
            qtd = st.number_input("Qtd", min_value=1, value=1, step=1)
            preco = st.number_input("Preço Unitário", min_value=0.0, format="%.2f")

            if st.button("📥 Adicionar à Cotação"):
                n_id = int(pd.to_numeric(df_atual["ID"], errors="coerce").max() + 1) if not df_atual.empty else 1
                nova = pd.DataFrame(
                    [[n_id, datetime.now().strftime("%d/%m/%Y"), cat_sel, prod_sel, int(qtd), float(preco), int(qtd) * float(preco), espec_final]],
                    columns=COTACAO_COLS,
                )
                salvar_csv_seguro(pd.concat([df_atual, nova], ignore_index=True), COTACOES_ARQ)
                st.success("Item adicionado à cotação.")
                st.rerun()

    st.title("🏛️ Mapa de Preços")

    if df_atual.empty:
        st.info("Nenhum item adicionado à cotação ainda.")
    else:
        st.dataframe(df_atual, use_container_width=True)
        st.metric("Total geral", formatar_moeda(df_atual["Total"].sum()))

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            try:
                pdf_bytes = gerar_pdf_cotacao(df_atual)
                st.download_button(
                    label="📄 Baixar Mapa (PDF)",
                    data=pdf_bytes,
                    file_name="Mapa_Cotacao_SMS.pdf",
                    mime="application/pdf",
                )
            except Exception as exc:
                st.error(f"Não foi possível gerar o PDF: {exc}")

        with col_d2:
            confirmar_limpeza = st.checkbox("Confirmo que desejo limpar a cotação atual")
            if st.button("🗑️ Limpar Cotação", disabled=not confirmar_limpeza):
                if os.path.exists(COTACOES_ARQ):
                    os.remove(COTACOES_ARQ)
                st.success("Cotação limpa.")
                st.rerun()


# --- ABA 2: BIBLIOTECA ---
with tab2:
    st.header("📚 Itens Cadastrados na Base")
    df_visualizar = carregar_bib()
    if df_visualizar.empty:
        st.info("Nenhum item cadastrado na biblioteca.")
    else:
        st.dataframe(df_visualizar, use_container_width=True)

    confirmar_biblioteca = st.checkbox("Confirmo que desejo zerar a biblioteca")
    if st.button("🔥 ZERAR BIBLIOTECA", disabled=not confirmar_biblioteca):
        if os.path.exists(BIBLIOTECA_ARQ):
            os.remove(BIBLIOTECA_ARQ)
        st.success("Biblioteca zerada.")
        st.rerun()


# --- ABA 3: ADICIONAR ITENS ---
with tab3:
    st.header("⚙️ Cadastro de Itens")
    col_a, col_b = st.columns(2)
    with col_a:
        nova_cat = st.selectbox("Categoria", ["HARDWARE", "REDES", "INFRAESTRUTURA", "FERRAMENTAS", "PERIFÉRICOS", "OUTROS"])
    with col_b:
        novo_nome = st.text_input("Nome do Equipamento")

    texto_word = st.text_area("Especificação Técnica (Cole do Word)", height=300)
    if st.button("💾 Salvar na Biblioteca"):
        if novo_nome and texto_word:
            salvar_item_bib(nova_cat, novo_nome, texto_word)
            st.success(f"Item '{novo_nome}' salvo!")
            st.rerun()
        else:
            st.warning("Informe o nome do equipamento e a especificação técnica antes de salvar.")
