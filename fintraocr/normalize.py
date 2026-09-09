import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache

@lru_cache(maxsize=1)
def country_inverted_names():
    """Unambiguous leading names from the installed ISO country registry.

    ISO sometimes stores an inverted name followed by its state qualifier.
    Derive aliases from that registry, never from evaluation answers or fuzzy
    matching. Shared leading names remain unresolved.
    """
    import pycountry
    candidates={};inverted=set()
    for country in pycountry.countries:
        leading=country.name.split(',',1)[0].strip().casefold()
        candidates.setdefault(leading,set()).add(country.alpha_2)
        if ',' in country.name:inverted.add(leading)
    return {name:next(iter(codes)) for name,codes in candidates.items() if name in inverted and len(codes)==1}

@lru_cache(maxsize=1)
def country_formal_name_order():
    """Restore registry 'Name, Republic of' to 'Republic of Name', exactly.

    Keep ambiguous aliases unresolved and do not repair OCR spellings.
    """
    import pycountry
    candidates={}
    for country in pycountry.countries:
        if ', ' not in country.name:continue
        name,qualifier=country.name.split(', ',1)
        if not qualifier.casefold().endswith(' of'):continue
        alias=(qualifier+' '+name).casefold()
        candidates.setdefault(alias,set()).add(country.alpha_2)
    return {name:next(iter(codes)) for name,codes in candidates.items() if len(codes)==1}

UNITS = {"pkg":"PKG", "pkgs":"PKG", "package":"PKG", "packages":"PKG", "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg", "킬로그램": "kg",
         "g": "g", "lb": "lb", "lbs": "lb", "mt": "t", "m/t": "t", "tonnes": "t",
         "pcs": "pcs", "pc": "pcs", "pieces": "pcs", "piece": "pcs", "ea": "ea", "개": "pcs", "sets":"set", "set":"set",
         "cft": "ft3", "cuft": "ft3", "cubic feet": "ft3", "drums": "drum", "drum": "drum",
         "ctn": "ctn", "ctns": "ctn", "cartons": "ctn", "carton": "ctn", "cbm": "m3", "m3": "m3", "m³": "m3"}
# UN name-change notices establish continuity of these country identities.
# https://turkiye.un.org/en/184798-turkeys-name-changed-t%C3%BCrkiye
# https://www.un.org/en/about-us/member-states/eswatini
# Exact historical names only, never OCR spelling repair or successor guessing.
HISTORICAL_COUNTRY_NAMES={'turkey':'TR','republic of turkey':'TR',
                          'swaziland':'SZ','kingdom of swaziland':'SZ'}

def normalize(raw, kind, date_order=None, decimal_separator=None):
    s = " ".join(unicodedata.normalize("NFKC", raw).split())
    if not s:
        return None, ["empty_value"]
    if kind in ("text", "party"):
        if not any(c.isalnum() for c in s):return None,['punctuation_only_value']
        return s, []
    if kind=='material':
        if not any(c.isalpha() for c in s):return None,['ambiguous_numeric_material_or_grade']
        return s,[]
    if kind=='incoterms':
        # Preserve historical ICC codes too; never silently convert their edition.
        if re.match(r'^(?:EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF|DAT|DAF|DES|DEQ|DDU)\b',s,re.I):return s,[]
        return None,['unrecognized_trade_delivery_term']
    if kind == "unit":
        return UNITS.get(s.casefold(), s), []
    if kind == 'country':
        import pycountry
        candidates=[s,re.sub(r'(?i)^the\s+','',s)]
        if ',' in s:candidates.append(s.rsplit(',',1)[1].strip())
        for candidate in candidates:
            try:return pycountry.countries.lookup(candidate).alpha_2,[]
            except LookupError:pass
            alias=country_inverted_names().get(candidate.casefold()) or country_formal_name_order().get(candidate.casefold()) or HISTORICAL_COUNTRY_NAMES.get(candidate.casefold())
            if alias:return alias,[]
        return None,['unrecognized_or_ambiguous_country']
    if kind == 'freight_terms':
        m=re.fullmatch(r'(?i)(?:freight\s+)?(prepaid|collect)',s)
        return (m.group(1).upper(),[]) if m else (None,['unrecognized_freight_terms'])
    if kind == "currency":
        import pycountry
        if re.fullmatch(r'(?i)US\s*\$',s):return 'USD',[]
        if re.fullmatch(r'\([A-Za-z]{3}\)',s):s=s[1:-1]
        if pycountry.currencies.get(alpha_3=s.upper()) is not None: return s.upper(), []
        symbols = {"€": "EUR", "US$": "USD", "₩": "KRW", "£": "GBP"}
        return (symbols[s], []) if s in symbols else (None, ["ambiguous_or_unsupported_currency"])
    if kind == "date":
        ordinal=re.search(r'(?i)\b(\d{1,2})(st|nd|rd|th)(?=\s+[A-Za-z])',s)
        if ordinal:
            day=int(ordinal.group(1))
            suffix='th' if 10<day%100<14 else {1:'st',2:'nd',3:'rd'}.get(day%10,'th')
            if ordinal.group(2).lower()!=suffix:return None,['invalid_day_ordinal']
            s=s[:ordinal.start()]+ordinal.group(1)+s[ordinal.end():]
        s=re.sub(r',(?=\d{4}\b)',', ',s)
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y년 %m월 %d일", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%d-%b-%Y"]
        formats += ["%b.%d.%Y", "%B.%d.%Y", "%d.%b.%Y", "%d.%B.%Y", "%b-%d-%Y", "%B-%d-%Y", "%b. %d, %Y", "%B. %d, %Y"]
        if date_order: formats += ["%d/%m/%Y", "%d-%m-%Y"] if date_order == "DMY" else ["%m/%d/%Y", "%m-%d-%Y"]
        for fmt in formats:
            try: return datetime.strptime(s, fmt).date().isoformat(), []
            except ValueError: pass
        if date_order is None and re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{4}",s):
            candidates=set()
            for fmt in ("%d/%m/%Y","%m/%d/%Y","%d-%m-%Y","%m-%d-%Y"):
                try:candidates.add(datetime.strptime(s,fmt).date().isoformat())
                except ValueError:pass
            if len(candidates)==1:return candidates.pop(),[]
        return None, ["ambiguous_or_invalid_date"]
    if kind == "number":
        s = re.sub(r"^[\$€£¥₩]\s*|\s*[\$€£¥₩]$", "", s)
        negative = s.startswith("(") and s.endswith(")")
        if negative: s = s[1:-1]
        if not re.fullmatch(r"[+-]?[0-9][0-9., ]*", s): return None, ["invalid_number_span"]
        if " " in s:
            if not re.fullmatch(r"[+-]?\d{1,3}(?: \d{3})+(?:[.,]\d+)?", s): return None, ["invalid_grouping"]
            s = s.replace(" ", "")
        if decimal_separator:
            dec = decimal_separator
        elif "," in s and "." in s:
            dec = "," if s.rfind(",") > s.rfind(".") else "."
        elif "," in s or "." in s:
            sep = "," if "," in s else "."
            if s.count(sep) == 1 and len(s.rsplit(sep, 1)[1]) == 3:
                return None, ["ambiguous_number_separator"]
            dec = sep if s.count(sep) == 1 else ("." if sep == "," else ",")
        else: dec = "."
        group = "," if dec == "." else "."
        parts = s.split(dec)
        if len(parts) > 2 or (len(parts) == 2 and not parts[1].isdigit()): return None, ["invalid_number"]
        integer = parts[0]
        if group in integer and not re.fullmatch(r"[+-]?\d{1,3}(?:" + re.escape(group) + r"\d{3})+", integer):
            return None, ["invalid_grouping"]
        canonical = integer.replace(group, "") + ("." + parts[1] if len(parts) == 2 else "")
        try:
            value = Decimal(canonical)
            if negative: value = -value
            return format(value, "f"), []
        except InvalidOperation: return None, ["invalid_number"]
    return None, ["unsupported_kind"]
