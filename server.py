# ==========================================================
# server.py  (YANGILANGAN)
# ------------------------------------------------------------
# Avvalgi versiyada bu yerda faqat "men tirikman" deb javob
# beruvchi oddiy HTTP server bor edi (Render.com portni ochiq
# ushlab turishi uchun). Endi shu server o'rniga to'liq
# Mini App + API (webapp_api.py) ishga tushadi — health-check
# vazifasini ham u bajaradi ("/" manzili 200 OK qaytaradi).
#
# main.py bu faylni threading.Thread orqali chaqiradi, botning
# o'zi (aiogram polling) alohida davom etaveradi — ikkalasi
# bir-biriga xalaqit bermaydi.
# ==========================================================

from config import PORT
from webapp_api import run_webapp_server


def run_dummy_server():
    """Nomi eski nomda qoldirildi (main.py shu nomni chaqiradi),
    lekin endi ichida to'liq Mini App + API serveri ishlaydi."""
    run_webapp_server(PORT)
