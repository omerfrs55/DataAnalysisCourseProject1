# DataAnalysisCourseProject1
-----
## Proje Hakkında

AnalizTrend, standart bir e-ticaret sitesi fonksiyonlarının ötesinde, kullanıcı davranışlarını (tıklama, satın alma, renk tercihi) ve demografik verileri (yaş, cinsiyet, meslek, şehir, eğitim durumu) kaydederek, bu veriler üzerinden "İş Zekası" (Business Intelligence) raporları oluşturan bir web tabanlı simülasyon projesidir.

Bu proje, Veri Analitiği dersi kapsamında; büyük veri setlerinin toplanması, işlenmesi, anlamlandırılması ve görselleştirilmesi süreçlerini simüle etmek amacıyla geliştirilmiştir. Sistem, arka planda çalışan algoritmalar sayesinde kullanıcı segmentasyonu yapabilmekte ve yönetim paneli üzerinden stratejik kararlar alınmasını sağlayan grafikler sunmaktadır.

## Geliştiriciler

  * **Emir Ecrin MALKOÇ**
  * **Ömer Faruk SAĞLAM**

**Geliştirme Ortamı:** Visual Studio Code

-----

## Projenin Amacı ve Kapsamı

Bu projenin temel amacı, bir e-ticaret platformunda oluşan ham verilerin nasıl işlenebilir bilgiye dönüştürüldüğünü göstermektir. Sistem iki ana modülden oluşmaktadır:

1.  **Müşteri Arayüzü:** Kullanıcıların ürünleri incelediği, dinamik filtreleme yaptığı ve satın alma simülasyonunu gerçekleştirdiği ön yüz.
2.  **Yönetici (Analiz) Paneli:** Toplanan verilerin işlendiği ve çapraz sorgularla (Örn: İstanbul'da yaşayan mühendislerin renk tercihleri) detaylı grafiklere dönüştürüldüğü arka yüz.

-----

## Kullanılan Teknolojiler ve Kütüphaneler

Bu proje Python programlama dili kullanılarak, Visual Studio Code editöründe geliştirilmiştir.

  * **Backend (Sunucu Tarafı):**

      * **Python 3.x:** Ana programlama dili.
      * **Flask:** Web sunucusu ve uygulama çatısı.
      * **Flask-SQLAlchemy:** Veritabanı modellemesi ve ORM (Object Relational Mapping) işlemleri.
      * **Flask-Login:** Kullanıcı oturum yönetimi ve güvenlik.

  * **Veritabanı:**

      * **SQLite:** Yerel, dosya tabanlı ilişkisel veritabanı yönetim sistemi.

  * **Frontend (İstemci Tarafı):**

      * **HTML5 & CSS3:** Sayfa iskeleti ve stil şablonları.
      * **Bootstrap 5:** Responsive (mobil uyumlu) ve modern arayüz tasarımı.
      * **Chart.js:** Veri görselleştirme ve interaktif grafik kütüphanesi.
      * **JavaScript (AJAX):** Sayfa yenilenmeden veri gönderme (Satın alma işlemleri) ve dinamik içerik yönetimi.

-----

## Sistemin Özellikleri

### 1\. Veri Simülasyonu ve Üretimi (Data Generator)

Proje, veritabanını manuel doldurma zahmetini ortadan kaldıran gelişmiş bir veri üretim motoruna sahiptir. `flask init-db` komutu çalıştırıldığında sistem şunları otomatik yapar:

  * Farklı kategorilerde ürünleri oluşturur.
  * Mantıksal tutarlılığa sahip (Örn: Lise mezunu 17 yaşında öğrenci, Yüksek Lisans mezunu 30 yaşında doktor gibi) 60+ farklı kullanıcı profili üretir.
  * Bu kullanıcılar adına binlerce "Tıklama" ve "Satın Alma" verisi üreterek veritabanını analize hazır hale getirir.

### 2\. Kullanıcı Arayüzü Fonksiyonları

  * **Dinamik Renk Seçimi:** Ürün detay sayfasında renk seçildiğinde ürün görseli anlık olarak değişir.
  * **Gelişmiş Filtreleme:** Kullanıcılar ürünleri isme, kategoriye veya renge göre arayabilir ve sıralayabilir.
  * **Hemen Al Simülasyonu:** Sepet mantığı yerine hızlı satın alma butonu kullanılmıştır. Satın alma işlemi gerçekleştiğinde stok düşümü simüle edilir ve veri anlık olarak analiz sistemine işlenir.

### 3\. Yönetici Paneli ve Analitik Raporlar

Yönetici paneli, toplanan verileri şu grafiklerle sunar:

  * **Popülerlik Analizi:** Ürünlerin görüntülenme sayısı ile satın alma sayısı arasındaki dönüşüm oranı (Conversion Rate).
  * **Cinsiyet Dağılımı:** Toplam satışların kadın/erkek dağılımı.
  * **Eğitim - Kategori İlişkisi:** Hangi eğitim seviyesindeki kullanıcıların hangi kategorilere (Elektronik, Giyim vb.) ilgi duyduğunun analizi.
  * **Segment Analizi (4 Boyutlu):** Şehir, Meslek, Cinsiyet ve Yaş verilerinin tek bir grafikte birleştirildiği gelişmiş analiz. (Örn: Ankara'daki Öğretmenlerin yaş ortalaması ve cinsiyet dağılımına göre harcama alışkanlıkları).

-----

## Veritabanı Mimarisi

Proje ilişkisel veritabanı yapısını kullanmaktadır. Temel tablolar şunlardır:

1.  **User (Kullanıcılar):**

      * ID, Kullanıcı Adı, Şifre (Hash), Admin Yetkisi
      * Demografik Veriler: Yaş, Cinsiyet, Eğitim Durumu, Şehir, Meslek.

2.  **Product (Ürünler):**

      * ID, Ürün Adı, Kategori, Fiyat.

3.  **ClickLog (Tıklama Kayıtları):**

      * Kullanıcı ID, Ürün ID, Zaman Damgası. (Kullanıcının ilgi alanını belirlemek için kullanılır).

4.  **PurchaseLog (Satın Alma Kayıtları):**

      * Kullanıcı ID, Ürün ID, Seçilen Renk, Zaman Damgası. (Kesinleşmiş satış verisi).

-----

## Kurulum ve Çalıştırma Kılavuzu

Projeyi kendi bilgisayarınızda çalıştırmak için aşağıdaki adımları takip ediniz.

### Adım 1: Gerekli Kütüphanelerin Yüklenmesi

Proje dizininde bir terminal açarak gerekli Python paketlerini yükleyiniz:

```bash
pip install Flask Flask-SQLAlchemy Flask-Login
```

### Adım 2: Veritabanının Oluşturulması

Projenin çalışabilmesi ve grafiklerin dolu gelebilmesi için veritabanının oluşturulması ve simülasyon verilerinin yüklenmesi gerekmektedir. Aşağıdaki komutu terminale giriniz:

```bash
flask init-db
```

*Not: Bu işlem veritabanına yüzlerce örnek veri ekleyeceği için birkaç saniye sürebilir. Terminalde "HAZIR" mesajını görene kadar bekleyiniz.*

### Adım 3: Uygulamanın Başlatılması

Veritabanı hazırlandıktan sonra sunucuyu başlatmak için şu komutu giriniz:

```bash
flask run
```

### Adım 4: Sisteme Erişim

Tarayıcınızın adres çubuğuna şu adresi girerek siteye erişebilirsiniz:
`http://127.0.0.1:5000`

**Yönetici Girişi Bilgileri:**

  * **Kullanıcı Adı:** admin
  * **Şifre:** 123

-----

## Dosya Yapısı

  * `app.py`: Uygulamanın ana beyni. Veritabanı modelleri, yönlendirmeler (routes) ve veri analitiği hesaplamaları burada yapılır.
  * `proje.db`: SQLite veritabanı dosyası (init-db komutu sonrası oluşur).
  * `templates/`: HTML dosyalarının bulunduğu klasör.
      * `layout.html`: Ana şablon (Navbar ve Footer).
      * `index.html`: Ana sayfa ve ürün listeleme.
      * `product.html`: Ürün detay, renk seçimi ve ürün özelindeki grafikler.
      * `dashboard.html`: Yönetici analiz paneli.
      * `login.html` / `register.html`: Kullanıcı giriş ve kayıt sayfaları.
  * `static/`: CSS ve görsel dosyaların bulunduğu klasör.

-----

Bu proje, veri analitiğinin e-ticaret süreçlerindeki önemini vurgulamak amacıyla **Emir Ecrin MALKOÇ** ve **Ömer Faruk SAĞLAM** tarafından hazırlanmıştır.
