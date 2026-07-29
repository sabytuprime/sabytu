"""
Watchlist central de tópicos do radar Sabytu.
Cada tópico tem: regex de detecção, emoji, nome de exibição,
e o slug usado como artigo da Wikipedia pra baseline de contexto.
"""
import re

TOPICOS = {
    "gasolina":       {"regex": r"gasolina",                          "emoji": "⛽", "nome": "Gasolina",       "wiki": "Gasolina"},
    "iphone":         {"regex": r"iphone",                            "emoji": "📱", "nome": "iPhone",         "wiki": "IPhone"},
    "bitcoin":        {"regex": r"bitcoin|\bbtc\b",                   "emoji": "₿", "nome": "Bitcoin",        "wiki": "Bitcoin"},
    "passagem_aerea": {"regex": r"passagem a[eé]rea|passagens? a[eé]reas?", "emoji": "✈️", "nome": "Passagens",  "wiki": "Tarifa_aérea"},
    "frete_gratis":   {"regex": r"frete gr[aá]tis",                   "emoji": "🛒", "nome": "Frete grátis",   "wiki": None},
    "pet_shop":       {"regex": r"pet ?shop",                         "emoji": "🐾", "nome": "Pet shop",       "wiki": None},
    "moto_0km":       {"regex": r"moto 0 ?km|moto zero ?km",          "emoji": "🏍️", "nome": "Moto 0km",       "wiki": None},
    "farmacia":       {"regex": r"farm[aá]cia",                       "emoji": "💊", "nome": "Farmácia",       "wiki": None},
    "aluguel":        {"regex": r"aluguel",                           "emoji": "🏠", "nome": "Aluguel",        "wiki": None},
    "futebol":        {"regex": r"futebol|libertadores|brasileir[aã]o", "emoji": "⚽", "nome": "Futebol",       "wiki": None},
    "black_friday":   {"regex": r"black friday",                      "emoji": "🎉", "nome": "Black Friday",   "wiki": "Black_Friday"},
    "novela":         {"regex": r"\bnovela\b|final da novela",        "emoji": "📺", "nome": "Novela",         "wiki": None},
    "serie":          {"regex": r"\bs[eé]rie\b|nova temporada",       "emoji": "🎬", "nome": "Série do momento", "wiki": None},
    "meme":           {"regex": r"\bmeme\b|viralizou|\bviral\b",      "emoji": "😂", "nome": "Meme do momento", "wiki": None},
    "cinema":         {"regex": r"\bcinema\b|estreia nos cinemas",    "emoji": "🎥", "nome": "Cinema",         "wiki": None},
    "show_ingresso":  {"regex": r"\bingresso\b|\bshow\b",             "emoji": "🎤", "nome": "Show/Ingresso",  "wiki": None},
    "notebook":       {"regex": r"\bnotebook\b|laptop",               "emoji": "💻", "nome": "Notebook",       "wiki": None},
    "moda":           {"regex": r"\bmoda\b|tend[eê]ncia de roupa",    "emoji": "👕", "nome": "Roupa/Moda",     "wiki": None},
    "dolar":          {"regex": r"\bd[oó]lar\b|c[aâ]mbio",            "emoji": "💵", "nome": "Dólar",          "wiki": None},
    "conta_de_luz":   {"regex": r"conta de luz|bandeira tarif[aá]ria","emoji": "💡", "nome": "Conta de luz",   "wiki": None},
    "chuva_clima":    {"regex": r"\bchuva\b|temporal|previs[aã]o do tempo", "emoji": "🌧️", "nome": "Chuva/Clima", "wiki": None},
    "transporte":     {"regex": r"\b[oô]nibus\b|transporte p[uú]blico","emoji": "🚌", "nome": "Transporte",     "wiki": None},
    "viagem":         {"regex": r"\bviagem\b|pacote de viagem",       "emoji": "🧳", "nome": "Viagem/Turismo", "wiki": None},
    "mega_sena":      {"regex": r"mega-?sena",                       "emoji": "🎰", "nome": "Mega-Sena",      "wiki": "Mega-Sena"},
    "netflix":        {"regex": r"\bnetflix\b",                      "emoji": "🎬", "nome": "Netflix",        "wiki": "Netflix"},
    "youtube":        {"regex": r"\byoutube\b",                      "emoji": "▶️", "nome": "YouTube",        "wiki": "YouTube"},
    "pix":            {"regex": r"\bpix\b",                          "emoji": "💳", "nome": "Pix",            "wiki": "Pix"},
    "inss":           {"regex": r"\binss\b",                         "emoji": "👴", "nome": "INSS",           "wiki": "Instituto_Nacional_do_Seguro_Social"},
    "fgts":           {"regex": r"\bfgts\b",                         "emoji": "💰", "nome": "FGTS",           "wiki": "FGTS"},
    "mundial_clubes": {"regex": r"mundial de clubes",                "emoji": "🏆", "nome": "Mundial de Clubes","wiki": None},
    "labubu":         {"regex": r"\blabubu\b",                       "emoji": "🧸", "nome": "Labubu",         "wiki": "Labubu"},
    "gemini_ia":      {"regex": r"\bgemini\b|intelig[eê]ncia artificial", "emoji": "🤖", "nome": "Gemini/IA", "wiki": None},
    "concurso_publico":{"regex": r"concurso p[uú]blico|\bedital\b",   "emoji": "📝", "nome": "Concurso Público","wiki": "Concurso_público"},
    "fipe":           {"regex": r"tabela fipe|\bfipe\b",              "emoji": "🚙", "nome": "Tabela FIPE",    "wiki": None},
    "clima_previsao": {"regex": r"previs[aã]o do tempo|clima hoje",   "emoji": "🌦️", "nome": "Clima/Previsão", "wiki": None},
    "whatsapp_web":   {"regex": r"whatsapp web|whatsapp fora do ar",  "emoji": "💬", "nome": "WhatsApp Web",   "wiki": None},
    "futebol_resultados":{"regex": r"resultado do jogo|placar de hoje","emoji": "⚽", "nome": "Resultado do jogo","wiki": None},
    "receitas":       {"regex": r"\breceita de\b|\breceitas\b",       "emoji": "🍰", "nome": "Receitas",       "wiki": None},
    "novelas_resumo": {"regex": r"resumo da novela|pr[oó]ximos cap[ií]tulos", "emoji": "📺", "nome": "Novelas (resumo)", "wiki": None},
    "tutoriais_como_fazer":{"regex": r"\bcomo fazer\b|passo a passo",  "emoji": "🎓", "nome": "Tutoriais",      "wiki": None},
    "emprego_vagas":  {"regex": r"vagas? de emprego|vaga de trabalho","emoji": "💼", "nome": "Emprego/Vagas",  "wiki": None},
    "remedio_farmacia":{"regex": r"\brem[eé]dio\b|\bsintoma\b",       "emoji": "💊", "nome": "Remédio/Farmácia","wiki": None},
    "onibus_passagem":{"regex": r"passagem de [oô]nibus|tarifa de [oô]nibus", "emoji": "🚌", "nome": "Ônibus/Passagem", "wiki": None},
    "preco_cafe":     {"regex": r"pre[cç]o do caf[eé]",               "emoji": "☕", "nome": "Preço do café",  "wiki": None},
    "preco_arroz_feijao":{"regex": r"pre[cç]o do arroz|pre[cç]o do feij[aã]o", "emoji": "🍚", "nome": "Arroz e Feijão", "wiki": None},
    "preco_carne":    {"regex": r"pre[cç]o da carne",                 "emoji": "🥩", "nome": "Preço da carne", "wiki": None},
    "futebol_internacional":{"regex": r"futebol internacional|liga dos campe[oõ]es", "emoji": "🌍", "nome": "Futebol Internacional", "wiki": None},
    "carro_usado":    {"regex": r"carro usado|carro seminovo",        "emoji": "🚗", "nome": "Carro usado",    "wiki": None},
    "escola_matricula":{"regex": r"matr[ií]cula escolar|volta [àa]s aulas", "emoji": "🏫", "nome": "Escola/Matrícula", "wiki": None},
    "plano_de_saude": {"regex": r"plano de sa[uú]de",                 "emoji": "🏥", "nome": "Plano de Saúde", "wiki": None},
    "dentista_tratamento":{"regex": r"\bdentista\b",                  "emoji": "🦷", "nome": "Dentista",       "wiki": None},
    "academia_emagrecer":{"regex": r"\bemagrecer\b|academia de gin[aá]stica", "emoji": "💪", "nome": "Academia/Emagrecer", "wiki": None},
    "viagem_hotel":   {"regex": r"pacote de hotel|reserva de hotel",  "emoji": "🏖️", "nome": "Viagem/Hotel",   "wiki": None},
    "morango_do_amor_receita":{"regex": r"morango do amor",           "emoji": "🍓", "nome": "Morango do amor","wiki": None},
    "bobbie_goods":   {"regex": r"bobbie goods",                      "emoji": "🎨", "nome": "Bobbie Goods",   "wiki": None},
    "bebe_reborn":    {"regex": r"beb[eê] reborn",                    "emoji": "👶", "nome": "Bebê reborn",    "wiki": None},
}

TOPICOS_RE = {k: re.compile(v["regex"], re.IGNORECASE) for k, v in TOPICOS.items()}


def detectar_topicos(texto):
    """Retorna lista de slugs de tópicos mencionados no texto."""
    achados = []
    for slug, rx in TOPICOS_RE.items():
        if rx.search(texto):
            achados.append(slug)
    return achados
