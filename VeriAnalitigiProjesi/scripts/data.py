from flask_sqlalchemy import SQLAlchemy # python ile pythonic olarak veritabanı ile iletişim yapabilmek için
from flask_login import UserMixin # şablon, Flash-Login kütüphanesinin ihtiyacı
from werkzeug.security import generate_password_hash, check_password_hash # hash işlemleri için
import datetime # tarih verileri için

db = SQLAlchemy()

COLOR_CODES = {
    "Siyah": "000000",
    "Beyaz": "F5F5F5",
    "Mavi": "0000FF",
    "Kırmızı": "FF0000",
    "Yeşil": "008000",
}

# Verilerin Tutulduğu Sınıf Yapıları


# Kullanıcı detayları
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    gender = db.Column(db.String(10))
    birth_date = db.Column(db.Date)
    education = db.Column(db.String(50))
    city = db.Column(db.String(50))
    job = db.Column(db.String(50))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):

        return check_password_hash(self.password_hash, password)

    # yaş verisini doğum tarihine göre alıyoruz
    @property
    def age(self):
        if not self.birth_date:
            return 25
        today = datetime.date.today()
        b_date = self.birth_date
        if isinstance(b_date, str):
            try:
                b_date = datetime.datetime.strptime(b_date, "%Y-%m-%d").date()
            except:
                try:
                    b_date = datetime.datetime.strptime(
                        b_date, "%Y-%m-%d %H:%M:%S.%f"
                    ).date()
                except:

                    return 25

        return (
            today.year
            - b_date.year
            - ((today.month, today.day) < (b_date.month, b_date.day))
        )


# Ürün bilgileri
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)


# Ürün sayfasına tıklanma verileri
class ClickLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship("User", backref="clicks")
    product = db.relationship("Product", backref="clicks")


# Ürün alım verileri
class PurchaseLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    selected_color = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship("User", backref="purchases")
    product = db.relationship("Product", backref="purchases")
