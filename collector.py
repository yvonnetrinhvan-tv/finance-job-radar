"""Finance Job Radar: conservative, no-key RSS discovery. Search results are leads, not verified live vacancies."""
import datetime as dt, json, os, re, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

BASE=Path(__file__).resolve().parent
DATA=BASE/'jobs.json'
QUERIES=[
 '"Finance Controller" "Ho Chi Minh" tuyển dụng',
 '"FP&A" "Ho Chi Minh" tuyển dụng',
 '"Finance Business Partner" "Ho Chi Minh" jobs',
 '"Senior Financial Analyst" "Ho Chi Minh" tuyển dụng',
 '"Financial Planning and Analysis" "Hồ Chí Minh"',
 '"Business Finance" "Hồ Chí Minh" tuyển dụng',
]
PREFERRED=['linkedin.com/jobs','vietnamworks.com','topcv.vn','careerbuilder.vn','careerviet.vn','glints.com','jobs.lever.co','greenhouse.io','workdayjobs.com','jobs.jobvite.com','smartrecruiters.com','recruiting.ultipro.com','jobs.ashbyhq.com','itviec.com','jobstreet.vn','vieclam24h.vn','indeed.com']
NEGATIVE=['internship','intern ','thực tập','fresher','new grad','graduate program','account payable','accounts payable','account receivable','accounts receivable','kế toán kho','kế toán công nợ','junior accountant','data entry']
SKILLS={'budgeting':['budget','ngân sách'],'forecasting':['forecast','dự báo'],'variance':['variance','chênh lệch'],'management_reporting':['management reporting','báo cáo quản trị'],'cost_control':['cost control','kiểm soát chi phí'],'working_capital':['working capital','vốn lưu động'],'internal_control':['internal control','kiểm soát nội bộ'],'capex':['capex','capital expenditure'],'business_partnering':['business partner','business partnering']}
ROLE_TERMS=['finance controller','financial controller','fp&a','financial planning','finance business partner','business finance','financial analyst','finance manager','kiểm soát tài chính','hoạch định tài chính']
LOC_TERMS=['ho chi minh','hồ chí minh','hcmc','hcm','sài gòn','saigon','tphcm','tp.hcm']
NOW=dt.datetime.now(dt.timezone.utc)

def clean(s): return re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',s or '')).strip()
def key(url):
 u=urllib.parse.urlparse(url); qs=urllib.parse.parse_qs(u.query)
 for k in ['url','u','target']:
  if k in qs and qs[k]: return key(qs[k][0])
 return (u.netloc.lower().removeprefix('www.')+u.path.rstrip('/')).lower()
def fetch(q):
 rss='https://www.bing.com/search?'+urllib.parse.urlencode({'q':q,'format':'rss','count':'25'})
 req=urllib.request.Request(rss,headers={'User-Agent':'Mozilla/5.0 FinanceJobRadar/1.0'})
 with urllib.request.urlopen(req,timeout=18) as resp: body=resp.read(2_000_000)
 root=ET.fromstring(body)
 for item in root.findall('./channel/item'):
  yield {'title':clean(item.findtext('title')),'url':clean(item.findtext('link')),'description':clean(item.findtext('description')),'source_published':clean(item.findtext('pubDate'))}

def score(job):
 txt=(job['title']+' '+job['description']).lower(); title=job['title'].lower()
 if any(n in title for n in NEGATIVE): return None
 if not any(r in txt for r in ROLE_TERMS): return None
 if not any(l in txt for l in LOC_TERMS): return None
 s=45
 if any(t in title for t in ['controller','fp&a','business partner','business finance']):s+=18
 if any(t in title for t in ['senior','lead','manager','trưởng']):s+=12
 found=[label for label,phrases in SKILLS.items() if any(p in txt for p in phrases)]
 s+=min(18,len(found)*3)
 if any(t in txt for t in ['manufacturing','fmcg','logistics','travel','tourism','retail','ecommerce','e-commerce']):s+=5
 if any(t in title for t in ['assistant','junior','staff','intern']):s-=28
 return max(0,min(100,s)), found

def main():
 old={key(j['url']):j for j in (json.loads(DATA.read_text(encoding='utf-8')).get('jobs',[]) if DATA.exists() else [])}
 found={}; errors=[]
 for q in QUERIES:
  try:
   for job in fetch(q):
    if not job['url'].startswith(('http://','https://')):continue
    sc=score(job)
    if sc is None:continue
    k=key(job['url']); domain=urllib.parse.urlparse(job['url']).netloc.lower()
    if k in found: continue
    prev=old.get(k,{})
    job.update(score=sc[0], matched_skills=sc[1],first_seen=prev.get('first_seen',NOW.date().isoformat()),last_seen=NOW.date().isoformat(),
               salary_status='Chưa xác minh',weekend_status='Chưa xác minh',work_mode='Chưa xác minh',opening_status='Chưa xác minh',
               source_type='Tin tìm thấy qua công cụ tìm kiếm',source_domain=domain, user_status=prev.get('user_status','Chưa xem'))
    found[k]=job
  except Exception as e:errors.append(f'{q}: {type(e).__name__}: {e}')
  time.sleep(1)
 # Keep past leads for 30 days; not seeing a listing today does not mean it closed.
 for k,job in old.items():
  if k not in found:
   try: days=(NOW.date()-dt.date.fromisoformat(job['last_seen'])).days
   except Exception: days=999
   if days<=30:found[k]=job
 jobs=sorted(found.values(),key=lambda x:(x['last_seen'],x['score']),reverse=True)[:500]
 result={'updated_at':NOW.isoformat(),'queries':QUERIES,'job_count':len(jobs),'errors':errors,'jobs':jobs}
 DATA.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Jobs:',len(jobs),'Errors:',errors)

if __name__=='__main__':main()
