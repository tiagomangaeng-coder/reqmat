import streamlit as st
import pandas as pd
import os
from datetime import date
import time
from supabase import create_client, Client

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Sistema Vander Velden", 
    layout="wide", 
    page_icon="🏗️",
    initial_sidebar_state="auto" # Recolhe a sidebar no mobile automaticamente
)

# --- 2. CSS RESPONSIVO (O SEGREDO DA ADAPTAÇÃO) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Estilo Base - Design Premium */
        .stApp {
            background-color: #f8fafc;
        }
        
        /* Garantir contraste de texto em Labels e Markdowns */
        .stMarkdown, p, span, label, div {
            color: #1e293b;
        }
        
        /* Ajuste específico para Títulos e Métricas */
        h1, h2, h3, .metric-value {
            color: #1e3a8a !important;
        }

        /* Cards Modernos */
        .metric-card {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
            transition: transform 0.2s ease-in-out;
            text-align: center;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #1e3a8a;
            margin: 0;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 8px;
        }

        /* Estilização de Botões */
        div.stButton > button {
            border-radius: 12px;
            font-weight: 600;
            padding: 0.5rem 1rem;
            transition: all 0.2s;
            border: none;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        div.stButton > button:hover {
            opacity: 0.9;
            transform: scale(1.02);
        }

        /* Rodapé Refinado */
        .footer {
            position: fixed;
            left: 50%;
            bottom: 15px;
            transform: translateX(-50%);
            text-align: center;
            color: #94a3b8;
            font-size: 11px;
            z-index: 999;
            background: rgba(255, 255, 255, 0.9);
            padding: 8px 20px;
            border-radius: 50px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        /* MOBILE */
        @media (max-width: 768px) {
            .footer {
                position: static;
                transform: none;
                margin: 20px auto;
                width: 80%;
            }
            .metric-value { font-size: 1.5rem; }
        }

        /* SPLASH SCREEN OPTIMIZED */
        .splash-container {
            background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%);
        }
    </style>
    <div class="footer">
        ✨ Desenvolvido por <b>Tiago Manga</b> | Versão 1.2 Premium
    </div>
    """, unsafe_allow_html=True)

# --- 3. TELA DE ABERTURA (LOADER) ---
if 'splash_mostrado' not in st.session_state:
    st.session_state['splash_mostrado'] = True
    splash = st.empty()
    with splash.container():
        st.markdown("""
            <div class="splash-container">
                <div class="splash-title">Sistema de Requisições</div>
                <div class="splash-subtitle">Vander Velden</div>
                <div class="loader"></div>
            </div>
        """, unsafe_allow_html=True)
    time.sleep(3)
    splash.empty()

# --- CONFIGURAÇÃO SUPABASE ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    st.error("⚠️ Configurações do Supabase não encontradas! Configure st.secrets['SUPABASE_URL'] e st.secrets['SUPABASE_KEY'].")
    st.stop()

# --- FUNÇÕES DE BANCO (SUPABASE) ---
def buscar_dados(tabela):
    try:
        response = supabase.table(tabela).select("*").execute()
        df = pd.DataFrame(response.data)
        
        # Estrutura padrão (Garantir colunas caso a tabela esteja vazia)
        colunas_padrao = {
            'solicitacoes': ['id', 'id_pedido', 'obra', 'item', 'unidade', 'apropriacao', 'data_necessidade', 'solicitante', 'status_compra', 'data_previsao_entrega', 'recebido_na_obra', 'preco', 'fornecedor', 'quantidade'],
            'usuarios': ['id', 'usuario', 'senha', 'funcao', 'obras_acesso'],
            'obras': ['id', 'nome_obra', 'endereco', 'status'],
            'apropriacoes': ['id', 'obra', 'apropriacao'],
            'unidades': ['id', 'unidade']
        }
        
        if tabela in colunas_padrao:
            for col in colunas_padrao[tabela]:
                if col not in df.columns:
                    if col == 'preco': df[col] = 0
                    elif col == 'quantidade': df[col] = 1
                    else: df[col] = ""

        # Ajustes de tipos e colunas (compatibilidade com código antigo)
        if tabela == 'solicitacoes':
            colunas_de_data = ['data_necessidade', 'data_previsao_entrega']
            for col in colunas_de_data:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Garantir tipos numéricos
            df['preco'] = pd.to_numeric(df['preco'], errors='coerce').fillna(0)
            df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce').fillna(1)
            
            df = df.rename(columns={
                'id_pedido': 'ID_Pedido', 'obra': 'Obra', 'item': 'Item', 'unidade': 'Unidade',
                'apropriacao': 'Apropriacao', 'data_necessidade': 'Data_Necessidade',
                'solicitante': 'Solicitante', 'status_compra': 'Status_Compra',
                'data_previsao_entrega': 'Data_Previsao_Entrega', 'recebido_na_obra': 'Recebido_Na_Obra',
                'preco': 'Preço', 'fornecedor': 'Fornecedor', 'quantidade': 'Qtd'
            })
        elif tabela == 'usuarios':
            df = df.rename(columns={'usuario': 'Usuario', 'senha': 'Senha', 'funcao': 'Funcao', 'obras_acesso': 'Obras_Acesso'})
        elif tabela == 'obras':
            df = df.rename(columns={'nome_obra': 'Nome_Obra', 'endereco': 'Endereco', 'status': 'Status'})
        elif tabela == 'apropriacoes':
            df = df.rename(columns={'obra': 'Obra', 'apropriacao': 'Apropriacao'})
        elif tabela == 'unidades':
            df = df.rename(columns={'unidade': 'Unidade'})
            
        # Garantir que 'id' existe e está em minúsculo para operações internas
        if not df.empty and 'id' not in df.columns:
            # Caso o Supabase retorne ID (maiusculo) ou algo assim
            df.columns = [c.lower() if c.lower() == 'id' else c for c in df.columns]

        return df
    except Exception as e:
        st.error(f"Erro ao buscar dados de {tabela}: {e}")
        return pd.DataFrame()

def salvar_registro(tabela, dados):
    try:
        # Converter chaves para lowercase para o Supabase
        dados_formatados = {k.lower(): v for k, v in dados.items()}
        # Remover colunas que não existem no banco ou são geradas automaticamente
        dados_formatados.pop('id', None)
        
        supabase.table(tabela).insert(dados_formatados).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar em {tabela}: {e}")
        return False

def atualizar_registro(tabela, id_linha, dados):
    try:
        # Mapeamento reverso para garantir que o Supabase receba o nome correto das colunas
        map_reverse = {
            'Preço': 'preco', 'Fornecedor': 'fornecedor', 'Qtd': 'quantidade',
            'ID_Pedido': 'id_pedido', 'Obra': 'obra', 'Item': 'item', 'Unidade': 'unidade',
            'Apropriacao': 'apropriacao', 'Data_Necessidade': 'data_necessidade',
            'Solicitante': 'solicitante', 'Status_Compra': 'status_compra',
            'Data_Previsao_Entrega': 'data_previsao_entrega', 'Recebido_Na_Obra': 'recebido_na_obra',
            'Usuario': 'usuario', 'Senha': 'senha', 'Funcao': 'funcao', 'Obras_Acesso': 'obras_acesso',
            'Nome_Obra': 'nome_obra', 'Endereco': 'endereco', 'Status': 'status'
        }
        
        dados_formatados = {}
        for k, v in dados.items():
            db_key = map_reverse.get(k, k.lower())
            dados_formatados[db_key] = v

        # Converter datas para string ISO
        for k, v in dados_formatados.items():
            if isinstance(v, (date, pd.Timestamp)):
                dados_formatados[k] = v.strftime('%Y-%m-%d') if pd.notnull(v) else None
        
        # Filtro de atualização (no Supabase padrão é o ID do banco)
        supabase.table(tabela).update(dados_formatados).eq('id', id_linha).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar em {tabela}: {e}")
        return False

def gerar_proximo_id(obra, df_materiais):
    if df_materiais.empty: return f"{obra} - 001"
    df_obra = df_materiais[df_materiais['Obra'] == obra]
    if df_obra.empty: return f"{obra} - 001"
    
    ids = [str(x) for x in df_obra['ID_Pedido'].unique() if " - " in str(x)]
    if not ids: return f"{obra} - 001"
    
    try:
        nums = [int(x.split(' - ')[-1]) for x in ids]
        return f"{obra} - {max(nums) + 1:03d}"
    except:
        return f"{obra} - 001"

# --- INICIALIZAÇÃO ---
cols_materiais = [
    'ID_Pedido', 'Obra', 'Item', 'Unidade', 'Apropriacao', 'Data_Necessidade', 'Solicitante', 
    'Status_Compra', 'Data_Previsao_Entrega', 'Recebido_Na_Obra'
]

if 'df_usuarios' not in st.session_state:
    st.session_state['df_usuarios'] = buscar_dados('usuarios')
if 'df_obras' not in st.session_state:
    st.session_state['df_obras'] = buscar_dados('obras')
if 'df_materiais' not in st.session_state:
    st.session_state['df_materiais'] = buscar_dados('solicitacoes')
if 'df_apropriacoes' not in st.session_state:
    st.session_state['df_apropriacoes'] = buscar_dados('apropriacoes')
if 'df_unidades' not in st.session_state:
    st.session_state['df_unidades'] = buscar_dados('unidades')

# Helper para exportação
def converter_para_excel(df):
    from io import BytesIO
    output = BytesIO()
    # Usando openpyxl diretamente para evitar erros de compatibilidade
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Planilha1')
    return output.getvalue()

if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario_atual' not in st.session_state: st.session_state['usuario_atual'] = ''
if 'funcao_atual' not in st.session_state: st.session_state['funcao_atual'] = ''
if 'obras_permitidas' not in st.session_state: st.session_state['obras_permitidas'] = []
if 'carrinho_pedidos' not in st.session_state: st.session_state['carrinho_pedidos'] = []

# --- CALLBACKS ---
def callback_adicionar_ao_carrinho():
    st.session_state['carrinho_pedidos'].append({
        "Item": st.session_state.temp_item,
        "Qtd": st.session_state.temp_qtd,
        "Unidade": st.session_state.temp_unidade,
        "Apropriacao": st.session_state.temp_aprop,
        "Data_Necessidade": st.session_state.temp_data,
        "Solicitante": st.session_state['usuario_atual']
    })
    st.toast("Adicionado!", icon="🛒")

def callback_finalizar_pedido():
    if not st.session_state['carrinho_pedidos']: return
    obra = st.session_state.temp_obra_master
    novo_id = gerar_proximo_id(obra, st.session_state['df_materiais'])
    sucesso_total = True
    for item in st.session_state['carrinho_pedidos']:
        dn = item['Data_Necessidade'].strftime('%Y-%m-%d')
        novo_reg = {
            "id_pedido": novo_id, "obra": obra, "item": item['Item'], "quantidade": item['Qtd'],
            "unidade": item['Unidade'], "apropriacao": item['Apropriacao'], "data_necessidade": dn,
            "solicitante": item['Solicitante'], "status_compra": "Pendente", "recebido_na_obra": False
        }
        if not salvar_registro('solicitacoes', novo_reg):
            sucesso_total = False
    
    if sucesso_total:
        st.session_state['df_materiais'] = buscar_dados('solicitacoes')
        st.session_state['carrinho_pedidos'] = []
        st.success(f"Pedido {novo_id} gerado!")
    else:
        st.error("Houve um erro ao salvar alguns itens do pedido.")

# ==========================================================
# TELA DE LOGIN
# ==========================================================
if not st.session_state['logado']:
    # Layout responsivo: No PC usa colunas para centralizar, no Mobile usa largura total
    col_vazia, col_titulo, col_logo = st.columns([1, 4, 1])
    
    with col_titulo:
        st.markdown("""
            <h1 style='text-align: center; color: #2E4053;'>
                Sistema de Requisições<br>
                <span style='font-size: 24px; color: #E67E22;'>Vander Velden</span>
            </h1>
            """, unsafe_allow_html=True)
            
    with col_logo:
        if os.path.exists("logo.png"): st.image("logo.png", width=120)

    st.markdown("---")
    
    # Ajuste para Mobile: Se for tela pequena, o Streamlit empilha automaticamente.
    # Mas aqui garantimos que o container central seja largo o suficiente.
    c_vazia_esq, c_login, c_vazia_dir = st.columns([1, 2, 1]) # Aumentei o meio para 2
    with c_login:
        st.subheader("🔐 Acesso ao Sistema")
        with st.form("login"):
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                df = st.session_state['df_usuarios']
                user = df[(df['Usuario'].astype(str) == u) & (df['Senha'].astype(str) == s)]
                if not user.empty:
                    st.session_state['logado'] = True
                    st.session_state['usuario_atual'] = u
                    st.session_state['funcao_atual'] = user.iloc[0]['Funcao']
                    perms = str(user.iloc[0]['Obras_Acesso'])
                    st.session_state['obras_permitidas'] = perms.split(';') if perms else []
                    st.rerun()
                else:
                    st.error("Dados incorretos")
    st.stop()

# ==========================================================
# ÁREA LOGADA
# ==========================================================
usuario = st.session_state['usuario_atual']
funcao = st.session_state['funcao_atual']
todas_obras = st.session_state['df_obras']['Nome_Obra'].tolist()

if funcao in ['Administrador', 'Comprador'] or 'Todas' in st.session_state['obras_permitidas']:
    obras_visiveis = todas_obras
else:
    obras_visiveis = [o for o in todas_obras if o in st.session_state['obras_permitidas']]

if os.path.exists("logo.png"): st.sidebar.image("logo.png", width=150)

st.sidebar.markdown(f"**Usuário:** {st.session_state['usuario_atual']}")
st.sidebar.markdown(f"**Função:** {funcao}")
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False; st.session_state['carrinho_pedidos'] = []; st.rerun()

st.sidebar.divider()

# Dica de Formatação
st.sidebar.info("💡 **Dica:** Use ponto `.` para centavos (ex: 50.50) caso a vírgula não funcione no seu navegador.")

# Menu lateral
menu = st.sidebar.radio("Menu", ["📊 Dashboard", "📦 Gestão de Suprimentos", "⚙️ Configurações (Admin)"] if funcao == "Administrador" else ["📦 Gestão de Suprimentos"])

# --- MENU: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Painel de Indicadores")
    df = st.session_state['df_materiais']
    
    if df.empty:
        st.info("Nenhum dado disponível para gerar indicadores.")
    else:
        # Métricas em Cards
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{len(df['ID_Pedido'].unique())}</div>
                    <div class="metric-label">📦 Total de Pedidos</div>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            total_gasto = df['Preço'].sum()
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">R$ {total_gasto:,.2f}</div>
                    <div class="metric-label">💰 Investimento Total</div>
                </div>
            """, unsafe_allow_html=True)
        with c3:
            pendentes = len(df[df['Status_Compra'] == 'Pendente'])
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{pendentes}</div>
                    <div class="metric-label">⏳ Aguardando Compra</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        col_esq, col_dir = st.columns(2)
        
        with col_esq:
            st.subheader("Pedidos por Obra")
            obra_counts = df['Obra'].value_counts()
            st.bar_chart(obra_counts)
            
        with col_dir:
            st.subheader("Status das Solicitações")
            status_counts = df['Status_Compra'].value_counts()
            st.bar_chart(status_counts)
            
        st.divider()
        st.subheader("Maiores Investimentos por Item")
        top_itens = df.groupby('Item')['Preço'].sum().sort_values(ascending=False).head(10)
        st.area_chart(top_itens)

# --- MENU: GESTÃO DE SUPRIMENTOS ---
elif menu == "📦 Gestão de Suprimentos":
    st.title(f"Painel do {funcao}")

    # --- 1. USUARIO OBRA ---
    if funcao == "Usuario Obra":
        if not obras_visiveis: st.warning("Sem obras vinculadas.")
        else:
            obra_sel = st.selectbox("Obra:", obras_visiveis, key="temp_obra_master")
            st.divider()
            
            # Layout adaptativo: No celular, as colunas empilham.
            c_form, c_cart = st.columns(2)
            
            with c_form:
                st.subheader("1. Adicionar Item")
                with st.form("add_item", clear_on_submit=True):
                    l_aprop = st.session_state['df_apropriacoes'][st.session_state['df_apropriacoes']['Obra'] == obra_sel]['Apropriacao'].tolist()
                    c_item, c_qtd = st.columns([3, 1])
                    c_item.text_input("Item", key="temp_item", help="Ex: Cimento, Areia, Brita...")
                    c_qtd.number_input("Qtd", min_value=0.01, value=1.0, step=0.01, key="temp_qtd", help="Quantidade do material")
                    c1, c2 = st.columns(2)
                    c1.selectbox("Unidade", st.session_state['df_unidades']['Unidade'].tolist(), key="temp_unidade", help="Unidade de medida (kg, m, un...)")
                    c2.date_input("Necessidade", value=date.today(), key="temp_data", help="Data em que o material deve estar na obra")
                    st.selectbox("Apropriação", l_aprop, key="temp_aprop", help="Centro de custo ou etapa da obra")
                    st.form_submit_button("➕ Adicionar ao Carrinho", on_click=callback_adicionar_ao_carrinho, use_container_width=True)
            
            with c_cart:
                st.subheader("2. Carrinho (Editável)")
                st.caption("📝 Clique nos itens para corrigir ou delete linhas.")
                
                if st.session_state['carrinho_pedidos']:
                    df_carrinho = pd.DataFrame(st.session_state['carrinho_pedidos'])
                    df_carrinho['Data_Necessidade'] = pd.to_datetime(df_carrinho['Data_Necessidade'])

                    df_carrinho_editado = st.data_editor(
                        df_carrinho[['Item', 'Qtd', 'Unidade', 'Apropriacao', 'Data_Necessidade']],
                        key="editor_carrinho_temp",
                        num_rows="dynamic",
                        use_container_width=True, # Essencial para Mobile
                        column_config={
                            "Data_Necessidade": st.column_config.DateColumn("Necessidade", format="DD/MM/YYYY"),
                            "Qtd": st.column_config.NumberColumn("Qtd", min_value=0.01, step=0.01)
                        }
                    )
                    
                    lista_atualizada = df_carrinho_editado.to_dict('records')
                    for item in lista_atualizada:
                        item['Solicitante'] = st.session_state['usuario_atual']
                    
                    st.session_state['carrinho_pedidos'] = lista_atualizada

                    if st.button("✅ Finalizar Pedido", type="primary", use_container_width=True): 
                        callback_finalizar_pedido()
                        # Link WhatsApp Simples
                        msg = f"Olá, fiz um novo pedido para a obra {obra_sel}. Verifique no sistema!"
                        st.markdown(f"[📲 Notificar Comprador via WhatsApp](https://wa.me/?text={msg.replace(' ', '%20')})")
                        st.rerun()
                        
                    if st.button("🗑️ Esvaziar Tudo", use_container_width=True): 
                        st.session_state['carrinho_pedidos'] = []
                        st.rerun()
                else: 
                    st.info("Lista vazia.")

            st.divider()
            st.subheader("Histórico de Pedidos")
            df_v = st.session_state['df_materiais'][st.session_state['df_materiais']['Obra'] == obra_sel]
            if not df_v.empty: df_v = df_v.sort_values(by="ID_Pedido", ascending=False)
            
            # Tabela Obra
            st.download_button("📥 Baixar Planilha (Excel)", data=converter_para_excel(df_v), file_name=f"pedidos_{obra_sel}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            df_ed = st.data_editor(df_v, key="ed_obra", use_container_width=True, 
                disabled=["ID_Pedido", "Obra", "Item", "Qtd", "Unidade", "Apropriacao", "Data_Necessidade", "Solicitante", "Status_Compra", "Data_Previsao_Entrega", "Preço", "Fornecedor"],
                column_config={
                    "Recebido_Na_Obra": st.column_config.CheckboxColumn("Recebido?"), 
                    "Data_Necessidade": st.column_config.DateColumn("Necessidade", format="DD/MM/YYYY"), 
                    "Data_Previsao_Entrega": st.column_config.DateColumn("Previsão", format="DD/MM/YYYY")
                })
            
            if not df_ed.equals(df_v):
                houve_alteracao = False
                for idx, row in df_ed.iterrows():
                    orig = df_v.loc[idx]
                    if not row.equals(orig):
                        # Validação regra de negócio
                        if row['Recebido_Na_Obra'] == True and row['Status_Compra'] != 'Comprado':
                            st.toast("🚫 Item não comprado ainda!", icon="🔒")
                            continue
                        
                        id_db = df_v.loc[idx, 'id']
                        if atualizar_registro('solicitacoes', id_db, row.to_dict()):
                            houve_alteracao = True
                
                if houve_alteracao:
                    st.session_state['df_materiais'] = buscar_dados('solicitacoes')
                    st.toast("Atualizado!")
                    st.rerun()

    # --- 2. COMPRADOR ---
    elif funcao == "Comprador":
        st.subheader("Central de Compras")
        f_obra = st.selectbox("Filtrar Obra", ["Todas"] + obras_visiveis)
        df_v = st.session_state['df_materiais'] if f_obra == "Todas" else st.session_state['df_materiais'][st.session_state['df_materiais']['Obra'] == f_obra]
        
        st.download_button("📥 Exportar Relatório de Compras", data=converter_para_excel(df_v), file_name="relatorio_compras.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        df_ed = st.data_editor(df_v, key="ed_comp", use_container_width=True, 
            disabled=["ID_Pedido", "Obra", "Item", "Qtd", "Unidade", "Apropriacao", "Data_Necessidade", "Solicitante", "Recebido_Na_Obra"],
            column_config={
                "Status_Compra": st.column_config.SelectboxColumn("Status", options=["Pendente", "Cotação", "Comprado", "Cancelado"], required=True), 
                "Data_Previsao_Entrega": st.column_config.DateColumn("Previsão", format="DD/MM/YYYY"), 
                "Data_Necessidade": st.column_config.DateColumn("Necessidade", format="DD/MM/YYYY"),
                "Preço": st.column_config.NumberColumn("Preço (R$)", format="R$ %.2f", min_value=0.0, step=0.01)
            })
        if not df_ed.equals(df_v):
            for idx, row in df_ed.iterrows():
                orig = df_v.loc[idx]
                if not row.equals(orig):
                    id_db = df_v.loc[idx, 'id']
                    atualizar_registro('solicitacoes', id_db, row.to_dict())
            st.session_state['df_materiais'] = buscar_dados('solicitacoes')
            st.toast("Atualizado!")
            st.rerun()

    # --- 3. ADMIN ---
    elif funcao == "Administrador":
        st.subheader("🛠️ Painel de Controle Admin")
        st.caption("Visão total de todos os pedidos e custos da empresa.")
        st.download_button("📥 Baixar Base Completa (Excel)", data=converter_para_excel(st.session_state['df_materiais']), file_name="base_total_materiais.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        df_ed = st.data_editor(st.session_state['df_materiais'], key="ed_adm", num_rows="dynamic", use_container_width=True, 
            column_config={
                "Data_Necessidade": st.column_config.DateColumn("Necessidade", format="DD/MM/YYYY"), 
                "Data_Previsao_Entrega": st.column_config.DateColumn("Previsão", format="DD/MM/YYYY"),
                "Preço": st.column_config.NumberColumn("Preço (R$)", format="R$ %.2f", min_value=0.0, step=0.01)
            })
        if not df_ed.equals(st.session_state['df_materiais']):
            st.warning("⚠️ Edições em massa via Admin estão em modo leitura com Supabase. Use as abas específicas abaixo para novos cadastros.")

# --- MENU: CONFIGURAÇÕES (ADMIN) ---
elif menu == "⚙️ Configurações (Admin)" and funcao == "Administrador":
    st.title("⚙️ Configurações Avançadas")
    st.caption("Gerencie usuários, obras, custos e unidades de medida.")
    t1, t2, t3, t4 = st.tabs(["👥 Usuários", "🏗️ Obras", "💰 Apropriações", "📏 Unidades"])
    
    with t1:
        with st.form("new_u", clear_on_submit=True):
            c1,c2,c3 = st.columns(3)
            nu, ns, nf = c1.text_input("User"), c2.text_input("Pass"), c3.selectbox("Role", ["Administrador", "Comprador", "Usuario Obra"])
            no = st.multiselect("Obras", todas_obras)
            if st.form_submit_button("Criar", use_container_width=True):
                novo_u = {"Usuario": nu, "Senha": ns, "Funcao": nf, "Obras_Acesso": ";".join(no)}
                if salvar_registro('usuarios', novo_u):
                    st.session_state['df_usuarios'] = buscar_dados('usuarios')
                    st.rerun()
        
        sel_u = st.selectbox("Editar User", st.session_state['df_usuarios']['Usuario'].tolist())
        if sel_u:
            curr = st.session_state['df_usuarios'][st.session_state['df_usuarios']['Usuario'] == sel_u].iloc[0]
            with st.form("ed_u"):
                ns_e = st.text_input("Senha", value=curr['Senha'])
                nf_e = st.selectbox("Role", ["Administrador", "Comprador", "Usuario Obra"], index=["Administrador", "Comprador", "Usuario Obra"].index(curr['Funcao']))
                curr_ob = str(curr['Obras_Acesso']).split(';') if str(curr['Obras_Acesso']) != 'nan' else []
                no_e = st.multiselect("Obras", todas_obras, default=[x for x in curr_ob if x in todas_obras])
                if st.form_submit_button("Salvar", use_container_width=True):
                    id_db = curr.get('id')
                    if id_db:
                        campos_upd = {"Senha": ns_e, "Funcao": nf_e, "Obras_Acesso": ";".join(no_e)}
                        if atualizar_registro('usuarios', id_db, campos_upd):
                            st.session_state['df_usuarios'] = buscar_dados('usuarios')
                            st.rerun()
                    else:
                        st.error("Erro: ID do usuário não encontrado.")

    with t2:
        st.subheader("🏢 Cadastrar Nova Obra")
        with st.form("new_o"):
            no = st.text_input("Nome da Obra", help="Ex: Residencial Verona, Edifício Solaris...")
            if st.form_submit_button("🔨 Criar Obra", use_container_width=True):
                if no:
                    novo_o = {"Nome_Obra": no, "Endereco": "", "Status": "Ativa"}
                    if salvar_registro('obras', novo_o):
                        st.session_state['df_obras'] = buscar_dados('obras')
                        st.rerun()
        
        # Edição de Obras
        df_ed_o = st.data_editor(st.session_state['df_obras'], key="ed_obr_tab", use_container_width=True)
        if not df_ed_o.equals(st.session_state['df_obras']):
            for idx, row in df_ed_o.iterrows():
                orig = st.session_state['df_obras'].loc[idx]
                if not row.equals(orig):
                    id_db = orig.get('id')
                    if id_db:
                        atualizar_registro('obras', id_db, row.to_dict())
            st.session_state['df_obras'] = buscar_dados('obras')
            st.rerun()

    with t3:
        for ob in todas_obras:
            with st.expander(f"🏗️ {ob}"):
                c1,c2 = st.columns([3,1])
                new_ap = c1.text_input(f"Nova Aprop. {ob}", key=f"n_ap_{ob}")
                if c2.button("Add", key=f"b_ap_{ob}") and new_ap:
                    novo_ap = {"Obra": ob, "Apropriacao": new_ap}
                    if salvar_registro('apropriacoes', novo_ap):
                        st.session_state['df_apropriacoes'] = buscar_dados('apropriacoes')
                        st.rerun()
                
                df_f = st.session_state['df_apropriacoes'][st.session_state['df_apropriacoes']['Obra'] == ob]
                df_e = st.data_editor(df_f, key=f"ed_ap_{ob}", use_container_width=True, hide_index=True)
                if not df_e.equals(df_f):
                    for idx, row in df_e.iterrows():
                        orig = df_f.loc[idx]
                        if not row.equals(orig):
                            id_db = df_f.loc[idx, 'id']
                            atualizar_registro('apropriacoes', id_db, row.to_dict())
                    st.session_state['df_apropriacoes'] = buscar_dados('apropriacoes')
                    st.rerun()

    with t4:
        with st.form("new_un"):
            un = st.text_input("Unidade")
            if st.form_submit_button("Add", use_container_width=True) and un:
                if salvar_registro('unidades', {"Unidade": un}):
                    st.session_state['df_unidades'] = buscar_dados('unidades')
                    st.rerun()
        st.data_editor(st.session_state['df_unidades'], key="ed_un", on_change=lambda: salvar_banco(st.session_state['df_unidades'], ARQ_UNIDADES), use_container_width=True)