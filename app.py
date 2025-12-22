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
        /* Estilo Base (PC) */
        .footer {
            position: fixed;
            right: 15px;
            bottom: 10px;
            text-align: right;
            font-family: sans-serif;
            color: #888;
            font-size: 12px;
            z-index: 999;
            background-color: rgba(255, 255, 255, 0.8);
            padding: 5px;
            border-radius: 5px;
        }
        
        /* Ajustes para MOBILE (Telas menores que 768px) */
        @media (max-width: 768px) {
            /* Títulos menores no celular */
            h1 { font-size: 1.5rem !important; }
            h2 { font-size: 1.3rem !important; }
            h3 { font-size: 1.1rem !important; }
            
            /* Rodapé deixa de ser fixo para não cobrir botões */
            .footer {
                position: static;
                text-align: center;
                margin-top: 20px;
            }
            
            /* Remove margens excessivas no topo */
            .block-container {
                padding-top: 2rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
        }
    </style>
    <div class="footer">
        Desenvolvido por Tiago Manga - Versão Mobile 1.0
    </div>
    """, unsafe_allow_html=True)

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
            'solicitacoes': ['id', 'id_pedido', 'obra', 'item', 'unidade', 'apropriacao', 'data_necessidade', 'solicitante', 'status_compra', 'data_previsao_entrega', 'recebido_na_obra'],
            'usuarios': ['id', 'usuario', 'senha', 'funcao', 'obras_acesso'],
            'obras': ['id', 'nome_obra', 'endereco', 'status'],
            'apropriacoes': ['id', 'obra', 'apropriacao'],
            'unidades': ['id', 'unidade']
        }
        
        if tabela in colunas_padrao:
            for col in colunas_padrao[tabela]:
                if col not in df.columns:
                    df[col] = None

        # Ajustes de tipos e colunas (compatibilidade com código antigo)
        if tabela == 'solicitacoes':
            colunas_de_data = ['data_necessidade', 'data_previsao_entrega']
            for col in colunas_de_data:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            df = df.rename(columns={
                'id_pedido': 'ID_Pedido', 'obra': 'Obra', 'item': 'Item', 'unidade': 'Unidade',
                'apropriacao': 'Apropriacao', 'data_necessidade': 'Data_Necessidade',
                'solicitante': 'Solicitante', 'status_compra': 'Status_Compra',
                'data_previsao_entrega': 'Data_Previsao_Entrega', 'recebido_na_obra': 'Recebido_Na_Obra'
            })
        elif tabela == 'usuarios':
            df = df.rename(columns={'usuario': 'Usuario', 'senha': 'Senha', 'funcao': 'Funcao', 'obras_acesso': 'Obras_Acesso'})
        elif tabela == 'obras':
            df = df.rename(columns={'nome_obra': 'Nome_Obra', 'endereco': 'Endereco', 'status': 'Status'})
        elif tabela == 'apropriacoes':
            df = df.rename(columns={'obra': 'Obra', 'apropriacao': 'Apropriacao'})
        elif tabela == 'unidades':
            df = df.rename(columns={'unidade': 'Unidade'})
            
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
        dados_formatados = {k.lower(): v for k, v in dados.items()}
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

if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario_atual' not in st.session_state: st.session_state['usuario_atual'] = ''
if 'funcao_atual' not in st.session_state: st.session_state['funcao_atual'] = ''
if 'obras_permitidas' not in st.session_state: st.session_state['obras_permitidas'] = []
if 'carrinho_pedidos' not in st.session_state: st.session_state['carrinho_pedidos'] = []

# --- CALLBACKS ---
def callback_adicionar_ao_carrinho():
    st.session_state['carrinho_pedidos'].append({
        "Item": st.session_state.temp_item,
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
            "id_pedido": novo_id, "obra": obra, "item": item['Item'], "unidade": item['Unidade'],
            "apropriacao": item['Apropriacao'], "data_necessidade": dn, "solicitante": item['Solicitante'],
            "status_compra": "Pendente", "recebido_na_obra": False
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

st.sidebar.markdown(f"### 👤 {usuario}")
st.sidebar.markdown(f"**Cargo:** {funcao}")
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False; st.session_state['carrinho_pedidos'] = []; st.rerun()

st.sidebar.divider()
menu = st.sidebar.radio("Menu", ["📦 Gestão de Suprimentos", "⚙️ Configurações (Admin)"] if funcao == "Administrador" else ["📦 Gestão de Suprimentos"])

# --- MENU: GESTÃO DE SUPRIMENTOS ---
if menu == "📦 Gestão de Suprimentos":
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
                    st.text_input("Item", key="temp_item")
                    c1, c2 = st.columns(2)
                    c1.selectbox("Unidade", st.session_state['df_unidades']['Unidade'].tolist(), key="temp_unidade")
                    c2.date_input("Necessidade", value=date.today(), key="temp_data")
                    st.selectbox("Apropriação", l_aprop, key="temp_aprop")
                    st.form_submit_button("Adicionar", on_click=callback_adicionar_ao_carrinho, use_container_width=True) # Botão largo no mobile
            
            with c_cart:
                st.subheader("2. Carrinho (Editável)")
                st.caption("📝 Clique nos itens para corrigir ou delete linhas.")
                
                if st.session_state['carrinho_pedidos']:
                    df_carrinho = pd.DataFrame(st.session_state['carrinho_pedidos'])
                    df_carrinho['Data_Necessidade'] = pd.to_datetime(df_carrinho['Data_Necessidade'])

                    df_carrinho_editado = st.data_editor(
                        df_carrinho[['Item', 'Unidade', 'Apropriacao', 'Data_Necessidade']],
                        key="editor_carrinho_temp",
                        num_rows="dynamic",
                        use_container_width=True, # Essencial para Mobile
                        column_config={
                            "Data_Necessidade": st.column_config.DateColumn("Necessidade", format="DD/MM/YYYY")
                        }
                    )
                    
                    lista_atualizada = df_carrinho_editado.to_dict('records')
                    for item in lista_atualizada:
                        item['Solicitante'] = st.session_state['usuario_atual']
                    
                    st.session_state['carrinho_pedidos'] = lista_atualizada

                    if st.button("✅ Finalizar Pedido", type="primary", use_container_width=True): 
                        callback_finalizar_pedido()
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
            df_ed = st.data_editor(df_v, key="ed_obra", use_container_width=True, 
                disabled=["ID_Pedido", "Obra", "Item", "Unidade", "Apropriacao", "Data_Necessidade", "Solicitante", "Status_Compra", "Data_Previsao_Entrega"],
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
        
        df_ed = st.data_editor(df_v, key="ed_comp", use_container_width=True, 
            disabled=["ID_Pedido", "Obra", "Item", "Unidade", "Apropriacao", "Data_Necessidade", "Solicitante", "Recebido_Na_Obra"],
            column_config={
                "Status_Compra": st.column_config.SelectboxColumn("Status", options=["Pendente", "Cotação", "Comprado", "Cancelado"], required=True), 
                "Data_Previsao_Entrega": st.column_config.DateColumn("Previsão", format="DD/MM/YYYY"), 
                "Data_Necessidade": st.column_config.DateColumn("Necessidade", format="DD/MM/YYYY")
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
        st.subheader("Admin Geral")
        df_ed = st.data_editor(st.session_state['df_materiais'], key="ed_adm", num_rows="dynamic", use_container_width=True, 
            column_config={
                "Data_Necessidade": st.column_config.DateColumn(format="DD/MM/YYYY"), 
                "Data_Previsao_Entrega": st.column_config.DateColumn(format="DD/MM/YYYY")
            })
        if not df_ed.equals(st.session_state['df_materiais']):
            # No Admin o editor dinâmico é mais complexo com Supabase sem Sync
            # Por simplicidade neste MVP, focamos nas edições. 
            # Para deleções/inserções em massa no Admin, o ideal é usar botões dedicados ou lógica de diff.
            st.warning("Edições em massa via Admin estão em modo leitura com Supabase. Use as telas específicas para cadastros.")

# --- MENU: CONFIGURAÇÕES (ADMIN) ---
elif menu == "⚙️ Configurações (Admin)" and funcao == "Administrador":
    t1, t2, t3, t4 = st.tabs(["Usuários", "Obras", "Apropriações", "Unidades"])
    
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
                    id_db = st.session_state['df_usuarios'][st.session_state['df_usuarios']['Usuario'] == sel_u].iloc[0]['id']
                    campos_upd = {"Senha": ns_e, "Funcao": nf_e, "Obras_Acesso": ";".join(no_e)}
                    if atualizar_registro('usuarios', id_db, campos_upd):
                        st.session_state['df_usuarios'] = buscar_dados('usuarios')
                        st.rerun()

    with t2:
        with st.form("new_o"):
            no = st.text_input("Nome")
            if st.form_submit_button("Criar Obra", use_container_width=True):
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
                    id_db = st.session_state['df_obras'].loc[idx, 'id']
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