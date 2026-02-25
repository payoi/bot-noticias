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
    "https://www.telesurtv.net/feed/",
]


# ═══════════════════════════════════════════════════════════════════════════════
# NOMBRES DE FUENTES
# ═══════════════════════════════════════════════════════════════════════════════

NOMBRES_FUENTES = {
    "bancaynegocios.com": "Banca y Negocios",
    "finanzasdigital.com": "Finanzas Digital",
    "telesurtv.net": "TeleSUR",
}

# ═══════════════════════════════════════════════════════════════════════════════
# FILTROS POR FUENTE
# ═══════════════════════════════════════════════════════════════════════════════

# Filtro para Banca y Negocios + Finanzas Digital
FILTRO_ECONOMIA = [
    "venezuela", "venezolano", "venezolana", "caracas",
    "economía", "economia", "económico", "económica",
    "finanzas", "financiero", "financiera",
    "banca", "banco", "bancos", "bancario", "bancaria",
    "banesco", "mercantil", "provincial", "bnc", "bod", "bicentenario",
    "bcv", "banco central", "sudeban",
    "dólar", "dolar", "bolívar", "bolivar", "divisas",
    "tipo de cambio", "tasa de cambio", "paralelo", "oficial",
    "inflación", "inflacion", "devaluación", "devaluacion",
    "pago móvil", "pago movil", "pagomovil", "c2p", "p2p",
    "tarjeta", "crédito", "credito", "débito", "debito",
    "transferencia", "remesas", "cuenta",
    "inversión", "inversion", "mercado", "bolsa", "acciones",
    "pdvsa", "petróleo", "petroleo", "gasolina",
    "seniat", "impuesto", "iva", "islr", "tributo",
    "usdt", "binance", "criptomoneda", "bitcoin", "petro",
]

# Filtro para TeleSUR
FILTRO_TELESUR = [
    # Política Venezuela
    "venezuela", "venezolano", "venezolana", "caracas", "maduro",
    "gobierno", "asamblea", "diputado", "ministro", "ministerio",
    "política", "politica", "político", "elecciones", "votación",
    "constitución", "ley", "decreto", "gaceta",
    "oposición", "oposicion", "sanciones",
    
    # Tecnología
    "tecnología", "tecnologia", "internet", "digital",
    "telecomunicaciones", "conectividad", "fibra óptica",
    "cantv", "movistar", "digitel", "satelital",
    "5g", "4g", "redes", "ciberseguridad",
    "app", "aplicación", "software", "innovación",
    "inteligencia artificial", "starlink",
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


def es_noticia_relevante(titulo, resumen, fuente):
    """Filtra noticias según la fuente"""
    texto_completo = f"{titulo} {resumen}".lower()
    
    # Seleccionar filtro según la fuente
    if fuente == "TeleSUR":
        palabras = FILTRO_TELESUR
    else:
        # Banca y Negocios, Finanzas Digital
        palabras = FILTRO_ECONOMIA
    
    for palabra in palabras:
        if palabra.lower() in texto_completo:
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
                
                if not es_noticia_relevante(titulo, resumen, nombre_fuente):
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


async def ejecutar_ciclo():
    bot = Bot(token=TOKEN)
    
    hora_venezuela = (datetime.utcnow() - timedelta(hours=4)).strftime('%H:%M:%S')
    
    print(f"\n{'═'*60}")
    print(f"⏰ [{hora_venezuela}] INICIANDO CICLO")
    print(f"{'═'*60}")
    
    noticias = await publicar_noticias(bot)
    
    print(f"\n{'─'*50}")
    print(f"📊 RESUMEN:")
    print(f"   📰 Noticias publicadas: {noticias}")
    print(f"{'─'*50}")


# ═══════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("="*60)
    print("   📰 BOT DE NOTICIAS VENEZUELA v2.2")
    print("="*60)
    print(f"   📢 Canal: {CHAT_ID}")
    print(f"   📡 Fuentes RSS: {len(RSS_URLS)}")
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