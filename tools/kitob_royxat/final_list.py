# -*- coding: utf-8 -*-
import json, gen, match

govw = json.load(open('gov_word.json'))
QOLDA = {("«She'rlar»", 'G‘afur G‘ulom')}
def gov_rows(grp, data):
    out = []
    for i, (n, t, a, s, y, iz) in enumerate(data):
        w = govw[grp][i]
        if s == gen.BOR:      # bazamizda bor — ro‘yxatga kirmaydi
            continue
        bor = bool(w['f']) or (t, a) in QOLDA
        out.append((t, a, y, bor, iz))
    return out

G1 = gov_rows('10-14 yosh toifasi', gen.g1)
G2 = gov_rows('15-19 yosh toifasi', gen.g2)

def mine(rows):
    out = []
    for t, a, y, iz in rows:
        tt = t.strip('«»').split(' (')[0]
        s, x = match.find(tt, a)
        if s < 0.8:
            s2, _ = match.find(tt)
            s = max(s, s2 if s2 >= 0.9 else 0)
        out.append((t, a, y, s >= 0.8, iz))
    return out

DOST = mine([
 ("«Alpomish»","Xalq og‘zaki ijodi","14-16","Milliy eposimiz — javonning boshida turishi kerak"),
 ("«Ravshan»","Xalq og‘zaki ijodi","11-13","«Go‘ro‘g‘li» turkumi · davlat ro‘yxatida ham bor"),
 ("«Go‘ro‘g‘lining tug‘ilishi»","Xalq og‘zaki ijodi","14-16","Davlat ro‘yxatida ham bor"),
 ("«Malika Husnobod»","Xalq og‘zaki ijodi","11-13","Davlat ro‘yxatida ham bor"),
 ("«Yunus va Misqol pari»","Xalq og‘zaki ijodi","11-13","Davlat ro‘yxatida ham bor"),
 ("«Yusuf va Ahmad»","Xalq og‘zaki ijodi","11-13","Qahramonlik dostoni"),
 ("«Avazxon»","Xalq og‘zaki ijodi","11-13","«Go‘ro‘g‘li» turkumi"),
 ("«Malika ayyor»","Xalq og‘zaki ijodi","11-13","«Go‘ro‘g‘li» turkumi"),
 ("«Rustamxon»","Xalq og‘zaki ijodi","11-13","Sarguzasht ohangi kuchli"),
 ("«Xoldorxon»","Xalq og‘zaki ijodi","14-16","Davlat ro‘yxatining 20-30 toifasida"),
 ("«Bo‘tako‘z»","Xalq og‘zaki ijodi","14-16",""),
 ("«Kuntug‘mish»","Xalq og‘zaki ijodi","14-16","Ishqiy-qahramonlik dostoni"),
 ("«Shirin bilan Shakar»","Xalq og‘zaki ijodi","14-16","Davlat ro‘yxatida ham bor"),
 ("«Mashriqo»","Xalq og‘zaki ijodi","14-16",""),
 ("«Bozirgon»","Xalq og‘zaki ijodi","14-16",""),
 ("«Alp Er To‘nga yoki Afrosiyob jangnomasi»","Xalq og‘zaki ijodi","14-16","Eng qadimgi turkiy qahramonlik dostoni"),
 ("«Tohir va Zuhra»","Xalq og‘zaki ijodi","14-16","Papkada ertak shaklida turibdi; fojiali yakun"),
 ("«Dada Qo‘rqut hikoyalari»","Turkiy xalqlar eposi","14-16","Davlat ro‘yxatida «Qo‘rqut Ota kitobi» nomi bilan"),
 ("«Kalila va Dimna»","Hind xalq eposi","11-13","Davlat ro‘yxatida ham bor"),
 ("«Manas»","Qirg‘iz xalq eposi","14-16",""),
 ("«Masposhsho»","Qoraqalpoq xalq eposi","14-16",""),
])

YOZMA = mine([
 ("«Farhod va Shirin»","Alisher Navoiy","14-16","Papkada she'riy matni bor; nasriy bayoni ham qidiriladi"),
 ("«Layli va Majnun»","Alisher Navoiy","14-16",""),
 ("«Hayrat ul-abror» (nasriy bayon)","Alisher Navoiy","14-16","Nasriy bayoni papkada bor"),
 ("«Lison ut-tayr» (nasriy bayon)","Alisher Navoiy","14-16","Davlat ro‘yxatida ham bor; moslashtirilgan matni ham bor"),
 ("«Saddi Iskandariy» (nasriy bayon)","Alisher Navoiy","17-19","Davlat ro‘yxatining 20-30 toifasida"),
 ("«Sab'ayi sayyor»","Alisher Navoiy","17-19",""),
 ("«Qutadg‘u bilig»","Yusuf Xos Hojib","17-19","Turkiy pand-nasihat dostoni"),
 ("«Mantiq ut-tayr»","Fariduddin Attor","17-19","Navoiy «Lison ut-tayr»ining manbai"),
])

OZBEK = mine([
 ("«O‘tkan kunlar»","Abdulla Qodiriy","14-16","Siz aytgan asar. Bazada Qodiriydan bironta asar yo‘q edi"),
 ("«Mehrobdan chayon»","Abdulla Qodiriy","14-16",""),
 ("«Obid ketmon»","Abdulla Qodiriy","17-19",""),
 ("«Navoiy»","Oybek","14-16",""),
 ("«Qutlug‘ qon»","Oybek","17-19",""),
 ("«Kecha va kunduz»","Abdulhamid Cho‘lpon","17-19","Jadid adabiyotining cho‘qqisi"),
 ("«Yulduzli tunlar»","Pirimqul Qodirov","14-16","Bobur haqidagi roman"),
 ("«Ulug‘bek xazinasi»","Odil Yoqubov","14-16","Ilm va hokimiyat mavzusi"),
 ("«Diyonat»","Odil Yoqubov","17-19",""),
 ("«Ikki eshik orasi»","O‘tkir Hoshimov","17-19","Urush va taqdir mavzusi"),
 ("«Ufq» (3 kitob)","Said Ahmad","17-19","Trilogiya — bosqichma-bosqich beriladi"),
 ("«Sarob»","Abdulla Qahhor","17-19",""),
 ("«Otamdan qolgan dalalar»","Tog‘ay Murod","17-19",""),
 ("«Boburnoma» (tabdil)","Zahiriddin Muhammad Bobur","14-16","Siz so‘ragan nasriy bayoni papkada bor"),
 ("«Temur tuzuklari»","Amir Temur","14-16","Bo‘limlarga bo‘lib berish qulay"),
 ("«Turkiston qayg‘usi»","Alixonto‘ra Sog‘uniy","14-16","Siz eslatgan asar"),
])

JAHON = mine([
 ("«Robinzon Kruzoning sarguzashtlari»","Daniel Defo","11-13","Mehnat va matonat"),
 ("«Sherlok Xolms sarguzashtlari»","Artur Konan Doyl","11-13","Mantiq va kuzatuvchanlik; test tuzishga qulay"),
 ("«Shohnoma» (2 kitob)","Abulqosim Firdavsiy","14-16","Sharq eposi"),
 ("«Iliada»","Homer","14-16",""),
 ("«Odisseya»","Gomer","14-16","Sarguzasht — o‘smirga yengil kiradi"),
 ("«Uch mushketyor»","Aleksandr Dyuma","14-16","Do‘stlik va sadoqat"),
 ("«Graf Monte-Kristo» (2 kitob)","Aleksandr Dyuma","14-16",""),
 ("«Don Kixot»","Migel de Servantes","14-16",""),
 ("«Chol va dengiz»","Ernest Xeminguey","14-16","Qisqa, g‘oyasi chuqur"),
 ("«Oq kema»","Chingiz Aytmatov","14-16","Yakuni og‘ir — ota-onaga eslatma bilan"),
 ("«Ilohiy komediya»","Dante Aligyeri","17-19",""),
 ("«Martin Iden»","Jek London","17-19","O‘z ustida ishlash mavzusi"),
 ("«Hamlet»","Uilyam Shekspir","17-19","Dramaturgiya — testi boshqacha tuziladi"),
 ("«Dorian Greyning portreti»","Oskar Uayld","17-19",""),
 ("«Buyuk Getsbi»","Frensis Fitsjerald","17-19",""),
 ("«Jenni Gerxardt»","Teodor Drayzer","17-19",""),
])

RIVOJ = mine([
 ("«Atom odatlar»","Jeyms Klir","14-16","Siz misol qilib keltirgan asar"),
 ("«Muvaffaqiyatli insonlarning 7 ko‘nikmasi»","Stiven Kovi","14-16",""),
 ("«Diqqat. Chalg‘ituvchi dunyoda muvaffaqiyat sirlari»","Kel Nyuport","14-16","Telefon va e'tibor mavzusi"),
 ("«Maqsad qudrati»","Richard Leider, Devid Shapiro","14-16",""),
 ("«Pul psixologiyasi»","Morgan Hauzel","14-16","«Bola va pul»ning davomi bo‘ladi"),
 ("«G‘olib iroda»","Ali Fuad Bashgil","14-16","Iroda tarbiyasi"),
 ("«Turkiy guliston yoxud axloq»","Abdulla Avloniy","14-16","Milliy axloq darsligi"),
 ("«Qobusnoma»","Kaykovus","14-16","Davlat ro‘yxatida ham bor"),
 ("«Do‘stlar orttirish va odamlarga ta'sir o‘tkazish xususida»","Deyl Karnegi","14-16","Muomala ko‘nikmasi"),
 ("«Raqamlar uchun yaralgan idrok»","Barbara Oukli","14-16","Qanday o‘qish va o‘rganish kerakligi — o‘quvchiga aynan mos"),
 ("«Samaradorlikning yigirma bir yo‘li»","Brayan Treysi","14-16","Vaqtni boshqarish"),
 ("«Guliston»","Sa'diy Sheroziy","14-16","Sharq pand-nasihati"),
 ("«Xavotirlanishni bas qilish va yashay boshlash yo‘llari»","Deyl Karnegi","17-19","Imtihon va kelajak xavotiri"),
 ("«Hayot uchun 12 qoida»","Jordan Piterson","17-19","Mas'uliyat va tartib"),
 ("«Ego — dushmaning»","Rayan Holidey","17-19","Kibr va muvaffaqiyat"),
 ("«Zukkolar va landavurlar»","Malkolm Gladuell","17-19","Muvaffaqiyat qanday shakllanadi"),
 ("«Factfulness»","Hans Rosling","17-19","Dunyoni raqamlar bilan to‘g‘ri ko‘rish"),
 ("«O‘zlikni qayta kashf etish»","Jon Gardner","17-19",""),
])

DINIY = mine([
 ("«Ijtimoiy odoblar»","Shayx Muhammad Sodiq Muhammad Yusuf","14-16","Siz aytgan kitob"),
 ("«Odoblar xazinasi» (4 juz)","Shayx Muhammad Sodiq Muhammad Yusuf","14-16","Juzlarga bo‘lingan — bosqichma-bosqich beriladi"),
 ("«Keksalarni e'zozlash»","Shayx Muhammad Sodiq Muhammad Yusuf","14-16","Qisqa risola — boshlash uchun qulay"),
 ("«Yolg‘on»","Shayx Muhammad Sodiq Muhammad Yusuf","14-16","Qisqa risola"),
 ("«Isrof»","Shayx Muhammad Sodiq Muhammad Yusuf","14-16","Qisqa risola"),
 ("«Yaxshilik va silai rahm» (2 juz)","Shayx Muhammad Sodiq Muhammad Yusuf","14-16",""),
 ("«Iymon»","Shayx Muhammad Sodiq Muhammad Yusuf","14-16","Aqida asoslari"),
 ("«101 ulug‘ sahobiy»","Moturidiy markazi","14-16","Qissalar shaklida — bolaga yengil kiradi"),
 ("«Imom Buxoriydan qirq hadis»","Moturidiy markazi","14-16",""),
 ("«Buyuk ajdodlarimiz»","Mualliflar jamoasi","14-16","Vatan tarixi bilan bog‘lanadi"),
 ("«Halol nima-yu, harom nima»","Tohir Malik","14-16","O‘smirga tushunarli tilda"),
 ("«Internet fiqhi»","Nuriddin Yildiz","14-16","Bugungi o‘smirning ayni muammosi"),
 ("«Ruhiy tarbiya» (3 juz)","Shayx Muhammad Sodiq Muhammad Yusuf","14-16",""),
 ("«Islom tarixi» (2 kitob)","Shayx Muhammad Sodiq Muhammad Yusuf","14-16",""),
 ("«Hadis va Hayot» (1-juz)","Shayx Muhammad Sodiq Muhammad Yusuf","14-16","22 juzdan iborat — birinchisidan boshlanadi"),
 ("«Qulog‘im senda, qizim»","Abdulloh Abdulmu'tiy","14-16","Qizlar uchun"),
 ("«Bu ummatning qizi»","Nuriddin Yildiz","14-16","Qizlar uchun"),
 ("«Tarixi Muhammadiy»","Alixonto‘ra Sog‘uniy","14-16","Siz aytgan kitob. Papkada yo‘q, saytda bor — faylini alohida berasiz"),
 ("«Sunniy aqiydalar»","Shayx Muhammad Sodiq Muhammad Yusuf","14-16","Siz aytgan kitob"),
 ("«Baxtiyor oila»","Shayx Muhammad Sodiq Muhammad Yusuf","17-19","Siz aytgan kitob"),
 ("«Mo‘minning me'roji»","Shayx Muhammad Sodiq Muhammad Yusuf","17-19","Namoz haqida"),
 ("«Mukammal saodat yo‘li»","Shayx Muhammad Sodiq Muhammad Yusuf","17-19",""),
 ("«Islomda Vatan tushunchasi»","Muftiy Nuriddin Xoliqnazarov","17-19",""),
 ("«Biz bilgan va bilmagan Imom Moturidiy»","So‘nmas Qutlug‘","17-19",""),
])

SECTIONS = [
 ("Davlat tanlovi · 10-14 yosh", G1),
 ("Davlat tanlovi · 15-19 yosh", G2),
 ("Xalq dostonlari va eposlar", DOST),
 ("Navoiy va Sharq dostonlari", YOZMA),
 ("O‘zbek klassikasi", OZBEK),
 ("Jahon klassikasi", JAHON),
 ("Shaxsiy rivojlanish", RIVOJ),
 ("Diniy-ma'rifiy", DINIY),
]
if __name__ == '__main__':
    jami = sum(len(r) for _, r in SECTIONS)
    tay = sum(1 for _, r in SECTIONS for x in r if x[3])
    print('JAMI', jami, 'PAPKADA', tay, 'YO‘Q', jami - tay)
    for nom, r in SECTIONS:
        print(f'{nom:34s} {len(r):3d}  papkada {sum(1 for x in r if x[3]):3d}')
        for x in r:
            if not x[3]: print('      yo‘q:', x[0], '|', x[1])
