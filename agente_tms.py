import os
import streamlit as st
from groq import Groq

# Configuração da página Web
st.set_page_config(page_title="Assistente TMS SSW", page_icon="🚚", layout="centered")

# CHAVE DA API DO GROQ
CHAVE_API_GROQ = "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"
client = Groq(api_key=CHAVE_API_GROQ)

ARQUIVO_BASE = "base_conhecimento_ssw.txt"

def carregar_base_conhecimento_direta():
    """Lê diretamente o ficheiro de conhecimento profundo consolidado."""
    if os.path.exists(ARQUIVO_BASE):
        with open(ARQUIVO_BASE, "r", encoding="utf-8") as f:
            texto = f.read()
            if len(texto.strip()) > 50:
                return texto
    return "Aviso: A base de conhecimento detalhada não foi encontrada."

def perguntar_ao_agente(duvida, base_conhecimento):
    # Restringe a base enviada para uma quantidade segura de tokens, evitando o erro de limite (413)
    base_resumida = base_conhecimento[:15000]

    prompt_sistema = (
        "Você é um assistente técnico operacional especialista no sistema TMS SSW. "
        "Sua função é ler a documentação técnica fornecida e responder à dúvida do operador de forma clara, "
        "indicando sempre a opção correta do menu (ex: Opção 004, Opção 038, etc.) e o passo a passo prático.\n"
        "Seja direto e objetivo, sem falas introdutórias genéricas."
    )

    prompt_usuario = f"DOCUMENTAÇÃO TÉCNICA SSW:\n{base_resumida}\n\nPERGUTA DO OPERADOR: {duvida}"

    # Lista estática e segura dos modelos oficiais da Groq (evita modelos experimentais restritos)
    modelos_seguros = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant"
    ]

    erros = []

    for modelo in modelos_seguros:
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario}
                ],
                model=modelo,
                temperature=0.1,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            erros.append(f"{modelo}: {e}")

    return f"Erro ao consultar a API do Groq: {' | '.join(erros)}"

# --- INTERFACE VISUAL (STREAMLIT) ---

st.title("🚚 Suporte Técnico TMS SSW")
st.caption("Assistente Inteligente alimentado pelos Manuais Oficiais do SSW")

# Carrega a base de conhecimento
with st.spinner("A carregar base de conhecimento detalhada do SSW..."):
    base_ssw = carregar_base_conhecimento_direta()

# Inicializa o histórico de mensagens na sessão
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Olá! Sou o seu assistente técnico do TMS SSW. Como posso ajudar nas rotinas de hoje?"}
    ]

# Exibe as mensagens anteriores
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Campo de entrada de texto para o usuário
if user_input := st.chat_input("Digite a sua dúvida sobre o SSW (ex: Como emitir CTRC?)..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("A consultar os manuais oficiais do SSW..."):
            resposta = perguntar_ao_agente(user_input, base_ssw)
            st.write(resposta)
            st.session_state.messages.append({"role": "assistant", "content": resposta})
