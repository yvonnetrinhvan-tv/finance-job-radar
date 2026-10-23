"""Yvonne Finance Job Radar: public search leads, not verified open jobs.
No API key. The search source may return zero leads; diagnostics explain why.
"""
import datetime as dt
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / 'jobs.json'
NOW = dt.datetime.now(dt.timezone.utc)

# Target job-posting pages rather than broad finance knowledge searches.
SEARCHES = [
    'site:careerviet.vn/viec-lam/ "finance controller"',
    'site:careerviet.vn/viec-lam/ "FP&A"',
    'site:topcv.vn/viec-lam/ "financial controller"',
    'site:topcv.vn/viec-lam/ "finance manager"',
    'site:vn.indeed.com/viewjob "finance controller"',
    'site:linkedin.com/jobs/view/ "finance business partner" Vietnam',
    'site:linkedin.com/jobs/view/ "FP&A" Vietnam',
    'site:jobs.lever.co/ "finance" "Vietnam"',
    'site:job-boards.greenhouse.io/ "finance" "Vietnam"',
    '"senior financial analyst" "Ho Chi Minh" jobs',
    '"Finance Controller" "Ho Chi Minh" jobs',
    '"FP&A Manager" "Ho Chi Minh" jobs',
]

# Strict enough to reject magazines, wikis, company homepages and search pages.
JOB_HOST_PATHS = {
    'careerviet.vn': ('/viec-lam/',),
    'topcv.vn': ('/viec-lam/',),
    'vietnamworks.com': ('/job/', '/viec-lam/',),
    'linkedin.com': ('/jobs/view/',),
    'vn.indeed.com': ('/viewjob', '/rc/clk',),
    'indeed.com': ('/viewjob', '/rc/clk',),
    'jobs.lever.co': ('/',),
    'job-boards.greenhouse.io': ('/',),
    'boards.greenhouse.io': ('/',),
    'jobs.ashbyhq.com': ('/',),
    'jobs.smartrecruiters.com': ('/',),
    'glints.com': ('/vn/opportunities/jobs/',),
}
ROLE_PATTERNS = [
    r'finance\s+controller', r'financial\s+controller', r'\bfp\s*&\s*a\b',
    r'financial\s+planning', r'finance\s+business\s+partner',
    r'business\s+finance', r'financial\s+analyst', r'finance\s+manager',
    r'kiểm soát tài chính', r'phân tích tài chính', r'hoạch định tài chính',
]
EXCLUDE_TITLE = [
    'intern', 'internship', 'fresher', 'new grad', 'graduate program',
    'junior accountant', 'accounts payable', 'accounts receivable',
    'kế toán kho', 'kế toán công nợ', 'data entry',
]
SKILLS = {
    'budgeting': ['budget', 'ngân sách'],
    'forecasting': ['forecast', 'dự báo'],
    'variance': ['variance', 'chênh lệch'],
    'management_reporting': ['management reporting', 'báo cáo quản trị'],
    'cost_control': ['cost control', 'kiểm soát chi phí'],
    'working_capital': ['working capital', 'vốn lưu động'],
    'internal_control': ['internal control', 'kiểm soát nội bộ'],
    'capex': ['capex', 'capital expenditure'],
    'business_partnering': ['business partner', 'business partnering'],
}
LOCATIONS = ['ho chi minh', 'hồ chí minh', 'hcmc', 'tp.hcm', 'tphcm', 'saigon', 'sài gòn']


def clean(value):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', html.unescape(value or ''))).strip()


def canonical(url):
    p = urllib.parse.urlparse(url)
    host = p.netloc.lower().removeprefix('www.')
    return f'{host}{p.path.rstrip("/")}'.lower()


def valid_job_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    host = parsed.hostname.lower().removeprefix('www.') if parsed.hostname else ''
    path = parsed.path.lower()
    return any((host == domain or host.endswith('.' + domain)) and
               any(path.startswith(prefix) for prefix in prefixes) and
               path.strip('/') for domain, prefixes in JOB_HOST_PATHS.items())


def fetch(query):
    url = 'https://www.bing.com/search?' + urllib.parse.urlencode(
        {'q': query, 'format': 'rss', 'count': 50})
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as response:
        body = response.read(2_000_000)
    root = ET.fromstring(body)
    return [{
        'title': clean(item.findtext('title')),
        'url': clean(item.findtext('link')),
        'description': clean(item.findtext('description')),
        'source_published': clean(item.findtext('pubDate')),
    } for item in root.findall('./channel/item')]


def score(job):
    title, text = job['title'].lower(), (job['title'] + ' ' + job['description']).lower()
    if any(x in title for x in EXCLUDE_TITLE):
        return None
    # Role must be in title (not just a mention deep inside an article).
    if not any(re.search(pattern, title) for pattern in ROLE_PATTERNS):
        return None
    matched = [name for name, terms in SKILLS.items() if any(term in text for term in terms)]
    result = 45
    if any(word in title for word in ('controller', 'fp&a', 'business partner', 'business finance')):
        result += 18
    if any(word in title for word in ('senior', 'lead', 'manager', 'trưởng')):
        result += 12
    result += min(len(matched) * 3, 18)
    if any(loc in text for loc in LOCATIONS):
        result += 5
    if any(word in title for word in ('assistant', 'junior', 'staff')):
        result -= 20
    return max(0, min(result, 100)), matched


def main():
    try:
        previous = json.loads(DATA.read_text(encoding='utf-8')).get('jobs', []) if DATA.exists() else []
    except (ValueError, OSError):
        previous = []
    # Drop any stale false positives from the old collector (such as Britannica).
    old = {canonical(j['url']): j for j in previous
           if j.get('url') and valid_job_url(j['url']) and score(j) is not None}
    seen, errors = {}, []
    counts = {'rss_results': 0, 'rejected_url': 0, 'rejected_role': 0, 'accepted': 0}
    rejected_url_samples = []
    source_hosts = {}
    for query in SEARCHES:
        try:
            results = fetch(query)
            counts['rss_results'] += len(results)
            for job in results:
                host = urllib.parse.urlparse(job['url']).hostname or '(no host)'
                source_hosts[host] = source_hosts.get(host, 0) + 1
                if not valid_job_url(job['url']):
                    counts['rejected_url'] += 1
                    if len(rejected_url_samples) < 15:
                        rejected_url_samples.append({'title': job['title'][:120], 'url': job['url'][:500]})
                    continue
                match = score(job)
                if match is None:
                    counts['rejected_role'] += 1
                    continue
                uid = canonical(job['url'])
                if uid in seen:
                    continue
                prev = old.get(uid, {})
                job.update(
                    score=match[0], matched_skills=match[1],
                    first_seen=prev.get('first_seen', NOW.date().isoformat()),
                    last_seen=NOW.date().isoformat(),
                    salary_status='Chưa xác minh', weekend_status='Chưa xác minh',
                    work_mode='Chưa xác minh', opening_status='Chưa xác minh',
                    location_status=('Có dấu hiệu TP.HCM' if any(loc in
                                     (job['title'] + ' ' + job['description']).lower()
                                     for loc in LOCATIONS) else 'Chưa xác minh'),
                    source_type='Tin tìm thấy qua công cụ tìm kiếm; chưa xác minh',
                    source_domain=urllib.parse.urlparse(job['url']).hostname or '',
                    user_status=prev.get('user_status', 'Chưa xem'),
                )
                seen[uid] = job
                counts['accepted'] += 1
        except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError) as exc:
            errors.append(f'{query}: {type(exc).__name__}: {exc}')
        time.sleep(0.5)
    # Keep previously detected valid leads for up to 30 days, without treating them as active vacancies.
    for uid, job in old.items():
        try:
            days = (NOW.date() - dt.date.fromisoformat(job['last_seen'])).days
        except (KeyError, ValueError):
            continue
        if uid not in seen and days <= 30:
            seen[uid] = job
    jobs = sorted(seen.values(), key=lambda j: (j.get('last_seen', ''), j.get('score', 0)), reverse=True)[:500]
    output = {'updated_at': NOW.isoformat(), 'queries': SEARCHES,
              'job_count': len(jobs), 'diagnostics': counts,
              'source_hosts': source_hosts, 'rejected_url_samples': rejected_url_samples,
              'errors': errors, 'jobs': jobs}
    DATA.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Job leads:', len(jobs), '| Diagnostics:', counts, '| Errors:', errors)


if __name__ == '__main__':
    main()
