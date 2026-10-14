import os
import re
import streamlit as st
from groq import Groq

# Tenta importar a biblioteca de navegação Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_DISPONIVEL = True
except ImportError:
    PLAYWRIGHT_DISPONIVEL = False

# Configuração da página Web
st.set_page_config(page_title="Assistente TMS SSW", page_icon="🚚", layout="centered")

# CHAVE DA API DO GROQ
CHAVE_API_GROQ = "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"
client = Groq(api_key=CHAVE_API_GROQ)

URLS_SSW = [
    "https://sistema.ssw.inf.br/ajuda/visao_geral.htm",
    "https://sistema.ssw.inf.br/ajuda/cursos_001.htm",
    "https://sistema.ssw.inf.br/ajuda/cursos.htm",
    "https://sistema.ssw.inf.br/ajuda/cursos_003.htm",
    "https://sistema.ssw.inf.br/ajuda/cursos_002.htm",
    "https://sistema.ssw.inf.br/ajuda/cursos_004.htm",
    "https://sistema.ssw.inf.br/ajuda/cursos_005.htm",
    "https://sistema.ssw.inf.br/ajuda/cursos_006.htm",
    "https://sistema.ssw.inf.br/ajuda/cursos_007.htm",
    "https://sistema.ssw.inf.br/ajuda/cursos_008.htm"
]

ARQUIVO_CACHE = "base_conhecimento_ssw.txt"

def extrair_texto_e_sublinks_playwright(url):
    """Abre a página num navegador Chromium real em segundo plano para capturar sublinks e quadros dinâmicos."""
    texto_limpo = ""
    sublinks = set()
    
    if not PLAYWRIGHT_DISPONIVEL:
        return texto_limpo, list(sublinks)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # Aguarda a renderização de elementos/frames da página
            page.wait_for_timeout(2000)
            
            # Extrai o texto visível da página
            texto_limpo = page.inner_text("body")
            
            # Captura todos os links presentes
            hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
            
            for href in hrefs:
                if "sistema.ssw.inf.br/ajuda/" in href and (href.endswith(".htm") or href.endswith(".html")):
                    url_limpa = href.split("?")[0].split("#")[0]
                    sublinks.add(url_limpa)

            browser.close()
    except Exception:
        pass

    return texto_limpo, list(sublinks)

@st.cache_data
def carregar_base_conhecimento(max_paginas=35):
    if os.path.exists(ARQUIVO_CACHE):
        with open(ARQUIVO_CACHE, "r", encoding="utf-8") as f:
            return f.read()

    conteudo_acumulado = []
    paginas_visitadas = set()
    fila_para_visitar = list(URLS_SSW)

    progress_bar = st.progress(0)
    status_text = st.empty()

    while fila_para_visitar and len(paginas_visitadas) < max_paginas:
        url_atual = fila_para_visitar.pop(0)
        if url_atual in paginas_visitadas:
            continue

        status_text.text(f"Mapeando página ({len(paginas_visitadas)+1}/{max_paginas}): {url_atual}")
        texto, novos_sublinks = extrair_texto_e_sublinks_playwright(url_atual)
        paginas_visitadas.add(url_atual)

        if texto and len(texto.strip()) > 50:
            conteudo_acumulado.append(f"=== INICIO FONTE: {url_atual} ===\n{texto}\n=== FIM FONTE ===")

        for link in novos_sublinks:
            if link not in paginas_visitadas and link not in fila_para_visitar:
                fila_para_visitar.append(link)

        progress_bar.progress(len(paginas_visitadas) / max_paginas)

    status_text.empty()
    progress_bar.empty()

    resultado_final = "\n\n".join(conteudo_acumulado)

    with open(ARQUIVO_CACHE, "w", encoding="utf-8") as f:
        f.write(resultado_final)
    
    return resultado_final

def buscar_contexto_relevante(duvida, base_conhecimento, limite_caracteres=14000):
    palavras_chave = [p.lower() for p in re.findall(r'\w+', duvida) if len(p) > 2]
    blocos = base_conhecimento.split("===")
    
    blocos_pontuados = []
    for bloco in blocos:
        if not bloco.strip():
            continue
        bloco_lower = bloco.lower()
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

    if not texto_selecionado.strip():
        return base_conhecimento[:limite_caracteres]

    return texto_selecionado

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

def perguntar_ao_agente(historico_mensagens, base_conhecimento):
    ultima_duvida = historico_mensagens[-1]["content"]
    contexto_filtrado = buscar_contexto_relevante(ultima_duvida, base_conhecimento)

    prompt_sistema = f"""
    Você é um consultor técnico especialista no TMS SSW.
    Sua única fonte de verdade é a BASE DE CONHECIMENTO fornecida abaixo.

    BASE DE CONHECIMENTO DE APOIO:
    {contexto_filtrado}

    REGRAS RÍGIDAS DE RESPOSTA:
    1. Forneça orientações operacionais práticas, objetivas e diretas.
    2. NUNCA mencione termos como "conforme o documento", "segundo a página" ou "de acordo com o texto". Responda diretamente como um especialista no sistema.
    3. Indique a Opção/Menu do SSW se constar explicitamente na base.
    4. Apresente os passos em lista numerada de forma clara.
    5. Finalize sempre com: "💡 *Caso precise de mais detalhes sobre alguma etapa ou pré-requisito, basta me pedir!*"
    """

    mensagens_payload = [{"role": "system", "content": prompt_sistema}]
    for msg in historico_mensagens[-6:]:
        mensagens_payload.append({"role": msg["role"], "content": msg["content"]})

    modelos_groq = obter_modelos_disponiveis()
    erros = []

    for modelo in modelos_groq:
        try:
            chat_completion = client.chat.completions.create(
                messages=mensagens_payload,
                model=modelo,
                temperature=0.1,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            erros.append(f"{modelo}: {e}")

    return f"Erro ao consultar a API do Groq: {' | '.join(erros)}"

# --- INTERFACE VISUAL (STREAMLIT) ---

st.title("🚚 Suporte Técnico TMS SSW")
st.caption("Assistente alimentado por varredura avançada via Playwright")

# Botão na barra lateral para reconstruir a base
with st.sidebar:
    st.header("Configurações da Base")
    if st.button("Reconstruir Base de Conhecimento"):
        if os.path.exists(ARQUIVO_CACHE):
            os.remove(ARQUIVO_CACHE)
        st.cache_data.clear()
        st.rerun()

# Carrega a base em cache
with st.spinner("A carregar base de conhecimento do SSW..."):
    base_ssw = carregar_base_conhecimento()

# Inicializa o histórico de mensagens na sessão
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Olá! Sou o seu assistente do TMS SSW. Como posso ajudar hoje?"}
    ]

# Exibe as mensagens anteriores
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Campo de entrada de texto para o usuário
if user_input := st.chat_input("Digite a sua dúvida sobre o SSW..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("A consultar a documentação..."):
            resposta = perguntar_ao_agente(st.session_state["messages"], base_ssw)
            st.write(resposta)
            st.session_state.messages.append({"role": "assistant", "content": resposta})