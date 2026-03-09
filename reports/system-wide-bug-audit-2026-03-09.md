# Sistem Geneli Bug Denetim Raporu

Tarih: 2026-03-09  
Kapsam: upload -> algorithm -> calibration -> measurement -> report/download uçtan uca akış  
Not: Bu doküman sadece bulgu raporudur, fix uygulanmamıştır.

---

## P1 (Kritik) Bulgular

### 1) Ölçüm sekmesinde X-ekseni seçim modu hâlâ aktif olabiliyor
- **Etki:** Kalibrasyon tamamlandıktan sonra ölçümde yanlışlıkla X1/X2 noktaları değişebiliyor; kullanıcı fark etmeden kalibrasyon state’i kirleniyor.
- **Tekrar adımı:**
  1. Görsel yükle, Y kalibrasyonu yap.
  2. Ölçüm sekmesine geç.
  3. Görsel üstüne tıkla.
  4. X noktalarının değiştiğini gözlemle.
- **Kök neden:** `handleAutoEdgeClick()` içinde X seçim kontrolü (`xCalState`) tab/mode kontrolünden önce çalışıyor.
- **İlgili kod:** `frontend/js/app.js` (`handleAutoEdgeClick`, `setCalibrationResult`, `setupTabs`)

### 2) Kalibrasyon state’i backend’de global tutuluyor
- **Etki:** Çoklu kullanıcı/sekme veya ardışık farklı parça ölçümlerinde eski kalibrasyon yeni ölçümü etkileyebiliyor.
- **Tekrar adımı:**
  1. Kullanıcı A kalibrasyon yapar.
  2. Kullanıcı B kalibrasyon yapmadan ölçüm alır.
  3. B’nin ölçümü A’nın kalibrasyonundan etkilenir.
- **Kök neden:** Process geneli tek `active_calibration` nesnesi kullanımı.
- **İlgili kod:** `backend/app.py` (`active_calibration`, `/api/calibrate*`, `/api/measure`, `/api/report/*`)

### 3) `x_user_calibrated` yüklemede yanlış `True` olabiliyor
- **Etki:** X ekseni gerçekten kalibre edilmediği halde sistem “kalibre” sanabiliyor; frontend yanlış güven verir.
- **Tekrar adımı:**
  1. Sadece Y kalibrasyonu ile profil kaydet.
  2. Profili yükle.
  3. `x_user_calibrated` değerinin beklenmedik biçimde `true` döndüğünü kontrol et.
- **Kök neden:** `__init__` içindeki `x_user_calibrated or True` ifadesi.
- **İlgili kod:** `backend/calibration.py` (`CalibrationProfile.__init__`, `from_dict`)

### 4) Ölçüm snapshot’ı yeni görselde temizlenmediğinde rapor karışabiliyor
- **Etki:** Yeni görsele geçip tekrar ölçüm almadan rapor indirildiğinde, eski ölçüm tablosu ile yeni görsel bir araya gelebilir.
- **Tekrar adımı:**
  1. Görsel A’da ölçüm al.
  2. Görsel B yükle.
  3. Yeniden ölçüm almadan PDF/Excel indir.
- **Kök neden:** Frontend’de yeni görsel yüklenince `lastMeasurementTable`/`lastSummary` reseti garanti değilse stale veri kalır.
- **İlgili kod:** `frontend/js/app.js` (`handleFile`, indirme aksiyonları)

---

## P2 (Yüksek/Orta) Bulgular

### 5) Kalibrasyon edge request’i geç dönerse yanlış sekmeyi overwrite edebiliyor
- **Etki:** Kullanıcı sekme değiştirse bile geç dönen cevap “Kenar Tespiti” overlay’ini aktif ekrana basabiliyor.
- **Tekrar adımı:**
  1. Kalibrasyon sekmesinde tıklayıp edge isteği başlat.
  2. Hızlıca Ölçüm/Algoritma sekmesine geç.
  3. Yanıt gelince ekranın overwrite edilip edilmediğini kontrol et.
- **Kök neden:** Request token / aktif sekme doğrulaması yok.
- **İlgili kod:** `frontend/js/app.js` (`handleAutoEdgeClick`)

### 6) Kalibrasyona girişte panel gizleme davranışı sekmeler arası sızabiliyor
- **Etki:** Split/single görünüm beklenmedik şekilde kalıcılaşabiliyor; UI tutarsız görünür.
- **Tekrar adımı:** Algoritma sonrası kalibrasyona geç -> tekrar başka sekmeye dön -> panel görünürlüğünü kontrol et.
- **Kök neden:** Geçici görünüm zorlaması için simetrik cleanup eksikliği.
- **İlgili kod:** `frontend/js/app.js` (`setupTabs`, `resetOverlays`)

### 7) Manuel moda geçince X seçim akışı her durumda durmuyor
- **Etki:** Kullanıcı manuel kalibrasyondayken bile tıklamalar X1/X2 akışını etkileyebilir.
- **Kök neden:** `calModeManual` yalnızca `isCalibrating` kapatıyor; `xCalState` ayrı state olduğu için açık kalabiliyor.
- **İlgili kod:** `frontend/js/app.js` (`setupCalibration`, `handleAutoEdgeClick`)

### 8) X2 slider/input ile tamamlanan akışta “X kalibre et” butonu pasif kalabiliyor
- **Etki:** Kullanıcı iki noktayı slider ile verdiği halde kalibrasyon butonu aktifleşmeyebilir.
- **Kök neden:** Buton enable mantığı ağırlıklı olarak tıklama akışında.
- **İlgili kod:** `frontend/js/app.js` (`handleXCalClick`, `setX1Value`, `setX2Value`)

### 9) `/api/detect-edges` `click_y` bilgisini aktif kullanmıyor
- **Etki:** Aynı `x` kolonda birden fazla olası kenar kümesi varsa kullanıcı hedeflediği bölgeyi seçemeyebilir.
- **Kök neden:** Kolonun sadece global ilk/son beyaz pikseli alınıyor.
- **İlgili kod:** `backend/app.py` (`detect_edges`)

### 10) Bölüm geçiş birleştirme mantığı başlangıç sınırını kaydırabiliyor
- **Etki:** Bölüm genişlikleri ve toplam boy değeri sapabilir.
- **Kök neden:** Yakın geçişlerde önceki sınırın overwrite edilmesi.
- **İlgili kod:** `backend/measurement_engine.py` (`detect_sections`, `clean_transitions`)

### 11) Kalibrasyon kaynağı görsel ile ölçüm kaynağı görsel ayrışabilir
- **Etki:** Kullanıcı farklı panel/görsel üzerinden kalibre edip başka kaynakla ölçüm alırsa tutarsızlık doğar.
- **Kök neden:** `image_id` seçimi panel ve state’e bağlı, akışta kesin bağlayıcı doğrulama yok.
- **İlgili kod:** `frontend/js/app.js` (`handleAutoEdgeClick`), `backend/app.py` (`/api/measure`)

---

## P3 (Düşük) Bulgular

### 12) Upload edge-case guard eksikliği (`filename` yoksa)
- **Etki:** Programatik bazı multipart çağrılarında beklenmeyen hata.
- **İlgili kod:** `backend/app.py` (`upload_image`)

### 13) Mutable default riski (`params: dict = {}`)
- **Etki:** Sürüm/yorum farklarına bağlı yan etki riski.
- **İlgili kod:** `backend/app.py` (`ProcessRequest`)

### 14) PDF’de görsel üretim hatası sessiz yutuluyor
- **Etki:** “Görselli rapor” beklentisi varken sessizce görselsiz rapor dönebilir.
- **İlgili kod:** `backend/app.py` (`/api/report/pdf`)

---

## Hızlı Öncelik Önerisi (Fix sırası)

1. **P1-1** Ölçümde X seçim sızıntısını kapat (tab/mode gating).  
2. **P1-3** `x_user_calibrated` mantık hatasını düzelt.  
3. **P1-2** Kalibrasyonun global state olmasını azaltacak güvenli geçiş (en azından image/session bağlama).  
4. **P1-4 + P2-5** stale snapshot ve async overwrite sorunlarını kapat.  
5. **P2-9 + P2-10** edge seçimi ve section geçiş stabilizasyonu.

---

## Kapanış

Kullanıcıdan gelen “kalibrasyonda doğru, ölçümde bozuluyor” ve “ölçümde X seçimi açık kalıyor” şikayetleri teknik olarak doğrulandı.  
Bir sonraki adımda bu raporu baz alıp P1’leri sırayla fixleyelim.
