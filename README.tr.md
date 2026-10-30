# PaperclipLite

🌐 Diller: [Deutsch](README.md) · [English](README.en.md) · **Türkçe** · [Srpski](README.sr.md) · [Bosanski](README.bs.md) · [Hrvatski](README.hr.md)

Düğüm editörü olarak bir yapay zekâ ajan ekibi; kendi sunucunuzda çalışır ve Raspberry Pi için yeterince hafiftir.
Proje oluşturun, ajanları sürükleyip alana bırakın, bağlayın (patron → çalışan), her düğüm için yapay zekâ sağlayıcısını, çalışma talimatını ve yetkileri ayarlayın ve görev atayın.

> `docs/` klasöründeki ayrıntılı kılavuzlar şu an yalnızca Almanca yazılmıştır. Uygulamadaki düğme ve menü adları Almanca olarak kalır.

## Kurulum

PaperclipLite bir Python programıdır (Flask + SQLite) ve birçok sistemde çalışır. Birden çok kurulum
paralel çalışabilir; her birinin kendi şirketleri ve verileri vardır.

| Sistem | Durum | Kılavuz |
| --- | --- | --- |
| Raspberry Pi / Linux (Debian, Ubuntu) | ana sistem, tam özellik kapsamı | aşağıda |
| Windows 10/11 | çalışır, `run_code` olmadan, bazı özellikler ek programlar gerektirir | [docs/windows.md](docs/windows.md) |
| macOS | test edilmedi, temel işlevler çalışmalı | aşağıda (elle) |
| Kendi görüntü bilgisayarı (ör. ekran kartı olmayan eski bir dizüstü) | referans görselleriyle ücretsiz görseller | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) |

Bir bilgisayardan diğerine taşıma: PaperclipLite'i durdurun ve `data.db`, `workspace/` klasörünü ve `.env` dosyasını kopyalayın
([Pi → Windows örneği](docs/windows.md)).

### Raspberry Pi / Linux

```bash
git clone https://github.com/KhungFu/paperclip-lite && cd paperclip-lite
./install.sh --service     # venv, bağımlılıklar, rastgele şifreli .env, systemd hizmeti
nano .env                  # API anahtarlarını girin, ardından: sudo systemctl restart paperclip-lite
```

Hizmet olmadan: `./install.sh` ve sonra `./venv/bin/python app.py` → http://127.0.0.1:8787.
Giriş şifresi `.env` içindedir (`APP_TOKEN`). Güncelleme, yeniden başlatma, yedekleme: [İşletim](#işletim-kim-neyi-nerede-ne-zaman-nasıl-yapar).
Daha fazla özellik (video, OCR, derleyiciler, tarayıcı): `./install.sh --all`.

### Windows

PaperclipLite klasöründe PowerShell:

```powershell
git clone https://github.com/KhungFu/paperclip-lite; cd paperclip-lite
powershell -ExecutionPolicy Bypass -File install.ps1
notepad .env
deploy\windows\paperclip-start.bat
```

Windows'ta eksik olanlar, otomatik başlatma ve Pi ile paralel çalışma: [docs/windows.md](docs/windows.md).
Sonradan güncelleme: `git pull`, ardından yeniden başlatın.

### macOS (test edilmedi)

```bash
git clone https://github.com/KhungFu/paperclip-lite && cd paperclip-lite
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env       # APP_TOKEN=<uzun şifre> girin, API anahtarlarını ekleyin
./venv/bin/python app.py   # http://127.0.0.1:8787
```

`install.sh` Debian/Ubuntu için yapılmıştır (apt), bu yüzden macOS'ta yukarıdaki gibi elle kurun. Ek programlar Homebrew ile
(`brew install ffmpeg tesseract poppler`). `run_code` yalnızca Linux'ta vardır.

### Kendi bilgisayarınızda görseller

Ev ağındaki bir bilgisayar (ekran kartı olmasa bile en az 8 GB RAM ile) PaperclipLite için referans görselleriyle
ücretsiz görseller üretebilir. `.env` dosyasında tam olarak bu iki satırı etkin bırakın (`#` olmadan yalnızca bir `IMAGE_PROVIDER=` satırı):

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://<görsel bilgisayarının IP'si>:1234    # görsel bilgisayarının kendisinde: http://127.0.0.1:1234
```

Kurulum: [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md).

## İşletim: kim neyi, nerede, ne zaman, nasıl yapar

**Kim:** Bunların hepsini bilgisayarın sahibi (siz) yapar, ajanlar değil. Komutlar PaperclipLite klasöründe çalışır: Pi'de terminalde (`cd ~/paperclip-lite`), Windows'ta PowerShell'de
(`cd $HOME\paperclip-lite`, ya da klasörü nereye koyduysanız orada).

### Kısa genel bakış

| Ne | Ne zaman | Raspberry Pi / Linux (hizmetle) | Windows |
| --- | --- | --- | --- |
| Başlatma | kurulumdan sonra, otomatik başlatma olmadan yeniden başlatmadan sonra | `sudo systemctl start paperclip-lite` | `deploy\windows\paperclip-start.bat` dosyasına çift tıklayın (pencereyi açık bırakın) |
| Durdurma | taşımadan, yedeklemeden, güncellemeden önce | `sudo systemctl stop paperclip-lite` | başlatma penceresini kapatın (ya da içinde Ctrl+C) |
| Yeniden başlatma | `.env` her değiştiğinde, güncellemeden sonra | `sudo systemctl restart paperclip-lite` | başlatma penceresini kapatın, `paperclip-start.bat` dosyasını yeniden çalıştırın |
| Çalışıyor mu? | sorun olduğunda | `systemctl status paperclip-lite` | başlatma penceresi açık mı? Tarayıcı: <http://127.0.0.1:8787> |
| Günlüğe bakma | hatalarda | `journalctl -u paperclip-lite -f` (Ctrl+C ile çıkılır) | başlatma penceresinde görünür |
| Güncelleme | yeni bir sürüm olduğunda (ör. birleştirilmiş bir pull request'ten sonra) | aşağıya bakın | aşağıya bakın |
| Kontrol | kurulumdan, güncellemeden, yeni anahtarlardan sonra | `./venv/bin/python selftest.py` | `venv\Scripts\python.exe selftest.py` |
| Anahtarlar / ayarlar | yeni anahtar, başka görsel sağlayıcısı | `nano .env`, sonra yeniden başlatın | `notepad .env`, sonra yeniden başlatın |
| Yedekleme | düzenli olarak, taşımadan ve büyük güncellemelerden önce | `data.db`, `workspace/`, `.env` kopyalayın (önce durdurun) | PaperclipLite klasöründe aynısı |

### Güncelleme (yeni sürümü alma)

**Raspberry Pi / Linux**, terminalde:

```bash
cd ~/paperclip-lite
git pull
./install.sh               # yalnızca requirements.txt değiştiyse gerekir; .env değişmez
sudo systemctl restart paperclip-lite
./venv/bin/python selftest.py llm     # yapay zekâ sağlayıcılarının yanıt verdiğini kısaca kontrol edin
```

**Windows**, PowerShell'de:

1. `cd $HOME\paperclip-lite`
2. `git pull`
3. Yalnızca paketler değiştiyse (ya da emin değilseniz): `powershell -ExecutionPolicy Bypass -File install.ps1`
   (mevcut `.env` değişmez).
4. PaperclipLite'in siyah başlatma penceresini kapatın.
5. `deploy\windows\paperclip-start.bat` dosyasını yeniden başlatın (çift tıklayın ya da PowerShell'e yazın).
6. Kontrol: `venv\Scripts\python.exe selftest.py llm`

`git pull` „local changes would be overwritten“ diyorsa, programın bir dosyasını kendiniz değiştirmişsiniz demektir.
`git stash` değişikliği kenara koyar, ardından `git pull` komutunu tekrarlayın. Verileriniz (`data.db`, `workspace/`, `.env`)
bundan asla etkilenmez, çünkü Git bunları bilmez.

### Otomatik başlatma

- **Pi:** `./install.sh --service` hizmeti kurar; böylece her açılışta kendiliğinden başlar.
- **Windows:** Win+R tuşlarına basın, `shell:startup` yazın ve oraya `deploy\windows\paperclip-start.bat` dosyasının bir kısayolunu koyun
  (kullanıyorsanız `bildrechner-start.bat` dosyasının da). Bunun için Windows'un kendiliğinden oturum açması gerekir
  ([docs/windows.md](docs/windows.md), bölüm 4).

### `.env` ayarlarını değiştirme

- Her ayar tam olarak bir kez, başında `#` olmadan yazılır. `#` ile başlayan satırlar kapalıdır. Yinelenen satırlarda
  ilki geçerlidir.
- Her değişiklikten sonra PaperclipLite'i yeniden başlatın, yoksa eski durum geçerli kalır.
- Anahtarları asla sohbetlere, ekran görüntülerine ya da depoya kopyalamayın. Bir anahtar bir yere yanlışlıkla düştüyse: sağlayıcıda iptal edin ve yenisini girin.
- Sonra `selftest.py` ile kontrol edin. Tek tek alanlar: `selftest.py llm`, `web`, `telegram`, `media`, `ocr`, `code`.

### Selbsttest sonuçlarını okumak

- **OK:** çalışıyor.
- **FEHLT (eksik):** isteğe bağlıdır; satır, eklemek için komutu verir (Windows'ta Windows komutunu).
  Yalnızca ajanlarınız bunu kullanıyorsa gerekir (ör. video, sesli okuma, taranmış PDF'ler).
- **FEHLER (hata):** girdiğiniz bir şey çalışmıyor; çoğu zaman geçersiz ya da süresi dolmuş bir anahtar ya da çalışmayan bir hizmet
  (ör. görsel bilgisayarı). Satır nedenini gösterir.
- Bir web hizmetinde tek bir zaman aşımı (Timeout) genellikle geçicidir: daha sonra yeniden deneyin.

### Görsel bilgisayarı (kullanılıyorsa)

- **Nerede:** görselleri üreten bilgisayarda (ör. dizüstü), klasör `C:\bildrechner`.
- **Ne zaman:** ajanların görsel üretmesi gerektiği sürece çalışmalı.
- **Nasıl:** Kurulum bir kez yapılır: PaperclipLite klasöründe PowerShell içinde
  `powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1` (program ve modelleri indirir).
- **Nasıl çalıştırılır:** `C:\bildrechner\bildrechner-start.bat` dosyasını başlatın, pencereyi açık bırakın. PaperclipLite'in `.env` dosyasında
  `IMAGE_PROVIDER=sdcpp` ve `SDCPP_URL=...` ([kılavuz](docs/laptop-bildrechner.md)), ardından PaperclipLite'i yeniden başlatın.

### Taşınma (ör. Pi → dizüstü)

Adım adım [docs/windows.md](docs/windows.md) dosyasında, „Phase 2 – Umzug“ bölümünde (Almanca). Kısaca: ikisini de durdurun, `data.db`,
`workspace/` ve `.env` dosyalarını kopyalayın, yeni bilgisayarda başlatıp kontrol edin ve ancak ondan sonra eskisini kapatın.
Telegram'ı yalnızca tek bir bilgisayarda kaydedin.

### Bir şey eksik olduğunda ne olur

Bu liste programda her değişiklikle genişletilir. Her satır sistemin ne yaptığını ve sizin ne yapmanız gerektiğini söyler.

| Eksik | Sistem ne yapar | Siz ne yaparsınız |
| --- | --- | --- |
| `.env` | PaperclipLite anahtarsız ve şifresiz başlar; yalnızca bu bilgisayardan erişilebilir. `HOST=0.0.0.0` ile `APP_TOKEN` boş olduğu sürece başlatma iptal edilir. | `./install.sh` (Pi) ya da `install.ps1` (Windows) rastgele şifreli bir tane oluşturur. |
| `data.db` | Boş olarak yeniden oluşturulur. Şirketler, görevler ve gönderiler kaybolur. | Önce yedekleyin (İşletim bölümüne bakın). Yalnızca bir yedekten geri kopyalayın. |
| `.env` içindeki API anahtarı | Sağlayıcı selbsttest'te FEHLT olarak gösterilir ve ajanlar kullanmaz. Girilmiş ama geçersizse: HTTP 401 ile FEHLER. | Anahtarı girin ya da satırı `#` ile kapatın. |
| `SDCPP_URL` (`IMAGE_PROVIDER=sdcpp` ile) | Görsel istekleri „SDCPP_URL fehlt“ (eksik) hatasıyla başarısız olur. `IMAGE_FALLBACK=pollinations` ile referanssız, ücretsiz bir yedek görsel üretilir ve sonuçta bir not yer alır. | `.env` dosyasına satırı ekleyin, PaperclipLite'i yeniden başlatın. |
| Görsel bilgisayarına ulaşılamıyor (dizüstü kapalı, güvenlik duvarı, yanlış IP) | Yukarıdaki gibi: „Bildrechner … nicht erreichbar“ (erişilemiyor) hatası; yedekle bir yedek görsel. | Dizüstünü açın, `bildrechner-start.bat` dosyasını başlatın, IP'yi ve güvenlik duvarını kontrol edin. |
| `sd-server.exe` (Windows, görsel bilgisayarı) | `bildrechner-start.bat` „sd-server.exe fehlt“ (eksik) gösterir ve hiçbir şey başlatmaz. | `deploy\windows\bildrechner-einrichten.ps1` dosyasını çalıştırın. |
| Model dosyası (Windows, görsel bilgisayarı) | Başlatma dosyası eksik dosyayı adıyla belirtir ve başlamaz. Yalnızca büyük dil modeli (`Qwen3-4B-Q4_K_M.gguf`) eksikse ve daha küçüğü varsa, onu kullanır. | Kurulum betiğini yeniden çalıştırın; yalnızca eksik dosyayı indirir. |
| Windows çalışma zamanı `VCOMP140.DLL` | `sd-server.exe` „VCOMP140.DLL nicht gefunden“ (bulunamadı) bildirir ve kapanır. | Kurulum betiğini yeniden çalıştırın (3. adım çalışma zamanını kurar), sonra başlatma dosyasını açın. |
| Port 1234 için güvenlik duvarı kuralı (Windows) | Yalnızca Pi görsel bilgisayarına ulaşamaz. Dizüstünün kendisi çalışmaya devam eder. | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) dosyasındaki 4. bölümden komutu yönetici olarak çalıştırın. |
| `FAL_KEY` (`VIDEO_PROVIDER=fal` ile) | Video üretimi „VIDEO_PROVIDER=fal, aber FAL_KEY fehlt“ hatasını verir. Kendi denetimi FEHLT gösterir. | fal.ai anahtarını `.env` dosyasına ekleyin veya `VIDEO_PROVIDER` alanını boş bırakın. |
| `ffmpeg`, `tesseract`, `pdftoppm`, sesli çıktı | İşlev eksiktir. Bunu kullanması gereken ajanlar hatayı sonuçta bildirir. Selbsttest FEHLER (Pi) ya da FEHLT (Windows) gösterir. | Programı kurun (komutlar selbsttest'te ve [docs/windows.md](docs/windows.md) dosyasında). |
| Telegram belirteci ya da sohbet kimliği | Telegram kapalı kalır, diğer her şey çalışır. Selbsttest FEHLT gösterir. | Yalnızca mesajları telefonunuza almak istiyorsanız gerekir. |
| Projede bir klasör ya da dosya (`wissen/`, `input/`) | Var olmayan klasörler boş sayılır. Ajanlar şirket bilgisi olmadan çalışmaya devam eder. | Projede dosyayı ya da klasörü oluşturun veya yükleyin. |

## İnternetten erişim

Uygulama kasıtlı olarak yalnızca `127.0.0.1` üzerinden dinler. Bir port açmak yerine bir tünel kullanırsınız.
Bu, mobil yönlendiriciniz gelen bağlantılara izin vermiyorsa (CGNAT) da gereklidir.

### Seçenek A (önerilen): Tailscale, özel, yalnızca kendi cihazlarınız için

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                    # tarayıcıda giriş bağlantısını açın
sudo tailscale serve --bg 8787       # yalnızca kendi tailnet'inizde HTTPS adresi
```

Tailscale'i telefonunuza/dizüstünüze de kurun, sonra gösterilen `https://dexter….ts.net` adresini açın.
`.env` dosyasına ekleyin: `TRUST_PROXY=1`, ardından hizmeti yeniden başlatın.
**`tailscale funnel` kullanmayın**; bu uygulamayı internete açık hale getirir.

### Seçenek B: Cloudflare Tunnel, kendi alan adınızla herkese açık adres

```bash
# cloudflared kurun (bkz. developers.cloudflare.com/cloudflare-one/connections/connect-networks)
cloudflared tunnel login
cloudflared tunnel create paperclip
cloudflared tunnel route dns paperclip agents.sizin-alaniniz.de
# ~/.cloudflared/config.yml:  ingress: - hostname: agents.sizin-alaniniz.de  service: http://127.0.0.1:8787
cloudflared tunnel run paperclip
```

Buna ek olarak şiddetle önerilir: önüne **Cloudflare Access** (e-posta girişi) koyun.
`.env` dosyasında: `TRUST_PROXY=1`. Komutlar değişebilir; emin değilseniz resmî kılavuz geçerlidir.

`TRUST_PROXY=1` ile uygulama yalnızca `APP_TOKEN` en az 12 karakter içeriyorsa başlar.

## Kullanım

| İşlem | Nasıl yapılır |
|---|---|
| Ajan oluşturma | paletteki girdiyi alana sürükleyin (ya da tıklayın) |
| Bağlama | bir düğümün alt noktasını başka bir düğüme sürükleyin (= patron → çalışan) |
| Bağlantıyı kesme | bağlantı çizgisine tıklayın |
| Taşıma | düğümü sürükleyin; arka planı sürüklemek görünümü kaydırır; fare tekerleği = yakınlaştırma |
| Ayarlama | düğüme tıklayın → sağdaki panel |
| Görev atama | Panel → „Aufgaben“ sekmesi (görevler) |
| Onaylama | kenar çubuğu „Freigaben“ (onaylar) |

## Şirket nasıl çalışır

Bir patron bir görev alır ve **planlar** (alt görevleri dağıtır) ya da işi kendisi yapar. Tüm
çalışanları bitirir bitirmez yeniden uyanır, **raporlarını okur**, eksikleri geri bildirimle iade eder ya da
her şeyi özetleyip kendi patronuna bildirir. Sonuç böylece istediğiniz kadar seviye yukarı çıkar.
„Wartet auf Team“ durumu (ekibi bekliyor) şu anlama gelir: patron ekibini bekliyor. Görevler sekmesinde tüm ağacı görürsünüz.

## Ajanların yetenekleri (internet, görseller, dosyalar)

Ajanlar turlar halinde çalışır: araç ister, sunucu çalıştırır ve sonuçları geri verir; bitene kadar böyle devam eder
(en fazla `PCL_MAX_TOOL_STEPS`). Ajan başına haklar: **internette araştırma**, **görseller**, **proje dosyalarını okuma**
(ve eskisi gibi dosya yazma).

| Araç | Ne yapar | Anahtarsız |
|---|---|---|
| `web_search` | web araması (yasalar, fiyatlar, rekabet …) | DuckDuckGo; daha iyisi: `SEARXNG_URL`, `BRAVE_API_KEY` ya da `TAVILY_API_KEY` |
| `fetch_url` | bir web sayfasını metin olarak okur | evet |
| `browse_page` | sayfayı gerçek bir tarayıcıda açar (JavaScript çalışır), isteğe bağlı olarak ajanın bir görsel olarak gördüğü bir ekran görüntüsüyle | evet, `./install.sh --browser` gerekir |
| `image_search` / `image_save` | özgür lisanslı fotoğrafları arar ve yazar ve lisansıyla birlikte `assets/` içine kaydeder | Openverse; isteğe bağlı `PEXELS_API_KEY` |
| `image_generate` | PNG olarak bir yapay zekâ görseli üretir; isteğe bağlı olarak projeden en fazla 4 referans görselle (bir dizide aynı figürler ve aynı stil), kare/dikey/yatay biçimle ve `assets/`, `output/` ya da `karten/` içinde hedef yolla. Hak **Görseller** veya **Medya** | Pollinations (anahtarsız: referans görselsiz; `POLLINATIONS_API_KEY` ve Pollen kredisiyle: model `POLLINATIONS_MODEL` ile, referans görsellerle); `IMAGE_STYLE` sabit bir çizim stili belirler; diğerleri: `nvidia` (build.nvidia.com üzerinden FLUX), `cloudflare` (Workers AI, referans görselli FLUX.2 klein), `hf` (Hugging Face), her biri için model `IMAGE_MODEL` ile; kendi bilgisayarınızda referans görselli ücretsiz: `IMAGE_PROVIDER=sdcpp` ([kılavuz](docs/laptop-bildrechner.md)); daha iyisi `OPENAI_API_KEY` ile `IMAGE_PROVIDER=openai`, `gemini`, ya da `OPENROUTER_API_KEY` ile `openrouter` |
| `list_files` / `read_file` | proje klasöründeki dosyaları okur (ör. meslektaşların metinleri) | evet |

Üretilen her şey `workspace/<proje-kimliği>/` altında durur. Kenar çubuğunda **📁 Dateien** (dosyalar) dosyaları gösterir, `index.html` dosyasını
bir web sayfası olarak açar (yalıtılmış sandbox) ve her şeyi ZIP olarak indirir. Bağlantı gizli bir anahtar içerir.

**Şirket şablonları** („Projekte“ yanında 🏢): *Web ajansı*, *Muhasebe/Mali müşavirlik*, *İthalat/İhracat ticareti* proje, organizasyon şeması, çalışma talimatları ve hakları eksiksiz oluşturur. Kendi şirketleriniz: proje hedefini yazın („siz bir …sınız“, ülke, sektör), ajanları ve hakları ayarlayın. Ajanlar tarihi ve proje hedefini alır; değişken bilgileri (yasalar, fiyatlar) önce araştırmalı ve kaynak göstermelidir.

**Araç güvenliği:** Sayfa çağrıları yalnızca genel adreslerle sınırlıdır (localhost, yerel ağ, Tailscale,
bulut meta verileri yok; yönlendirmeler tek tek denetlenir). Ajanlar için web içeriği güvenilmeyen veri sayılır,
ama hazırlanmış bir sayfa yine de bir modeli etkileyebilir: internet erişimi olan ajanlara kabuk (shell) vermeyin ve sonuçları kontrol edin.
Ajanların satın alma, sipariş, ödeme ya da e-posta gönderme için **hiçbir** aracı yoktur; yalnızca taslak ve öneri üretirler.
Görsel lisansları (CC) çoğu zaman atıf ister; görsel editörü bunu `bildnachweis.md` dosyasına yazar.

## Medya, belgeler ve kendi dosyalarınız

**Medya ve belge oluşturma** hakkıyla (ve Pi'de `ffmpeg`/yazı tipleriyle, bkz. `install.sh`):

| Araç | Neler yapabilir |
|---|---|
| `video_edit` | videoyu kesme (`trim`), birleştirme (`concat`), görsellerden **zoom'lu slayt gösterisi animasyonu** (`slideshow`, isteğe bağlı sesle), metin/altyazı/logo ekleme, sesi değiştirme ya da karıştırma, hızı değiştirme, GIF/WebM/MP3'e dönüştürme, durağan kare çıkarma |
| `speak` | metni konuşmacı sesine çevirir (espeak-ng çevrimdışı; daha iyisi: Piper; isteğe bağlı Edge sesleri) |
| `write_file` | **dosya yazma** hakkıyla: bölümleri, HTML, CSV vb. hemen oluşturur; böylece aynı görevde bunlardan bir PDF/DOCX/EPUB üretilebilir |
| `make_document` | Markdown bölümlerinden **PDF, DOCX, EPUB ya da HTML** (A4/A5, kapak, görseller, Almanca ve Türkçe karakterler); `html` ile **HTML+CSS**'ten serbest düzenli bir PDF (şablonları yeniden oluşturma, WeasyPrint ile, yalnızca proje dosyalarını yükler) |
| `video_generate` | metinden **yapay zekâ video klibi** (isteğe bağlı başlangıç görseliyle), yaklaşık 4–10 sn. Sağlayıcılar: Google'ın Gemini API'si (Google Flow'un arkasındaki model, başlangıç görseliyle) veya fal.ai (`VIDEO_PROVIDER=fal` + `FAL_KEY`, varsayılan model Kling, yalnızca metin). Varsayılan kapalı, `VIDEO_PROVIDER=gemini` veya `fal` ile açılır. **Video saniyesi başına ücret alır**; Flow/Google One aboneliği burada geçerli değildir |
| `media_info` | süre, çözünürlük, kodekler |
| `download_file` | PDF, EPUB, Office, ses, video, ZIP dosyalarını internetten `downloads/` klasörüne indirir |
| `read_file` | metin, Markdown, HTML, **PDF, DOCX, EPUB** okur; uzun dosyaları da bölümler halinde |
| `view_image` | görselleri, ekran görüntülerini, haritaları, düzenleri ve taranmış PDF sayfalarını **görür** (görsel anlayışı olan bir model gerekir, ör. Claude, GPT-4o, Gemini) |

**Öz denetim:** Bir ajan PDF oluşturduğunda sunucu bunu bir görsel olarak işler (tüm sayfaların genel görünümü + 1. sayfa büyük)
ve ajana gönderir; ajan bildirmeden önce görevin her gereksinimini kontrol edip hataları düzeltmekle yükümlüdür (`PCL_SELF_CHECKS`, varsayılan 1, 0 = kapalı).

**Kendi dosyalarınız** (düzenlenecek videolar, PDF'ler, görseller, düzenler, metinler) „📁 Dateien dieses Projekts“ bölümünde yüklenir ya da
doğrudan **💬 Chat** içinde bir ajana gönderilir (📎 düğmesi, sürükleyip bırakma ya da görsel yapıştırma, birden çok birden). Dosyalar
`input/` klasörüne düşer (adı temizlenir, mevcut dosyalar asla üzerine yazılmaz, bunun yerine `name-1.png` … olur, sınır `PCL_MAX_UPLOAD_MB`);
sohbette ajan **içeriği** doğrudan mesajla birlikte alır (metinler, PDF'ler, Word metin olarak, görseller görsel olarak, model görselleri anlıyorsa;
aksi halde metin tanıma). **📂 aus input/** ile zaten orada duran dosyaları ekleyebilir ya da mesajın içine dosya adını yazabilirsiniz; „Als Auftrag erteilen“ (görev olarak ver) bunu ekibe iletir. Biten sonuçlar `output/` içinde, görseller `assets/` içinde durur. Dürüst sınırlar: `video_generate` olmadan **yapay zekâ ile video üretimi yoktur** (metinden videoya); „Animation“ o zaman şu demektir: yapay zekâ görselleriyle sahne görüntüleri + zoom/kaydırma + konuşmacı + kurgu. `video_generate` ile kısa klipler oluşur; daha uzun filmler `video_edit op=concat` ile birleştirilir. MagicLight'ın API'si yoktur: orada üretilen videoları `input/` klasörüne yükleyin. Raspberry Pi'de
ffmpeg yavaş çalışır (720p videonun bir dakikası birkaç dakika sürebilir), zaman sınırı `PCL_FFMPEG_TIMEOUT` (adım başına varsayılan 1 saat).

**Taranmış PDF'ler ve görseller (OCR):** `read_file` taramaları `tesseract` ile otomatik okur (`sudo apt install tesseract-ocr tesseract-ocr-deu poppler-utils`). Bu yavaştır (Pi'de sayfa başına yaklaşık 5–15 sn, sınır `PCL_OCR_MAX_PAGES`) ve hatalar içerebilir.

**İyi bir konuşmacı sesi:** `./install.sh --piper` Piper'ı Almanca bir sesle kurar; bundan sonra Almanca metinler için otomatik kullanılır (diğer diller: espeak-ng).

## Sohbet ve şablonlar

- **💬 Chat sekmesi** (ajan panelinde): her ajanla serbest sohbet; örneğin *Düşünce atölyesi*'nin başıyla felsefe yapmak,
  fikir geliştirmek ve sorgulamak için. „📋 Als Auftrag erteilen“ sohbeti ajana ve ekibine devreder; sonuç bir gönderi olarak geri gelir.
  Sohbet araçsız çalışır.
- **Şirket şablonları** (🏢): Web ajansı, Muhasebe/Mali müşavirlik, İthalat/İhracat ticareti, **Animasyon ajansı**, **Kitap yayıncılığı/İçerik ajansı**,
  **Düşünce atölyesi**, **Araştırma bürosu** (PDF'leri bulur ve okur). Kurarken patron ve çalışanlar için model seçersiniz.

## Gönderi ve Telegram

Size ait bir **üst düzey görev** (bir ajana, genellikle CEO'ya verdiğiniz görev) bittiğinde, başarısız olduğunda ya da
engellendiğinde, sizin için bir gönderi hazır olur: kenar çubuğunda „📬 Post“ ve kuruluysa bir Telegram mesajı;
tür, görev, ekip rakamları ve sonuçla. Altındaki hak ve rapor zinciri eskisi gibi işler.

**Telegram'ı kurma (yaklaşık 2 dakika):**
1. Telegram'da `@BotFather` → `/newbot` → belirteci kopyalayın → `.env`: `TELEGRAM_BOT_TOKEN=…`
2. `sudo systemctl restart paperclip-lite`, yeni bota `/start` yazın → sohbet kimliğinizi size söyler.
3. `.env`: `TELEGRAM_CHAT_ID=…` girin, hizmeti yeniden başlatın. Web'de „Post“ altında bir test mesajı vardır.

**Telegram'da kullanım:**

| Siz yaparsınız | Sonuç |
|---|---|
| Yalnızca metin yazın | seçilen projenin patronuna yeni görev (`@Name Text` = belirli bir ajan) |
| Bir gönderi mesajına **yanıt verin** | görev, metninizi talimat olarak alıp yeniden işlenir |
| ✅ düğmesi ya da „ok“ yanıtı | görev tamamlandı olarak işaretlenir |
| Dosya, fotoğraf, albüm, video ya da sesli mesaj gönderin | seçilen projenin `input/` klasörüne düşer; resim altyazısı görev olur (bir gönderiye yanıt olarak: düzeltme için), metin yoksa dosya bir sonraki göreviniz için beklenir. Telegram botları yalnızca 20 MB'a kadar dosya indirebilir; daha büyüklerini web'den yükleyin |
| `/post`, `/status`, `/ok <No>`, `/neu <Metin>`, `/projekt [No]` | genel bakış ya da kısa komutlar |

Uygulama Telegram'ı yalnızca dışarıdan yoklar; hiçbir port açılmaz (CGNAT arkasında da çalışır). Yalnızca
`.env` içindeki sohbet kimliği komut verebilir; özel bir sohbet kullanın, grup değil. Kabuk komutları için onaylar bilerek
Telegram üzerinden **geçmez**; orada yalnızca bir uyarı gelir.

## Ajan başına haklar

- **Devretme**: görevleri *doğrudan* çalışanlara dağıtabilir (`PCL_MAX_DEPTH` seviyeye kadar, varsayılan 8).
  İsteğe bağlı olarak otomatik başlarlar; yoksa onları siz başlatırsınız.
- **Sonuçları değerlendirme**: patron işi geri bildirimle revizyona gönderebilir (çalışan başına en fazla 2 tur).
- **Okuma**: patronlar çalışanlarının raporlarını her zaman görür; bunun için ayrı bir hak gerekmez.
- **Dosya yazma**: yalnızca `workspace/<proje-kimliği>/` içinde; dışarıdaki yollar reddedilir.
- **Kod çalıştırma** (varsayılan kapalı): `run_code` bir sandbox'ta Python, JavaScript, Bash, Ruby, PHP ya da Lua başlatır, aşağıya bakın.
- **Kabuk önerme**: yalnızca sunucuda `PCL_ALLOW_SHELL=1` varsa ve ancak onaydan sonra.
- **Duraklatma**: ajanın tüm yeni görevlerini engeller.

Haklar **sunucuda** denetlenir. Bir model yanıtına izin verilmeyen bir eylem yazarsa, bu yok sayılır ve geçmişte kaydedilir.

## Yapay zekâ sağlayıcıları ve model seçimi

Ajan başına **sağlayıcı ve model** seçersiniz (panel → Ayarlar). Uygulama model listesini sağlayıcıdan canlı olarak çeker;
**▶ Test** ile anahtarı ve modeli hemen kontrol edersiniz. Her rol için doğru modeli böyle ayarlarsınız: patronlar için en güçlüsü
(planlama, kontrol, düşünme), çalışanlar için iyi metin ya da kod modelleri, basit işler için hızlı ve ucuz olanlar.

| Sağlayıcı | `.env` içinde anahtar | Not |
|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | Sonnet, Haiku, Opus … ajan başına seçilebilir |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | yüzlerce model için tek anahtar (Claude, GPT, Gemini, DeepSeek, Qwen, Llama …) |
| Groq, Gemini, DeepSeek, Qwen | `GROQ_API_KEY`, `GEMINI_API_KEY`, … | virgülle ayrılmış birden çok anahtar = sınıra gelince döndürme |
| Mistral, NVIDIA NIM, Together, Perplexity | `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `TOGETHER_API_KEY`, `PERPLEXITY_API_KEY` | Perplexity modelleri (`sonar`) webde kendileri arar |
| Hugging Face, Cloudflare Workers AI | `HF_TOKEN` ya da `CF_ACCOUNT_ID` + `CF_API_TOKEN` | küçük ücretsiz kotalar |
| Ollama | – | Pi üzerindeki yerel modeller |
| Claude (CLI, aboneliğiniz) / ChatGPT (Codex CLI, aboneliğiniz) | – | yerleşik: `claude -p --tools "" --strict-mcp-config --no-session-persistence` (Claude kendi araçları ve bağlayıcıları olmadan, yalnızca metin; çalışma talimatı Claude Code sistem istemini değiştirir) ya da `codex exec --skip-git-repo-check --ephemeral -` (Codex kendi başına salt okunur bir sandbox'ta çalışır), model açılır listede (Claude: sonnet/opus/haiku); `PCL_ALLOW_CLI=1` ve Pi'de oturumu açılmış program gerekir |
| CLI ajanı | – | istemi stdin'den okuyan bir komut, ör. `claude -p --model sonnet`; `PCL_ALLOW_CLI=1` gerekir |

**Önemli:** ChatGPT ya da Claude'un web girişi (OAuth, „abonelik“) temiz bir API olarak kullanılamaz; web oturumlarını ele geçirmek
kullanım koşullarını ihlal eder. Yollar: sağlayıcının **API anahtarı** (kullanıma göre faturalandırılır, sohbet aboneliği değil) ya da
bir kez oturum açılmış resmî CLI ile **CLI ajanı**. Uygulamada bütçe yoktur: ücretli API'lerde ve çok araç turunda
maliyet doğabilir; belirteçleri düğümde ajan başına görürsünüz.

## Güvenlik

- İmzalı çerezli giriş sayfası (7 gün, `HttpOnly`, `SameSite=Strict`, HTTPS arkasında `Secure`).
- 5 yanlış şifreden sonra IP başına 10 dakikalık kilit; tüm denemeler denetim günlüğünde durur.
- Yazma yapan API çağrılarının kendi başlığı olmalıdır (CSRF koruması), ayrıca CSP ve diğer başlıklar.
- Kabuk ve CLI ajanları varsayılan olarak **kapalıdır**. Şifreyi bilen ve `PCL_ALLOW_SHELL=1` ayarlayan biri,
  komutları uygulama kullanıcısının haklarıyla onaylayabilir. `workspace/` çalışma dizinidir, ama **sandbox değildir**.
- `.env`, veritabanı ve çalışma klasörleri `.gitignore` içindedir. Anahtarlar asla depoya ait değildir.
- Ticaret botlarında (NEXUS) ajanlara asla insan onayı olmadan işlem yaptırmayın.

## Şirket bilgisi ve hafıza

- **🧠 Şirket bilgisi** (kenar çubuğu): bir projenin tüm ajanlarının her zaman bilmesi gerekenler (şirket, müşteriler, stil, fiyatlar, kurallar). Projenin
  `wissen/firmenwissen.md` dosyasında durur. `wissen/` içindeki tüm `.md`/`.txt` dosyaları her görevde ve sohbette yer alır (toplam
  `PCL_KNOWLEDGE_CHARS` sınırına, varsayılan 8000 karaktere kadar); oradaki diğer belgeleri (PDF, Word …) ajanlar bir liste olarak görür ve gerektiğinde okur.
- **Ajan başına hafıza**: bir ajan bir görevin sonunda en fazla 5 kalıcı bilgiyi hatırlayabilir (tercihler, kararlar, müşteriler,
  işe yarayan şeyler). Bunlar ajan panelinde „🧠 Gedächtnis“ altında görünür; değiştirebilir ya da temizleyebilirsiniz. Sınır `PCL_MEMORY_CHARS`
  (4000); en eski kayıtlar önce çıkar. Her yeni not denetim günlüğündedir.

## Hedefler, onaylar, kullanım (Paperclip gibi)

- **🎯 Hedefler**: proje başına hedefler ve alt hedefler. Bir görev atarken isteğe bağlı olarak hedefi seçersiniz; devredilen görevler onu devralır.
  Patronlar hedefleri ilerlemeyle birlikte istemde görür, CEO'nun kontrol turu bunu raporlar. İşaretlenmesi = ulaşıldı.
- **Önce sorun** (✋ Freigaben penceresi, proje başına, varsayılan kapalı): *En üst patronun planını onayla* yeni bir görevi,
  siz dağıtım planını onaylayana kadar bekletir; *Yeni çalışanları onayla* CEO'nun kendi kendine kadro kurmasını bekletir. Onaylama/reddetme Telegram düğmesiyle de yapılır.
  Reddedilen görev gönderide ❌ olarak düşer; ona yanıtınız patronun yeniden planlamasını sağlar.
  Kabuk onayları yalnızca web'de yapılır.
- **📊 Kullanım ve maliyetler**: proje, ajan ve model başına çağrılar, belirteçler ve tahmini maliyetler (bugün, 7, 30 gün). Sınır yoktur.
  Abonelik CLI'leri ve Ollama 0 $ sayılır; `PCL_ABO_WARN_5H` değerinden (varsayılan 150, 0 = kapalı) itibaren 5 saatte abonelik çağrıları için Telegram uyarısı gelir.
  Fiyatlar kabaca tahmindir; kendi fiyatlarınızı `PCL_PRICES='{"sonnet": 5}'` ile girebilirsiniz (1 milyon belirteç başına US$, model adının parçası).

## Testler

```bash
./venv/bin/pip install pytest && ./venv/bin/python -m pytest -q tests
```
İnternet ve anahtar olmadan çalışır (sağlayıcı `mock`, kendi veritabanı).

## 🔌 Bağlantılar (webhook'lar)

- **Çıkış:** 🔌 Verbindungen penceresinde adresleri girersiniz (n8n, Zapier, Make, kendi hizmetiniz; Pi'de `http://127.0.0.1:…` de dahil),
  ajanlar için bir açıklama ve isteğe bağlı başlıklarla. Gizli bilgiler `.env` içinde durur ve `${NAME}` olarak kullanılır.
  **„Darf Verbindungen nutzen“** (bağlantıları kullanabilir) hakkı olan ajanlar bunları `call_connection` aracıyla çağırır; ajan adresi
  ya da başlıkları değiştiremez, yalnızca veri gönderir. **„Nur nach meiner Freigabe“** (yalnızca benim onayımdan sonra, varsayılan açık) her çağrıyı önce ✋ Freigaben altına koyar.
  **„Bei Post benachrichtigen“** (gönderide bildir), üst düzey bir görevin her biten sonucunu JSON olarak adrese yollar. Zaman sınırı `PCL_CONN_TIMEOUT` (30 sn).
- **Giriş:** „Aufträge von außen“ (dışarıdan görevler) açılırsa `POST /hook/<proje>/<anahtar>` ile `{"text": "…", "agent": "isteğe bağlı"}` gönderilerek
  patron için bir görev kabul edilir (ör. n8n, iOS kısayollarından ya da DEXTER'dan). Giriş gerektirmez; yalnızca adresteki anahtarla korunur.
  „Neuen Schlüssel“ (yeni anahtar) eski adresi geçersiz kılar. Adrese yalnızca PaperclipLite'in kendisi kadar erişilebilir (ör. yalnızca tailnet içinde).

## 🌐 Gerçek tarayıcı ve ▶ kod çalıştırma

- **Tarayıcı** (`./install.sh --browser`, Playwright + Chromium kurar, yaklaşık 400 MB, yalnızca 64 bit sistem): „Internet recherchieren“ (internette araştırma) hakkı olan ajanlar `browse_page` aracını alır.
  Sayfa JavaScript ile çalışır; ajan görünür metni, bağlantıları ve isteğe bağlı bir ekran görüntüsünü alır (`view_image` gibi bir görsel olarak görür; `save` onu `assets/screenshots/` içine kaydeder).
  Sayfanın her isteği (betikler, çerçeveler, XHR, WebSocket'ler) genel bir adrese gitmelidir; LAN/localhost engellenir, WebRTC ve indirmeler kapalıdır.
  Aynı anda yalnızca bir tarayıcı (RAM), zaman sınırı `PCL_BROWSER_TIMEOUT` (30 sn). Kendi Chromium'unuz: `PCL_BROWSER_PATH`; kapalı: `PCL_BROWSER=0`.
- **Kod çalıştırma** (`./install.sh --run`, bubblewrap kurar): „Darf Code ausführen“ (kod çalıştırabilir, varsayılan kapalı) hakkı `run_code` aracını verir.
  Betik yalıtılmış çalışır: **internet yok**, yalnızca `/usr` ve proje klasörü görünür (`/projekt` altında salt okunur),
  `.env` yok, veritabanı yok, ev klasörü yok. Betiğin çalışma dizinine yazdığı her şey `output/run/<zaman>/` içine düşer
  (en fazla 50 dosya/50 MB). Sınırlar: `PCL_RUN_TIMEOUT` (60 sn), `PCL_RUN_MEM_MB` (1024). Sistemin Python/Node'unu çalıştırır,
  yani yalnızca apt ile kurulmuş paketler (ör. `sudo apt install python3-pandas python3-matplotlib`). Genel olarak kapatmak: `PCL_ALLOW_RUN=0`.
  Kontrol: `./venv/bin/python selftest.py run browser`.

## Paralel çalışma

Aynı anda en fazla `PCL_WORKERS` görev çalışır (varsayılan 2, en fazla 6); örneğin bir patronun birden çok çalışanı ya da
farklı projelerin görevleri. Bir ajan asla aynı anda iki görev üzerinde çalışmaz ve aynı anda en fazla bir Ollama görevi çalışır
(Pi'deki RAM). Abonelik CLI'lerinde (Claude, Codex) paralel çağrılar abonelik sınırına daha hızlı ulaşır; bu durumda `PCL_WORKERS=1` ayarlayın.

## Bu sürümün sınırları

- Zamanlamaya göre otomatik bir heartbeat yoktur (görevler elle ya da devretmeyle başlar).
- Metinden videoya yapay zekâ yoktur, taranmış/görsel PDF'ler için OCR yoktur; CEO kendi başına yeni ajan işe almaz (organizasyon şemasını siz oluşturursunuz).
- Gerçek tarayıcı (`browse_page`) sayfaları okur ama tıklamaz ve form doldurmaz (giriş yok, satın alma yok). Anahtarsız DuckDuckGo araması sınırlı olabilir ya da değişebilir.
- Bütçe yoktur: belirteçler ve tahmini maliyetler yalnızca gösterilir (📊). Tur sınırları (revizyonlar, kontrol geçişleri, derinlik) sonsuz döngüleri önler.
- Oturumlar basit imzalı çerezlerdir; tek bir cihazın oturumu özel olarak kapatılamaz
  (şifre değiştirmek tüm oturumları geçersiz kılar).


## Selbsttest (öz test)

Kurulum ve anahtarların girilmesinden sonra `./venv/bin/python selftest.py` internet olmadan test edilemeyen her gerçek şeyi kontrol eder:
web araması, sayfa okuma, görsel araması ve görsel üretici, SSRF koruması, her yapay zekâ sağlayıcısı mini bir istekle (Ollama dahil),
Telegram (bot belirteci ve sohbet kimliğinize test mesajı), ffmpeg, sesli çıktı, Almanca karakterli PDF, OCR. Tek tek gruplar:
`selftest.py web | llm | telegram | media | ocr`. Her satır OK, FEHLT (isteğe bağlı) ya da somut bir notla FEHLER gösterir.

## Ollama (yerel modeller)

Sağlayıcı „Ollama (lokal)“: anahtar gerekmez, model listesi doğrudan Ollama'dan gelir (`ollama pull qwen2.5:3b`). „Firma aus Vorlage“ (şablondan şirket) penceresinde
„Alles lokal“ (her şey yerel) ve „Nur Mitarbeiter lokal“ (yalnızca çalışanlar yerel) düğmeleri vardır; aksi halde Ollama'yı ajan başına seçersiniz. Ollama başka bir bilgisayarda
çalışıyorsa (ör. dizüstü) `OLLAMA_URL` değerini onun adresine ayarlayın. Küçük modeller (3B) Pi'de yavaştır ve araç protokolüne çoğu zaman zayıf uyar;
patronlar için güçlü bir model, yerel olarak daha çok basit çalışanlar ya da sohbet için uygundur.

## Claude ve ChatGPT aboneliğinizle (API anahtarı yerine CLI)

`.env` içinde: `PCL_ALLOW_CLI=1`. Programları Pi'de kendiniz kurup bir kez oturum açarsınız (üreticilerin kılavuzları:
Claude Code `claude`, OpenAI Codex `codex`; aboneliğinizle giriş). Bundan sonra „Claude (CLI, dein Abo)“ ve „ChatGPT (Codex-CLI, dein Abo)“
tüm sağlayıcı listelerinde görünür. Sunucu bunları bir kabuk olmadan, boş bir klasörde ve **ortamda API anahtarlarımız olmadan** çağırır
(aksi halde `claude` aboneliği değil API anahtarını faturalandırırdı). Sınırlar: API'den yavaştır (her yanıtta program başlatma), abonelik sınırları geçerlidir
(çok ajan = hızla sınıra), ve CLI programlarının kendi araçları vardır; gerekirse komutu `PCL_CLI_CLAUDE` / `PCL_CLI_CODEX` ile uyarlayın.

## Model gitti mi? Ajanları değiştirin

PaperclipLite her 6 saatte bir (`PCL_MODEL_CHECK_HOURS`) ajanların modellerinin sağlayıcıda hâlâ var olup olmadığını kontrol eder ve bir çağrı „Modell nicht gefunden“ (model bulunamadı) bildirdiğinde de fark eder. O zaman bir Telegram mesajı gelir, görev açık bir notla başarısız olur ve **⚠ Modelle** (modeller) menüsünde etkilenen tüm ajanları tek tıkla başka bir modele çevirirsiniz.

## Büyük ekipler

Bir patronun istediği kadar çalışanı olabilir. Patronun panelinde (Ayarlar) **Unterstellte Mitarbeiter** (bağlı çalışanlar) altında onay kutularıyla hepsini seçer ve atamayı kaydedersiniz. Alternatif olarak: patronun alt noktasını bir çalışanın üzerine sürükleyin. **🗂 Ordnen** (düzenle) düğmesi her şeyi bir organizasyon şeması olarak oluşturur (6 ve üzeri çalışanlı gruplar, 5'erli sıralar halinde).

## CEO ekibini kendisi kurar

Palettedeki CEO, **„Darf sein Team selbst zusammenstellen“** (kendi ekibini kurabilir, `recruit`) hakkına sahiptir. Henüz çalışanı yoksa ve bir görev alırsa, görevi analiz eder ve rol, çalışma talimatı ve raporlama hatlarıyla çalışanlar oluşturur (20'ye kadar; kendi ekibi olan bölüm başkanları da dahil). Yeni çalışanların **henüz yapay zekâsı yoktur**: bunları **⚠ Modelle** menüsünde (hepsini birden) ya da ajan başına ayarlarda atarsınız; sonra görevin altındaki **Post**'a yanıt verirsiniz (ör. „Weiter“ = devam). Bundan sonra CEO işi her zamanki gibi dağıtır. CEO yeni çalışanlara yalnızca web, görseller, dosya okuma/yazma ve medya verebilir, asla kabuk vermez.

## Çalışma saatleri ve günlük görevler

Kenar çubuğunda **🕘 Zeitplan** (zamanlama): proje başına iş başlangıcı, mesai bitişi ve çalışma günlerini belirleyin. Her çalışan için **günlük görevler** oluşturabilirsiniz (sabit saat, iş başlangıcında ya da mesai bitişinde, seçilebilir haftanın günlerinde), ör. „her gün 15:00'te web sitesini kontrol et“. Sonuç her gönderi gibi „Post“ görünümüne (ve Telegram'a) gelir. Bir zamanlamanın son görevi hâlâ çalışıyorsa tekrar başlatılmaz; saatte Pi kapalıysa 6 saate kadar telafi edilir.
İş başlangıcında şirket yarım kalan görevleri yeniden alır (başlamamış olanlar başlar, başarısız üst düzey görevler `PCL_MAX_RESUMES`=2 kereye kadar yeniden denenir). İsteğe bağlı olarak şirket çalışma saatleri dışında tamamen dinlenir. Saat Pi'nin saatidir; yanlışsa `.env` içine `PCL_TZ=Europe/Vienna` yazın.

## CEO kontrol turu

**🕘 Zeitplan** penceresinde **👑 CEO-Kontrollgang** (CEO kontrol turu) en üst patron için günlük bir kontrol turu kurar (varsayılan: mesai bitişinde; diğer saatler „Neue tägliche Aufgabe“ + *Kontrollgang* onay kutusuyla). Sistem ona olgularla bir **durum raporu** ekler: çalışan başına bugün başlayan/biten/başarısız olan/açık kalan işler, çalışma saatleri dışındaki başlangıçlar, iş başlangıcı olmayan açık görevler, yapay zekâsı olmayan çalışanlar, yarım kalan görevler ve günlük görevlerin çalışıp çalışmadığı. CEO bunu değerlendirir, gerekirse ekibine takip görevleri dağıtır ve gönderiye bir kontrol raporu yazar. „📋 Statusbericht ansehen“ (durum raporunu gör) CEO olmadan olguları gösterir.

## Proje klasörü

Her projenin `workspace/` altında **kendi adını taşıyan bir klasörü** vardır (ör. `workspace/Buchverlag-Content-Agentur/`, Almanca karakterler dönüştürülür). Proje yeniden adlandırıldığında aynı kalır ve bir proje silindiğinde **asla silinmez**. Aynı adla yeni bir proje oluşturursanız, mevcut klasörü dosyalarıyla birlikte devralır. Eski numara klasörleri (`workspace/1`, `workspace/2` …) başlangıçta otomatik olarak proje adına yeniden adlandırılır.

## Web sayfası yayınlama

**📁 Dateien dieses Projekts** penceresinde **🚀 Veröffentlichen** (yayınla) vardır. Yalnızca proje klasöründeki `www/` klasörü yayınlanır (`www/index.html`, bununla birlikte CSS, görseller … göreli yollarla); projedeki diğer her şey (notlar, `output/`, `input/`, nokta dosyaları, dışarıya simgesel bağlantılar) görünmez kalır. `www/` klasörü yoksa proje klasörünün `index.html` dosyası eskisi gibi sunulur (`input/` ve gizli dosyalar olmadan). Sayfa kendi bağlantı noktasında (8800'den itibaren, `PCL_SITE_PORT_BASE`) kalıcı olarak çalışır; varsayılan olarak yalnızca Pi'nin kendisinde: `http://127.0.0.1:8800/`. Ağdan erişim için `.env` içinde `PCL_SITE_HOST=0.0.0.0` ayarlayın. „Darf die Webseite zur Veröffentlichung vorschlagen“ (web sayfasını yayınlamayı önerebilir) hakkına sahip ajanlar „veröffentlichen“ için bir onay isteyebilir; sayfayı çevrimiçi yapan yalnızca **Freigaben** altındaki tıklamanızdır. Ajanların değişiklikleri hemen görünür; yeniden başlatmadan sonra sayfa otomatik olarak yeniden çalışır. Açık internet için önüne HTTPS'li bir ters vekil (ör. Caddy) konmalıdır; küçük sunucunun kendisi değil.
