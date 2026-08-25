import os

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
        "Ibn Sino. Oʻsimliklar bilan tanishuv. Nilufar Jabborova.", "Alisher. Maktabda birinchi kun. Dilnavoz Najimova.",
        "Toʻmaris. Tovuqni kim oʻgʻirladi?. Dinara Muminova.", "Bobur. Hindistonda. Gulnoz Tojiboyeva.",
        "Amir Temur. Qilichsiz gʻalaba. Qobiljon Shermatov.", "Forobiy. Gulnoz Tojiboyeva.",
        "Ulugʻbek. Kiyik ovida. Qobiljon Shermatov.", "Mushukchaning hikoyasi. Anvar Obidjon.",
        "Quyonchaning hikoyasi. Anvar Obidjon.", "Xoʻtikning hikoyasi. Anvar Obidjon.",
        "Toshbaqaning hikoyasi. Anvar Obidjon.", "Assalomu alaykum. Vasiliy Suxomlinskiy.",
        "Yetti qiz. Vasiliy Suxomlinskiy."
    ],
    "6": [
        "Joʻjaning hikoyasi. Anvar Obidjon.", "Tulkichaning hikoyasi. Anvar Obidjon.", "Choʻchqachaning hikoyasi. Anvar Obidjon.",
        "Hakkaning hikoyasi. Anvar Obidjon.", "Chumolining hikoyasi. Anvar Obidjon.", "Qurbaqaning hikoyasi. Anvar Obidjon.",
        "Uloqchaning hikoyasi. Anvar Obidjon.", "Bu sizga, oyijon. Yoqut Rahimova.", "Suv va daraxt. Zamira Ibrohimova.",
        "Bir bor ekan, pul bor ekan. Namoz Saʼdullayev.", "Bola va pul. Gʻiyosiddin Yusuf.", "Goʻzal xulqlar. Gʻiyosiddin Yusuf.",
        "Kundalik odoblar. Gʻiyosiddin Yusuf.", "Hayvonlar haqida hikoyalar. Aziz Nesin.", "Olmaxonning xotirasi. Mixail Prishvin.",
        "Jiblajibonning xatlari. Nikolay Sladkov.", "Assalomu alaykum. Vasiliy Suxomlinskiy.", "Odam boʻlish qiyin. Vasiliy Suxomlinskiy.",
        "Yetti qiz. Vasiliy Suxomlinskiy.", "Uzunquloq. Georgiy Skrebitskiy.", "Oʻgʻrivoy. Georgiy Skrebitskiy.",
        "Buyuk sayohatchilar. Mixail Zoshchenko.", "Pinokkioning boshidan kechirganlari. Karlo Kollodi.",
        "Maugli. Jozef Redyard Kipling.", "Bilmasvoy va doʻstlarining boshidan kechirganlari. Nikolay Nosov."
    ],
    "8": [
        "Oltin yurakli avtobola. Anvar Obidjon.", "Alamazon va uning piyodalari. Anvar Obidjon.", "0099 raqamli yolgʻonchi. Anvar Obidjon.",
        "Meshpolvonning janglari. Anvar Obidjon.", "Pashshavoyning boshidan kechirganlari. Anvar Obidjon.", "Futbol toʻpining sarguzashtlari. Anvar Obidjon.",
        "Moʻttivoymisan, Mittivoymisan?. Anvar Obidjon.", "Galaktikada bir kun 1-2-3. Saʼdulla Quronov.", "Shaytonvachchaning nayranglari. Erkin Malik.",
        "7-“A” da. Erkin Malik.", "Champo otli ilon. Erkin Malik.", "Qaldirgʻoch. Erkin Malik.", "Quyonlar saltanati. Xudoyberdi Toʻxtaboyev.",
        "Shirin qovunlar mamlakati. Xudoyberdi Toʻxtaboyev.", "Sehrli qalpoqcha. Xudoyberdi Toʻxtaboyev.", "Qaylardasan, bolaligim. Xudoyberdi Toʻxtaboyev.",
        "Changalzor iti. Normurod Norqobilov.", "Belbogʻ. Normurod Norqobilov.", "Paxmoq. Normurod Norqobilov.",
        "Amir Temur haqida hikoyalar. Toʻlqin Hayit.", "Olimjonning sarguzashtlari. Otabek Quvvatov.", "Ulugʻbek yulduzlar saltanatida. Otabek Quvvatov.",
        "Akramning sarguzashtlari. Pirimqul Qodirov.", "Ajab qishloq. Ergash Raimov.", "Chillak oʻyin. Shukur Xolmirzayev.",
        "Oqtosh. Shukur Xolmirzayev.", "Sulaymon ovchi va uning iti haqida. Sunnatulla Anorboyev.", "Yalpiz somsa. Oʻtkir Hoshimov.",
        "Shaytonni tutgan Shertoy. Abror Qoʻshnazarov.", "Boychechak. Abdusaid Koʻchimov.", "Hovlidagi maydoncha. Abdusaid Koʻchimov.",
        "Raqamlar sarguzashtlari. Saidqul Uspanov.", "Kichkina shahzoda. Antuan de Sent-Ekzyuperi.", "Yovvoyi yoʻrgʻa. Ernest Seton-Tompson.",
        "Domino. Ernest Seton-Tompson.", "Lobo. Ernest Seton-Tompson.", "Springfild tulkisi. Ernest Seton-Tompson.",
        "Chink. Ernest Seton-Tompson.", "Jonni laqabli ayiqcha. Ernest Seton-Tompson.", "Bingo. Ernest Seton-Tompson.",
        "Bugʻular izidan. Ernest Seton-Tompson.", "Snap. Ernest Seton-Tompson.", "Arno. Ernest Seton-Tompson.",
        "Bilmasvoy va doʻstlarining boshidan kechirganlari. Nikolay Nosov.", "Bilmasvoy quyosh shahrida. Nikolay Nosov.",
        "Pinokkioning boshidan kechirganlari. Karlo Kollodi.", "Buratino va uning sarguzashtlari. Aleksey Tolstoy.",
        "Tom Soyerning boshidan kechirganlari. Mark Tven.", "Tom Soyerning yangi sarguzashtlari. Mark Tven.", "Antiqa qurbaqa. Mark Tven.",
        "Alisaning sayohatlari. Kir Bulichev.", "Gʻaroyib bolalar. Aziz Nesin.", "Vinni Pux va uning sarguzashtlari. Alan Aleksandr Miln.",
        "Maugli. Jozef Redyard Kipling.", "Robinzonlar maktabi. Jyul Vern.", "Muzlar iskanjasida. Jyul Vern.",
        "Oʻqituvchi odam boʻlgan ekan. Ayzek Azimov.", "Men, buvim, Iliko va Illarion. Nodar Dumbadze.",
        "Anton boʻrini uchratgan kecha. Edith Shrayber Vike.", "Teddi. Yuriy Kazakov.", "Hikoyalar. Jek London.",
        "Baron Myunxauzenning sarguzashtlari. Erix Raspe.", "Maysajonning sarguzashtlari. Sergey Rozanov.",
        "Lider bola. Gʻiyosiddin Yusuf.", "Kundalik odoblar. Gʻiyosiddin Yusuf.", "Stiv Jobs. Navroʻz Ergash oʻgʻli.",
        "Muhammad Ali. Navroʻz Ergash oʻgʻli.", "Leonardo da Vinchi. Navroʻz Ergash oʻgʻli.", "Motsart. Navroʻz Ergash oʻgʻli.",
        "Albert Eynshteyn. Navroʻz Ergash oʻgʻli."
    ],
    "12": [
        "Sariq devni minib. Xudoyberdi Toʻxtaboyev.", "Qasoskorning oltin boshi. Xudoyberdi Toʻxtaboyev.",
        "Besh bolali yigitcha. Xudoyberdi Toʻxtaboyev.", "Shum bola. Gʻafur Gʻulom.", "Oʻtmishdan ertaklar. Abdulla Qahhor.",
        "Dunyoning ishlari. Oʻtkir Hoshimov.", "Galaktikada bir kun 1-2-3. Saʼdulla Quronov.", "Ot kishnagan oqshom. Togʻay Murod.",
        "Bolalik xotiralarim. Oybek.", "Jayhun ustida bulutlar. Mirkarim Osim.", "Zulmat ichra nur. Mirkarim Osim.",
        "Nur va zulmat. Mirkarim Osim.", "Olmos jilosi. Hojiakbar Shayxov.", "Afandining qirq bir pashshasi. Zohir Aʼlam.",
        "Boʻsh kelma, Aliqulov!. Farhod Musajonov.", "Qaysar bolaning hayoti. Mirzakalon Ismoiliy.", "Yonar daryo. Hakim Nazir.",
        "Kenjatoy. Hakim Nazir.", "Eski maktab. Sadriddin Ayniy.", "Jadidlar. Abdulla Qodiriy. Bahodir Karimov.",
        "Jadidlar. Abdulhamid Choʻlpon. Dilmurod Quronov.", "Jadidlar. Abdurauf Fitrat. Hamidulla Boltaboyev.",
        "Jadidlar. Abdulla Avloniy. Olim Oltinbek.", "Jadidlar. Isʼhoqxon toʻra Ibrat. Ulugʻbek Dolimov.",
        "Uygʻonish. Abu Ali ibn Sino. Abdulqodir Zohidiy.", "Uygʻonish. Abu Rayhon Beruniy. Abror Xidirov.",
        "Uygʻonish. Ahmad al-Fargʻoniy. Ashraf Ahmedov.", "Uygʻonish. Muso al-Xorazmiy. Ashraf Ahmedov.",
        "Kichkina shahzoda. Antuan de Sent-Ekzyuperi.", "Oʻn besh yoshli kapitan. Jyul Vern.", "Kapitan Grant bolalari. Jyul Vern.",
        "Klodius Bombarnak. Jyul Vern.", "Robinzonlar maktabi. Jyul Vern.", "Oliver Tvistning boshidan kechirganlari. Charlz Dikkens.",
        "Shahzoda va gado. Mark Tven.", "Tom Soyerning boshidan kechirganlari. Mark Tven.", "Gulliverning sayohatlari. Jonatan Svift.",
        "Merosxoʻr. Robert Luis Stivenson.", "Kapitan Vrungelning sarguzashtlari. Andrey Nekrasov.",
        "Birinchi muallim. Chingiz Aytmatov.", "Bolaligim. Chingiz Aytmatov.", "Fransuz tili saboqlari. Valentin Rasputin.",
        "Bir kunlik yoz. Rey Bredberi.", "Kavkaz asiri. Lev Tolstoy.", "Quyoshni koʻryapman. Nodar Dumbadze.",
        "Men, buvim, Iliko va Illarion. Nodar Dumbadze.", "Eski telefon. Pol Villard.", "Yoz bilan xayrlashuv. Konstantin Paustovskiy.",
        "Vaqtni qoʻyib yuboring!. Janni Rodari.", "Maktab alamlari va zavqlari. Orxan Pamuk.",
        "Marko Poloning ajoyib va gʻaroyib sarguzashtlari. Villi Maynk.", "Yovvoyi yoʻrgʻa. Ernest Seton-Tompson.",
        "Domino. Ernest Seton-Tompson.", "Lobo. Ernest Seton-Tompson."
    ]
}
