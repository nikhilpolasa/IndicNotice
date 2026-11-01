"""Run the checked-in multilingual QA matrix through authenticated Chrome UI."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
from scripts.acceptance_qa_capture import CASES
from browser_personalized_notices import CDP,page_for,login
from demo.product import initial_analysis
from demo.questions import answer_notice
from demo.i18n import tr

BASE=os.environ.get('INDICNOTICE_AUDIT_ORIGIN','http://127.0.0.1:8531')
PORT=int(os.environ.get('INDICNOTICE_CDP_PORT','9224'))
ADMIN=os.environ['INDICNOTICE_AUDIT_ADMIN']
PASSWORD=os.environ['INDICNOTICE_AUDIT_PASSWORD']

LANG_LABEL={'en':'English','te':'తెలుగు','hi':'हिन्दी'}
ASK_LABEL={'en':'Ask this notice','te':'ఈ నోటీసును అడగండి','hi':'इस सूचना से पूछें'}
QUESTION_LABEL={'en':'Your question','te':'మీ ప్రశ్న','hi':'आपका प्रश्न'}
READ_LABEL={'en':'Read a notice','te':'నోటీసు చదవండి','hi':'सूचना पढ़ें'}

def select_radio(page: CDP, label: str):
    q=json.dumps(label,ensure_ascii=False)
    page.wait("document.querySelectorAll('input[type=radio]').length>=4")
    page.js(f"[...document.querySelectorAll('label[data-testid=stRadioOption]')].find(e=>e.innerText.trim()==={q}).click()")
    page.wait(f"[...document.querySelectorAll('label[data-testid=stRadioOption]')].some(e=>e.innerText.trim()==={q} && e.getAttribute('data-selected')==='true')")

def language(page: CDP, label: str, lang: str):
    q=json.dumps(label,ensure_ascii=False)
    page.js("document.querySelector('[data-testid=stExpandSidebarButton]')?.click()")
    page.js("document.querySelector('[role=combobox]').parentElement.querySelector('button').click()")
    page.wait(f"[...document.querySelectorAll('[role=option]')].some(e=>e.innerText.trim()==={q})")
    page.js(f"[...document.querySelectorAll('[role=option]')].find(e=>e.innerText.trim()==={q}).click()")
    nav=json.dumps(READ_LABEL[lang],ensure_ascii=False)
    page.wait(f"[...document.querySelectorAll('label[data-testid=stRadioOption]')].some(e=>e.innerText.trim()==={nav})")

def upload(page: CDP,path: Path,lang: str):
    page.wait("!!document.querySelector('input[type=file]')")
    root=page.call('DOM.getDocument',{'depth':-1})['root']['nodeId']
    node=page.call('DOM.querySelector',{'nodeId':root,'selector':'input[type=file]'}).get('nodeId')
    if not node: raise AssertionError('Reader upload input not found')
    page.call('DOM.setFileInputFiles',{'nodeId':node,'files':[str(path.resolve())]})
    analyze=tr('analyze',lang)
    page.wait(f"[...document.querySelectorAll('button')].some(b=>b.innerText.trim()==={json.dumps(analyze,ensure_ascii=False)}&&!b.disabled)")
    page.click_text(analyze)
    page.wait(f"document.body.innerText.includes({json.dumps(tr('initial',lang),ensure_ascii=False)})",60)

def ask(page: CDP,question: str,lang: str):
    q=json.dumps(question,ensure_ascii=False)
    label=json.dumps(QUESTION_LABEL[lang],ensure_ascii=False)
    page.wait(f"[...document.querySelectorAll('input[aria-label]')].some(e=>e.getAttribute('aria-label')==={label})")
    point=page.js(f"(()=>{{const e=[...document.querySelectorAll('input[aria-label]')].find(x=>x.getAttribute('aria-label')==={label});const form=e?.closest('[data-testid=stForm]');const button=form?.querySelector('button[kind=\\\"secondaryFormSubmit\\\"],button[kind=\\\"primaryFormSubmit\\\"]');if(!e||!button)throw new Error('Question form not found');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,{q});e.dispatchEvent(new Event('input',{{bubbles:true}}));e.dispatchEvent(new Event('change',{{bubbles:true}}));button.scrollIntoView({{block:'center'}});const r=button.getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})()")
    page.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':point['x'],'y':point['y']})
    page.call('Input.dispatchMouseEvent',{'type':'mousePressed','x':point['x'],'y':point['y'],'button':'left','clickCount':1})
    page.call('Input.dispatchMouseEvent',{'type':'mouseReleased','x':point['x'],'y':point['y'],'button':'left','clickCount':1})

def main():
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    browser=CDP(json.load(urlopen(f'http://127.0.0.1:{PORT}/json/version'))['webSocketDebuggerUrl'])
    context=browser.call('Target.createBrowserContext')['browserContextId']
    page=page_for(browser,context)
    try:
        login(page,ADMIN,PASSWORD)
        page.navigate(BASE+'/')
        page.wait("document.querySelectorAll('input[type=radio]').length>=4 && !!document.querySelector('input[type=file]')")
        language(page,LANG_LABEL['en'],'en')
        page.wait("[...document.querySelectorAll('label[data-testid=stRadioOption]')].some(e=>e.innerText.trim()==='Read a notice')")
        records=[]; analyses={}
        for name,case in CASES.items():
            path=ROOT/case['path']
            language(page,LANG_LABEL['en'],'en')
            if name!='hindi_scert':
                page.click_text('Clear notice and profile')
                page.wait("!document.body.innerText.includes('Initial analysis')")
            select_radio(page,'Read a notice')
            upload(page,path,'en')
            result=initial_analysis(path.read_bytes(),path.name)
            analyses[name]=result
            for lang,questions in case['questions'].items():
                language(page,LANG_LABEL[lang],lang)
                select_radio(page,ASK_LABEL[lang])
                for question_index,(kind,question) in enumerate(questions):
                    # Browser acceptance checks one deadline submission per
                    # language and fixture. The full intents matrix is captured
                    # separately through the same real analysis/QA services.
                    if kind!='deadline':
                        continue
                    expected=answer_notice(question,result,language=lang)
                    ask(page,question,lang)
                    try:
                        page.wait(f"document.body.innerText.includes({json.dumps(expected.answer_text.splitlines()[0],ensure_ascii=False)})",20)
                    except AssertionError as exc:
                        current=page.text()
                        label=json.dumps(QUESTION_LABEL[lang],ensure_ascii=False)
                        actual_input=page.js(f"[...document.querySelectorAll('input[aria-label]')].find(e=>e.getAttribute('aria-label')==={label})?.value")
                        (ROOT/'.tmp'/'v2c-qa-mismatch.json').write_text(json.dumps({'language':lang,'question':question,'expected':expected.answer_text,'actual_input':actual_input,'body':current},ensure_ascii=False,indent=2),encoding='utf-8')
                        raise AssertionError(f"QA UI mismatch lang={lang}, question={question!r}, expected={expected.answer_text!r}, input={actual_input!r}, body={current[-1600:]}") from exc
                    body=page.text()
                    pages=sorted({int(n) for n in __import__('re').findall(r'(?:Page|పేజీ|पृष्ठ)\s+(\d+)',body)})
                    expected_pages=sorted({c.page_number for c in expected.citations})
                    if expected_pages and not set(expected_pages).issubset(set(pages)):
                        raise AssertionError(f'Citation page missing in browser for {question!r}: expected {expected_pages}, body pages {pages}')
                    if not expected.citations and expected.answerability.value=='UNANSWERABLE':
                        if 'not stated' not in expected.answer_text.casefold() and 'పేర్కొనబడలేదు' not in expected.answer_text and 'नहीं दी गई' not in expected.answer_text:
                            raise AssertionError('Unexpected unsupported answer copy')
                    item={'document':name,'language':lang,'kind':kind,'question':question,
                          'answer':expected.answer_text,'answerability':expected.answerability.value,
                          'abstained':expected.abstained,'citation_pages':expected_pages,
                          'browser_citation_pages':pages}
                    records.append(item)
                    if kind=='deadline' and lang in {'en','te','hi'} and len([x for x in records if x['document']==name and x['language']==lang and x['kind']=='deadline'])==1:
                        shot=f'notifications-ask-{lang}.png'
                        data=page.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':True})['data']
                        (ROOT/'reports'/shot).write_bytes(base64.b64decode(data))
        out={'browser':'Chrome headless CDP','checks':len(records),'records':records,
             'screenshots':[f'reports/notifications-ask-{k}.png' for k in ('en','te','hi')]}
        (ROOT/'reports'/'notifications_browser_qa_matrix.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'checks':len(records),'screenshots':out['screenshots'],'status':'PASS'},ensure_ascii=True,indent=2))
    finally:
        try: page.ws.close()
        except Exception: pass
        try: browser.call('Target.disposeBrowserContext',{'browserContextId':context})
        except Exception: pass
        browser.ws.close()

if __name__=='__main__': main()
