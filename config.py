import os
import time

# ==========================================================
# VAQT MINTAQASI — TOSHKENT (2026-09-03 da tuzatilgan)
# ----------------------------------------------------------
# MUAMMO: server Render'da UTC vaqtida ishlaydi, O‘zbekiston esa
# UTC+5. Kod ichidagi «kechqurun soat 20 da xulosa yubor» degan
# qoidalar server soatiga qarardi — natijada xabarlar Toshkent
# vaqti bilan **soat 01:00 da** kelardi. Foydalanuvchilar buni
# «yarim tunda xabar kelayapti» deb aytishdi.
#
# YECHIM: butun jarayon Toshkent vaqtida ishlaydi. Shu bir qator
# hamma joyni to‘g‘rilaydi: xabar soatlari ham, «bugun» degan
# hisob ham (kunlik parvoz, kunlik chegaralar) endi mahalliy
# kun bo‘yicha hisoblanadi.
# ==========================================================
os.environ.setdefault("TZ", "Asia/Tashkent")
try:
    time.tzset()          # faqat Linux/Mac'da bor, Windows'da yo‘q
except AttributeError:
    pass

# Render Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
ACCESS_CODE = os.getenv("ACCESS_CODE", "BILIG-TEST")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
PORT = int(os.environ.get("PORT", 8080))

# Doimiy matnlar
MUTOLAA_NOTE = "\n\n💡 <i>Izoh: Agarda ushbu kitoblarni bosma shaklda topa olmasangiz, ularni 'Mutolaa' ilovasida elektron o‘qish yoki tinglash shaklida topishingiz mumkin.</i>"

WELCOME_TEXT = (
    "👋 <b>Bilig AI ga xush kelibsiz!</b>\n\n"
    "Ushbu bot bolalar yozuvchisi <b>Sa'dullo Quronov</b> tomonidan farzandiga kitob o‘qitishda qiynalayotgan ota-onalarga yordam berish uchun yaratildi.\n\n"
    "🎯 <b>Qanday ishlaydi?</b>\n"
    "📖 <b>Bola o‘qiydi</b> ➡️ 🤖 <b>AI tekshirib \"Bilig\" (🔅 oltin tanga) beradi</b> ➡️ 🎁 <b>Bola tangalariga siz belgilagan sovg‘alarni oladi!</b>\n\n"
    "Kitob o‘qish endi urush-janjal emas, qiziqarli o‘yin! 🚀\n\n"
    "👇 <b>Boshlash uchun kimsiz?</b>"
)

# Tavsiya etilgan asarlar bazasi
RECOMMENDED_BOOKS = {
    "3": [
        "O‘zbek xalq ertaklari", "Kuchukning hikoyasi. Anvar Obidjon.", "Buzoqning hikoyasi. Anvar Obidjon.",
        "Xorazmiy. 0 bilan tanishuv. Dinara Muminova.", "Beruniy. Sahrodagi qahramon. Saʼdullo Quronov.",
        "Ibn Sino. O‘simliklar bilan tanishuv. Nilufar Jabborova.", "Alisher. Maktabda birinchi kun. Dilnavoz Najimova.",
        "To‘maris. Tovuqni kim o‘g‘irladi?. Dinara Muminova.", "Bobur. Hindistonda. Gulnoz Tojiboyeva.",
        "Amir Temur. Qilichsiz g‘alaba. Qobiljon Shermatov.", "Forobiy. Gulnoz Tojiboyeva.",
        "Ulug‘bek. Kiyik ovida. Qobiljon Shermatov.", "Mushukchaning hikoyasi. Anvar Obidjon.",
        "Quyonchaning hikoyasi. Anvar Obidjon.", "Xo‘tikning hikoyasi. Anvar Obidjon.",
        "Toshbaqaning hikoyasi. Anvar Obidjon.", "Assalomu alaykum. Vasiliy Suxomlinskiy.",
        "Yetti qiz. Vasiliy Suxomlinskiy."
    ],
    "6": [
        "Jo‘janing hikoyasi. Anvar Obidjon.", "Tulkichaning hikoyasi. Anvar Obidjon.", "Cho‘chqachaning hikoyasi. Anvar Obidjon.",
        "Hakkaning hikoyasi. Anvar Obidjon.", "Chumolining hikoyasi. Anvar Obidjon.", "Qurbaqaning hikoyasi. Anvar Obidjon.",
        "Uloqchaning hikoyasi. Anvar Obidjon.", "Bu sizga, oyijon. Yoqut Rahimova.", "Suv va daraxt. Zamira Ibrohimova.",
        "Bir bor ekan, pul bor ekan. Namoz Saʼdullayev.", "Bola va pul. G‘iyosiddin Yusuf.", "Go‘zal xulqlar. G‘iyosiddin Yusuf.",
        "Kundalik odoblar. G‘iyosiddin Yusuf.", "Hayvonlar haqida hikoyalar. Aziz Nesin.", "Olmaxonning xotirasi. Mixail Prishvin.",
        "Jiblajibonning xatlari. Nikolay Sladkov.", "Assalomu alaykum. Vasiliy Suxomlinskiy.", "Odam bo‘lish qiyin. Vasiliy Suxomlinskiy.",
        "Yetti qiz. Vasiliy Suxomlinskiy.", "Uzunquloq. Georgiy Skrebitskiy.", "O‘g‘rivoy. Georgiy Skrebitskiy.",
        "Buyuk sayohatchilar. Mixail Zoshchenko.", "Pinokkioning boshidan kechirganlari. Karlo Kollodi.",
        "Maugli. Jozef Redyard Kipling.", "Bilmasvoy va do‘stlarining boshidan kechirganlari. Nikolay Nosov."
    ],
    "8": [
        "Oltin yurakli avtobola. Anvar Obidjon.", "Alamazon va uning piyodalari. Anvar Obidjon.", "0099 raqamli yolg‘onchi. Anvar Obidjon.",
        "Meshpolvonning janglari. Anvar Obidjon.", "Pashshavoyning boshidan kechirganlari. Anvar Obidjon.", "Futbol to‘pining sarguzashtlari. Anvar Obidjon.",
        "Mo‘ttivoymisan, Mittivoymisan?. Anvar Obidjon.", "Galaktikada bir kun 1-kitob. Saʼdullo Quronov.",
        "Galaktikada bir kun 2-kitob. Saʼdullo Quronov.",
        "Galaktikada bir kun 3-kitob. Saʼdullo Quronov.", "Shaytonvachchaning nayranglari. Erkin Malik.",
        "7-“A” da. Erkin Malik.", "Champo otli ilon. Erkin Malik.", "Qaldirg‘och. Erkin Malik.", "Quyonlar saltanati. Xudoyberdi To‘xtaboyev.",
        "Shirin qovunlar mamlakati. Xudoyberdi To‘xtaboyev.", "Sehrli qalpoqcha. Xudoyberdi To‘xtaboyev.", "Qaylardasan, bolaligim. Xudoyberdi To‘xtaboyev.",
        "Changalzor iti. Normurod Norqobilov.", "Belbog‘. Normurod Norqobilov.", "Paxmoq. Normurod Norqobilov.",
        "Amir Temur haqida hikoyalar. To‘lqin Hayit.", "Olimjonning sarguzashtlari. Otabek Quvvatov.", "Ulug‘bek yulduzlar saltanatida. Otabek Quvvatov.",
        "Akramning sarguzashtlari. Pirimqul Qodirov.", "Ajab qishloq. Ergash Raimov.", "Chillak o‘yin. Shukur Xolmirzayev.",
        "Oqtosh. Shukur Xolmirzayev.", "Sulaymon ovchi va uning iti haqida. Sunnatulla Anorboyev.", "Yalpiz somsa. O‘tkir Hoshimov.",
        "Shaytonni tutgan Shertoy. Abror Qo‘shnazarov.", "Boychechak. Abdusaid Ko‘chimov.", "Hovlidagi maydoncha. Abdusaid Ko‘chimov.",
        "Raqamlar sarguzashtlari. Saidqul Uspanov.", "Kichkina shahzoda. Antuan de Sent-Ekzyuperi.", "Yovvoyi yo‘rg‘a. Ernest Seton-Tompson.",
        "Domino. Ernest Seton-Tompson.", "Lobo. Ernest Seton-Tompson.", "Springfild tulkisi. Ernest Seton-Tompson.",
        "Chink. Ernest Seton-Tompson.", "Jonni laqabli ayiqcha. Ernest Seton-Tompson.", "Bingo. Ernest Seton-Tompson.",
        "Bug‘ular izidan. Ernest Seton-Tompson.", "Snap. Ernest Seton-Tompson.", "Arno. Ernest Seton-Tompson.",
        "Bilmasvoy va do‘stlarining boshidan kechirganlari. Nikolay Nosov.", "Bilmasvoy quyosh shahrida. Nikolay Nosov.",
        "Pinokkioning boshidan kechirganlari. Karlo Kollodi.", "Buratino va uning sarguzashtlari. Aleksey Tolstoy.",
        "Tom Soyerning boshidan kechirganlari. Mark Tven.", "Tom Soyerning yangi sarguzashtlari. Mark Tven.", "Antiqa qurbaqa. Mark Tven.",
        "Alisaning sayohatlari. Kir Bulichev.", "G‘aroyib bolalar. Aziz Nesin.", "Vinni Pux va uning sarguzashtlari. Alan Aleksandr Miln.",
        "Maugli. Jozef Redyard Kipling.", "Robinzonlar maktabi. Jyul Vern.", "Muzlar iskanjasida. Jyul Vern.",
        "O‘qituvchi odam bo‘lgan ekan. Ayzek Azimov.", "Men, buvim, Iliko va Illarion. Nodar Dumbadze.",
        "Anton bo‘rini uchratgan kecha. Edith Shrayber Vike.", "Teddi. Yuriy Kazakov.", "Hikoyalar. Jek London.",
        "Baron Myunxauzenning sarguzashtlari. Erix Raspe.", "Maysajonning sarguzashtlari. Sergey Rozanov.",
        "Lider bola. G‘iyosiddin Yusuf.", "Kundalik odoblar. G‘iyosiddin Yusuf.", "Stiv Jobs. Navro‘z Ergash o‘g‘li.",
        "Muhammad Ali. Navro‘z Ergash o‘g‘li.", "Leonardo da Vinchi. Navro‘z Ergash o‘g‘li.", "Motsart. Navro‘z Ergash o‘g‘li.",
        "Albert Eynshteyn. Navro‘z Ergash o‘g‘li."
    ],
    "12": [
        "Sariq devni minib. Xudoyberdi To‘xtaboyev.", "Qasoskorning oltin boshi. Xudoyberdi To‘xtaboyev.",
        "Besh bolali yigitcha. Xudoyberdi To‘xtaboyev.", "Shum bola. G‘afur G‘ulom.", "O‘tmishdan ertaklar. Abdulla Qahhor.",
        "Dunyoning ishlari. O‘tkir Hoshimov.", "Galaktikada bir kun 1-kitob. Saʼdullo Quronov.",
        "Galaktikada bir kun 2-kitob. Saʼdullo Quronov.",
        "Galaktikada bir kun 3-kitob. Saʼdullo Quronov.", "Ot kishnagan oqshom. Tog‘ay Murod.",
        "Bolalik xotiralarim. Oybek.", "Jayhun ustida bulutlar. Mirkarim Osim.", "Zulmat ichra nur. Mirkarim Osim.",
        "Nur va zulmat. Mirkarim Osim.", "Olmos jilosi. Hojiakbar Shayxov.", "Afandining qirq bir pashshasi. Zohir Aʼlam.",
        "Bo‘sh kelma, Aliqulov!. Farhod Musajonov.", "Qaysar bolaning hayoti. Mirzakalon Ismoiliy.", "Yonar daryo. Hakim Nazir.",
        "Kenjatoy. Hakim Nazir.", "Eski maktab. Sadriddin Ayniy.", "Jadidlar. Abdulla Qodiriy. Bahodir Karimov.",
        "Jadidlar. Abdulhamid Cho‘lpon. Dilmurod Quronov.", "Jadidlar. Abdurauf Fitrat. Hamidulla Boltaboyev.",
        "Jadidlar. Abdulla Avloniy. Olim Oltinbek.", "Jadidlar. Isʼhoqxon to‘ra Ibrat. Ulug‘bek Dolimov.",
        "Uyg‘onish. Abu Ali ibn Sino. Abdulqodir Zohidiy.", "Uyg‘onish. Abu Rayhon Beruniy. Abror Xidirov.",
        "Uyg‘onish. Ahmad al-Farg‘oniy. Ashraf Ahmedov.", "Uyg‘onish. Muso al-Xorazmiy. Ashraf Ahmedov.",
        "Kichkina shahzoda. Antuan de Sent-Ekzyuperi.", "O‘n besh yoshli kapitan. Jyul Vern.", "Kapitan Grant bolalari. Jyul Vern.",
        "Klodius Bombarnak. Jyul Vern.", "Robinzonlar maktabi. Jyul Vern.", "Oliver Tvistning boshidan kechirganlari. Charlz Dikkens.",
        "Shahzoda va gado. Mark Tven.", "Tom Soyerning boshidan kechirganlari. Mark Tven.", "Gulliverning sayohatlari. Jonatan Svift.",
        "Merosxo‘r. Robert Luis Stivenson.", "Kapitan Vrungelning sarguzashtlari. Andrey Nekrasov.",
        "Birinchi muallim. Chingiz Aytmatov.", "Bolaligim. Chingiz Aytmatov.", "Fransuz tili saboqlari. Valentin Rasputin.",
        "Bir kunlik yoz. Rey Bredberi.", "Kavkaz asiri. Lev Tolstoy.", "Quyoshni ko‘ryapman. Nodar Dumbadze.",
        "Men, buvim, Iliko va Illarion. Nodar Dumbadze.", "Eski telefon. Pol Villard.", "Yoz bilan xayrlashuv. Konstantin Paustovskiy.",
        "Vaqtni qo‘yib yuboring!. Janni Rodari.", "Maktab alamlari va zavqlari. Orxan Pamuk.",
        "Marko Poloning ajoyib va g‘aroyib sarguzashtlari. Villi Maynk.", "Yovvoyi yo‘rg‘a. Ernest Seton-Tompson.",
        "Domino. Ernest Seton-Tompson.", "Lobo. Ernest Seton-Tompson."
    ]
}
