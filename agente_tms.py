import os
import re
import streamlit as st
from groq import Groq

st.set_page_config(page_title="Assistente TMS SSW", page_icon="🚚", layout="centered")

# Captura a API Key do Streamlit Secrets ou usa valor padrão
if "CHAVE_API_GROQ" in st.secrets:
    CHAVE_API_GROQ = st.secrets["CHAVE_API_GROQ"]
else:
    CHAVE_API_GROQ = "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"

client = Groq(api_key=CHAVE_API_GROQ)
ARQUIVO_BASE = "base_conhecimento_ssw.txt"

@st.cache_data
def carregar_base():
    """Lê a base completa com todas as telas gerada previamente."""
    if os.path.exists(ARQUIVO_BASE):
        with open(ARQUIVO_BASE, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def buscar_contexto_relevante(duvida, base_conhecimento, limite_caracteres=16000):
    """Filtra na base completa quais blocos de páginas/manuais contêm a resposta."""
    if not base_conhecimento:
        return ""

    palavras_chave = [p.lower() for p in re.findall(r'\w+', duvida) if len(p) > 2]
    blocos = base_conhecimento.split("===")
    
    blocos_pontuados = []
    for bloco in blocos:
        if not bloco.strip():
            continue
        bloco_lower = bloco.lower()
        # Calcula a relevância do bloco com base nas palavras buscadas
        pontuacao = sum(bloco_lower.count(palavra) for palavra in palavras_chave)
        if pontuacao > 0:
            blocos_pontuados.append((pontuacao, "===" + bloco))

    blocos_pontuados.sort(key=lambda x: x[0], reverse=True)
    
    texto_selecionado = ""
    for _, bloco_texto in blocos_pontuados:
        if len(texto_selecionado) + len(bloco_texto) <= limite_caracteres:
            texto_selecionado += "\n\n" + bloco_texto
        else:
            break

    return texto_selecionado if texto_selecionado.strip() else base_conhecimento[:limite_caracteres]

def perguntar_ao_agente(historico_mensagens, base_conhecimento):
    ultima_duvida = historico_mensagens[-1]["content"]
    contexto_filtrado = buscar_contexto_relevante(ultima_duvida, base_conhecimento)

    prompt_sistema = f"""
    Você é o assistente técnico oficial e especialista no sistema TMS SSW.
    Sua única fonte de consulta é a documentação completa dos manuais do SSW fornecida abaixo.

    DOCUMENTAÇÃO E MANUAIS DO SSW:
    {contexto_filtrado}

    REGRAS DE RESPOSTA:
    1. Identifique no texto a Opção/Menu do SSW referente à dúvida e exiba na primeira linha no formato:
       **Opção / Menu SSW:** [Número ou Nome do Menu extraído da documentação]
    2. Detalhe os passos práticos exatamente como descritos nos manuais do SSW.
    3. Seja direto, prático e evite respostas genéricas.
    4. NUNCA mencione "de acordo com o texto" ou "na documentação". Fale com propriedade como consultor do SSW.
    5. Finalize sempre com: "💡 *Caso precise de mais detalhes sobre alguma etapa ou pré-requisito, basta me pedir!*"
    """

    mensagens_payload = [{"role": "system", "content": prompt_sistema}]
    for msg in historico_mensagens[-6:]:
        mensagens_payload.append({"role": msg["role"], "content": msg["content"]})

    try:
        chat_completion = client.chat.completions.create(
            messages=mensagens_payload,
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Erro ao consultar a inteligência da Groq: {e}"

# --- INTERFACE VISUAL STREAMLIT ---

st.title("🚚 Suporte Técnico TMS SSW")
st.caption("Base Integrada com Mapeamento Completo de Telas do SSW")

base_ssw = carregar_base()

if not base_ssw:
    st.warning("⚠️ O arquivo 'base_conhecimento_ssw.txt' não foi encontrado no repositório. Por favor, envie o arquivo gerado pelo script para o GitHub.")

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Olá! Sou o seu assistente do TMS SSW. Como posso ajudar com os menus e rotinas do sistema hoje?"}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if user_input := st.chat_input("Digite a sua dúvida sobre o SSW..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("A consultar documentação completa do SSW..."):
            resposta = perguntar_ao_agente(st.session_state["messages"], base_ssw)
            st.write(resposta)
            st.session_state.messages.append({"role": "assistant", "content": resposta})
