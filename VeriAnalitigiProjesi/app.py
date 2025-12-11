import os
import random
import datetime
import statistics
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, desc, or_

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cok-gizli-anahtar-final-v10'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///proje.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELLER ---
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
    
    @property
    def age(self):
        if not self.birth_date: return 25 
        today = datetime.date.today()
        b_date = self.birth_date
        if isinstance(b_date, str):
            try: b_date = datetime.datetime.strptime(b_date, '%Y-%m-%d').date()
            except:
                try: b_date = datetime.datetime.strptime(b_date, '%Y-%m-%d %H:%M:%S.%f').date()
                except: return 25
        return today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)

class ClickLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship('User', backref='clicks')
    product = db.relationship('Product', backref='clicks')

class PurchaseLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    selected_color = db.Column(db.String(50)) 
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship('User', backref='purchases')
    product = db.relationship('Product', backref='purchases')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_cart_count():
    return dict(cart_item_count=0)

COLOR_CODES = {'Siyah': '000000', 'Beyaz': 'F5F5F5', 'Mavi': '0000FF', 'Kırmızı': 'FF0000', 'Yeşil': '008000'}
ALL_COLORS = list(COLOR_CODES.keys())

# --- ROUTE'LAR ---
@app.route('/')
def index():
    q = request.args.get('q', '')
    category = request.args.get('category', '')
    sort = request.args.get('sort', '')

    query = db.session.query(Product).outerjoin(ClickLog).group_by(Product.id)
    if q: 
        query = query.filter(or_(Product.name.ilike(f'%{q}%'), Product.category.ilike(f'%{q}%')))
    if category: query = query.filter(Product.category == category)

    if sort == 'price_asc': query = query.order_by(Product.price.asc())
    elif sort == 'price_desc': query = query.order_by(Product.price.desc())
    else: query = query.order_by(func.count(ClickLog.id).desc())

    products = query.all()
    prod_list = []
    for p in products:
        img = f"https://placehold.co/400x400/2c3e50/FFFFFF/png?text={p.name.replace(' ', '+')}"
        prod_list.append({'obj': p, 'img': img})

    categories = [c[0] for c in db.session.query(Product.category).distinct()]
    return render_template('index.html', products=prod_list, categories=categories, current_filters={'q': q, 'category': category, 'sort': sort})

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    selected_color = request.args.get('color', 'Siyah')
    
    if current_user.is_authenticated:
        db.session.add(ClickLog(user_id=current_user.id, product_id=product.id))
        db.session.commit()

    hex_code = COLOR_CODES.get(selected_color, '000000')
    text_c = '000000' if selected_color == 'Beyaz' else 'FFFFFF'
    dynamic_img = f"https://placehold.co/500x500/{hex_code}/{text_c}/png?text={product.name.replace(' ', '+')}+({selected_color})"

    purchases = PurchaseLog.query.filter_by(product_id=product.id).all()
    
    color_dist = {c: 0 for c in ALL_COLORS} 
    for p in purchases:
        if p.selected_color in color_dist: color_dist[p.selected_color] += 1
            
    age_groups = ['18-25', '26-40', '40+']
    age_color_matrix = {grp: {c: 0 for c in ALL_COLORS} for grp in age_groups}
    for p in purchases:
        age = p.user.age
        grp = '18-25' if age <= 25 else '26-40' if age <= 40 else '40+'
        c = p.selected_color
        if c in age_color_matrix[grp]: age_color_matrix[grp][c] += 1

    # Ürün detay sayfasında outlier hesabı (Düzeltme Mantığı: Balina Çıkarma)
    prod_outlier_data = {'labels': [], 'data': [], 'clean_data': []}
    if current_user.is_authenticated and current_user.is_admin:
        try:
            # {tarih: {total: 5, purchases: [1, 1, 1, 1, 1]}}
            date_map = {}
            for p in purchases:
                d_str = p.timestamp.strftime('%Y-%m-%d')
                if d_str not in date_map: date_map[d_str] = []
                date_map[d_str].append(p.user_id) # Kim almış kaydedelim
            
            if date_map:
                sorted_dates = sorted(date_map.keys())
                counts = [len(date_map[d]) for d in sorted_dates]
                
                if len(counts) > 1:
                    mean = statistics.mean(counts)
                    stdev = statistics.stdev(counts)
                else:
                    mean = counts[0]; stdev = 0

                threshold = mean + (2 * stdev) if stdev > 0 else mean + 5
                
                prod_outlier_data['labels'] = sorted_dates
                prod_outlier_data['data'] = counts
                
                outliers_arr = []
                clean_arr = []
                
                for i, c in enumerate(counts):
                    if c > threshold:
                        # Outlier tespit edildi
                        outliers_arr.append(c)
                        
                        # O gün bu ürünü en çok alan kişiyi (Balina) bul
                        users_on_day = date_map[sorted_dates[i]]
                        user_counts = Counter(users_on_day)
                        whale_qty = user_counts.most_common(1)[0][1]
                        
                        # Düzeltilmiş = Toplam - Balina Miktarı
                        clean_arr.append(c - whale_qty)
                    else:
                        outliers_arr.append(None)
                        clean_arr.append(c)

                prod_outlier_data['outliers'] = outliers_arr
                prod_outlier_data['clean_data'] = clean_arr
        except Exception as e:
            print(f"Prod Detail Chart Error: {e}")

    return render_template('product.html', product=product, current_image=dynamic_img, 
                           selected_color=selected_color, colors=ALL_COLORS, 
                           color_dist=color_dist, age_color_matrix=age_color_matrix,
                           prod_outlier_data=prod_outlier_data)

@app.route('/buy_now', methods=['POST'])
@login_required
def buy_now():
    data = request.json
    db.session.add(PurchaseLog(user_id=current_user.id, product_id=data['product_id'], selected_color=data['color']))
    db.session.commit()
    return jsonify({'success': True, 'message': f'{data["color"]} rengi satın alındı.'})

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin: return "Yetkisiz", 403

    default_data = {
        'pop_data': {'labels': [], 'clicks': [], 'purchases': []},
        'gender_data': {'labels': [], 'data': []},
        'segment_gender_data': {'labels': [], 'male': [], 'female': [], 'avg_age': []},
        'segment_cat_data': {'labels': [], 'datasets': []},
        'outlier_data': {'labels': [], 'data': [], 'outliers': [], 'clean_data': [], 'details': []}
    }

    try:
        # 1. Popülerlik
        top_prods = db.session.query(Product, func.count(ClickLog.id).label('clicks'))\
            .outerjoin(ClickLog).group_by(Product.id).order_by(desc('clicks')).limit(10).all()
        
        pop_data = {'labels': [], 'clicks': [], 'purchases': []}
        for p, c in top_prods:
            pop_data['labels'].append(p.name)
            pop_data['clicks'].append(c)
            p_count = db.session.query(func.count(PurchaseLog.id)).filter(PurchaseLog.product_id == p.id).scalar()
            pop_data['purchases'].append(p_count)

        # 2. Cinsiyet
        gender_stats = db.session.query(User.gender, func.count(PurchaseLog.id)).join(PurchaseLog).group_by(User.gender).all()
        g_map = {'E': 0, 'K': 0}
        for g, c in gender_stats: g_map[g] = c
        gender_data = {'labels': ['Erkek', 'Kadın'], 'data': [g_map['E'], g_map['K']]}

        # 3. Segmentasyon
        all_purchases = db.session.query(PurchaseLog).all()
        if not all_purchases: return render_template('dashboard.html', **default_data)

        segments = {}
        for p in all_purchases:
            u = p.user
            if not u: continue
            key = f"{u.city} - {u.job}"
            if key not in segments: segments[key] = {'E': 0, 'K': 0, 'ages': []}
            segments[key][u.gender] += 1
            segments[key]['ages'].append(u.age)
            
        sorted_segments = sorted(segments.items(), key=lambda item: item[1]['E'] + item[1]['K'], reverse=True)[:15]
        
        segment_gender_data = {'labels': [], 'male': [], 'female': [], 'avg_age': []}
        for key, val in sorted_segments:
            segment_gender_data['labels'].append(key)
            segment_gender_data['male'].append(val['E'])
            segment_gender_data['female'].append(val['K'])
            avg = round(sum(val['ages']) / len(val['ages']), 1) if val['ages'] else 0
            segment_gender_data['avg_age'].append(avg)

        # Kategori
        cat_segments = {}
        all_categories = set()
        for p in all_purchases:
            if not p.product: continue
            key = f"{p.user.city} - {p.user.job}"
            cat = p.product.category
            if key not in cat_segments: cat_segments[key] = {}
            if cat not in cat_segments[key]: cat_segments[key][cat] = 0
            cat_segments[key][cat] += 1
            all_categories.add(cat)
        
        all_categories = sorted(list(all_categories))
        seg_labels = segment_gender_data['labels']
        segment_cat_data = {'labels': seg_labels, 'datasets': []}
        for cat in all_categories:
            data_points = []
            for label in seg_labels:
                val = cat_segments.get(label, {}).get(cat, 0)
                data_points.append(val)
            segment_cat_data['datasets'].append({'label': cat, 'data': data_points})

        # --- OUTLIER ANALİZİ (Balina Kullanıcı Tespiti) ---
        # { '2025-12-01': { 'total': 150, 'users': {user_id: count}, 'products': {prod_name: count} } }
        daily_stats = {} 
        
        for p in all_purchases:
            d_str = p.timestamp.strftime('%Y-%m-%d')
            if d_str not in daily_stats:
                daily_stats[d_str] = {'total': 0, 'users': Counter(), 'products': Counter()}
            
            daily_stats[d_str]['total'] += 1
            daily_stats[d_str]['users'][p.user_id] += 1
            daily_stats[d_str]['products'][p.product.name] += 1

        outlier_data = {'labels': [], 'data': [], 'outliers': [], 'clean_data': [], 'details': []}

        if daily_stats:
            sorted_dates = sorted(daily_stats.keys())
            counts = [daily_stats[d]['total'] for d in sorted_dates]

            if len(counts) > 1:
                mean = statistics.mean(counts)
                stdev = statistics.stdev(counts)
            else:
                mean = counts[0]; stdev = 0
            
            # Eşik değer
            threshold = mean + (2 * stdev) if stdev > 0 else mean + 10

            outliers_arr = []
            clean_arr = []
            details_list = []

            for i, d in enumerate(sorted_dates):
                total = daily_stats[d]['total']
                
                if total > threshold:
                    # Outlier tespit edildi
                    outliers_arr.append(total)
                    
                    # O gün en çok alım yapan kişiyi (Balina) bul
                    user_counts = daily_stats[d]['users']
                    # En çok alan kişi ve adedi
                    whale_user_id, whale_qty = user_counts.most_common(1)[0]
                    
                    # --- DÜZELTME MANTIĞI: BALİNAYI ÇIKAR ---
                    # Toplam satıştan, anomaliliğe sebep olan kişinin alımını çıkarıyoruz.
                    # Geriye kalan veri, o günkü "doğal" satışları temsil eder.
                    cleaned_val = total - whale_qty
                    clean_arr.append(cleaned_val)

                    # Hangi ürün patlama yapmış?
                    top_prod_name = daily_stats[d]['products'].most_common(1)[0][0]
                    prod_obj = Product.query.filter_by(name=top_prod_name).first()

                    details_list.append({
                        'date': d,
                        'total_sales': total,
                        'outlier_qty': whale_qty, # Ekrana basmak için fazlalık miktar
                        'prod_name': top_prod_name,
                        'prod_id': prod_obj.id if prod_obj else 0,
                        'category': prod_obj.category if prod_obj else 'Genel'
                    })
                else:
                    outliers_arr.append(None)
                    clean_arr.append(total)

            outlier_data['labels'] = sorted_dates
            outlier_data['data'] = counts
            outlier_data['outliers'] = outliers_arr
            outlier_data['clean_data'] = clean_arr
            outlier_data['details'] = details_list

    except Exception as e:
        print(f"DASHBOARD ERROR: {e}")
        import traceback
        traceback.print_exc()
        return render_template('dashboard.html', **default_data)

    return render_template('dashboard.html', 
                           pop_data=pop_data, 
                           gender_data=gender_data, 
                           segment_gender_data=segment_gender_data, 
                           segment_cat_data=segment_cat_data,
                           outlier_data=outlier_data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            b_date = datetime.datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d').date()
            user = User(username=request.form.get('username'), gender=request.form.get('gender'), 
                        birth_date=b_date, education=request.form.get('education'), 
                        city=request.form.get('city'), job=request.form.get('job'))
            user.set_password(request.form.get('password'))
            if User.query.count() == 0: user.is_admin = True
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('index'))
        except: flash("Hata oluştu", "danger")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user, remember=True)
            return redirect(url_for('index'))
        flash("Hatalı giriş", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('index'))

@app.cli.command('init-db')
def init_db():
    db.drop_all()
    db.create_all()
    print("1. Ürünler Ekleniyor...")
    
    names = [
        ("iPhone 15", "Elektronik", 50000), ("MacBook Air", "Elektronik", 45000), ("iPad Pro", "Elektronik", 35000),
        ("Sony Kulaklık", "Elektronik", 9000), ("Oyun PC", "Elektronik", 60000), ("Samsung S24", "Elektronik", 55000),
        ("Yazlık Elbise", "Giyim", 900), ("Kot Ceket", "Giyim", 1200), ("Keten Pantolon", "Giyim", 800),
        ("İpek Şal", "Giyim", 600), ("Deri Mont", "Giyim", 4000), ("Spor Tayt", "Giyim", 500),
        ("Nike Air", "Ayakkabı", 4500), ("Adidas Superstar", "Ayakkabı", 3800), ("Topuklu Ayakkabı", "Ayakkabı", 1500),
        ("Bot", "Ayakkabı", 2000), ("Koşu Ayakkabısı", "Ayakkabı", 3000),
        ("Kahve Makinesi", "Ev", 5000), ("Robot Süpürge", "Ev", 15000), ("Kitaplık", "Ev", 2500), ("Çalışma Masası", "Ev", 3500)
    ]
    for n, c, p in names: db.session.add(Product(name=n, category=c, price=p))
    db.session.commit()
    
    print("2. Kullanıcılar Ekleniyor...")
    db.session.add(User(username="admin", gender="E", birth_date=datetime.date(1990,1,1), education="Yuksek", city="İstanbul", job="Yönetici", is_admin=True, password_hash=generate_password_hash("123")))
    
    jobs = {"Lise": ["Öğrenci", "Garson", "Kasiyer"], "Lisans": ["Mühendis", "Öğretmen", "Yazılımcı"], "Yuksek": ["Doktor", "Avukat", "Akademisyen"]}
    cities = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya"]
    
    # Kullanıcı sayısını arttırdık (120)
    users = []
    for i in range(120):
        edu = random.choice(list(jobs.keys()))
        u = User(username=f"user{i}", gender=random.choice(['E','K']), 
                 birth_date=datetime.date(random.randint(1980, 2005), 1, 1),
                 education=edu, city=random.choice(cities), job=random.choice(jobs[edu]))
        u.set_password("123")
        users.append(u)
    db.session.add_all(users)
    db.session.commit()
    
    print("3. VERİ SİMÜLASYONU BAŞLIYOR (NORMAL + OUTLIER)...")
    prods = Product.query.all()
    all_users = User.query.filter(User.username != 'admin').all()
    colors = list(COLOR_CODES.keys())
    
    # Ürünleri kategorilere ayır
    products_by_cat = {}
    for p in prods:
        if p.category not in products_by_cat: products_by_cat[p.category] = []
        products_by_cat[p.category].append(p)

    today = datetime.datetime.utcnow()
    
    # 3 Rastgele Outlier Günü Seç
    days_range = list(range(1, 29))
    outlier_deltas = random.sample(days_range, 3) 
    outlier_dates = [(today - datetime.timedelta(days=d)).strftime('%Y-%m-%d') for d in outlier_deltas]
    print(f"Outlier Günleri: {outlier_dates}")

    bulk_purchases = []
    bulk_clicks = []

    for delta in range(30):
        current_date = today - datetime.timedelta(days=delta)
        date_str = current_date.strftime('%Y-%m-%d')
        
        # --- NORMAL TRAFİK SİMÜLASYONU ---
        # Günlük 10-100 arası satış hacmi oluşturmak için rastgele sayıda aktif kullanıcı seç
        daily_active_users_count = random.randint(10, 40)
        daily_users = random.sample(all_users, daily_active_users_count)
        
        for u in daily_users:
            # Her kullanıcı her kategoriden rastgele 3 ürün seçsin (Prompt isteği)
            # Ancak çok fazla kategori varsa bunu sınırlayabiliriz, şimdilik kategorilerden rastgele ürünler seçtiriyoruz.
            # Her kategoriden 3 ürün almak yerine, rastgele 3-5 işlem yaptırıyoruz ki dağılım doğal olsun.
            
            # Rastgele 3 ürün seç
            selected_prods = random.sample(prods, 3)
            
            for p in selected_prods:
                # Miktar: Minimum 1, Maksimum 5
                qty = random.randint(1, 5)
                
                # Tıklanma sayısı (Alımdan biraz fazla olsun)
                click_count = qty + random.randint(1, 5)
                for _ in range(click_count):
                    bulk_clicks.append(ClickLog(user_id=u.id, product_id=p.id, timestamp=current_date))

                # Satın alma kaydı (Adet sütunu olmadığı için satır satır ekliyoruz)
                for _ in range(qty):
                    bulk_purchases.append(PurchaseLog(
                        user_id=u.id, product_id=p.id, 
                        selected_color=random.choice(colors), 
                        timestamp=current_date
                    ))

        # --- OUTLIER (BALİNA) SİMÜLASYONU ---
        if date_str in outlier_dates:
            whale_user = random.choice(all_users)
            whale_product = random.choice(prods)
            
            # O gün normalde 1-5 alan biri yerine, 50-100 adet alan biri olsun
            whale_qty = random.randint(50, 100)
            print(f"!!! OUTLIER: {date_str} - {whale_user.username} - {whale_product.name} - {whale_qty} adet")
            
            # Balina tıklamaları
            for _ in range(int(whale_qty * 1.2)):
                bulk_clicks.append(ClickLog(user_id=whale_user.id, product_id=whale_product.id, timestamp=current_date))

            # Balina alımları
            for _ in range(whale_qty):
                bulk_purchases.append(PurchaseLog(
                    user_id=whale_user.id, product_id=whale_product.id, 
                    selected_color=random.choice(colors), 
                    timestamp=current_date
                ))

    print("Veriler kaydediliyor (Biraz sürebilir)...")
    db.session.bulk_save_objects(bulk_clicks)
    db.session.bulk_save_objects(bulk_purchases)
    db.session.commit()
    print("BİTTİ. Veritabanı hazır.")

if __name__ == '__main__':
    app.run(debug=True)