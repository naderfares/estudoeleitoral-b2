import re, base64, html, glob, sys
src, imgdir, out = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(src, encoding='utf-8').read().split('\n')
imgs = sorted(glob.glob(imgdir + '/*.png'))

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\[(.+?)\]\((https?://[^)]+)\)', r'<a href="\2">\1</a>', t)
    return t

body, k, in_list = [], 0, False
for ln in lines:
    s = ln.strip()
    if s.startswith('- '):
        if not in_list: body.append('<ul>'); in_list = True
        body.append('<li>' + inline(s[2:]) + '</li>'); continue
    if in_list: body.append('</ul>'); in_list = False
    if not s or re.match(r'^Nov 1, 2026', s): continue
    if s.startswith('# '): body.append('<h1>' + inline(s[2:]) + '</h1>')
    elif s.startswith('## '): body.append('<h2>' + inline(s[3:]) + '</h2>')
    elif 'embedded content:' in s:
        cap = re.sub(r'^&#91;embedded content:\s*', '', s).rstrip(']').rstrip('\\').strip()
        b64 = base64.b64encode(open(imgs[k], 'rb').read()).decode()
        body.append(f'<figure><img src="data:image/png;base64,{b64}" alt="{html.escape(cap)}"><figcaption>{html.escape(cap)}</figcaption></figure>')
        k += 1
    else: body.append('<p>' + inline(s) + '</p>')
if in_list: body.append('</ul>')
assert k == len(imgs) == 9, k

page = f'''<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Se a mobilização do 2º turno tivesse vindo no 1º, o Congresso seria outro?</title>
<style>
body{{max-width:700px;margin:40px auto;padding:0 20px;font:20px/1.6 Georgia,serif;color:#242424}}
h1{{font:700 40px/1.2 -apple-system,Helvetica,Arial,sans-serif;margin-bottom:32px}}
h2{{font:700 26px/1.3 -apple-system,Helvetica,Arial,sans-serif;margin-top:44px}}
figure{{margin:36px 0}} img{{width:100%;height:auto;display:block}}
figcaption{{font:14px/1.4 -apple-system,Helvetica,Arial,sans-serif;color:#6b6b6b;text-align:center;margin-top:8px}}
a{{color:inherit}}
</style></head><body>
{chr(10).join(body)}
</body></html>'''
open(out, 'w', encoding='utf-8').write(page)
print('ok', k, 'imagens', len(page)//1024, 'KB')
