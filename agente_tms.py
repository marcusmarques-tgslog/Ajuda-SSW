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
            if len(texto.strip()) > 100:
                return texto
    return "Aviso: A base de conhecimento detalhada não foi encontrada ou está vazia."

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
    base_resumida = base_conhecimento[:25000]

    prompt_sistema = (
        "Você é um consultor especialista sênior no sistema TMS SSW. "
        "Sua função é ler atentamente a base de conhecimento técnica fornecida abaixo e responder à dúvida do usuário de forma completa, prática e objetiva.\n\n"
        "ESTRUTURA OBRIGATÓRIA DA RESPOSTA:\n"
        "1. O que é / Objetivo: Uma breve explicação do processo ou funcionalidade solicitada.\n"
        "2. Opção/Menu de Acesso: Informe claramente o código ou número da opção do menu no SSW (ex: Opção 004, Opção 038, Opção 056, etc.) que consta na documentação.\n"
        "3. Passo a Passo Detalhado: Explique as etapas operacionais necessárias com base estritamente nos manuais.\n"
        "4. Observações / Recomendações: Adicione alertas, regras fiscais ou dicas importantes relacionadas ao processo.\n\n"
        "DIRETRIZES:\n"
        "- Nunca diga que faltam informações genéricas se a resposta estiver mencionada na documentação abaixo.\n"
        "- Se a dúvida for sobre emissão de CTRC, consulte os dados da Opção 004 / 005 / 006 presentes na base."
    )

    prompt_usuario = f"BASE DE CONHECIMENTO OFICIAL SSW:\n{base_resumida}\n\nDÚVIDA DO OPERADOR:\n{duvida}"

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
