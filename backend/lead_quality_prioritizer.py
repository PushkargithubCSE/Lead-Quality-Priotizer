"""
lead_quality_prioritizer.py

MVP Lead Quality Scorer & Enrichment Prioritizer

Purpose
-------
A lightweight, practical tool (single-file) to: 
 - Score scraped B2B leads using deterministic heuristics
 - Deduplicate simple duplicates
 - Prioritize which leads to enrich given a credit budget

Intended 5-hour scope
---------------------
This script is a production-ready prototype you can run locally or deploy as a microservice.
It focuses on deterministic rules (no ML) so it's explainable and fast to iterate on.

Features implemented
--------------------
- CSV in / CSV out (common fields supported)
- Per-lead scoring (0-100) with breakdown reasons
- Simple deduplication (email primary, fallback on name+domain)
- Prioritization function that selects top-N leads given a credit budget
- Optional MX check (requires `dnspython` and outbound DNS/network access)
- Clear extension points for third-party enrichment (Clearbit/Hunter/Cognism)

Dependencies
------------
- Python 3.8+
- (Optional) dnspython for MX checks: pip install dnspython
- (Optional) tldextract for robust domain parsing: pip install tldextract

Usage (examples)
-----------------
# Score + prioritize with 10 credits, write outputs
python lead_quality_prioritizer.py --input leads_input.csv --scored scored.csv --priority prioritized.csv --credits 10

# Score with MX checks (slower, network required)
python lead_quality_prioritizer.py --input leads_input.csv --scored scored.csv --priority prioritized.csv --credits 50 --mx-check

CSV input expected columns (case-insensitive):
- first_name, last_name, full_name
- email
- job_title
- company_name
- company_domain (or website)
- linkedin_url
- phone
- estimated_revenue (optional)

Output:
- scored.csv: all leads + score (0-100) + reasons (JSON string)
- prioritized.csv: top leads to enrich within credits budget

"""

import csv
import re
import argparse
import json
import math
from collections import defaultdict
from urllib.parse import urlparse

# Optional imports (used if installed)
try:
    import tldextract
except Exception:
    tldextract = None

try:
    import dns.resolver
except Exception:
    dns = None

# -----------------------------
# Configurable weights & lists
# -----------------------------
WEIGHTS = {
    'completeness': 0.30,
    'seniority': 0.30,
    'email_validity': 0.20,
    'domain_match': 0.10,
    'company_signal': 0.10
}

PERSONAL_EMAIL_DOMAINS = {
    'gmail.com','yahoo.com','hotmail.com','outlook.com','aol.com','icloud.com',
    'me.com','protonmail.com','ymail.com','gmx.com'
}

# Title keywords mapping to a simple seniority score 0..1
TITLE_KEYWORDS = {
    # executive
    r'\b(c[- ]?level|ceo|chief executive officer|coo|cfo|cto|chief technology officer|chief financial officer|founder|co-founder)\b': 1.0,
    r'\b(president|vp\b|vice president|vice-president|head of|head,|head )\b': 0.85,
    r'\b(director|senior director|sr director)\b': 0.7,
    r'\b(manager|senior manager|mgr)\b': 0.5,
    r'\b(lead|principal)\b': 0.6,
    r'\b(engineer|developer|analyst|specialist|associate)\b': 0.3,
}

# -----------------------------
# Utilities
# -----------------------------

def normalize(s):
    if s is None:
        return ''
    return re.sub(r'\s+', ' ', str(s).strip()).lower()


def extract_domain_from_email(email):
    if not email:
        return ''
    email = email.strip().lower()
    parts = email.split('@')
    if len(parts) != 2:
        return ''
    return parts[1]


def extract_domain_from_url(url):
    if not url:
        return ''
    url = url.strip()
    if not url:
        return ''
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'http://' + url
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ''
    except Exception:
        host = ''

    host = host.lower() if host else ''
    if tldextract:
        ext = tldextract.extract(host)
        if ext.registered_domain:
            return ext.registered_domain
    # fallback: try to return last two labels
    parts = host.split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return host


def email_syntax_valid(email):
    if not email:
        return False
    email = email.strip()
    # Simple but practical regex
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(pattern, email) is not None


def is_personal_email_domain(domain):
    if not domain:
        return False
    return domain.lower() in PERSONAL_EMAIL_DOMAINS


def mx_lookup(domain, timeout=3.0):
    """
    Returns True if MX records found. Requires dnspython and network/DNS resolution.
    If dns library not available, returns None (meaning 'unchecked').
    """
    if not dns:
        return None
    try:
        answers = dns.resolver.resolve(domain, 'MX', lifetime=timeout)
        return len(answers) > 0
    except Exception:
        return False

# -----------------------------
# Scoring components
# -----------------------------

def completeness_score(lead):
    # presence of email, phone, linkedin, domain/company
    score = 0.0
    score += 1.0 if lead.get('email') else 0.0
    score += 0.6 if lead.get('phone') else 0.0
    score += 0.6 if lead.get('linkedin_url') else 0.0
    score += 0.8 if (lead.get('company_domain') or lead.get('company_name')) else 0.0
    # max theoretical = 3.0, normalize to 0..1
    return min(score / 3.0, 1.0)


def seniority_score(job_title):
    if not job_title:
        return 0.0
    title = normalize(job_title)
    best = 0.0
    for pat, val in TITLE_KEYWORDS.items():
        if re.search(pat, title):
            best = max(best, val)
    return best  # 0..1


def domain_match_score(lead):
    # If email domain matches company domain -> good
    email = lead.get('email')
    cdom = lead.get('company_domain') or ''
    if not email or not cdom:
        return 0.0
    ed = extract_domain_from_email(email)
    cd = normalize(cdom)
    # extract registered domain
    ed_r = extract_domain_from_email(ed) if '@' in ed else ed
    if tldextract:
        e_ext = tldextract.extract(ed_r)
        e_reg = e_ext.registered_domain or ed_r
        c_ext = tldextract.extract(cd)
        c_reg = c_ext.registered_domain or cd
    else:
        e_reg = '.'.join(ed_r.split('.')[-2:]) if ed_r else ''
        c_reg = '.'.join(cd.split('.')[-2:]) if cd else ''

    if not e_reg or not c_reg:
        return 0.0
    return 1.0 if e_reg == c_reg else 0.0


def company_signal_score(lead):
    # Lightweight: reward non-personal email domain, and estimated_revenue if present
    score = 0.0
    email = lead.get('email')
    if email:
        d = extract_domain_from_email(email)
        if not is_personal_email_domain(d):
            score += 0.6
    # estimated revenue: map to 0..1 where higher revenue => higher score
    rev = lead.get('estimated_revenue')
    try:
        if rev is not None and rev != '':
            v = float(re.sub(r"[^0-9.]", '', str(rev)))
            # simple mapping: 0..1 for 0..10M (cap)
            v = min(v, 1e7)
            score += (v / 1e7) * 0.4
    except Exception:
        pass
    return min(score, 1.0)


def email_validity_score(lead, mx_check=None):
    # syntax, personal domain penalty, optional MX
    score = 0.0
    email = lead.get('email')
    if not email:
        return 0.0
    if email_syntax_valid(email):
        score += 0.6
    d = extract_domain_from_email(email)
    if d and not is_personal_email_domain(d):
        score += 0.3
    # MX check gives final 0.1 boost
    if mx_check is True:
        mx = mx_lookup(d)
        if mx:
            score += 0.1
    elif mx_check is None:
        # unchecked: no boost or penalty
        pass
    elif mx_check is False:
        # explicit disable
        pass
    return min(score, 1.0)


def compute_lead_score(lead, mx_check=None):
    # lead is dict; returns score (0-100) and breakdown dict
    c = completeness_score(lead)
    s = seniority_score(lead.get('job_title'))
    e = email_validity_score(lead, mx_check=mx_check)
    d = domain_match_score(lead)
    cs = company_signal_score(lead)

    # weighted sum
    raw = (
        WEIGHTS['completeness'] * c +
        WEIGHTS['seniority'] * s +
        WEIGHTS['email_validity'] * e +
        WEIGHTS['domain_match'] * d +
        WEIGHTS['company_signal'] * cs
    )
    score = int(round(raw * 100))
    breakdown = {
        'completeness': round(c, 3),
        'seniority': round(s, 3),
        'email_validity': round(e, 3),
        'domain_match': round(d, 3),
        'company_signal': round(cs, 3),
        'raw_weighted': round(raw, 4)
    }
    return score, breakdown

# -----------------------------
# Deduplication
# -----------------------------

def dedupe_leads(leads):
    # Simple dedupe: prefer richer lead when email duplicates
    by_email = {}
    no_email = []
    for L in leads:
        email = normalize(L.get('email') or '')
        if email:
            key = email
            if key not in by_email:
                by_email[key] = L
            else:
                # pick the record with more filled fields
                existing = by_email[key]
                if count_nonempty_fields(L) > count_nonempty_fields(existing):
                    by_email[key] = L
        else:
            no_email.append(L)
    # de-dupe no_email by name+company_domain
    by_name_dom = {}
    for L in no_email:
        name = normalize(L.get('full_name') or (L.get('first_name','') + ' ' + L.get('last_name','')))
        dom = normalize(L.get('company_domain') or '')
        key = (name, dom)
        if key not in by_name_dom:
            by_name_dom[key] = L
        else:
            existing = by_name_dom[key]
            if count_nonempty_fields(L) > count_nonempty_fields(existing):
                by_name_dom[key] = L
    result = list(by_email.values()) + list(by_name_dom.values())
    return result


def count_nonempty_fields(lead):
    c = 0
    for k, v in lead.items():
        if v not in (None, '', []):
            c += 1
    return c

# -----------------------------
# Prioritization
# -----------------------------

def prioritize(leads_scored, credits=10, cost_per_enrich=1):
    # leads_scored: list of dicts with 'score' key
    budget = credits
    per_cost = cost_per_enrich
    # sort desc by score
    sorted_leads = sorted(leads_scored, key=lambda x: x.get('score', 0), reverse=True)
    selected = []
    for lead in sorted_leads:
        if budget >= per_cost:
            selected.append(lead)
            budget -= per_cost
        else:
            break
    return selected

# -----------------------------
# CSV helpers
# -----------------------------

def read_csv_to_dicts(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [dict((k.strip(), (v.strip() if isinstance(v,str) else v)) for k, v in row.items()) for row in reader]
    # Normalize common column names
    for r in rows:
        # unify company_domain
        if 'website' in r and not r.get('company_domain'):
            r['company_domain'] = r.get('website')
        if 'full name' in r and not r.get('full_name'):
            r['full_name'] = r.get('full name')
    return rows


def write_dicts_to_csv(path, rows, fieldnames=None):
    if not rows:
        print('No rows to write to', path)
        return
    if fieldnames is None:
        # union of keys preserving order
        keys = []
        for r in rows:
            for k in r.keys():
                if k not in keys:
                    keys.append(k)
        fieldnames = keys
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            # ensure JSON-serializable values for dicts
            out = {}
            for k in fieldnames:
                v = r.get(k, '')
                if isinstance(v, (dict, list)):
                    out[k] = json.dumps(v, ensure_ascii=False)
                else:
                    out[k] = v
            writer.writerow(out)

# -----------------------------
# CLI / main
# -----------------------------

def process_file(input_csv, scored_csv, prioritized_csv, credits=10, cost_per_enrich=1, dedupe=True, mx_check=False):
    leads = read_csv_to_dicts(input_csv)
    print('Read', len(leads), 'rows')
    if dedupe:
        before = len(leads)
        leads = dedupe_leads(leads)
        print(f'Deduplicated: {before} -> {len(leads)}')

    scored = []
    for L in leads:
        # normalize fields we use
        lead = {k.lower(): v for k, v in L.items()}
        # ensure keys used by functions
        for k in ['email','job_title','company_domain','linkedin_url','phone','estimated_revenue','first_name','last_name','full_name']:
            if k not in lead:
                lead[k] = ''
        score, breakdown = compute_lead_score(lead, mx_check=mx_check)
        lead['score'] = score
        lead['score_breakdown'] = breakdown
        scored.append(lead)

    # Save scored
    write_dicts_to_csv(scored_csv, scored)
    print('Wrote scored leads to', scored_csv)

    # Prioritize
    prioritized = prioritize(scored, credits=credits, cost_per_enrich=cost_per_enrich)
    write_dicts_to_csv(prioritized_csv, prioritized)
    print('Wrote prioritized leads to', prioritized_csv)
    return scored, prioritized

def score_leads(df, mx_check=False):
    """
    Wrapper function for FastAPI backend.
    Input: pandas DataFrame of leads
    Output: list of dicts with 'score' and 'score_breakdown' added
    """
    leads = df.to_dict(orient='records')
    scored = []
    for L in leads:
        # normalize fields we use
        lead = {k.lower(): v for k, v in L.items()}
        for k in ['email','job_title','company_domain','linkedin_url','phone','estimated_revenue','first_name','last_name','full_name']:
            if k not in lead:
                lead[k] = ''
        score, breakdown = compute_lead_score(lead, mx_check=mx_check)
        lead['score'] = score
        lead['score_breakdown'] = breakdown
        scored.append(lead)
    return scored






if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Lead Quality Scorer & Prioritizer')
    parser.add_argument('--input', required=True, help='Input CSV path')
    parser.add_argument('--scored', required=True, help='Output scored CSV path')
    parser.add_argument('--priority', required=True, help='Output prioritized CSV path')
    parser.add_argument('--credits', type=int, default=10, help='Enrichment credits available')
    parser.add_argument('--cost-per-enrich', type=int, default=1, help='Credits cost per lead')
    parser.add_argument('--no-dedupe', action='store_true', help='Disable deduplication')
    parser.add_argument('--mx-check', action='store_true', help='Attempt MX checks (requires dnspython and network)')

    args = parser.parse_args()
    process_file(args.input, args.scored, args.priority, credits=args.credits, cost_per_enrich=args.cost_per_enrich, dedupe=not args.no_dedupe, mx_check=args.mx_check)

