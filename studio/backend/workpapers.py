# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Evidence-linked working-paper drafts. Generation never changes audit decisions."""
import json,time,hashlib,threading
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from audit_research import topic_for,TOPICS,retrieve
from report_content import facts_for
from grounded_chat import describe,model
from logistics_writer import interpret
import enrichment
POOL=ThreadPoolExecutor(max_workers=1)
LOCK=threading.RLock()
ACTIVE=set()
VERSION=4

def read(p):
    with LOCK:return json.loads(p.read_text('utf-8'))
def write(p,obj):
    with LOCK:
        tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),'utf-8')
        for attempt in range(6):
            try:tmp.replace(p);break
            except PermissionError:
                if attempt==5:raise
                time.sleep(.05)
def fingerprint(result):return hashlib.sha256(json.dumps(result.get('audit'),sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def generate(result,settings,progress=lambda *args:None,ask=model,search=enrichment.request):
    from review_rules import normalized_audit,build,summary
    from comparison_scope import coverage
    audit=normalized_audit(result.get('audit') or {})
    if not audit.get('transactions'):raise ValueError('연결된 거래의 비교 결과가 필요합니다.')
    facts=facts_for(result);review=build(audit);counts=facts['counts'];framework=settings.get('framework')
    sections=[{'heading':'1. 검토 목적과 범위','text':f"업로드된 증빙 {facts['document_count']}개와 연결 거래 {len(facts['transactions'])}건을 대상으로 문서 간 일관성, 장부와 증빙의 대응 관계 및 회계적 추가 검토 사항을 검토한다. 대상은 제출된 자료로 한정한다. 전체 원장 모집단의 완전성, 외부조회, 재고실사 및 내부통제 운영 효과는 이 분석만으로 확인되지 않았다."},
      {'heading':'2. 업무 정보와 판단 전제','text':'적용 회계기준: '+(framework or '미지정 — 검색 원문은 K-IFRS 조건부 참고')+'\n대상 회사·감사 대상 기간: 담당자 확인 필요\n중요성 및 수행중요성: 미입력 — 중요왜곡 여부 판정 보류\n실제 계정 및 매출·매입 구분: 장부 분개와 계약으로 확인 필요\n작성: Fintra AI 초안 / 검토자·검토일: 검토 완료 시 기록'},
      {'heading':'3. 수행한 절차와 증거','text':'[자동 수행] 제출 문서의 문자와 항목을 추출·표준화하고, 연결된 거래별 비교 규칙으로 값·단위·참조번호를 대조했다. 저장된 검사 결과를 조서의 사실 근거로 사용한다. 사용자 수정값이 있는 항목은 원본과 수정 이력을 함께 검토해야 한다.\n[미수행] 원본의 진위 확인, 거래처 외부조회, 실물 재고 확인, 전체 분개 검증 및 후속 증빙 입수. 아래 제안 절차는 완료된 감사 절차가 아니다.'}]
    references={};gaps=[];groups=[];validations=[]
    for ti,tx in enumerate(audit['transactions']):
        buckets=defaultdict(list)
        for c in tx.get('checks',[]):
            if c['status'] in ('flag','review') or c['check_id'] in coverage(tx)['required_missing_ids']:buckets[topic_for(c)].append(c)
        for topic,checks in buckets.items():groups.append((ti,topic,checks))
    for gi,(ti,topic,checks) in enumerate(groups):
        progress(gi,len(groups),TOPICS[topic][0]+' 검토 작성')
        label=facts['transactions'][ti]['title'];code='WP-'+str(gi+1).zfill(2)
        refs=[{'id':c['check_id'],'kind':'check','title':c.get('title','검사'),'check':c} for c in checks]
        question=('재고자산 감모손실 비용 인식' if topic=='quantity' else TOPICS[topic][0])+'에 관한 거래별 감사 검토. 관찰 결과에 근거한 회계 영향 및 후속 절차를 작성하세요.'
        try:
            sources,trace=retrieve(question,checks,framework,search,ask,purpose="report")
            refs.extend(sources)
            text,used_refs,verdict=interpret(question,checks,refs,ask)
            validations.append({'workpaper':code,'retrieval':trace,'verdict':verdict})
            for ref in used_refs:references[ref['id']]=ref
            if not text:gaps.append(code+' 회계 해석 생성 실패')
            elif verdict.get('method')=='original_passages' or sources and verdict.get('method')=='evidence_only':
                gaps.append(code+' '+('기준 원문은 확보했으나 AI 해설 검증을 통과하지 못했습니다.' if verdict['method']=='original_passages' else '연결할 회계기준 원문을 확보하지 못했습니다.'))
        except Exception as exc:
            text='';gaps.append(code+' '+type(exc).__name__)
        observed='\n\n'.join(describe(c) for c in checks)
        for c in checks:
            units={str(e.get('normalized_value')) for e in c.get('evidence',[]) if e.get('field_name')=='unit' and e.get('normalized_value')}
            comparison_unit=c.get('context',{}).get('comparison_unit')
            if topic=='quantity' and comparison_unit and units and comparison_unit not in units:
                observed+='\n단위 검증 필요: 검사 결과 단위 '+comparison_unit+'와 추출된 단위 '+', '.join(sorted(units))+'가 다릅니다. 위 차이를 확정 수량으로 사용하지 말고 원본과 단위 매핑을 다시 확인하세요.'
        source_ids=' / '.join(c['check_id'] for c in checks)
        sections.append({'heading':f'4.{gi+1} {code} · {label} · {TOPICS[topic][0]}',
          'text':'확인된 사실\n'+observed+'\n\n회계적 검토와 제안 절차\n'+(text or '기준에 근거한 해석 초안을 완성하지 못했습니다. 이 항목은 검토 대기로 남겼습니다. 원인·수정 분개·최종 결론은 확정하지 않았습니다.')+'\n\n결론 상태: 추가 증빙과 담당자 검토 전까지 판단 보류.\n근거 식별자: '+source_ids})
    missing=[(t['title'],c) for t in facts['transactions'] for c in t['checks'] if c['status']=='cannot_evaluate' and c.get('coverage_scope')!='supplementary']
    supplemental=sum(c.get('coverage_scope')=='supplementary' for t in facts['transactions'] for c in t['checks'])
    missing_types=list(dict.fromkeys(c['title'] for _,c in missing))
    if supplemental:sections.append({'heading':'보조 항목의 비교 범위','text':f'필수 비교 범위와 별도로 보조 항목은 검토 대상 아님(N/A)으로 분류하고 핵심 검토 영역의 집계에서 제외했다. 보조 참조번호, 송장·포장명세서의 본선 적재일, 기재되지 않은 품목별 중량·포장 정보 등이다. 미비교를 일치로 바꾸지 않았으며 개별 증거와 원래 검사 결과는 부록에 유지한다.'})
    sections.append({'heading':'5. 증거의 한계와 추가 자료 요청','text':f"필수 누락값 {sum(len(t['missing_required']) for t in review['transactions'])}건. "+('미확인 항목: '+', '.join(missing_types)+'.' if missing else '필수 비교 범위의 누락 항목은 없으나 원본 진위 및 거래 실질 검토는 별도이다.')+'\n요청 자료: 계약·발주서, 확정 송장 및 정정 이력, 상세 원장과 분개, 거래일·출고일·인도일의 증빙, 차이 조정 명세. 항목별 실제 필요 자료를 검토자가 확정한다.\n회신 담당자·기한·수령 여부: 미지정 / 미수령. 미수령 자료를 입수 완료로 기록하지 않는다.'})
    sections.append({'heading':'6. 왜곡표시 평가와 후속 조치','text':'문서 불일치 금액은 확인된 왜곡표시 금액과 구분한다. 차이 원인과 올바른 측정 기준을 확인한 뒤 조정 필요 여부를 판단한다. 같은 차이를 중복 합산하거나 서로 다른 통화를 단순 합산하지 않는다. 중요성 기준·모집단·분개 영향이 확보되지 않아 중요왜곡 여부 및 수정 분개는 현재 미확정이다. 후속 확인 완료 시 WP별 결론과 담당자 검토 의견을 갱신한다.'})
    from standard_eligibility import report_references
    references={r['id']:r for r in report_references(list(references.values()),audit)}
    if not references:sections.append({'heading':'관련 회계기준','text':'직접 연결된 회계기준 없음. 현재 수행한 절차는 증빙 대조이며 회계 인식·측정 요건을 검증한 것으로 표시하지 않습니다.'})
    for i,ref in enumerate(references.values(),1):
        sections.append({'heading':f'7.{i} 후속 검토 참고 기준 · '+ref['title'],'text':ref['link_reason']+'\n'+ref['source'].get('framework','')+' / 조건: '+'; '.join(ref['required_conditions'])+'\n'+(ref.get('relevant_text') or ref['quote'])+'\n출처: '+ref['source']['source']['file']})
    facts['references']=[{'title':r['title'],'quote':r['quote'],'excerpt':r.get('relevant_text') or r['quote'],'source':r['source']['source'],'framework':r['source'].get('framework'),'source_type':r['source']['source_type'],'link_reason':r['link_reason'],'link_role':r['link_role'],'check_ids':r['check_ids']} for r in references.values()]
    progress(len(groups),len(groups),'초안 정리 완료')
    return {'title':'거래별 실증절차 검토조서','summary':summary(review),
      'sections':sections,'conclusion':'제출 자료의 비교 결과는 위와 같다. 발견 사항의 원인, 적용 기준의 요건 충족 및 추가 증빙을 확인하기 전에는 거래의 회계적 적정성을 확정할 수 없다. 담당자는 항목별 후속 절차 결과와 중요성 평가를 반영하여 결론을 수정하고 검토 완료를 기록한다.',
      'revision':0,'reviewed':False,'facts':facts,'generation':{'version':VERSION,'created_at':time.time(),'status':'partial' if gaps else 'complete','gaps':gaps,'input_hash':fingerprint(result),'framework':framework,'reference_count':len(references),'validations':validations}}

def state(folder):
    p=Path(folder)/'workpaper-task.json'
    result=read(p) if p.exists() else {'status':'idle'}
    if result['status']=='running' and str(Path(folder)) not in ACTIVE:result.update(status='failed',error='초안 작성이 중단되었습니다. 다시 작성해 주세요.')
    return result

def resume_preparation(jobs,root):
    """Resume interrupted automatic drafts only; never replace saved user work."""
    resumed=[]
    for job in jobs.values():
        folder=Path(root)/job['id'];task=folder/'workpaper-task.json'
        if job.get('status') not in {'complete','partial'} or (folder/'draft.json').exists() or not task.exists():continue
        try:
            if read(task).get('status')!='running':continue
            start(folder,job.get('settings',{}),0,'Fintra AI');resumed.append(job['id'])
        except (OSError,ValueError):continue
    return resumed

def start(folder,settings,revision,editor):
    folder=Path(folder)
    with LOCK:
        if str(folder) in ACTIVE:return state(folder)
        p=folder/'draft.json';saved=read(p) if p.exists() else {'revision':0}
        if saved['revision']!=revision:raise ValueError('보고서가 변경되었습니다. 다시 열어주세요.')
        ACTIVE.add(str(folder));write(folder/'workpaper-task.json',{'status':'running','completed':0,'total':0,'message':'근거와 기준을 준비하고 있어요'})
        POOL.submit(execute,folder,settings,revision,editor)
        return state(folder)

def execute(folder,settings,revision,editor):
    try:
        result=read(folder/'result.json')
        def progress(done,total,message):write(folder/'workpaper-task.json',{'status':'running','completed':done,'total':total,'message':message})
        from model_config import local_model
        policy_files=('workpapers.py','logistics_writer.py','audit_research.py','knowledge_answer.py','current_principles.py','claim_validation.py','review_rules.py','standard_eligibility.py')
        policy=hashlib.sha256(b''.join((Path(__file__).parent/name).read_bytes() for name in policy_files)).hexdigest()
        identity={'input':fingerprint(result),'framework':settings.get('framework'),'version':VERSION,'policy':policy,'model':local_model()}
        key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        cache=folder/('generated-workpaper-'+key+'.json')
        draft=None
        if cache.exists():
            candidate=read(cache)
            if time.time()-candidate.get('generation',{}).get('created_at',0)<86400 and candidate.get('generation',{}).get('status')=='complete':
                draft=candidate;progress(1,1,'같은 자료와 회계기준으로 검증된 초안을 불러오고 있어요')
        if draft is None:
            draft=generate(result,settings,progress)
            if draft.get('generation',{}).get('status')=='complete':write(cache,draft)

        with LOCK:
            p=folder/'draft.json';previous=read(p) if p.exists() else {'revision':0}
            if previous['revision']!=revision:raise ValueError('작성 중 보고서가 수정되어 AI 초안을 덮어쓰지 않았습니다. 다시 생성해 주세요.')
            if fingerprint(read(folder/'result.json'))!=draft['generation']['input_hash']:raise ValueError('분석 결과가 변경되었습니다. 다시 생성해 주세요.')
            if p.exists():write(folder/('draft-before-ai-'+str(time.time_ns())+'.json'),previous)
            draft.update(revision=revision+1,editor=editor)
            write(p,draft);write(folder/'workpaper-task.json',{'status':'complete','generation':draft['generation']})
    except Exception as exc:write(folder/'workpaper-task.json',{'status':'failed','error':str(exc)})
    finally:ACTIVE.discard(str(folder))
