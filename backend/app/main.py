# ============================
# IMPORTAÇÕES
# ============================

# FastAPI e utilitários
from fastapi                 import FastAPI, File, UploadFile, HTTPException  # importa FastAPI e tipos/erros para endpoints de upload
from fastapi.responses       import JSONResponse                              # importa JSONResponse para retornar JSON customizado
from fastapi.middleware.cors import CORSMiddleware                            # importa middleware CORS para permitir chamadas do frontend

# Matching aproximado, leitura de bytes, regex, ID de sessão, normalização de caracteres
from difflib                 import get_close_matches                         # para similaridade de strings (detecta colunas aproximadas)
from io                      import BytesIO                                   

import re, uuid, unicodedata, uvicorn, pandas as pd                           


# ============================
# INICIALIZAÇÃO DO SERVIDOR FASTAPI
# ============================

app = FastAPI()                                                               # cria a instância da aplicação FastAPI

# Configuração de CORS para permitir que o frontend acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,                                                   # permite cookies e autenticação se necessário
    allow_origins=["*"],                                                      # libera acesso de qualquer origem (ideal para desenvolvimento)
    allow_methods=["*"],                                                      # libera todos os métodos HTTP
    allow_headers=["*"]                                                       # libera todos os headers
)

# Armazena DataFrames por sessão.
# Cada vez que o usuário faz upload, criamos um session_id único e guardamos o DF.
sessions = {}


# ======================================================================
# FUNÇÕES AUXILIARES
# ======================================================================

# --------------------------------------------------------
# NORMALIZAÇÃO DE TEXTO (remove acentos, baixa caixa etc)
# --------------------------------------------------------

def normalize_text(text):
    """Normaliza texto para facilitar comparação: remove acentos, caracteres especiais e deixa minúsculo."""
    if text is None:
        return ""
    return (
        unicodedata.normalize('NFKD', str(text))  # remove acentos
                  .encode('ASCII', 'ignore')       # remove caracteres não ASCII
                  .decode('utf-8')
                  .lower()
                  .strip()
    )


def normalize_series(s):
    """
    Normaliza uma série inteira do pandas, aplicando normalize_text e removendo caracteres
    que não interessam. Mantém hífen pois é útil para alguns valores.
    """
    return (
        s.astype(str)
         .apply(normalize_text)
         .str.replace(r'[^a-z0-9\s\-]+', '', regex=True)
         .str.strip()
    )


def prepare_normalized_columns(df: pd.DataFrame):
    """
    Cria colunas auxiliares *_norm em todas as colunas,
    preservando as originais e criando versões normalizadas para filtros textuais.
    """
    for col in list(df.columns):
        df[col + "_norm"] = normalize_series(df[col])
    return df


# ======================================================================
# EXTRAÇÃO DE COLUNA CANDIDATA A PARTIR DA PERGUNTA DO USUÁRIO
# ======================================================================

def extract_column_candidate(question: str, columns: list, df: pd.DataFrame, numeric_only=False):
    """
    Tenta identificar qual coluna o usuário está se referindo na pergunta.
    Usa normalização + pontuação por matching aproximado.
    """
    q = normalize_text(question)
    columns_norm = [normalize_text(c) for c in columns]

    best_col = None
    best_score = 0

    # tokens da pergunta para comparação
    q_tokens = q.replace("=", " ").replace(">", " ").replace("<", " ").split()

    for col, col_norm in zip(columns, columns_norm):

        # ignorar colunas auxiliares *_norm
        if str(col).endswith("_norm"):
            continue

        score = 0

        # Se a operação for numérica, ignorar colunas não numéricas
        if numeric_only:
            from pandas.api.types import is_numeric_dtype
            try:
                if not is_numeric_dtype(df[col]):
                    continue
            except Exception:
                # se der erro, ignora checagem pra evitar crash
                continue

        # coluna aparece literalmente na pergunta
        if col_norm in q:
            score += 3

        # comparar tokens
        for token in col_norm.split("_"):
            if token in q_tokens:
                score += 2
            elif token in q:
                score += 1

        # similaridade aproximada
        match = get_close_matches(col_norm, [q], n=1, cutoff=0.5)
        if match:
            score += 1

        # atualiza melhor coluna
        if score > best_score:
            best_score = score
            best_col = col

    return best_col


# ======================================================================
# OPERAÇÕES SUPORTADAS (sum, mean, count, list)
# ======================================================================

def apply_count(df, col):
    return len(df[col].dropna())

def apply_sum(df, col):
    try:
        return df[col].sum()
    except Exception as e:
        return f"Não é possível somar a coluna '{col}': {e}"

def apply_mean(df, col):
    try:
        return df[col].mean()
    except Exception as e:
        return f"Não é possível calcular a média da coluna '{col}': {e}"

def apply_list(df, col):
    return df[col].dropna().unique().tolist()


def execute_operation(intent, df, col):
    """
    Executa a operação solicitada na coluna indicada.
    """
    if intent is None:
        return "Intenção não reconhecida."

    # count sem coluna => contar linhas
    if intent == "count" and col is None:
        return len(df)

    if col is None:
        return "Não consegui identificar a coluna para a operação."

    if intent == "count": return apply_count(df, col)
    if intent == "sum":   return apply_sum(df, col)
    if intent == "mean":  return apply_mean(df, col)
    if intent == "list":  return apply_list(df, col)

    return "Intenção não reconhecida."


# ======================================================================
# DETECÇÃO DE INTENÇÃO (sum/count/mean/list)
# ======================================================================

def is_count_intent(q: str) -> bool:
    return any(k in q for k in ["quantos", "quantas", "contagem", "número de", "numero de"])

def is_sum_intent(q: str) -> bool:
    return any(k in q for k in ["soma", "somar", "somatório", "somatorio", "totalizar", "total da"])

def is_mean_intent(q: str) -> bool:
    return any(k in q for k in ["média", "media", "valor médio", "valor medio"])

def is_list_intent(question: str) -> bool:
    keywords = [
        "listar","liste","mostre","mostra","mostrar","exibir","exiba","quais",
        "quais são","quais sao","me de","me dê","retornar","retorne","trazer","traga"
    ]
    return any(k in question for k in keywords)

def has_total_phrase(q: str) -> bool:
    return "total de" in q


# ======================================================================
# DETECÇÃO DE FILTROS (ex: "onde empresa = X")
# ======================================================================

def has_filter_intent(question: str):
    """
    Detecta se a pergunta contém algo como 'onde', 'em que', 'por', etc.
    """
    filter_phrases = [
        "no qual", "na qual", "nos quais", "nas quais",
        "onde", "em que",
        " por ", " para ",
        " no ", " na ", " nos ", " nas ",
        " em "
    ]

    # frasa maior primeiro para evitar conflitos
    filter_phrases = sorted(filter_phrases, key=len, reverse=True)

    for phrase in filter_phrases:
        pos = question.find(phrase)
        if pos != -1:
            return True, pos, phrase

    return False, -1, None


def detect_intent(df: pd.DataFrame, question: str):
    """
    Divide a pergunta em: parte da operação (sum/count/etc)
    e parte do filtro (empresa = X)
    """
    q = normalize_text(question)
    has_filter, pos, phrase = has_filter_intent(q)

    if has_filter:
        q_operation = q[:pos].strip()                     # antes da frase-chave
        q_filter    = q[pos+len(phrase):].strip()         # depois da frase-chave
    else:
        q_operation = q
        q_filter    = None
    
    columns = list(df.columns)

    # detectar intenção
    if is_mean_intent(q_operation):  return "mean",  q_filter
    if is_sum_intent(q_operation):   return "sum",   q_filter
    if is_count_intent(q_operation): return "count", q_filter
    if is_list_intent(q_operation):  return "list",  q_filter

    # tentativa de fallback
    if has_total_phrase(q_operation):
        col = extract_column_candidate(q_operation, columns, df)
        if col:
            if pd.api.types.is_numeric_dtype(df[col]): return "sum", q_filter
            else: return "count", q_filter
        else:
            return "erro_coluna", q_filter

    return None, q_filter


# ======================================================================
# EXTRAÇÃO E APLICAÇÃO DE FILTROS
# ======================================================================

def extract_filters(filter_text: str, df: pd.DataFrame):
    """
    Extrai filtros do tipo:
    coluna = valor,
    coluna != valor,
    coluna > número,
    coluna < número
    """
    if not filter_text:
        return []

    f = normalize_text(filter_text)

    # regex para capturar coluna e valor
    patterns = [
        r"(\w+)\s*=\s*([\w\s\-\.\:\/]+)",
        r"(\w+)\s*==\s*([\w\s\-\.\:\/]+)",
        r"(\w+)\s*!=\s*([\w\s\-\.\:\/]+)",
        r"(\w+)\s*>\s*([\d\.]+)",
        r"(\w+)\s*<\s*([\d\.]+)"
    ]

    filters = []

    for pat in patterns:
        matches = re.findall(pat, f)
        for col_raw, val_raw in matches:

            col = extract_column_candidate(col_raw, df.columns, df)
            if not col:
                continue

            val = normalize_text(val_raw).rstrip(".,;!?: ")

            # tenta converter para número
            try:
                val = float(val)
            except:
                pass

            filters.append((col, pat, val))

    return filters


def apply_filters(df: pd.DataFrame, filters):
    """
    Aplica lista de filtros ao DataFrame.
    Operações numéricas usam coluna original.
    Operações textuais usam coluna normalizada *_norm.
    """
    df2 = df.copy()

    for col, pat, val in filters:

        is_numeric = isinstance(val, (int, float))

        if is_numeric:
            if   ">" in pat: df2 = df2[df2[col] > val]
            elif "<" in pat: df2 = df2[df2[col] < val]
            else:            df2 = df2[df2[col] == val]

        else:
            col_norm = col + "_norm"
            val_norm = normalize_text(val)

            series_norm = df2[col_norm].fillna('')

            if "!=" in pat:
                df2 = df2[series_norm != val_norm]
            else:
                df2 = df2[series_norm == val_norm]

    return df2


# ======================================================================
# PIPELINE FINAL: ENTENDER A PERGUNTA E RESPONDER
# ======================================================================

def parse_and_answer(df: pd.DataFrame, pergunta: str):
    """
    Função completa que:
    - identifica intenção
    - extrai filtros
    - filtra dataframe
    - identifica coluna da operação
    - executa operação
    """
    intent, filter_part = detect_intent(df, pergunta)

    filters = extract_filters(filter_part, df)

    df_filtered = apply_filters(df, filters) if filters else df

    coluna = extract_column_candidate(
        pergunta,
        df.columns,
        df,
        numeric_only = intent in ["sum", "mean"]
    )

    # impedir retornar coluna *_norm
    if coluna and coluna.endswith("_norm"):
        coluna = None

    resultado = execute_operation(intent, df_filtered, coluna)

    # count sem coluna => contar linhas filtradas
    if intent == "count" and coluna is None:
        resultado = len(df_filtered)

    return str(resultado)


# ======================================================================
# ENDPOINTS FASTAPI
# ======================================================================

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Recebe um arquivo .xlsx do usuário e cria uma sessão contendo o DataFrame.
    """
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(400, "Apenas arquivos .xlsx são suportados")

    contents = await file.read()                                               # lê bytes do arquivo
    df = pd.read_excel(BytesIO(contents))                                      # converte para DataFrame

    df = prepare_normalized_columns(df)                                        # cria colunas *_norm

    session_id = str(uuid.uuid4())                                             # gera ID de sessão
    sessions[session_id] = {"df": df, "history": []}                           # guarda DF e histórico vazio

    return JSONResponse({
        "session_id": session_id,
        "message": f"Arquivo {file.filename} recebido com sucesso",
        "columns": list(df.columns)
    })


@app.post("/ask")
async def ask(payload: dict):
    """
    Recebe uma pergunta do usuário e retorna a resposta da análise.
    """
    sessao_id = payload.get("session_id")
    pergunta  = payload.get("question")

    if not sessao_id or not pergunta:
        raise HTTPException(400, '"session_id" e "question" são obrigatórios!')

    sessao = sessions.get(sessao_id)
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada")

    df = sessao["df"]
    answer = parse_and_answer(df, pergunta)

    # salva histórico
    sessao["history"].append({"q": pergunta, "a": answer})

    return JSONResponse({"answer": answer, "history": sessao["history"]})


# ======================================================================
# EXECUÇÃO LOCAL (python main.py)
# ======================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
