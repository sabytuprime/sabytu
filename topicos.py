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
}

TOPICOS_RE = {k: re.compile(v["regex"], re.IGNORECASE) for k, v in TOPICOS.items()}


def detectar_topicos(texto):
    """Retorna lista de slugs de tópicos mencionados no texto."""
    achados = []
    for slug, rx in TOPICOS_RE.items():
        if rx.search(texto):
            achados.append(slug)
    return achados
