import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, joinedload



# Configuração do banco de dados
engine = create_engine('sqlite:///bolos.db', echo=True)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# Modelo para Ingredientes
class Ingrediente(Base):
    __tablename__ = 'ingredientes'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    preco_por_unidade = Column(Float, nullable=False)
    unidade = Column(String(20), nullable=False)

# Modelo para Receitas
class Receita(Base):
    __tablename__ = 'receitas'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(String(500))
    margem_lucro = Column(Float, default=0)
    ingredientes = relationship("IngredienteReceita", back_populates="receita")

# Modelo para Ingredientes na Receita
class IngredienteReceita(Base):
    __tablename__ = 'ingredientes_receita'
    id = Column(Integer, primary_key=True)
    receita_id = Column(Integer, ForeignKey('receitas.id'))
    ingrediente_id = Column(Integer, ForeignKey('ingredientes.id'))
    quantidade = Column(Float, nullable=False)
    receita = relationship("Receita", back_populates="ingredientes")
    ingrediente = relationship("Ingrediente")

# Criar tabelas
Base.metadata.create_all(engine)

# Adicione esta função no início do seu arquivo, logo após as definições dos modelos
def recriar_banco_de_dados():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Banco de dados recriado com sucesso!")

# Adicione esta função no início do seu arquivo, logo após as definições dos modelos
def adicionar_coluna_margem_lucro():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE receitas ADD COLUMN margem_lucro FLOAT DEFAULT 0"))
            conn.commit()
            print("Coluna margem_lucro adicionada com sucesso!")
        except Exception as e:
            print(f"Erro ao adicionar coluna margem_lucro: {str(e)}")
            # Se a coluna já existir, não é um erro crítico
            if "duplicate column name" not in str(e).lower():
                raise

# Função para adicionar ingrediente
def adicionar_ingrediente(nome, preco, unidade):
    session = Session()
    novo_ingrediente = Ingrediente(nome=nome, preco_por_unidade=preco, unidade=unidade)
    session.add(novo_ingrediente)
    session.commit()
    session.close()

# Função para listar ingredientes em ordem alfabética
def listar_ingredientes():
    session = Session()
    ingredientes = session.query(Ingrediente).order_by(Ingrediente.nome).all()
    session.close()
    return ingredientes

# Função para adicionar receita
def adicionar_receita(nome, descricao, ingredientes_quantidades, margem_lucro):
    session = Session()
    nova_receita = Receita(nome=nome, descricao=descricao, margem_lucro=margem_lucro)
    session.add(nova_receita)
    session.flush()
    
    for ingrediente_id, quantidade in ingredientes_quantidades:
        ingrediente_receita = IngredienteReceita(
            receita_id=nova_receita.id,
            ingrediente_id=ingrediente_id,
            quantidade=quantidade
        )
        session.add(ingrediente_receita)
    
    session.commit()
    session.close()

# Função para listar receitas em ordem alfabética
def listar_receitas():
    session = Session()
    receitas = session.query(Receita).options(joinedload(Receita.ingredientes)).order_by(Receita.nome).all()
    return receitas, session

# Função para calcular custo da receita
def calcular_custo_receita(receita_id):
    session = Session()
    try:
        receita = session.query(Receita).options(
            joinedload(Receita.ingredientes).joinedload(IngredienteReceita.ingrediente)
        ).get(receita_id)
        
        if not receita:
            return None, [], 0, 0, 0

        custo_ingredientes = 0
        ingredientes_detalhes = []
        ingredientes_invalidos = []
        
        for ingrediente_receita in receita.ingredientes:
            ingrediente = ingrediente_receita.ingrediente
            if ingrediente is None:
                ingredientes_invalidos.append(ingrediente_receita)
            else:
                custo_item = ingrediente.preco_por_unidade * ingrediente_receita.quantidade
                custo_ingredientes += custo_item
                ingredientes_detalhes.append({
                    'nome': ingrediente.nome,
                    'quantidade': ingrediente_receita.quantidade,
                    'unidade': ingrediente.unidade,
                    'preco_unitario': ingrediente.preco_por_unidade,
                    'custo_item': custo_item
                })
        
        for ingrediente_invalido in ingredientes_invalidos:
            session.delete(ingrediente_invalido)
        
        custo_mao_de_obra = custo_ingredientes
        custo_total = custo_ingredientes + custo_mao_de_obra
        
        # Calcula o preço final considerando a margem de lucro
        preco_final = custo_total / (1 - receita.margem_lucro / 100)
        
        session.commit()
        return custo_total, ingredientes_detalhes, len(ingredientes_invalidos), custo_mao_de_obra, preco_final
    finally:
        session.close()

# Adicione esta nova função para excluir ingrediente
def excluir_ingrediente(ingrediente_id):
    session = Session()
    ingrediente = session.query(Ingrediente).get(ingrediente_id)
    if ingrediente:
        session.delete(ingrediente)
        session.commit()
    session.close()

# Adicione esta nova função para excluir receita
def excluir_receita(receita_id):
    session = Session()
    receita = session.query(Receita).get(receita_id)
    if receita:
        session.delete(receita)
        session.commit()
    session.close()

# Adicione esta nova função para editar ingrediente
def editar_ingrediente(ingrediente_id, novo_nome, novo_preco, nova_unidade):
    session = Session()
    ingrediente = session.query(Ingrediente).get(ingrediente_id)
    if ingrediente:
        ingrediente.nome = novo_nome
        ingrediente.preco_por_unidade = novo_preco
        ingrediente.unidade = nova_unidade
        session.commit()
    session.close()

# Adicione esta nova função para editar receita
def editar_receita(receita_id, novo_nome, nova_descricao, nova_margem_lucro, novos_ingredientes):
    session = Session()
    receita = session.query(Receita).get(receita_id)
    if receita:
        receita.nome = novo_nome
        receita.descricao = nova_descricao
        receita.margem_lucro = nova_margem_lucro
        
        # Remove os ingredientes antigos
        session.query(IngredienteReceita).filter_by(receita_id=receita_id).delete()
        
        # Adiciona os novos ingredientes
        for ingrediente_id, quantidade in novos_ingredientes:
            ingrediente_receita = IngredienteReceita(
                receita_id=receita_id,
                ingrediente_id=ingrediente_id,
                quantidade=quantidade
            )
            session.add(ingrediente_receita)
        
        session.commit()
    session.close()

# Configuração do tema e estilo
st.set_page_config(page_title="Sistema de Controle de Custo de Receitas de Bolos", page_icon="🍰", layout="wide")

# CSS personalizado para responsividade
st.markdown("""
<style>
    .reportview-container .main .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 5rem;
        padding-right: 5rem;
    }
    .stButton > button {
        width: 100%;
    }
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select {
        width: 100%;
    }
    @media (max-width: 768px) {
        .reportview-container .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .row-widget.stRadio > div {
            flex-direction: column;
        }
    }
    .sidebar .sidebar-content {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .sidebar img {
        margin-bottom: 20px;
        max-width: 80%;
    }
</style>
""", unsafe_allow_html=True)

# Função para criar o menu lateral
def sidebar_menu():
    with st.sidebar:
        st.image("logo-bia-sf.png", width=230)  # Ajuste o caminho e o tamanho conforme necessário
        return st.radio('Menu', ['Adicionar Ingrediente', 'Listar Ingredientes', 'Adicionar Receita', 'Listar Receitas', 'Recriar Banco de Dados', 'Atualizar Banco de Dados'])

# Interface principal
def main():
    st.title('Sistema de Controle de Custo de Receitas de Bolos')

    menu = sidebar_menu()

    if menu == 'Adicionar Ingrediente':
        adicionar_ingrediente_ui()
    elif menu == 'Listar Ingredientes':
        listar_ingredientes_ui()
    elif menu == 'Adicionar Receita':
        adicionar_receita_ui()
    elif menu == 'Listar Receitas':
        listar_receitas_ui()
    elif menu == 'Recriar Banco de Dados':
        recriar_banco_dados_ui()
    elif menu == 'Atualizar Banco de Dados':
        atualizar_banco_dados_ui()

# Funções de UI para cada seção
def adicionar_ingrediente_ui():
    st.header('Adicionar Novo Ingrediente')
    with st.form("adicionar_ingrediente_form", clear_on_submit=True):
        nome = st.text_input('Nome do Ingrediente')
        preco = st.number_input('Preço por Unidade (R$)', min_value=0.01, step=0.01)
        unidade = st.selectbox('Unidade', ['kg', 'g', 'L', 'ml', 'unidade'])
        
        submitted = st.form_submit_button('Adicionar Ingrediente')
        
    if submitted:
        if nome and preco > 0:
            adicionar_ingrediente(nome, preco, unidade)
            st.success(f'Ingrediente "{nome}" adicionado com sucesso!')
        else:
            st.error('Por favor, preencha todos os campos corretamente.')

def listar_ingredientes_ui():
    st.header('Lista de Ingredientes')
    ingredientes = listar_ingredientes()
    if ingredientes:
        for ingrediente in ingredientes:
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                st.write(f"**{ingrediente.nome}**")
            with col2:
                st.write(f"R$ {ingrediente.preco_por_unidade:.2f} / {ingrediente.unidade}")
            with col3:
                if st.button('✏️', key=f'edit_{ingrediente.id}'):
                    st.session_state.editing_ingredient = ingrediente.id
            with col4:
                if st.button('🗑️', key=f'delete_{ingrediente.id}'):
                    excluir_ingrediente(ingrediente.id)
                    st.success(f'Ingrediente "{ingrediente.nome}" excluído com sucesso!')
                    st.rerun()
        
        # Formulário de edição de ingrediente
        if 'editing_ingredient' in st.session_state:
            ingrediente_para_editar = next((i for i in ingredientes if i.id == st.session_state.editing_ingredient), None)
            if ingrediente_para_editar:
                st.subheader(f"Editar Ingrediente: {ingrediente_para_editar.nome}")
                with st.form(key=f"edit_form_{ingrediente_para_editar.id}"):
                    novo_nome = st.text_input("Novo nome", value=ingrediente_para_editar.nome)
                    novo_preco = st.number_input("Novo preço", min_value=0.01, value=ingrediente_para_editar.preco_por_unidade, step=0.01)
                    nova_unidade = st.selectbox("Nova unidade", ['kg', 'g', 'L', 'ml', 'unidade'], index=['kg', 'g', 'L', 'ml', 'unidade'].index(ingrediente_para_editar.unidade))
                    
                    if st.form_submit_button("Salvar Alterações"):
                        editar_ingrediente(ingrediente_para_editar.id, novo_nome, novo_preco, nova_unidade)
                        st.success(f"Ingrediente '{novo_nome}' atualizado com sucesso!")
                        del st.session_state.editing_ingredient
                        st.rerun()
                
                if st.button("Cancelar Edição"):
                    del st.session_state.editing_ingredient
                    st.rerun()
        
        st.markdown("---")
    else:
        st.info('Nenhum ingrediente cadastrado ainda.')

def adicionar_receita_ui():
    st.header('Adicionar Nova Receita')
    
    ingredientes = listar_ingredientes()
    
    with st.form("adicionar_receita_form", clear_on_submit=True):
        nome_receita = st.text_input('Nome da Receita')
        descricao_receita = st.text_area('Descrição da Receita')
        margem_lucro = st.number_input('Margem de Lucro (%)', min_value=0.0, max_value=100.0, step=0.1, value=0.0)
        
        st.subheader("Ingredientes")
        ingredientes_selecionados = []
        for ingrediente in ingredientes:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"{ingrediente.nome} ({ingrediente.unidade})")
            with col2:
                quantidade = st.number_input(
                    f'Quantidade',
                    min_value=0.0,
                    step=0.01,
                    key=f'quantidade_{ingrediente.id}'
                )
            if quantidade > 0:
                ingredientes_selecionados.append((ingrediente.id, quantidade))
        
        submitted = st.form_submit_button('Adicionar Receita')
    
    if submitted:
        if nome_receita and ingredientes_selecionados:
            adicionar_receita(nome_receita, descricao_receita, ingredientes_selecionados, margem_lucro)
            st.success('Receita adicionada com sucesso!')
        else:
            st.error('Por favor, preencha o nome da receita e adicione pelo menos um ingrediente com quantidade maior que zero.')

def listar_receitas_ui():
    st.header('Lista de Receitas')
    receitas, session = listar_receitas()
    try:
        if receitas:
            for receita in receitas:
                with st.expander(receita.nome):
                    st.write(f"**Descrição:** {receita.descricao}")
                    custo_total, ingredientes_detalhes, ingredientes_removidos, custo_mao_de_obra, preco_final = calcular_custo_receita(receita.id)
                    
                    st.subheader("Ingredientes:")
                    for item in ingredientes_detalhes:
                        st.write(f"- {item['nome']}: {item['quantidade']} {item['unidade']} "
                                 f"(R$ {item['preco_unitario']:.2f}/{item['unidade']}) "
                                 f"= R$ {item['custo_item']:.2f}")
                    
                    st.write(f'**Custo dos ingredientes:** R$ {custo_mao_de_obra:.2f}')
                    st.write(f'**Custo da mão de obra:** R$ {custo_mao_de_obra:.2f}')
                    st.write(f'**Custo total da receita:** R$ {custo_total:.2f}')
                    st.write(f'**Margem de lucro:** {receita.margem_lucro:.2f}%')
                    st.write(f'**Preço final sugerido:** R$ {preco_final:.2f}')
                    
                    if ingredientes_removidos > 0:
                        st.warning(f'{ingredientes_removidos} ingrediente(s) desta receita foram removidos porque não existem mais.')
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button('✏️ Editar', key=f'edit_receita_{receita.id}'):
                            st.session_state.editing_recipe = receita.id
                    with col2:
                        if st.button('🗑️ Excluir', key=f'delete_receita_{receita.id}'):
                            excluir_receita(receita.id)
                            st.success(f'Receita "{receita.nome}" excluída com sucesso!')
                            st.rerun()
            
            # Formulário de edição de receita
            if 'editing_recipe' in st.session_state:
                receita_para_editar = next((r for r in receitas if r.id == st.session_state.editing_recipe), None)
                if receita_para_editar:
                    st.subheader(f"Editar Receita: {receita_para_editar.nome}")
                    with st.form(key=f"edit_form_receita_{receita_para_editar.id}"):
                        novo_nome = st.text_input("Novo nome", value=receita_para_editar.nome)
                        nova_descricao = st.text_area("Nova descrição", value=receita_para_editar.descricao)
                        nova_margem_lucro = st.number_input("Nova margem de lucro (%)", min_value=0.0, max_value=100.0, value=float(receita_para_editar.margem_lucro), step=0.1)
                        
                        st.subheader("Ingredientes")
                        ingredientes = listar_ingredientes()
                        novos_ingredientes = []
                        for ingrediente in ingredientes:
                            quantidade_atual = next((float(ir.quantidade) for ir in receita_para_editar.ingredientes if ir.ingrediente_id == ingrediente.id), 0.0)
                            nova_quantidade = st.number_input(
                                f'{ingrediente.nome} ({ingrediente.unidade})',
                                min_value=0.0,
                                value=float(quantidade_atual),
                                step=0.01,
                                key=f'edit_quantidade_{receita_para_editar.id}_{ingrediente.id}'
                            )
                            if nova_quantidade > 0:
                                novos_ingredientes.append((ingrediente.id, nova_quantidade))
                        
                        if st.form_submit_button("Salvar Alterações"):
                            editar_receita(receita_para_editar.id, novo_nome, nova_descricao, nova_margem_lucro, novos_ingredientes)
                            st.success(f"Receita '{novo_nome}' atualizada com sucesso!")
                            del st.session_state.editing_recipe
                            st.rerun()
                    
                    if st.button("Cancelar Edição"):
                        del st.session_state.editing_recipe
                        st.rerun()
        else:
            st.info('Nenhuma receita cadastrada ainda.')
    finally:
        session.close()

def recriar_banco_dados_ui():
    st.header('Recriar Banco de Dados')
    st.warning("Atenção: Esta ação irá apagar todos os dados existentes e recriar o banco de dados. Esta operação não pode ser desfeita.")
    
    if st.button("Recriar Banco de Dados"):
        try:
            recriar_banco_de_dados()
            st.success("Banco de dados recriado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao recriar o banco de dados: {str(e)}")

def atualizar_banco_dados_ui():
    st.header('Atualizar Banco de Dados')
    st.info("Esta função adiciona novas colunas ou faz outras alterações necessárias no banco de dados sem perder os dados existentes.")
    
    if st.button("Atualizar Banco de Dados"):
        try:
            adicionar_coluna_margem_lucro()
            st.success("Banco de dados atualizado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao atualizar o banco de dados: {str(e)}")

if __name__ == "__main__":
    main()