from flask import render_template, request # belirli html dosyasında dosyanın beklediği parametreleri doldurmak için
from flask_login import current_user  # o an sitedeki kişi kim
from sqlalchemy import func, desc, or_

# func: sql fonksiyonları için
# desc: alfabetik ters sıralama için
# or_: mantıksal veya
from collections import Counter  # sayaç
import datetime  # tarih verileri için
import statistics  # istatistiksel matematik kütüphanesi, outlier analizi vb. için

from scripts.data import db, Product, ClickLog, PurchaseLog, User, COLOR_CODES

ALL_COLORS = list(COLOR_CODES.keys())


# Ana Sayfa
def index():
    # url üzerinden (var ise) verileri okuyarak filtrelendirme/sıralama
    q = request.args.get("q", "")
    category = request.args.get("category", "")
    sort = request.args.get("sort", "")

    # query default olarak en popüleri sıralıyor
    # eğer bir filtreleme ayarı girildiyse ileride değişecek
    query = db.session.query(Product).outerjoin(ClickLog).group_by(Product.id)

    # arama kutusuna bir şey yazıldı mı
    if q:
        query = query.filter(
            or_(Product.name.ilike(f"%{q}%"), Product.category.ilike(f"%{q}%"))
        )
    # kategori seçildi mi
    if category:
        query = query.filter(Product.category == category)

    # sıralama A'dan Z'ye mi
    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    # sıralama Z'den A'ya mı
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    # sıralama yoksa tıklanma verisine göre sırala
    else:
        query = query.order_by(func.count(ClickLog.id).desc())

    # sorguyu çalıştır, verileri çek ve işle
    products = query.all()
    prod_list = []
    for p in products:
        img = f"https://placehold.co/400x400/2c3e50/FFFFFF/png?text={p.name.replace(' ', '+')}"
        prod_list.append({"obj": p, "img": img})

    # sidebar da göstermek için veritabanında bulunan kategorileri tekrar etmeyecek şekilde çekiyoruz
    categories = [c[0] for c in db.session.query(Product.category).distinct()]

    # filtreleri de gönderiyoruz ki sayfa yenilendiğinde girdiği parametreler kaybolmasın
    return render_template(
        "index.html",
        products=prod_list,
        categories=categories,
        current_filters={"q": q, "category": category, "sort": sort},
    )


# Ürün Sayfası
def product_detail(product_id):
    # ürünün verilerini alma
    product = Product.query.get_or_404(product_id)
    # default seçili renk
    selected_color = request.args.get("color", "Siyah")

    # kullanıcı loginyapmış mı
    if current_user.is_authenticated:
        db.session.add(ClickLog(user_id=current_user.id, product_id=product.id))
        db.session.commit()

    # ürünün tüm satış verilerini alıyoruz, OUTLIER ANALİZİ İÇİN BU GEREKLİ
    purchases_list = PurchaseLog.query.filter_by(product_id=product.id).all()
    
    # default olarak temizlenmiş satış sayısı tüm satışlar olsun
    clean_purchases_count = len(purchases_list)
    prod_outlier_data = {"labels": [], "data": [], "clean_data": []}

    # kullanıcı admin mi kontrolü
    if current_user.is_authenticated and current_user.is_admin:
        try:
            # ürünün satışlarını gün gün alıyoruz
            date_map = {}
            for p in purchases_list:
                d_str = p.timestamp.strftime("%Y-%m-%d")
                if d_str not in date_map:
                    date_map[d_str] = []
                date_map[d_str].append(p.user_id)

            # ürün verisi varsa
            if date_map:
                # tarih ve satın alma verilerini hazırlama
                sorted_dates = sorted(date_map.keys())
                counts = [len(date_map[d]) for d in sorted_dates]

                # günlük ortalama kaç satıyoruz
                mean = statistics.mean(counts)  # mean
                # satışlar ne kadar dalgalı
                stdev = statistics.stdev(counts)  # standart sapma

                # anormallik sınırı
                threshold = mean + (2 * stdev)

                prod_outlier_data["labels"] = sorted_dates
                prod_outlier_data["data"] = counts

                outliers_arr = []
                clean_arr = []

                # her günü kontrol ediyoruz
                # eğer o günkü satış anormallik sınırını aşarsa;
                # o gün alışveriş yapanları alır, en çok alışveriş yapanı (Whale) bulur
                # onu toplam satıştan çıkartır, optimize grafik elimizde olur
                whale_total_removed = 0 # Balinanın toplam alım miktarı
                for i, c in enumerate(counts):
                    if c > threshold:
                        users_on_day = date_map[sorted_dates[i]]
                        user_counts = Counter(users_on_day)
                        whale_qty = user_counts.most_common(1)[0][1]

                        # sadece toplam satış yetmez, balina alımı da ortalamanın 2 katından büyükse outlier say
                        if whale_qty > (mean * 2):
                            outliers_arr.append(c)
                            clean_arr.append(c - whale_qty)
                            whale_total_removed += whale_qty # Balina alımını toplama ekle
                        else:
                            outliers_arr.append(None)
                            clean_arr.append(c)
                    else:
                        outliers_arr.append(None)
                        clean_arr.append(c)

                prod_outlier_data["outliers"] = outliers_arr
                prod_outlier_data["clean_data"] = clean_arr
                
                # temizlenmiş satış sayısı hesaplama başlangıcı
                clean_purchases_count = len(purchases_list) - whale_total_removed


        except Exception as e:
            print(f"Prod Detail Chart Error: {e}")

    # ürünle alakalı bilgileri alma
    clicks = ClickLog.query.filter_by(product_id=product.id).count()
    # purchases = PurchaseLog.query.filter_by(product_id=product.id).count() # ESKİ SATIR
    
    # DÜZELTME: Dönüşüm oranı için temizlenmiş satış sayısını kullanıyoruz (clean_purchases_count)
    purchases = clean_purchases_count # Yeni temizlenmiş satış sayısı
    # DÜZELTME: Bu sayede Conversion Rate %100'ün üstüne çıkmaz.
    rate = round((purchases / clicks) * 100, 2) if clicks > 0 else 0

    stats = {"clicks": clicks, "purchases": purchases, "rate": rate}

    # ürünün resmini oluşturma
    hex_code = COLOR_CODES.get(selected_color, "000000")
    text_c = "000000" if selected_color == "Beyaz" else "FFFFFF"
    dynamic_img = f"https://placehold.co/500x500/{hex_code}/{text_c}/png?text={product.name.replace(' ', '+')}+({selected_color})"

    # ürün renk tercih verilerini alma
    # Bu listeyi zaten başta almıştık, tekrar almayalım, var olanı kullanalım: purchases_list
    color_dist = {c: 0 for c in ALL_COLORS}
    for p in purchases_list:
        if p.selected_color in color_dist:
            color_dist[p.selected_color] += 1
            
    # gerekli parametreleri ürün sayfasına yönlendirir
    return render_template(
        "product.html",
        product=product,
        current_image=dynamic_img,
        selected_color=selected_color,
        colors=ALL_COLORS,
        color_dist=color_dist,
        prod_outlier_data=prod_outlier_data,
        stats=stats,
    )


# Yönetici Paneli Sayfası
def admin_dashboard():
    # kullanıcı admin mi kontrolu
    if not current_user.is_admin:
        return "Yetkisiz", 403

    default_data = {
        "pop_data": {"labels": [], "clicks": [], "purchases": []},
        "gender_data": {"labels": [], "data": []},
        "segment_gender_data": {"labels": [], "male": [], "female": [], "avg_age": []},
        "segment_cat_data": {"labels": [], "datasets": []},
        "outlier_data": {
            "labels": [],
            "data": [],
            "outliers": [],
            "clean_data": [],
            "details": [],
        },
    }

    try:
        # veri tabanındaki tüm satışları al
        all_purchases = db.session.query(PurchaseLog).all()

        # her satışı tek tek ait olduğu güne göre dictionary yapısına yaz
        daily_stats = {}
        for p in all_purchases:
            d_str = p.timestamp.strftime("%Y-%m-%d")
            if d_str not in daily_stats:
                daily_stats[d_str] = {
                    "total": 0,
                    "users": Counter(),
                    "products": Counter(),
                }

            daily_stats[d_str]["total"] += 1
            daily_stats[d_str]["users"][p.user_id] += 1
            daily_stats[d_str]["products"][p.product.name] += 1

        # "Whale" kullanıcıların kara listesi, sayfadaki diğer grafiklerin doğru veri gösterebilmesi için
        whale_blacklist = set()

        outlier_data = {
            "labels": [],
            "data": [],
            "outliers": [],
            "clean_data": [],
            "details": [],
        }
        sorted_dates = sorted(daily_stats.keys())
        counts = [daily_stats[d]["total"] for d in sorted_dates]

        # mean ve standart sapma hesaplama
        if len(counts) > 1:
            mean = statistics.mean(counts)
            stdev = statistics.stdev(counts)
        else:
            mean = counts[0]
            stdev = 0

        # anormallik sınırı
        threshold = mean + (2 * stdev) if stdev > 0 else mean + 10

        outliers_arr = []
        details_list = []

        # temiz grafik verisini bulundurmak için
        clean_arr = []

        # her günü işle
        for i, d in enumerate(sorted_dates):
            total = daily_stats[d]["total"]

            # eğer o gün anormallik sınırı aşılmış ise;
            # o gün en çok alım yapan kullanıcıyı (Whale) bul, kara listeye ekle
            if total > threshold:
                outliers_arr.append(total)
                user_counts = daily_stats[d]["users"]
                whale_user_id, whale_qty = user_counts.most_common(1)[0]
                whale_blacklist.add((whale_user_id, d))

                cleaned_val = total - whale_qty
                clean_arr.append(cleaned_val)

                top_prod_name = daily_stats[d]["products"].most_common(1)[0][0]
                prod_obj = Product.query.filter_by(name=top_prod_name).first()

                details_list.append(
                    {
                        "date": d,
                        "total_sales": total,
                        "outlier_qty": whale_qty,
                        "prod_name": top_prod_name,
                        "prod_id": prod_obj.id if prod_obj else 0,
                        "category": prod_obj.category if prod_obj else "Genel",
                    }
                )
            # aşılmamış ise olduğu gibi devam et
            else:
                outliers_arr.append(None)
                clean_arr.append(total)

            # outlier verilerini hazırla
            outlier_data["labels"] = sorted_dates
            outlier_data["data"] = counts
            outlier_data["outliers"] = outliers_arr
            outlier_data["clean_data"] = clean_arr
            outlier_data["details"] = details_list

        # "Whale" alımları grafikten temizleme
        clean_purchases = []
        for p in all_purchases:
            d_str = p.timestamp.strftime("%Y-%m-%d")
            if (p.user_id, d_str) in whale_blacklist:
                continue
            clean_purchases.append(p)

        # Popüler Ürünler Grafiği

        # tıklanma sayısına göre ilk 10 ürünü getir
        top_prods = (
            db.session.query(Product, func.count(ClickLog.id).label("clicks"))
            .outerjoin(ClickLog)
            .group_by(Product.id)
            .order_by(desc("clicks"))
            .limit(10)
            .all()
        )

        pop_data = {"labels": [], "clicks": [], "purchases": []}
        for p_obj, c in top_prods:
            # "Whale" den arınmış temiz veriler içerisinden say
            clean_count = sum(1 for cp in clean_purchases if cp.product_id == p_obj.id)

            pop_data["labels"].append(p_obj.name)
            pop_data["clicks"].append(c)
            pop_data["purchases"].append(clean_count)

        # Cinsiyet Dağılımı Grafiği

        # veri tabanında kaç erkek kaç kadın var say (admin dışı)
        gender_stats = (
            db.session.query(User.gender, func.count(User.id))
            .filter(User.username != "admin")
            .group_by(User.gender)
            .all()
        )

        g_map = {"E": 0, "K": 0}
        for g, c in gender_stats:
            if g in g_map:
                g_map[g] = c
        gender_data = {"labels": ["Erkek", "Kadın"], "data": [g_map["E"], g_map["K"]]}

        # Müşteri Segmentasyonu Grafiği (Şehir / Meslek)

        # Her temiz satışı alıp, müşterinin bilgilerine göre anahtar oluşturuyoruz
        # o grupta kaç erkek kaç kadın var
        segments = {}
        for cp in clean_purchases:
            u = cp.user
            if not u:

                continue

            key = f"{u.city} - {u.job}"
            if key not in segments:
                segments[key] = {"E": 0, "K": 0, "ages": []}

            segments[key][u.gender] += 1
            segments[key]["ages"].append(u.age)

        # en çok hacmi olan ilk 15 grubu seçiyoruz
        sorted_segments = sorted(
            segments.items(), key=lambda item: item[1]["E"] + item[1]["K"], reverse=True
        )[:15]

        segment_gender_data = {"labels": [], "male": [], "female": [], "avg_age": []}
        for key, val in sorted_segments:
            segment_gender_data["labels"].append(key)
            segment_gender_data["male"].append(val["E"])
            segment_gender_data["female"].append(val["K"])
            avg = round(sum(val["ages"]) / len(val["ages"]), 1) if val["ages"] else 0
            segment_gender_data["avg_age"].append(avg)

        # Kategori Tercihleri Grafiği (Şehir / Meslek)

        # kategoriye göre veri seti hazırlıyoruz,
        cat_segments = {}
        all_categories = set()
        for cp in clean_purchases:
            if not cp.product:
                continue
            key = f"{cp.user.city} - {cp.user.job}"
            cat = cp.product.category
            if key not in cat_segments:
                cat_segments[key] = {}
            if cat not in cat_segments[key]:
                cat_segments[key][cat] = 0
            cat_segments[key][cat] += 1
            all_categories.add(cat)

        all_categories = sorted(list(all_categories))
        seg_labels = segment_gender_data["labels"]
        segment_cat_data = {"labels": seg_labels, "datasets": []}

        for cat in all_categories:
            data_points = []
            for label in seg_labels:
                val = cat_segments.get(label, {}).get(cat, 0)
                data_points.append(val)
            segment_cat_data["datasets"].append({"label": cat, "data": data_points})

    except Exception as e:
        print(f"DASHBOARD ERROR: {e}")
        import traceback

        traceback.print_exc()
        return render_template("dashboard.html", **default_data)

    # gerekli parametreleri panel grafik sayfasına yönlendirir
    return render_template(
        "dashboard.html",
        pop_data=pop_data,
        gender_data=gender_data,
        segment_gender_data=segment_gender_data,
        segment_cat_data=segment_cat_data,
        outlier_data=outlier_data,
    )
