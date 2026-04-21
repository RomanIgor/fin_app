"""
Categorizare automată bazată pe keyword-uri germane comune.
Folosește word-boundary matching pentru keyword-uri scurte ca să evite false positives
precum 'rwe' prinzând în 'überweisung' sau 'hem' prinzând în 'Chemnitz'.
"""
import re
import pandas as pd
from db import get_rules


# IMPORTANT: ordinea contează. Prima categorie care match-uiește câștigă.
# Categoriile specifice (Einkommen, Wohnen) trebuie ÎNAINTEA celor generice.
CATEGORIES = {
    'Einkommen': [
        'gehalt', 'lohn/gehalt', 'lohn / gehalt', 'sala lohn',
        'honorar', 'salary', 'community4you', 'community 4 you', 'dmi archivorg',
        'familienkasse', 'bundesagentur für arbeit', 'kindergeld',
        'check24 punkteauszahlung', 'punkteauszahlung',
        'rueckerstattung', 'rückerstattung', 'erstattung'
    ],
    'Wohnen': [
        'miete', 'nebenkosten', 'hausgeld', 'vermieter',
        'grundsteuer', 'gebäudeversicherung', 'gebaeudeversicherung',
        'mario endrich'
    ],
    'Energie': [
        'stadtwerke', 'vattenfall', 'eprimo', 'montana erdgas',
        'naturwerke', 'naturstrom', 'abschlag strom', 'abschlag gas',
        'eon se', 'enbw', 'enercity', 'e.on', 'e-on'
    ],
    'Telekom & Internet': [
        'telekom deutschland', 'vodafone gmbh', 'vodafone kabel',
        'o2 telefonica', 'telefónica', '1&1', 'congstar', 'freenet',
        'aldi talk', 'lidl connect', 'winsim', 'drillisch', 'starlink'
    ],
    'Abos & Streaming': [
        'netflix', 'spotify', 'amazon prime', 'amznprime', 'disney',
        'paramount', 'apple.com', 'apple music', 'apple tv', 'dazn',
        'youtube premium', 'audible', 'hbo max', 'magenta tv', 'joyn',
        'google payment', 'google play'
    ],
    'Versicherung': [
        'versicherung', 'allianz', 'huk-coburg', 'huk coburg',
        'ergo versicherung', 'debeka', 'signal iduna', 'generali',
        'devk', 'württembergische', 'provinzial', 'haftpflicht',
        'kfz-versicherung', 'krankenversicherung', 'barmer',
        'hausrat', 'privathaftpflicht', 'adac autovers'
    ],
    'Bank & Gebühren': [
        'kontoführung', 'kontofuehrung', 'bankgebühr', 'kartengebühr',
        'dispozins', 'überziehung',
        'darlehensrate', 'commerzbank', 'tilgung',
        'bike.v', 'bik e.v', 'bik e. v', 'bike. v', 'bfs '
    ],
    'Steuern & Abgaben': [
        'finanzamt', 'lohnsteuer', 'einkommensteuer', 'umsatzsteuer',
        'gez', 'rundfunkbeitrag', 'landesjustizkasse', 'justizkasse'
    ],
    'Gesundheit': [
        'apotheke', 'arzt', 'praxis', 'klinik', 'zahnarzt', 'physio', 'optiker',
        'fielmann', 'apollo optik', 'sanicare', 'shop apotheke', 'medpex',
        'loewen-apotheke', 'ig bergbau', 'ig bce', 'industriegewerkschaft',
        'barbershop', 'barber', 'friseur', 'gentlemens'
    ],
    'Haushalt': [
        'ikea', 'hornbach', 'obi ', 'bauhaus', 'toom ', 'toom bm', 'hagebaumarkt',
        'poco ', 'roller', 'höffner', 'xxxlutz', 'möbel'
    ],
    'Lebensmittel': [
        'edeka', 'rewe', 'aldi', 'lidl', 'kaufland', 'penny',
        'netto marken', 'nettomarken',
        'dm-drogerie', 'dmdrogerie', 'dm drogerie', 'rossmann',
        'norma', 'tegut', 'bio company', 'supermarkt', 'mix markt', 'mixmarkt',
        'edk.', 'e center', 'ecenter', 'edeka heymer', 'edekaheymer'
    ],
    'Gastronomie': [
        'restaurant', 'café', 'cafe', 'bäckerei', 'baeckerei', 'baecker',
        'moebius', 'lieferando', 'wolt', 'mcdonalds', 'burger king', 'kfc',
        'subway', 'pizzeria', 'imbiss', 'bistro', 'starbucks', 'persepolis',
        'repo chemnitz', 'repochemnitz', 'repo 20'
    ],
    'Transport': [
        'db vertrieb', 'deutsche bahn', 'bvg ', 'mvg ', 'vgn ', 'hvv ', 'rmv ',
        'flixbus', 'flixtrain', 'tankstelle', 'aral', 'shell ', 'esso',
        'total energies', 'adac ', 'parkhaus', 'parking', 'bolt ',
        'freenow', 'taxi', 'sixt', 'europcar', 'carsharing', 'easypark',
        'chemnitzer verkehrs', 'cvag',
        'star chemnitz', 'starchemnitz'  # benzinărie STAR din Chemnitz
    ],
    'Kleidung': [
        'h&m', 'zara', 'c&a', 'c+a', 'primark', 'zalando', 'about you',
        'peek', 'deichmann', 'snipes', 's.oliver', 'tchibo', 'uniqlo'
    ],
    'Elektronik': [
        'mediamarkt', 'saturn', 'conrad', 'alternate', 'mindfactory',
        'cyberport', 'apple store', 'gravis', 'notebooksbilliger'
    ],
    'Online Shopping': [
        'amazon', 'amzn', 'ebay', 'otto ', 'otto payments', 'ottopayments',
        'klarna', 'aliexpress', 'temu', 'shein', 'mopla solutions',
        'kaufland.de', 'paypal', 'pay pal'
    ],
    'Freizeit': [
        'fitness', 'fitx', 'mcfit', 'urban sports', 'cinema',
        'kino', 'cinestar', 'cineplex', 'uci ', 'theater', 'museum',
        'konzert', 'ticketmaster', 'eventim'
    ],
    'Reisen': [
        'booking.com', 'airbnb', 'expedia', 'trivago', 'hrs', 'lufthansa',
        'ryanair', 'eurowings', 'easyjet', 'tuifly', 'hotel', 'hostel',
        'maritim', 'proarte'
    ],
    'Bildung': [
        'udemy', 'coursera', 'linkedin learning', 'skillshare', 'duolingo',
        'buchhandlung', 'thalia', 'hugendubel', 'f+u sachsen', 'anmeldegebühr'
    ],
    'Sparen & Investition': [
        'trade republic', 'scalable capital', 'comdirect', 'consorsbank',
        'ing-diba', 'etf', 'depot', 'sparplan'
    ],
    'Cash': [
        'bargeldauszahlung', 'geldautomat', 'bargeld'
    ],
    'Transfer': [
        'umbuchung', 'dauerauftrag', 'gesendet von revolut', 'revolut',
        'moneygram', 'trustly', 'roman liuba', 'roman raisa', 'raisa',
        'familie', 'regalo', 'notprovided'
    ],
}


def _normalize(text: str) -> str:
    """Text pentru matching: lowercase, spații normalizate."""
    t = text.lower()
    t = re.sub(r'\s+', ' ', t)
    return t


def _keyword_matches(keyword: str, text: str) -> bool:
    """
    Matchează keyword cu word-boundary inteligentă:
    - Keyword-uri cu spațiu la final: boundary strict (evităm "lohn" prinzând în "kalor")
    - Keyword-uri scurte (≤4 chars) doar litere: substring simplu DAR cu excepții
      pentru cuvinte comune germane care apar frecvent
    - Altfel: substring simplu
    """
    kw = keyword.lower()
    text = text.lower()
    
    # Keyword cu spațiu explicit la final → boundary
    if kw.endswith(' '):
        kw_clean = kw.rstrip()
        pattern = r'\b' + re.escape(kw_clean) + r'\b'
        return bool(re.search(pattern, text))
    
    # Keyword-uri PROBLEMATICE care trebuie cu word boundary (False positives cunoscute)
    # 'hem' prinde în 'chemnitz', 'rwe' în 'überweisung', 'bce' în 'bezdresde' etc.
    PROBLEMATIC_SHORT = {'hem', 'rwe', 'bce', 'aok', 'dak', 'bvg', 'mvg', 'vgn', 'hvv', 'rmv', 'obi', 'hrs', 'uci'}
    if kw in PROBLEMATIC_SHORT:
        pattern = r'\b' + re.escape(kw) + r'\b'
        return bool(re.search(pattern, text))
    
    # Substring simplu — prinde și cuvinte lipite precum "normasagtdanke", "dmdrogerie"
    return kw in text


def categorize_single(text: str, custom_rules: dict = None) -> str:
    """Returnează categoria pentru un text."""
    text_norm = _normalize(text)
    
    if custom_rules:
        for keyword, category in custom_rules.items():
            if _keyword_matches(keyword, text_norm):
                return category
    
    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if _keyword_matches(kw, text_norm):
                return category
    
    return 'Sonstiges'


def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplică categorizarea. Încearcă întâi pe merchant (curat),
    apoi fallback pe description.
    """
    custom_rules = get_rules()
    df = df.copy()
    
    def categorize_row(row):
        merchant = str(row.get('merchant', '') or '')
        if merchant:
            cat = categorize_single(merchant, custom_rules)
            if cat != 'Sonstiges':
                return cat
        desc = str(row.get('description', ''))
        return categorize_single(desc, custom_rules)
    
    df['category'] = df.apply(categorize_row, axis=1)
    return df


def update_rule(keyword: str, category: str):
    from db import upsert_rule
    upsert_rule(keyword, category)
