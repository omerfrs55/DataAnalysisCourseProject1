import datetime # tarih verileri için
from flask import render_template, request, redirect, url_for, flash, jsonify
# render_template: spesifik bir sayfayı ekrana basma
# request: kullanıcı verisini yakalama
# redirect: yönlendirme
# url_for: adres defteri, fonksiyon adından url üretme
# flash: uyarı mesajı
# jsonify: dictionary'leri json formatına çevirme
from flask_login import login_user, logout_user, current_user # kullanıcı işlemleri için

from scripts.data import db, User, PurchaseLog


# Giriş yapan kullanıcıyı ID'sinden tanıma
def load_user(user_id):

    return User.query.get(int(user_id))


# Kayıt fonksiyonu
def register():
    if request.method == "POST":
        try:
            b_date = datetime.datetime.strptime(
                request.form.get("birth_date"), "%Y-%m-%d"
            ).date()
            user = User(
                username=request.form.get("username"),
                gender=request.form.get("gender"),
                birth_date=b_date,
                education=request.form.get("education"),
                city=request.form.get("city"),
                job=request.form.get("job"),
            )
            user.set_password(request.form.get("password"))
            if User.query.count() == 0:
                user.is_admin = True
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("index"))
        except:
            flash("Hata oluştu", "danger")

    return render_template("register.html")


# Giriş Yapma fonksiyonu
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username")).first()
        if user and user.check_password(request.form.get("password")):
            login_user(user, remember=True)
            return redirect(url_for("index"))
        flash("Hatalı giriş", "danger")

    return render_template("login.html")


# Çıkış yapma fonksiyonu
def logout():
    logout_user()

    return redirect(url_for("index"))


# O kullanıcının alım yapmasını sağlayan fonksiyon
def buy_now():
    data = request.json
    db.session.add(
        PurchaseLog(
            user_id=current_user.id,
            product_id=data["product_id"],
            selected_color=data["color"],
        )
    )
    db.session.commit()

    return jsonify({"success": True, "message": f'{data["color"]} rengi satın alındı.'})
