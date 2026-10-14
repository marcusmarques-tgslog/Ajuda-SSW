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

def obter_modelos_disponiveis():
    modelos_padrao = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-8b-8192"
    ]
    try:
        resposta_modelos = client.models.list()
        modelos_api = [m.id for m in resposta_modelos.data if "whisper" not in m.id and "guard" not in m.id]
        if modelos_api:
            return modelos_api
    except Exception:
        pass
    return modelos_padrao

def perguntar_ao_agente(duvida, base_conhecimento):
    # Pega uma parte rica e profunda do meio/fim da base onde contêm as opções de menu e cursos (evitando índices iniciais)
    base_resumida = base_conhecimento[5000:35000] if len(base_conhecimento) > 35000 else base_conhecimento

    prompt_sistema = (
        "Você é um assistente técnico operacional estritamente focado no sistema TMS SSW. "
        "O usuário fará uma pergunta sobre uma rotina do sistema (ex: emissão de CTRC, cadastros, baixas, faturamento).\n"
        "Sua única tarefa é responder diretamente à pergunta utilizando os dados técnicos da documentação abaixo.\n"
        "NÃO faça discursos introdutórios, NÃO diga que vai analisar a base e NÃO invente exemplos.\n\n"
        "ESTRUTURA OBRIGATÓRIA DA RESPOSTA:\n"
        "1. **Objetivo / Resumo:** O que é o processo.\n"
        "2. **Opção de Menu:** Indique o código exato da opção (ex: Opção 004, Opção 038, etc.).\n"
        "3. **Passo a Passo Prático:** Instruções operacionais detalhadas com base nos manuais.\n"
        "4. **Observações:** Alertas importantes ou regras associadas."
    )

    prompt_usuario = f"DOCUMENTAÇÃO TÉCNICA SSW:\n{base_resumida}\n\nPERGUTA DO OPERADOR: {duvida}"

    modelos_groq = obter_modelos_disponiveis()
    erros = []

    for modelo in modelos_groq:
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

# Carrega a base de conhecimento de forma garantida
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
