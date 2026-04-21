"""
Parser pentru extrase Deutsche Bank (Kontoauszug PDF).

Format real observat:
- Datele sunt pe 2 linii (zi+lună pe prima, an pe a doua)
- Suma apare pe prima linie a tranzacției, după tipul tranzacției
- Descrierea se întinde pe mai multe linii (nume, IBAN, Verwendungszweck, etc.)

Exemplu:
  02.03. 01.03. SEPA Echtzeitüberweisung von + 100,00
  2026   2026   ROMAN RAISA
                Verwendungszweck/ Kundenreferenz
                regalo
"""
import re
import pdfplumber


# Pattern pentru prima linie: "DD.MM. DD.MM. [text] [+/-]X,XX"
# Textul între date și sumă poate conține spații variate
TX_START_RE = re.compile(
    r'^(\d{2}\.\d{2}\.)\s+(\d{2}\.\d{2}\.)\s+(.+?)\s+([+\-]\s?[\d\.]+,\d{2})\s*$'
)

# Linia cu ani: "2026 2026" + posibil continuare descriere
YEAR_LINE_RE = re.compile(r'^(\d{4})\s+(\d{4})(?:\s+(.*))?$')

# Linii de header/footer/boilerplate de sărit
SKIP_PATTERNS = [
    r'^DeutscheBankAG', r'^Deutsche\s+Bank\s+AG',
    r'^Filiale\s*$', r'^Chemnitz\s*$',
    r'^Falkeplatz', r'^Herrn\b', r'^IgorRoman', r'^Igor\s+Roman\s*$',
    r'^Selbständige', r'^Erkerweg', r'^09\d{3}',
    r'^Telefon', r'^24h-Kundenservice',
    r'^\d+\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)',
    r'^Kontoauszugvom', r'^Kontoauszug\s+vom',
    r'^Kontoinhaber',
    r'^Auszug\s+Seite', r'^Auszug\s+Seite\s+von\s+IBAN',
    r'^\d+\s+\d+\s+\d+\s+DE\d',
    r'^Buchung\s+Valuta',
    r'^\d{10,}$',
    r'^\d+/\d+/\d+$',
    r'^Wichtige\s*Hinweise',
    r'^Bitte\s+erheben', r'^Die\s+abgerechneten',
    r'^Guthaben\s+sind', r'^Somit\s+k',
    r'^\d+\)\s+Der\s+Begriff',
    r'^\s*Kontonummer\s*$', r'^\s*Filialnummer\s*$',
    r'^\s*BIC\s*\(SWIFT\)\s*$',
    r'^\s*Ihre\s+eingeräumte',
    r'^\s*Sollzinssatz',
    r'^\s*Neuer\s+Saldo',
    r'^\s*EUR\s+-?[\d\.]+,\d{2}\s*$',
    r'^\s*DEUTDEDB',
    r'^Saldo\s+der\s+Abschlussposten',
    r'^\s*Alter\s+Saldo',
]
SKIP_RE = re.compile('|'.join(SKIP_PATTERNS), re.IGNORECASE)


def parse_german_amount(s: str) -> float:
    """'+ 100,00' -> 100.0 | '-1.234,56' -> -1234.56"""
    s = s.strip().replace(' ', '')
    sign = 1
    if s.startswith('-'):
        sign = -1
        s = s[1:]
    elif s.startswith('+'):
        s = s[1:]
    s = s.replace('.', '').replace(',', '.')
    try:
        return sign * float(s)
    except ValueError:
        return 0.0


def build_date(day_month: str, year: str) -> str:
    """'02.03.' + '2026' -> '2026-03-02'"""
    try:
        parts = day_month.rstrip('.').split('.')
        d, m = parts[0], parts[1]
        return f"{year}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return None


def add_word_spaces(text: str) -> str:
    """pdfplumber lipește uneori cuvinte. Adaugă spații la tranziții evidente."""
    # Lowercase -> Uppercase: "vonROMAN" -> "von ROMAN"
    text = re.sub(r'([a-zäöüß])([A-ZÄÖÜ])', r'\1 \2', text)
    # Literă -> cifră: "Rate22" -> "Rate 22"
    text = re.sub(r'([a-zA-ZäöüÄÖÜß])(\d)', r'\1 \2', text)
    # Cifră -> literă: "2026ROMAN" -> "2026 ROMAN"
    text = re.sub(r'(\d)([A-ZÄÖÜa-zäöü])', r'\1 \2', text)
    # Punctuație lipită: ".GmbH" -> ". GmbH"
    text = re.sub(r'([a-z])\.([A-Z])', r'\1. \2', text)
    return text


def extract_merchant(description: str, vorgang: str) -> str:
    """
    Extrage numele comerciantului/contrapartidei pentru afișare.
    Mai curat decât descrierea completă.
    """
    desc = description
    
    # Pentru Kartenzahlung: merchant e între 'Kundenreferenz' și '//'
    # ex: "Kartenzahlung MIXMARKT 172 OHG//CHEMNITZ/DE 26-02-2026..."
    if 'Kartenzahlung' in vorgang or 'Karten' in vorgang:
        m = re.search(r'(?:Kundenreferenz\s+)?([^/]+?)//[^/]*/', desc)
        if m:
            return m.group(1).strip()
        # fallback: primul grup de cuvinte după Kundenreferenz
        m = re.search(r'Kundenreferenz\s+(.+?)(?:\s+\d{2}-|\s+T\d{2}:|$)', desc)
        if m:
            return m.group(1).strip()[:60]
    
    # Pentru SEPA: contrapartida e după tipul tranzacției (linia 2 din PDF)
    # ex: "SEPAEchtzeitüberweisungvon ROMAN RAISA regalo"
    # Eliminăm prefixul SEPA...von/an
    cleaned = re.sub(r'^SEPA\s*(?:Echtzeit)?(?:Überweisung|Lastschrifteinzug)\s*(?:von|an)?\s*', '', desc, flags=re.IGNORECASE)
    # Ia primele 4-6 cuvinte (de obicei e numele)
    words = cleaned.split()
    if words:
        # Ia până primul semn că începe contextul (IBAN, cifre lungi, etc.)
        merchant_words = []
        for w in words[:8]:
            if re.match(r'^(IBAN|BIC|Verwendungszweck|Gläubiger|Mand|ABWA|ABWE|RCUR|SALA|\d{5,})', w):
                break
            merchant_words.append(w)
        if merchant_words:
            return ' '.join(merchant_words)[:60]
    
    return desc[:60]


def clean_description(desc: str) -> str:
    """Îndepărtează zgomotul din descriere și adaugă spații între cuvinte."""
    desc = add_word_spaces(desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    desc = re.sub(r'Verwendungszweck\s*/\s*Kundenreferenz', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'Kartennr\.\s*\d+', '', desc)
    desc = re.sub(r'Folgenr\.\s*\d+\s*Verfalld\.\s*\d+', '', desc)
    desc = re.sub(r'Gläubiger-ID\s+\S+', '', desc)
    desc = re.sub(r'Mand-ID\s+\S+', '', desc)
    desc = re.sub(r'IBAN\s+[A-Z]{2}\d{2}[A-Z0-9]+', '', desc)
    desc = re.sub(r'BIC\s+[A-Z]{4,}', '', desc)
    desc = re.sub(r'ABWA\s+\S+', '', desc)
    desc = re.sub(r'ABWE\s+\S+', '', desc)
    desc = re.sub(r'RCUR\s+Wiederholungslastschrift', '', desc)
    desc = re.sub(r'RCUR\b', '', desc)
    desc = re.sub(r'SALA\s+Lohn/Gehalt', '(Lohn/Gehalt)', desc)
    desc = re.sub(r'CGDD\s+SEPA\s+Lastschrift\s+ELV', '', desc)
    desc = re.sub(r'OTHR\s+Sonst\.\s*Transakt\.?', '', desc)
    desc = re.sub(r'\d{2}-\d{2}-\d{4}T\d{2}:\d{2}:\d{2}', '', desc)
    desc = re.sub(r'T\d{2}:\d{2}:\d{2}', '', desc)
    desc = re.sub(r'\b\d{15,}\b', '', desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc[:250]


def should_skip_line(line: str) -> bool:
    """True dacă linia e header/footer/boilerplate."""
    if not line.strip():
        return True
    if SKIP_RE.search(line):
        return True
    return False


def parse_db_pdf(pdf_path: str) -> list[dict]:
    """Parsează PDF Deutsche Bank și returnează lista de tranzacții."""
    all_lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split('\n'):
                all_lines.append(line)
    
    transactions = []
    i = 0
    n = len(all_lines)
    
    while i < n:
        line = all_lines[i]
        
        m = TX_START_RE.match(line.strip())
        if not m:
            i += 1
            continue
        
        buchung_date, valuta_date, vorgang_text, amount_str = m.groups()
        
        # Pe linia următoare așteptăm anii
        year = None
        merchant_line = ""
        if i + 1 < n:
            next_line = all_lines[i + 1].strip()
            ym = YEAR_LINE_RE.match(next_line)
            if ym:
                year = ym.group(1)
                if ym.group(3):
                    merchant_line = ym.group(3).strip()
            else:
                # Fallback: un singur an
                ym2 = re.match(r'^(\d{4})\s*(.*)$', next_line)
                if ym2:
                    year = ym2.group(1)
                    merchant_line = ym2.group(2).strip()
        
        if not year:
            i += 1
            continue
        
        date_iso = build_date(buchung_date, year)
        amount = parse_german_amount(amount_str)
        
        if not date_iso or amount == 0:
            i += 1
            continue
        
        # Acumulează descrierea
        description_parts = [vorgang_text.strip()]
        if merchant_line:
            description_parts.append(merchant_line)
        
        j = i + 2
        while j < n:
            next_line = all_lines[j]
            
            if TX_START_RE.match(next_line.strip()):
                break
            if 'Saldo der Abschlussposten' in next_line or re.search(r'Neuer\s+Saldo', next_line):
                break
            
            if should_skip_line(next_line):
                j += 1
                continue
            
            if re.match(r'^\s*Verwendungszweck', next_line):
                j += 1
                continue
            
            description_parts.append(next_line.strip())
            j += 1
            
            # Safety: nu permite descrieri prea lungi (peste 15 linii = parsing greșit)
            if j - i > 20:
                break
        
        description = clean_description(' '.join(description_parts))
        merchant = extract_merchant(description, vorgang_text)
        
        transactions.append({
            'date': date_iso,
            'description': description,
            'merchant': merchant,
            'amount': amount,
            'raw_text': f"{buchung_date}/{year} | {amount_str}"
        })
        
        i = j if j > i + 2 else i + 2
    
    # Dedup și filtrare finală
    filtered = []
    seen = set()
    for tx in transactions:
        key = (tx['date'], round(tx['amount'], 2), tx['description'][:100])
        if key in seen:
            continue
        seen.add(key)
        
        if len(tx['description']) < 3:
            continue
        
        desc_lower = tx['description'].lower()
        if any(skip in desc_lower for skip in ['alter saldo', 'neuer saldo', 'abschlussposten']):
            continue
        
        filtered.append(tx)
    
    return filtered


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        txs = parse_db_pdf(sys.argv[1])
        print(f"Găsite {len(txs)} tranzacții:\n")
        total_in = sum(t['amount'] for t in txs if t['amount'] > 0)
        total_out = sum(t['amount'] for t in txs if t['amount'] < 0)
        print(f"Total Einnahmen: +{total_in:,.2f} €")
        print(f"Total Ausgaben: {total_out:,.2f} €")
        print(f"Saldo net: {total_in + total_out:,.2f} €\n")
        for t in txs:
            sign = "+" if t['amount'] > 0 else " "
            print(f"  {t['date']} | {sign}{t['amount']:>10.2f} € | {t['merchant'][:40]:40} | {t['description'][:60]}")
