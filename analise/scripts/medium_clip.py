import re, base64, html, glob, json, sys
src, imgdir, out = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(src, encoding='utf-8').read().split('\n')
imgs = sorted(glob.glob(imgdir + '/*.png'))
def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    return re.sub(r'\[(.+?)\]\((https?://[^)]+)\)', r'<a href="\2">\1</a>', t)
full, plain_ph, k, lst = [], [], 0, False
caps = []
for ln in lines:
    s = ln.strip()
    if s.startswith('- '):
        if not lst: full.append('<ul>'); plain_ph.append('<ul>'); lst = True
        x = '<li>' + inline(s[2:]) + '</li>'; full.append(x); plain_ph.append(x); continue
    if lst: full.append('</ul>'); plain_ph.append('</ul>'); lst = False
    if not s or s.startswith('Nov 1, 2026'): continue
    if s.startswith('# '): x = '<h1>' + inline(s[2:]) + '</h1>'
    elif s.startswith('## '): x = '<h3>' + inline(s[3:]) + '</h3>'
    elif 'embedded content:' in s:
        cap = re.sub(r'^&#91;embedded content:\s*', '', s).rstrip(']').rstrip('\\').strip()
        caps.append(cap)
        b64 = base64.b64encode(open(imgs[k], 'rb').read()).decode()
        full.append(f'<figure><img src="data:image/png;base64,{b64}"><figcaption>{html.escape(cap)}</figcaption></figure>')
        k += 1
        plain_ph.append(f'<p>[GRAFICO {k}]</p>')
        continue
    else: x = '<p>' + inline(s) + '</p>'
    full.append(x); plain_ph.append(x)
if lst: full.append('</ul>'); plain_ph.append('</ul>')
assert k == 9
data = {'full': '\n'.join(full), 'ph': '\n'.join(plain_ph),
        'imgs': [base64.b64encode(open(f,'rb').read()).decode() for f in imgs], 'caps': caps}
btns = ['<button id="b-full" data-k="full">A. Copiar artigo completo (com gráficos)</button>',
        '<button id="b-ph" data-k="ph">B. Copiar só o texto (com marcadores)</button>']
btns += [f'<button id="b-{i+1}" data-k="img{i}">Gráfico {i+1}</button>' for i in range(9)]
btns += [f'<button id="c-{i+1}" data-k="cap{i}">Legenda {i+1}</button>' for i in range(9)]
page = '''<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pacote Medium: Se a mobilização do 2º turno tivesse vindo no 1º</title>
<style>body{font:16px/1.4 -apple-system,Helvetica,Arial,sans-serif;margin:16px;background:#fff;color:#222}
#g{display:grid;grid-template-columns:repeat(2,330px);gap:8px}
button{height:40px;font:inherit;text-align:left;padding:0 12px;border:1px solid #bbb;border-radius:6px;background:#f6f6f6;cursor:pointer}
button.ok{background:#d9f2dd;border-color:#5a9}#st{margin:12px 0;font-weight:600;min-height:20px}</style></head><body>
<div id="st">Clique num botão para copiar.</div><div id="g">''' + ''.join(btns) + '''</div>
<script>const D=''' + json.dumps(data) + ''';
function b64blob(b){const s=atob(b),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);return new Blob([u],{type:'image/png'})}
const B=D.imgs.map(b64blob);
function htmlItem(h){const t=document.createElement('div');t.innerHTML=h;return new ClipboardItem({'text/html':new Blob([h],{type:'text/html'}),'text/plain':new Blob([t.innerText],{type:'text/plain'})})}
document.querySelectorAll('button').forEach(b=>b.addEventListener('click',async()=>{const k=b.dataset.k;let it;
 if(k==='full'||k==='ph')it=htmlItem(D[k]);else if(k.startsWith('img'))it=new ClipboardItem({'image/png':B[+k.slice(3)]});
 else{const c=D.caps[+k.slice(3)];it=new ClipboardItem({'text/plain':new Blob([c],{type:'text/plain'})})}
 try{await navigator.clipboard.write([it]);document.querySelectorAll('button.ok').forEach(x=>x.classList.remove('ok'));b.classList.add('ok');document.getElementById('st').textContent='Copiado: '+b.textContent}
 catch(e){document.getElementById('st').textContent='Erro: '+e.name+' '+e.message}}));
</script></body></html>'''
open(out,'w',encoding='utf-8').write(page); print(len(page)//1024,'KB')
