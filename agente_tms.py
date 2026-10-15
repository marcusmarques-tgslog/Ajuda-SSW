import os
from datetime import datetime
import streamlit as st
from groq import Groq

# Configuração da página Web
st.set_page_config(page_title="Assistente TMS SSW", page_icon="🚚", layout="centered")

# CHAVE DA API DO GROQ
CHAVE_API_GROQ = "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"
client = Groq(api_key=CHAVE_API_GROQ)

ARQUIVO_BASE = "base_conhecimento_ssw.txt"
ARQUIVO_LOG_TESTES = "log_perguntas_testes.txt"

def carregar_base_conhecimento_direta():
    """Lê diretamente o ficheiro de conhecimento profundo consolidado."""
    if os.path.exists(ARQUIVO_BASE):
        with open(ARQUIVO_BASE, "r", encoding="utf-8") as f:
            texto = f.read()
            if len(texto.strip()) > 50:
                return texto
    return "Aviso: A base de conhecimento detalhada não foi encontrada."

def registar_interacao_teste(duvida, resposta):
    """Guarda todas as perguntas e respetivas respostas num ficheiro de texto separado."""
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bloco_log = f"[{data_hora}]\nPERGUTA: {duvida}\nRESPOSTA:\n{resposta}\n" + "-"*50 + "\n\n"
    
    with open(ARQUIVO_LOG_TESTES, "a", encoding="utf-8") as f:
        f.write(bloco_log)

def perguntar_ao_agente(duvida, base_conhecimento):
    # Procura inteligente: se a dúvida citar uma opção específica (ex: 600, 004), 
    # tenta fatiar a base em torno desse termo para garantir que a IA recebe o contexto exato.
    duvida_lower = duvida.lower()
    base_resumida = base_conhecimento
    
    if "tela" in duvida_lower or "opção" in duvida_lower or "opcao" in duvida_lower:
        import re
        numeros = re.findall(r'\d+', duvida)
        if numeros:
            termo_busca = numeros[0] # ex: "600" ou "004"
            pos = base_conhecimento.find(termo_busca)
            if pos != -1:
                # Pega um bloco de 15.000 caracteres em torno da menção encontrada
                inicio = max(0, pos - 3000)
                fim = min(len(base_conhecimento), pos + 12000)
                base_resumida = base_conhecimento[inicio:fim]

    # Se não encontrar um termo específico, usa uma fatia ampla inicial
    if len(base_resumida) > 20000:
        base_resumida = base_resumida[:20000]

    prompt_sistema = (
        "Você é um assistente técnico operacional especialista no sistema TMS SSW. "
        "Sua função é ler a documentação técnica fornecida e responder à dúvida do operador de forma clara, "
        "indicando sempre a opção correta do menu (ex: Opção 600, Opção 004, etc.) e o passo a passo prático.\n"
        "Seja direto e objetivo, explicando exatamente o que a tela ou rotina faz com base na documentação."
    )

    prompt_usuario = f"DOCUMENTAÇÃO TÉCNICA SSW:\n{base_resumida}\n\nPERGUTA DO OPERADOR: {duvida}"

    # Modelos disponíveis na Groq
    modelos_disponiveis = [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "qwen/qwen3-32b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile"
    ]

    erros = []

    for modelo in modelos_disponiveis:
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
if user_input := st.chat_input("Digite a sua dúvida sobre o SSW (ex: O que a tela 600 faz?)..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("A consultar os manuais oficiais do SSW..."):
            resposta = perguntar_ao_agente(user_input, base_ssw)
            
            # Grava automaticamente no ficheiro de log separado (tanto perguntas respondidas como falhas)
            registar_interacao_teste(user_input, resposta)
            
            st.write(resposta)
            st.session_state.messages.append({"role": "assistant", "content": resposta})
