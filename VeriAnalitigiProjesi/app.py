import random # rastgelelik gerektiren işlemler için
import datetime # tarih verileri için
from flask import Flask # ana web server kütüphanesi
from flask_login import LoginManager, login_required # login işlemleri ve loginsiz yapılamayacak işlemler için
from werkzeug.security import generate_password_hash # şifreyi veri tabanına hashleyerek saklama, güvenlik

# Kendi yazdığımız modüller
from scripts.data import db, User, Product, ClickLog, PurchaseLog, COLOR_CODES
import scripts.user_man as user_man
import scripts.data_man as data_man

app = Flask(__name__) # bu dosya kök dosya
app.config["SECRET_KEY"] = "cok-gizli-anahtar-final-v10" # cookie
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///proje.db" # veritabanı yolu
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False # gereksiz uyarıları kapama

# Veritabanını uygulamaya bağlıyoruz
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


# Giriş yapan kullanıcıyı ID'sinden tanıma
@login_manager.user_loader
def load_user(user_id):
    return user_man.load_user(user_id)


# Ana Sayfa


# ürünleri belirtilen kategoriye, aramaya ya da sıralama isteğine göre veritabanından ilgili verileri çekiyor.
# popülerliğe göre sıralamda ClickLog tablo verisi kullanılıyor
@app.route("/")
def index():
    return data_man.index()


# Ürün Sayfası


# Kullanıcı sayfaya girdiği an ClickLog kaydı atar
# Ürünün renk seçim grafiklerini sunar
# Ürünün son 1 aylık alım grafiğini outlier analizi ve analiz sonucu optimize edilmiş grafikleri sunar.
@app.route("/product/<int:product_id>")
def product_detail(product_id):
    return data_man.product_detail(product_id)


# Satın Alma İşlemi


# Hızlı satın alma
# X ürününü Y renkte satın aldı
@app.route("/buy_now", methods=["POST"])
@login_required
def buy_now():
    return user_man.buy_now()


# Yönetici Paneli


# Tüm verileri harmanlar, popüler ürünlerin tıklanma-alımı, kullanıcı cinsiyet dağılımı, şehir-meslek-kategori bazlı segmentasyon
# Global Outlier Analizi, son 30 güne bakar, standart sapmanın 2 katından fazla satış olan günleri,
# ardından o günkü anomaliye sebep olan "Whale" müşteriyi bulur ve temizleyip raporlar
# Outlier analizi ile temizlediği verileri kullanarak segment1 ve segment2 grafiklerini de ona göre oluşturur. whale_blacklist{}
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    return data_man.admin_dashboard()


# Yetkilendirme Fonksiyonları


# Klasik giriş çıkış ve kayıt işlemleri
@app.route("/register", methods=["GET", "POST"])
def register():
    return user_man.register()


@app.route("/login", methods=["GET", "POST"])
def login():
    return user_man.login()


@app.route("/logout")
def logout():
    return user_man.logout()


# Veri Oluşturma Fonksiyonu


# Eski veri tabanını silip sıfırdan kurar
# Sahte trafik yaratır
# Her güne normal satış yaptırır
# Bilerek Outlier çıkartacak şekilde "Whale" anormal verisi oluşturur,
# bu sayede analiz tarafında inceleyebilelim
@app.cli.command("init-db")
def init_db():
    db.drop_all()  # tabloları temizle
    db.create_all()  # tabloları yeniden oluştur

    # Statik ürün verilerini ekleme
    print("1. Ürünler Ekleniyor...")

    names = [
        ("iPhone 15", "Elektronik", 50000),
        ("MacBook Air", "Elektronik", 45000),
        ("iPad Pro", "Elektronik", 35000),
        ("Sony Kulaklık", "Elektronik", 9000),
        ("Oyun PC", "Elektronik", 60000),
        ("Samsung S24", "Elektronik", 55000),
        ("Yazlık Elbise", "Giyim", 900),
        ("Kot Ceket", "Giyim", 1200),
        ("Keten Pantolon", "Giyim", 800),
        ("İpek Şal", "Giyim", 600),
        ("Deri Mont", "Giyim", 4000),
        ("Spor Tayt", "Giyim", 500),
        ("Nike Air", "Ayakkabı", 4500),
        ("Adidas Superstar", "Ayakkabı", 3800),
        ("Topuklu Ayakkabı", "Ayakkabı", 1500),
        ("Bot", "Ayakkabı", 2000),
        ("Koşu Ayakkabısı", "Ayakkabı", 3000),
        ("Kahve Makinesi", "Ev", 5000),
        ("Robot Süpürge", "Ev", 15000),
        ("Kitaplık", "Ev", 2500),
        ("Çalışma Masası", "Ev", 3500),
    ]

    for n, c, p in names:
        db.session.add(Product(name=n, category=c, price=p))
    db.session.commit()

    # admin kullanıcısı statik olmak üzere "usercount" kadar rastgele verilere sahip kullanıcı oluştur
    usercount = 200
    print("2. Kullanıcılar Ekleniyor...")
    db.session.add(
        User(
            username="admin",
            gender="E",
            birth_date=datetime.date(1990, 1, 1),
            education="Yuksek",
            city="İstanbul",
            job="Yönetici",
            is_admin=True,
            password_hash=generate_password_hash("123"),
        )
    )

    jobs = {
        "Lise": ["Öğrenci", "Garson", "Kasiyer"],
        "Lisans": ["Mühendis", "Öğretmen", "Yazılımcı"],
        "Yuksek": ["Doktor", "Avukat", "Akademisyen"],
    }

    cities = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya"]

    users = []
    for i in range(usercount):  # usercount
        edu = random.choice(list(jobs.keys()))
        u = User(
            username=f"user{i}",
            gender=random.choice(["E", "K"]),
            birth_date=datetime.date(random.randint(1980, 2005), 1, 1),
            education=edu,
            city=random.choice(cities),
            job=random.choice(jobs[edu]),
        )
        u.set_password("123")
        users.append(u)
    db.session.add_all(users)
    db.session.commit()

    # son 30 gün için "outliercount" kadar outlier değeri oluşturur
    outliercount = 2
    print("3. VERİ SİMÜLASYONU BAŞLIYOR (NORMAL + OUTLIER)...")
    prods = Product.query.all()
    all_users = User.query.filter(User.username != "admin").all()

    colors = list(COLOR_CODES.keys())

    products_by_cat = {}
    for p in prods:
        if p.category not in products_by_cat:
            products_by_cat[p.category] = []
        products_by_cat[p.category].append(p)

    today = datetime.datetime.utcnow()

    # outlier günleri oluşturma
    days_range = list(range(1, 29))
    outlier_deltas = random.sample(days_range, outliercount)  # outliercount
    outlier_dates = [
        (today - datetime.timedelta(days=d)).strftime("%Y-%m-%d")
        for d in outlier_deltas
    ]
    print(f"Outlier Günleri: {outlier_dates}")

    bulk_purchases = []
    bulk_clicks = []

    # bugünden itibaren 30 gün geriye kadar sayar
    for delta in range(30):
        current_date = today - datetime.timedelta(days=delta)
        date_str = current_date.strftime("%Y-%m-%d")

        # siteyi ziyaret edecek kişilerin sayısı "minvis" ve "maxvis" değerlerine bağlı
        minvis = 10
        maxvis = 40
        daily_active_users_count = random.randint(minvis, maxvis)  # minvis maxvis
        daily_users = random.sample(all_users, daily_active_users_count)

        # seçilen her kullanıcı için o gün 3 farklı ürünle etkileşime girer
        # ürünün alım miktarı "minqty" ve "maxqty" değişkenlerine göre değişir
        minqty = 1
        maxqty = 3
        for u in daily_users:
            selected_prods = random.sample(prods, 3)

            for p in selected_prods:
                qty = random.randint(minqty, maxqty)  # minqty maxqty

                # ürünün tıklanma miktarını da "minclick" ve "maxclick" değerleri üzerinden hesaplıyoruz
                minclick = 1
                maxclick = 5
                click_count = random.randint(minclick, maxclick)
                for _ in range(click_count):
                    bulk_clicks.append(
                        ClickLog(user_id=u.id, product_id=p.id, timestamp=current_date)
                    )

                for _ in range(qty):
                    bulk_purchases.append(
                        PurchaseLog(
                            user_id=u.id,
                            product_id=p.id,
                            selected_color=random.choice(colors),
                            timestamp=current_date,
                        )
                    )

        # seçilmiş outlier günü ise;
        # o gün rastgele bir kullanıcı tek bir üründen "outlmin" ve "outlmax" değerlerine göre alım yapsın
        outlmin = 200
        outlmax = 500
        if date_str in outlier_dates:
            whale_user = random.choice(all_users)
            whale_product = random.choice(prods)

            whale_qty = random.randint(outlmin, outlmax)  # outlmin outlmax
            print(
                f"!!! OUTLIER: {date_str} - {whale_user.username} - {whale_product.name} - {whale_qty} adet"
            )

            for _ in range(whale_qty):
                bulk_purchases.append(
                    PurchaseLog(
                        user_id=whale_user.id,
                        product_id=whale_product.id,
                        selected_color=random.choice(colors),
                        timestamp=current_date,
                    )
                )

    print("Veriler kaydediliyor (Biraz sürebilir)...")
    db.session.bulk_save_objects(bulk_clicks)
    db.session.bulk_save_objects(bulk_purchases)
    db.session.commit()
    print("BİTTİ. Veritabanı hazır.")


if __name__ == "__main__":
    app.run(debug=True)
