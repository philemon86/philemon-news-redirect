import json,pathlib,html
ROOT=pathlib.Path(__file__).resolve().parent
BASE='https://philemon.com.tw'
def page(path,fallback=False):
 target=BASE+path
 script=("const u=new URL(window.location.href);const path=u.pathname.replace(/^\\/C(\\d+)(?=\\/|$)/,(_,n)=>'/c'+n);const target='https://philemon.com.tw'+path;" if fallback else 'const target='+json.dumps(target)+';')
 return '<!doctype html>\n<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="robots" content="noindex,follow"><link rel="canonical" href="'+html.escape(target,quote=True)+'"><script>'+script+'window.location.replace(target+window.location.search+window.location.hash);</script><meta http-equiv="refresh" content="0;url='+html.escape(target,quote=True)+'"><title>網頁已搬遷</title></head><body><noscript><a href="'+html.escape(target,quote=True)+'">前往新網址</a></noscript></body></html>\n'
def main():
 routes=json.loads((ROOT/'migration-routes.json').read_text(encoding='utf-8'))
 for r in routes:
  dest=ROOT/r['source_file']
  if dest.suffix!='.html' or not dest.resolve().is_relative_to(ROOT): raise ValueError(r)
  dest.parent.mkdir(parents=True,exist_ok=True)
  dest.write_text(page(r['new_path'],r['source_file']=='404.html'),encoding='utf-8')
 (ROOT/'404.html').write_text(page('/404.html',True),encoding='utf-8')
 print(f'Generated {len({r["source_file"] for r in routes} | {"404.html"})} logical redirect pages from {len(routes)} routes; preserve case-sensitive paths in Git')
if __name__=='__main__': main()
