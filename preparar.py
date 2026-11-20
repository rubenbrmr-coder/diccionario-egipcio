"""Prepara el proyecto Android de una app de Medu Netjer (lo usa GitHub Actions).

  python preparar.py web     -> crea proyecto/www con index.html y las fuentes descargadas (funciona sin internet)
  python preparar.py iconos  -> pone el icono y la pantalla de inicio en proyecto/android
"""
import os, re, sys, glob, json, urllib.request
from PIL import Image, ImageDraw

AZUL = (31, 59, 111)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'


def descargar(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()




def web():
    os.makedirs('proyecto/www/fuentes', exist_ok=True)
    html = open('index.html', encoding='utf-8').read()
    m = re.search(r'<link href="(https://fonts\.googleapis\.com/css2\?[^"]+)" rel="stylesheet">', html)
    if m:
        try:
            css = descargar(m.group(1).replace('&amp;', '&')).decode('utf-8')
            for i, url in enumerate(sorted(set(re.findall(r'url\((https://[^)]+)\)', css)))):
                nombre = f'f{i}.woff2'
                open(f'proyecto/www/fuentes/{nombre}', 'wb').write(descargar(url))
                css = css.replace(url, f'fuentes/{nombre}')
            open('proyecto/www/fuentes.css', 'w', encoding='utf-8').write(css)
            html = html.replace(m.group(0), '<link href="fuentes.css" rel="stylesheet">')
            html = re.sub(r'<link rel="preconnect"[^>]*>\n?', '', html)
            print('Fuentes incluidas en la app:', i + 1, 'archivos')
        except Exception as e:
            print('AVISO: no se pudieron descargar las fuentes; la app las cargará de internet.', e)
    escribir_app(html)
    if not os.path.exists('proyecto/package.json'):
        json.dump({'name': 'medu-netjer-app', 'version': '1.0.0', 'private': True}, open('proyecto/package.json', 'w'))


def iconos():
    res = 'proyecto/android/app/src/main/res'
    icono = Image.open('icon.png').convert('RGB')
    fondo = icono.getpixel((4, 4))
    tam = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
    for dens, t in tam.items():
        carpeta = f'{res}/mipmap-{dens}'
        os.makedirs(carpeta, exist_ok=True)
        normal = icono.resize((t, t), Image.LANCZOS)
        normal.save(f'{carpeta}/ic_launcher.png')
        mascara = Image.new('L', (t * 4, t * 4), 0)
        ImageDraw.Draw(mascara).ellipse((0, 0, t * 4 - 1, t * 4 - 1), fill=255)
        redondo = Image.new('RGBA', (t, t), (0, 0, 0, 0))
        redondo.paste(normal, (0, 0), mascara.resize((t, t), Image.LANCZOS))
        redondo.save(f'{carpeta}/ic_launcher_round.png')
        # icono adaptativo: lienzo de 108 dp con el dibujo en la zona segura
        f = int(t * 108 / 48)
        frente = Image.new('RGB', (f, f), fondo)
        dentro = int(f * 0.70)
        frente.paste(icono.resize((dentro, dentro), Image.LANCZOS), ((f - dentro) // 2, (f - dentro) // 2))
        frente.save(f'{carpeta}/ic_launcher_foreground.png')
    os.makedirs(f'{res}/values', exist_ok=True)
    color = '#%02X%02X%02X' % fondo
    open(f'{res}/values/ic_launcher_background.xml', 'w').write(
        f'<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">{color}</color>\n</resources>\n')
    # pantalla de inicio: fondo azul con el icono en el centro
    for ruta in glob.glob(f'{res}/drawable*/splash.png'):
        w, h = Image.open(ruta).size
        lienzo = Image.new('RGB', (w, h), fondo)
        lado = int(min(w, h) * 0.45)
        lienzo.paste(icono.resize((lado, lado), Image.LANCZOS), ((w - lado) // 2, (h - lado) // 2))
        lienzo.save(ruta)
    print('Iconos y pantalla de inicio listos')



# ===================== Actualización automática =====================
# La app instalada abre primero un pequeño «lanzador» (index.html) que busca en GitHub
# la última versión publicada de la app (rama «actualizacion» del repositorio).
# Si hay internet y una versión más nueva, la usa y la guarda; si no hay internet,
# abre la última versión guardada o, si no hay ninguna, la que viene dentro del APK.
import subprocess, time, tempfile, html as _html

LANZADOR = r'''<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITULO__</title>
<style>html,body{margin:0;height:100%;background:#1f3b6f;color:#f4ecdb;font:16px system-ui,sans-serif}
#m{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:12px;opacity:.9}</style>
</head><body><div id="m"><div style="font-size:44px">&#x13080;</div><div>Cargando…</div></div>
<script>
(function(){
var REMOTO='__REMOTO__', LOCAL='__VERSION__', DB='medu-actualizador';
function ver(t){var m=/<meta name="medu-version" content="(\d+)"/.exec(t||'');return m?m[1]:'0'}
function abrir(){return new Promise(function(ok,ko){try{var r=indexedDB.open(DB,1);r.onupgradeneeded=function(){r.result.createObjectStore('a')};r.onsuccess=function(){ok(r.result)};r.onerror=function(){ko(r.error)}}catch(e){ko(e)}})}
function leer(){return abrir().then(function(db){return new Promise(function(ok){try{var q=db.transaction('a').objectStore('a').get('app');q.onsuccess=function(){ok(q.result||null)};q.onerror=function(){ok(null)}}catch(e){ok(null)}})}).catch(function(){return null})}
function guardar(t){return abrir().then(function(db){return new Promise(function(ok){try{var tx=db.transaction('a','readwrite');tx.objectStore('a').put(t,'app');tx.oncomplete=ok;tx.onerror=ok}catch(e){ok()}})}).catch(function(){})}
function mostrar(t){document.open();document.write(t);document.close()}
function remoto(){
 if(!REMOTO||!window.fetch)return Promise.resolve(null);
 return new Promise(function(ok){
  var fin=false;var to=setTimeout(function(){if(!fin){fin=true;ok(null)}},3500);
  fetch(REMOTO+'?v='+Date.now(),{cache:'no-store'}).then(function(r){return r.ok?r.text():null}).then(function(t){
   if(fin)return;fin=true;clearTimeout(to);ok(t&&t.indexOf('</html>')>0&&t.length>5000&&ver(t)!=='0'?t:null)
  }).catch(function(){if(!fin){fin=true;clearTimeout(to);ok(null)}})
 })
}
function local(){return fetch('app.html').then(function(r){return r.text()})}
Promise.all([remoto(),leer()]).then(function(x){
 var r=x[0],c=x[1],mejor=null,mv=LOCAL;
 if(r&&(!c||ver(r)>ver(c)))guardar(r);
 [r,c].forEach(function(t){if(t&&ver(t)>mv){mejor=t;mv=ver(t)}});
 if(mejor)mostrar(mejor);else local().then(mostrar);
}).catch(function(){local().then(mostrar)});
})();
</script>
</body></html>
'''


def publicar(html, repo, version):
    """Sube la app preparada a la rama «actualizacion» del repositorio."""
    try:
        cab = subprocess.run(['git', 'config', '--get', 'http.https://github.com/.extraheader'],
                             capture_output=True, text=True).stdout.strip()
        d = tempfile.mkdtemp()
        open(os.path.join(d, 'app.html'), 'w', encoding='utf-8').write(html)
        open(os.path.join(d, 'LEEME.txt'), 'w', encoding='utf-8').write(
            'Rama generada automaticamente por GitHub Actions: contiene la ultima version de la app.\n'
            'Las apps instaladas la descargan al abrirse. No hace falta tocarla.\n')
        def g(*a):
            return subprocess.run(['git', *a], cwd=d, capture_output=True, text=True)
        g('init', '-q'); g('checkout', '-q', '-b', 'actualizacion')
        g('config', 'user.name', 'github-actions'); g('config', 'user.email', 'actions@github.com')
        g('add', '-A'); g('commit', '-q', '-m', 'Actualizacion ' + version)
        orden = ['git'] + (['-c', 'http.extraheader=' + cab] if cab else []) + \
                ['push', '-f', 'https://github.com/%s.git' % repo, 'actualizacion']
        r = subprocess.run(orden, cwd=d, capture_output=True, text=True)
        if r.returncode == 0:
            print('Actualizacion publicada en la rama «actualizacion» (version %s)' % version)
        else:
            print('AVISO: no se pudo publicar la actualizacion:', r.stderr[-400:])
    except Exception as e:
        print('AVISO: no se pudo publicar la actualizacion:', e)


def escribir_app(html):
    version = time.strftime('%Y%m%d%H%M%S', time.gmtime())
    html = re.sub(r'<meta name="medu-version"[^>]*>\n?', '', html)
    html = re.sub(r'(<head[^>]*>)', r'\1\n<meta name="medu-version" content="%s">' % version, html, count=1)
    open('proyecto/www/app.html', 'w', encoding='utf-8').write(html)
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    remoto = 'https://raw.githubusercontent.com/%s/actualizacion/app.html' % repo if repo else ''
    t = re.search(r'<title>(.*?)</title>', html, re.S)
    titulo = _html.escape(_html.unescape(t.group(1).strip())) if t else 'Medu Netjer'
    open('proyecto/www/index.html', 'w', encoding='utf-8').write(
        LANZADOR.replace('__REMOTO__', remoto).replace('__VERSION__', version).replace('__TITULO__', titulo))
    print('Lanzador con actualizacion automatica:', remoto or '(sin repositorio: solo version local)')
    if repo:
        publicar(html, repo, version)

if __name__ == '__main__':
    {'web': web, 'iconos': iconos}[sys.argv[1]]()
