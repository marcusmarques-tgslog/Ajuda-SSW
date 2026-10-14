import os
import streamlit as st
from openai import OpenAI  # Ou a biblioteca de IA que estiver a utilizar (ex: Groq, LangChain, etc.)

# Configuração da Página do Streamlit
st.set_page_config(
    page_title="Assistente Operacional SSW TMS",
    page_icon="🚛",
    layout="wide"
)

st.title("🚛 Assistente Operacional - SSW TMS")
st.markdown("Agente inteligente especializado nas rotinas, opções de menu e manuais oficiais do sistema SSW.")

# Caminho do ficheiro de conhecimento profundo que gerámos
CAMINHO_BASE = "base_conhecimento_ssw.txt"

@st.cache_resource
def carregar_base_conhecimento():
    """Carrega o conteúdo completo da base de conhecimento para a memória do agente."""
    if os.path.exists(CAMINHO_BASE):
        with open(CAMINHO_BASE, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return "Aviso: Base de conhecimento não encontrada. Certifique-se de enviar o ficheiro."

base_texto = carregar_base_conhecimento()

# Inicializar o cliente de IA (exemplo com OpenAI ou compatível)
# Certifique-se de configurar a sua chave de API nas variáveis de ambiente ou secrets do Streamlit
api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", "")

if not api_key:
    st.warning("⚠️ Chave de API não detetada. Por favor, configure a chave da API nas definições do Streamlit (st.secrets) ou variáveis de ambiente.")
else:
    client = OpenAI(api_key=api_key)

    # Histórico de mensagens no chat do Streamlit
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Exibir mensagens anteriores
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Entrada do utilizador
    if prompt := st.chat_input("Ex: Como faço a emissão de CTRC na opção 004 ou a baixa de entrega na opção 038?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Construção do Prompt do Sistema injetando a Base de Conhecimento Oficial do SSW
        system_prompt = f"""
        Você é um assistente técnico e operacional especialista no Sistema SSW (TMS - Transportation Management System).
        O seu objetivo é auxiliar os operadores de logística a resolverem dúvidas do dia a dia, indicando os passos corretos, 
        códigos de opções do menu (ex: Opção 004, Opção 038, Opção 056, etc.) e regras de negócio com base estritamente na seguinte base de conhecimento oficial:

        === INÍCIO DA BASE DE CONHECIMENTO OFICIAL SSW ===
        {base_texto}
        === FIM DA BASE DE CONHECIMENTO ===

        Regras de resposta:
        1. Responda sempre em Português de Portugal / PT-BR de forma clara, objetiva e profissional.
        2. Baseie as suas respostas exclusivamente nos dados técnicos fornecidos na base de conhecimento acima.
        3. Indique sempre a opção de menu correta correspondente à rotina perguntada quando aplicável.
        4. Se a informação não estiver presente na base de conhecimento, informe educadamente que o manual correspondente não contém essa especificação.
        """

        # Mensagens para a API
        mensagens_api = [{"role": "system", "content": system_prompt}]
        for m in st.session_state.messages:
            mensagens_api.append({"role": m["role"], "content": m["content"]})

        with st.chat_message("assistant"):
            with st.spinner("A consultar os manuais oficiais do SSW..."):
                try:
                    # Chamada ao modelo de IA
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",  # Ou outro modelo económico e rápido da sua preferência
                        messages=mensagens_api,
                        temperature=0.2
                    )
                    resposta_agente = response.choices[0].message.content
                    st.markdown(resposta_agente)
                    st.session_state.messages.append({"role": "assistant", "content": resposta_agente})
                except Exception as e:
                    st.error(f"Ocorreu um erro ao comunicar com a IA: {e}")
