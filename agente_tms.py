import os
import urllib.request
from urllib.parse import urljoin, urlparse
import streamlit as st
from google import genai

# Configuração da página Web
st.set_page_config(page_title="Assistente TMS SSW", page_icon="🚚", layout="centered")

# CHAVE DA API DO GOOGLE GEMINI
# Dica: Pode colocar a chave diretamente aqui ou via st.secrets["GOOGLE_API_KEY"]
CHAVE_API_GOOGLE = st.secrets.get("GOOGLE_API_KEY", "SUA_CHAVE_GOOGLE_AQUI")

# Inicializa o cliente do Google GenAI
client = genai.Client(api_key=CHAVE_API_GOOGLE)

URLS_SSW = [
    "https://sistema.ssw.inf.br/ajuda/visao_geral.htm",
    "https://sistema.ssw.inf.br/ajuda/cursos_001.htm",
    "https://sistema.ssw.inf.br/ajuda/cursos.htm"
]
ARQUIVO_CACHE = "base_conhecimento_ssw.txt"

def extrair_texto_e_sublinks(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    sublinks = set()
    texto_limpo = ""
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('latin-1', errors='ignore')
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            dominio_base = urlparse(url).netloc
            for tag_a in soup.find_all('a', href=True):
                href = tag_a['href']
                url_completa = urljoin(url, href)
                if urlparse(url_completa).netloc == dominio_base and "/ajuda/" in url_completa:
                    url_limpa = url_completa.split('?')[0].split('#')[0]
                    if url_limpa.endswith('.htm') or url_limpa.endswith('.html'):
                        sublinks.add(url_limpa)

            for script in soup(["script", "style"]):
                script.extract()
            
            # Filtra linhas muito curtas (menus de navegação/botões desnecessários)
            linhas = [linha.strip() for linha in soup.get_text(separator='\n').splitlines() if len(linha.strip()) > 25]
            texto_limpo = "\n".join(linhas)

    except Exception:
        pass

    return texto_limpo[:3000], list(sublinks)

@st.cache_data
def carregar_base_conhecimento(max_paginas=15):
    if os.path.exists(ARQUIVO_CACHE):
        with open(ARQUIVO_CACHE, "r", encoding="utf-8") as f:
            return f.read()

    paginas_visitadas = set()
    fila_para_visitar = list(URLS_SSW)
    conteudo_acumulado = []

    while fila_para_visitar and len(paginas_visitadas) < max_paginas:
        url_atual = fila_para_visitar.pop(0)
        if url_atual in paginas_visitadas:
            continue

        texto, novos_sublinks = extrair_texto_e_sublinks(url_atual)
        paginas_visitadas.add(url_atual)

        if texto:
            conteudo_acumulado.append(f"--- FONTE: {url_atual} ---\n{texto}\n")

        for link in novos_sublinks:
            if link not in paginas_visitadas and link not in fila_para_visitar:
                fila_para_visitar.append(link)

    resultado_final = "\n".join(conteudo_acumulado)

    with open(ARQUIVO_CACHE, "w", encoding="utf-8") as f:
        f.write(resultado_final)
    
    return resultado_final

def perguntar_ao_agente(duvida, base_conhecimento):
    base_resumida = base_conhecimento[:15000]

    prompt_sistema = """
    Você é um consultor especialista no sistema TMS SSW.
    Sua função é fornecer respostas claras, bem estruturadas e informativas.

    ESTRUTURA A SEGUIR NAS RESPOSTAS:
    1. **O que é / Objetivo:** Uma breve explicação do processo ou funcionalidade solicitada.
    2. **Opção/Menu de Acesso:** Informe o caminho ou número do menu no SSW (ex: Opção 412, Opção 101, etc.).
    3. **Passo a Passo Detalhado:** Explique as etapas necessárias de forma clara e instrutiva.
    4. **Observações / Recomendações (se aplicável):** Adicione alertas, pré-requisitos ou dicas importantes relacionadas ao processo.

    DIRETRIZES DE ESTILO:
    - Mantenha um tom profissional, prestativo e instrutivo.
    - Evite copiar e colar menus de navegação do site que não agreguem valor à resposta do usuário.
    - Se a informação não constar na documentação, informe de forma gentil que os detalhes específicos não foram encontrados na base.
    """

    prompt_completo = f"""
    {prompt_sistema}

    DOCUMENTAÇÃO SSW:
    {base_resumida}

    DÚVIDA DO USUÁRIO:
    {duvida}
    """

    # Modelos recomendados do Google Gemini (ex: gemini-2.5-flash ou gemini-2.5-pro)
    modelos_google = ["gemini-2.5-flash", "gemini-2.5-pro"]
    erros = []

    for modelo in modelos_google:
        try:
            resposta = client.models.generate_content(
                model=modelo,
                contents=prompt_completo,
            )
            if resposta and resposta.text:
                return resposta.text
        except Exception as e:
            erros.append(f"{modelo}: {e}")

    return f"Erro ao consultar a API do Google Gemini: {' | '.join(erros)}"

# --- INTERFACE VISUAL (STREAMLIT) ---

st.title("🚚 Suporte Técnico TMS SSW")
st.caption("Assistente Inteligente alimentado pelo Google Gemini")

# Carrega a base em cache
with st.spinner("Carregando base de conhecimento do SSW..."):
    base_ssw = carregar_base_conhecimento()

# Inicializa o histórico de mensagens na sessão
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Olá! Sou o seu assistente do TMS SSW alimentado pelo Google. Como posso ajudar hoje?"}
    ]

# Exibe as mensagens anteriores
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Campo de entrada de texto para o usuário
if user_input := st.chat_input("Digite a sua dúvida sobre o SSW..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Consultando documentação no Google Gemini..."):
            resposta = perguntar_ao_agente(user_input, base_ssw)
            st.write(resposta)
            st.session_state.messages.append({"role": "assistant", "content": resposta})
