"""
BOT DE NOTICIAS VENEZUELA
Versión: 2.1 - Con Twitter integrado
"""

import asyncio
import feedparser
import os
import time
import re
from html import unescape
from telegram import Bot
from telegram.constants import ParseMode
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

TOKEN = os.getenv('TOKEN_TELEGRAM', "7933470868:AAE2vYm73cJLTcxMlLDzdVS7oE5Pe2g7xJs")
CHAT_ID = os.getenv('CHAT_ID', "@notiglobalve")
HISTORIAL_FILE = "enviados.txt"
INTERVALO = int(os.getenv('INTERVALO', '1800'))

# ═══════════════════════════════════════════════════════════════════════════════
# FUENTES RSS DE NOTICIAS
# ═══════════════════════════════════════════════════════════════════════════════

RSS_URLS = [
    "https://www.bancaynegocios.com/feed/",
    "https://finanzasdigital.com/feed/",
    "https://www.elnacional.com/feed/",
    "https://talcualdigital.com/feed/",
    "https://efectococuyo.com/feed/",
]

# ═══════════════════════════════════════════════════════════════════════════════
# FUENTES TWITTER (VIA NITTER RSS)
# ═══════════════════════════════════════════════════════════════════════════════

TWITTER_CUENTAS = [
    {"url": "https://nitter.poast.org/EconViews/rss", "nombre": "Econoviews"},
    {"url": "https://nitter.poast.org/RonaldBalza/rss", "nombre": "Ronald Balza"},
    {"url": "https://nitter.poast.org/asdrubal/rss", "nombre": "Asdrúbal Oliveros"},
    {"url": "https://nitter.poast.org/humbertogr/rss", "nombre": "Henkel García"},
    {"url": "https://nitter.poast.org/joseeguerra/rss", "nombre": "José Guerra"},
    {"url": "https://nitter.poast.org/anabcoello/rss", "nombre": "Anabel Coello"},
    {"url": "https://nitter.poast.org/BancayNegocios/rss", "nombre": "Banca y Negocios"},
    {"url": "https://nitter.poast.org/monitor_dolar/rss", "nombre": "Monitor Dólar"},
    {"url": "https://nitter.poast.org/ovallesuy/rss", "nombre": "Omar Vallés"},
]

# ═══════════════════════════════════════════════════════════════════════════════
# NOMBRES DE FUENTES
# ═══════════════════════════════════════════════════════════════════════════════

NOMBRES_FUENTES = {
    "bancaynegocios.com": "Banca y Negocios",
    "finanzasdigital.com": "Finanzas Digital",
    "elnacional.com": "El Nacional",
    "talcualdigital.com": "Tal Cual",
    "efectococuyo.com": "Efecto Cocuyo",
}

# ═══════════════════════════════════════════════════════════════════════════════
# FILTROS PARA NOTICIAS
# ═══════════════════════════════════════════════════════════════════════════════

PALABRAS_CLAVE_NOTICIAS = [
    "venezuela", "venezolano", "venezolana", "caracas", "maduro",
    "economía", "economia", "económico", "inflación", "inflacion",
    "pib", "crecimiento", "recesión", "devaluación",
    "finanzas", "financiero", "inversión", "inversion",
    "bolsa", "acciones", "mercado", "divisas", "dólar", "dolar", "euro",
    "tipo de cambio", "tasa de cambio", "bcv", "banco central",
    "banca", "banco", "bancos", "banesco", "mercantil", "provincial",
    "bnc", "bod", "bicentenario", "bancario",
    "cuenta", "tarjeta", "crédito", "credito", "débito", "debito",
    "pago móvil", "pago movil", "pagomovil", "c2p", "p2p", "p2c",
    "patria", "carnet de la patria", "petro", "criptomoneda", "bitcoin",
    "usdt", "binance", "remesas", "transferencia", "sudeban",
    "cantv", "movistar", "digitel", "corpoelec", "electricidad",
    "pdvsa", "gasolina", "combustible",
    "tecnología", "tecnologia", "internet", "telecomunicaciones",
    "seniat", "impuesto", "iva", "islr", "tributo", "fiscal",
    "petroleo", "petróleo",
]

# ═══════════════════════════════════════════════════════════════════════════════
# FILTROS PARA TWEETS
# ═══════════════════════════════════════════════════════════════════════════════

PALABRAS_CLAVE_TWEETS = [
    "venezuela", "bcv", "dólar", "dolar", "bolívar", "bolivar",
    "inflación", "inflacion", "economía", "economia",
    "banco", "banca", "sudeban", "finanzas",
    "pago", "remesas", "salario", "sueldo", "mínimo",
    "petróleo", "petroleo", "pdvsa", "gasolina",
    "importación", "exportación", "producción",
    "tipo de cambio", "paralelo", "oficial",
    "crisis", "escasez", "desabastecimiento",
]

IMAGENES_BLOQUEADAS = [
    'facebook', 'twitter', 'whatsapp', 'instagram', 'linkedin',
    'youtube', 'telegram', 'icon', 'logo', 'share', 'social',
    'button', 'avatar', 'default', 'placeholder', 'blank',
    'empty', '1x1', 'pixel', 'tracking', 'banner-ad', 'advertisement',
]

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def limpiar_html(texto):
    if not texto:
        return ""
    texto = unescape(texto)
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = re.sub(r'http[s]?://\S+', '', texto)
    texto = re.sub(r'[\[\]{}]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    
    # Eliminar frases comunes de RSS al final
    frases_eliminar = [
        r'The post.*appeared first on.*$',
        r'La entrada.*aparece primero en.*$',
        r'Leer más.*$',
        r'Seguir leyendo.*$',
        r'Continuar leyendo.*$',
    ]
    for frase in frases_eliminar:
        texto = re.sub(frase, '', texto, flags=re.IGNORECASE)
    
    return texto.strip()


def cortar_resumen(resumen):
    if len(resumen) > 280:
        resumen_corto = resumen[:280]
        ultimo_punto = resumen_corto.rfind('.')
        if ultimo_punto > 100:
            return resumen_corto[:ultimo_punto + 1]
        else:
            return resumen_corto.rsplit(' ', 1)[0] + "..."
    return resumen


def es_noticia_relevante(titulo, resumen):
    texto_completo = f"{titulo} {resumen}".lower()
    for palabra in PALABRAS_CLAVE_NOTICIAS:
        if palabra.lower() in texto_completo:
            return True
    return False


def es_tweet_relevante(texto):
    texto_lower = texto.lower()
    for palabra in PALABRAS_CLAVE_TWEETS:
        if palabra.lower() in texto_lower:
            return True
    return False


def noticia_ya_enviada(url):
    if not os.path.exists(HISTORIAL_FILE):
        return False
    with open(HISTORIAL_FILE, "r", encoding='utf-8') as f:
        enviados = f.read().splitlines()
    return url in enviados


def registrar_noticia(url):
    with open(HISTORIAL_FILE, "a", encoding='utf-8') as f:
        f.write(url + "\n")


def es_imagen_valida(url):
    if not url:
        return False
    url_lower = url.lower()
    for palabra in IMAGENES_BLOQUEADAS:
        if palabra in url_lower:
            return False
    return True


def obtener_imagen(entry):
    img_url = None
    
    if 'media_content' in entry:
        try:
            url = entry.media_content[0]['url']
            if es_imagen_valida(url):
                img_url = url
        except (IndexError, KeyError):
            pass
    
    if not img_url and 'media_thumbnail' in entry:
        try:
            url = entry.media_thumbnail[0]['url']
            if es_imagen_valida(url):
                img_url = url
        except (IndexError, KeyError):
            pass
    
    if not img_url and 'enclosures' in entry and entry.enclosures:
        for enclosure in entry.enclosures:
            if 'image' in enclosure.get('type', ''):
                url = enclosure.get('url') or enclosure.get('href')
                if es_imagen_valida(url):
                    img_url = url
                    break
    
    if not img_url and 'links' in entry:
        for link in entry.links:
            link_type = link.get('type', '')
            if 'image' in link_type:
                url = link.get('href')
                if es_imagen_valida(url):
                    img_url = url
                    break
    
    if not img_url:
        contenido = entry.get('content', [{}])
        if contenido:
            html_content = contenido[0].get('value', '') if isinstance(contenido, list) else str(contenido)
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_content)
            if img_match:
                url = img_match.group(1)
                if es_imagen_valida(url):
                    img_url = url
    
    if not img_url:
        descripcion = entry.get('description', '')
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', descripcion)
        if img_match:
            url = img_match.group(1)
            if es_imagen_valida(url):
                img_url = url
    
    return img_url


def formatear_mensaje_noticia(titulo, resumen, fuente):
    mensaje = (
        f"🔴 <b>{titulo}</b>\n\n"
        f"{resumen}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📰 Fuente: {fuente}\n"
        f"📲 <b>@notiglobalve</b>"
    )
    return mensaje


def formatear_mensaje_tweet(texto, autor):
    mensaje = (
        f"🐦 <b>{autor}</b>\n\n"
        f"{texto}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📲 <b>@notiglobalve</b>"
    )
    return mensaje


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE PUBLICACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

async def publicar_noticias(bot):
    print(f"\n{'─'*50}")
    print("📰 REVISANDO NOTICIAS")
    print(f"{'─'*50}")
    
    noticias_publicadas = 0
    
    for rss_url in RSS_URLS:
        try:
            dominio = rss_url.split('/')[2].replace('www.', '')
            nombre_fuente = NOMBRES_FUENTES.get(dominio, dominio)
            print(f"\n🔍 {nombre_fuente}")
            
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                print(f"   ⚠️ Sin noticias")
                continue
            
            for entry in feed.entries[:2]:
                url = entry.link
                
                if noticia_ya_enviada(url):
                    continue
                
                titulo = limpiar_html(entry.title)
                resumen = limpiar_html(entry.get('description') or entry.get('summary') or "")
                
                if not es_noticia_relevante(titulo, resumen):
                    continue
                
                print(f"   📰 {titulo[:50]}...")
                
                img_url = obtener_imagen(entry)
                resumen_corto = cortar_resumen(resumen)
                mensaje = formatear_mensaje_noticia(titulo.upper(), resumen_corto, nombre_fuente)
                
                try:
                    if img_url:
                        await bot.send_photo(
                            chat_id=CHAT_ID,
                            photo=img_url,
                            caption=mensaje,
                            parse_mode=ParseMode.HTML
                        )
                        print(f"   ✅ Publicada con imagen")
                    else:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=mensaje,
                            parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True
                        )
                        print(f"   ✅ Publicada")
                    
                    registrar_noticia(url)
                    noticias_publicadas += 1
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        
        except Exception as e:
            print(f"   ❌ Error en fuente: {e}")
    
    return noticias_publicadas


async def publicar_tweets(bot):
    print(f"\n{'─'*50}")
    print("🐦 REVISANDO TWITTER")
    print(f"{'─'*50}")
    
    tweets_publicados = 0
    
    for cuenta in TWITTER_CUENTAS:
        try:
            print(f"\n🔍 @{cuenta['nombre']}")
            
            feed = feedparser.parse(cuenta['url'])
            
            if not feed.entries:
                print(f"   ⚠️ Sin tweets")
                continue
            
            for entry in feed.entries[:1]:
                url = entry.link
                
                if noticia_ya_enviada(url):
                    continue
                
                texto_tweet = limpiar_html(entry.title)
                
                if not es_tweet_relevante(texto_tweet):
                    continue
                
                print(f"   🐦 {texto_tweet[:50]}...")
                
                img_url = obtener_imagen(entry)
                mensaje = formatear_mensaje_tweet(texto_tweet, cuenta['nombre'])
                
                try:
                    if img_url:
                        await bot.send_photo(
                            chat_id=CHAT_ID,
                            photo=img_url,
                            caption=mensaje,
                            parse_mode=ParseMode.HTML
                        )
                        print(f"   ✅ Tweet publicado con imagen")
                    else:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=mensaje,
                            parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True
                        )
                        print(f"   ✅ Tweet publicado")
                    
                    registrar_noticia(url)
                    tweets_publicados += 1
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        
        except Exception as e:
            print(f"   ❌ Error en cuenta: {e}")
    
    return tweets_publicados


async def ejecutar_ciclo():
    bot = Bot(token=TOKEN)
    
    hora_venezuela = (datetime.utcnow() - timedelta(hours=4)).strftime('%H:%M:%S')
    
    print(f"\n{'═'*60}")
    print(f"⏰ [{hora_venezuela}] INICIANDO CICLO")
    print(f"{'═'*60}")
    
    noticias = await publicar_noticias(bot)
    tweets = await publicar_tweets(bot)
    
    print(f"\n{'─'*50}")
    print(f"📊 RESUMEN:")
    print(f"   📰 Noticias publicadas: {noticias}")
    print(f"   🐦 Tweets publicados: {tweets}")
    print(f"{'─'*50}")


# ═══════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("="*60)
    print("   📰 BOT DE NOTICIAS VENEZUELA v2.1")
    print("="*60)
    print(f"   📢 Canal: {CHAT_ID}")
    print(f"   📡 Fuentes RSS: {len(RSS_URLS)}")
    print(f"   🐦 Cuentas Twitter: {len(TWITTER_CUENTAS)}")
    print(f"   ⏰ Intervalo: {INTERVALO // 60} minutos")
    print("="*60)
    
    while True:
        try:
            asyncio.run(ejecutar_ciclo())
            print(f"\n💤 Esperando {INTERVALO // 60} minutos...")
            time.sleep(INTERVALO)
        except KeyboardInterrupt:
            print("\n⛔ Bot detenido")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)