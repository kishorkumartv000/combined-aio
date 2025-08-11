class TR(object):
    __language__ = 'tr'
#----------------
#
# TEMEL
#
#----------------
    WELCOME_MSG = "Merhaba {}"
    DOWNLOADING = 'İndiriliyor........'
    DOWNLOAD_PROGRESS = """
<b>╭─ İlerleme
│
├ {0}
│
├ Tamamlandı : <code>{1} / {2}</code>
│
├ Başlık : <code>{3}</code>
│
╰─ Tür : <code>{4}</code></b>
"""
    UPLOADING = 'Yükleniyor........'
    ZIPPING = 'Arşivleniyor........'
    TASK_COMPLETED = "İndirme Tamamlandı"

#----------------
#
# AYARLAR PANELİ
#
#----------------
    INIT_SETTINGS_PANEL = '<b>Bot Ayarlarına Hoş Geldiniz</b>'
    LANGUAGE_PANEL = 'Buradan bot dilini seçin'
    CORE_PANEL = 'Ana ayarları buradan düzenleyin'
    PROVIDERS_PANEL = 'Her platformu ayrı ayrı yapılandırın'

    

    TELEGRAM_PANEL = """
<b>Telegram Ayarları</b>

Yöneticiler : {2}
Yetkili Kullanıcılar : {3}
Yetkili Sohbetler : {4}
"""
    BAN_AUTH_FORMAT = '/komut {userid} kullanın'
    BAN_ID = 'Banı kaldırıldı: {}'
    USER_DOEST_EXIST = "Bu ID mevcut değil"
    USER_EXIST = 'Bu ID zaten mevcut'
    AUTH_ID = 'Başarıyla Yetkilendirildi'

#----------------
#
# DÜĞMELER
#
#----------------
    MAIN_MENU_BUTTON = 'ANA MENÜ'
    CLOSE_BUTTON = 'KAPAT'
    PROVIDERS = 'HİZMETLER'
    TELEGRAM = 'Telegram'
    CORE = 'ÇEKİRDEK'
    


    BOT_PUBLIC = 'Bot Herkese Açık - {}'
    BOT_LANGUAGE = 'Dil'
    ANTI_SPAM = 'Spam Koruması - {}'
    LANGUAGE = 'Dil'
    QUALITY = 'Kalite'
    AUTHORIZATION = "Yetkilendirmeler"

    POST_ART_BUT = "Posterleri Gönder : {}"
    SORT_PLAYLIST = 'Çalma Listesini Sırala : {}'
    DISABLE_SORT_LINK = 'Sıralama Bağlantısını Devre Dışı Bırak : {}'
    PLAYLIST_CONC_BUT = "Çalma Listesi Toplu İndirme : {}"
    PLAYLIST_ZIP = 'Çalma Listesi Arşivle : {}'
    ARTIST_BATCH_BUT = 'Sanatçı Toplu Yükle : {}'
    ARTIST_ZIP = 'Sanatçı Arşivle : {}'
    ALBUM_ZIP = 'Albüm Arşivle : {}'





    RCLONE_LINK = 'Doğrudan Bağlantı'
    INDEX_LINK = 'Dizin Bağlantısı'

#----------------
#
# HATALAR
#
#----------------
    ERR_NO_LINK = 'Bağlantı bulunamadı :('
    ERR_LINK_RECOGNITION = "Üzgünüm, verilen bağlantı tanınamadı."



#----------------
#
# UYARILAR
#
#----------------


#----------------
#
# PARÇA & ALBÜM PAYLAŞIMLARI
#
#----------------
    ALBUM_TEMPLATE = """
🎶 <b>Başlık :</b> {title}
👤 <b>Sanatçı :</b> {artist}
📅 <b>Çıkış Tarihi :</b> {date}
🔢 <b>Toplam Parça :</b> {totaltracks}
📀 <b>Toplam Albüm :</b> {totalvolume}
💫 <b>Kalite :</b> {quality}
📡 <b>Sağlayıcı :</b> {provider}
🔞 <b>Açık İçerik :</b> {explicit}
"""

    PLAYLIST_TEMPLATE = """
🎶 <b>Başlık :</b> {title}
🔢 <b>Toplam Parça :</b> {totaltracks}
💫 <b>Kalite :</b> {quality}
📡 <b>Sağlayıcı :</b> {provider}
"""

    SIMPLE_TITLE = """
Adı : {0}
Türü : {1}
Sağlayıcı : {2}
"""

    ARTIST_TEMPLATE = """
👤 <b>Sanatçı :</b> {artist}
💫 <b>Kalite :</b> {quality}
📡 <b>Sağlayıcı :</b> {provider}
"""
