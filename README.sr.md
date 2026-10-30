# PaperclipLite

🌐 Jezici: [Deutsch](README.md) · [English](README.en.md) · [Türkçe](README.tr.md) · **Srpski** · [Bosanski](README.bs.md) · [Hrvatski](README.hr.md)

Tim agenata veštačke inteligencije kao uređivač čvorova, samostalno hostovan, dovoljno lagan za Raspberry Pi.
Napravite projekat, prevucite agente na površinu, povežite ih (šef → saradnik), podesite AI provajdera, radno uputstvo i prava po čvoru i dodelite zadatke.

> Detaljna uputstva u `docs/` su trenutno napisana samo na nemačkom. Nazivi dugmadi i menija u aplikaciji ostaju na nemačkom.

## Instalacija

PaperclipLite je Python program (Flask + SQLite) i radi na više sistema. Više instalacija
može raditi paralelno; svaka ima svoje firme i podatke.

| Sistem | Stanje | Uputstvo |
| --- | --- | --- |
| Raspberry Pi / Linux (Debian, Ubuntu) | glavni sistem, pun obim funkcija | dole |
| Windows 10/11 | radi, bez `run_code`, neke funkcije traže dodatne programe | [docs/windows.md](docs/windows.md) |
| macOS | nije testirano, osnovne funkcije bi trebalo da rade | dole (ručno) |
| Sopstveni računar za slike (npr. stari laptop bez grafičke kartice) | besplatne slike sa referentnim slikama za PaperclipLite | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) |

Selidba sa jednog računara na drugi: zaustavite PaperclipLite i kopirajte `data.db`, folder `workspace/` i `.env`
([primer Pi → Windows](docs/windows.md)).

### Raspberry Pi / Linux

```bash
git clone https://github.com/KhungFu/paperclip-lite && cd paperclip-lite
./install.sh --service     # venv, zavisnosti, .env sa nasumičnom lozinkom, systemd servis
nano .env                  # unesite API ključeve, zatim: sudo systemctl restart paperclip-lite
```

Bez servisa: `./install.sh`, pa `./venv/bin/python app.py` → http://127.0.0.1:8787.
Lozinka za prijavu nalazi se u `.env` (`APP_TOKEN`). Ažuriranje, ponovno pokretanje, rezerva: [Rad](#rad-ko-šta-gde-kada-i-kako).
Više funkcija (video, OCR, kompajleri, pregledač): `./install.sh --all`.

### Windows

PowerShell u folderu PaperclipLite:

```powershell
git clone https://github.com/KhungFu/paperclip-lite; cd paperclip-lite
powershell -ExecutionPolicy Bypass -File install.ps1
notepad .env
deploy\windows\paperclip-start.bat
```

Šta nedostaje na Windowsu, automatsko pokretanje i paralelni rad sa Pi-jem: [docs/windows.md](docs/windows.md).
Kasnije ažuriranje: `git pull`, pa ponovo pokrenite.

### macOS (nije testirano)

```bash
git clone https://github.com/KhungFu/paperclip-lite && cd paperclip-lite
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env       # upišite APP_TOKEN=<dugačka lozinka>, dodajte API ključeve
./venv/bin/python app.py   # http://127.0.0.1:8787
```

`install.sh` je napravljen za Debian/Ubuntu (apt), pa na macOS-u radite ručno kao gore. Dodatni programi preko Homebrew-a
(`brew install ffmpeg tesseract poppler`). `run_code` postoji samo na Linuxu.

### Slike na sopstvenom računaru

Računar u kućnoj mreži (i bez grafičke kartice, bar 8 GB RAM-a) može za PaperclipLite besplatno da pravi slike sa
referentnim slikama. U `.env` ostavite aktivne tačno ove dve linije (samo jedna `IMAGE_PROVIDER=` linija bez `#`):

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://<IP računara za slike>:1234    # na samom računaru za slike: http://127.0.0.1:1234
```

Podešavanje: [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md).

### Animirani filmovi uz Blender

Ako je Blender instaliran na računaru na kojem radi PaperclipLite, agenti prave crtane filmove: likove sa sopstvenim glasovima i
pokretima usta, scene, kameru, titlove, gotov film sa zvukom (alat `film`, predložak firme „🐶 Animationsstudio“).
Ako PaperclipLite sam ne pronađe Blender, upišite ga u `.env`:

```
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```

Uputstvo i format scenarija (na nemačkom): [docs/filmstudio.md](docs/filmstudio.md).

## Rad: ko šta, gde, kada i kako

**Ko:** sve ovo radi vlasnik računara (vi), a ne agenti. Komande se izvršavaju u
folderu PaperclipLite: na Pi-ju u terminalu (`cd ~/paperclip-lite`), na Windowsu u PowerShell-u
(`cd $HOME\paperclip-lite`, ili gde god ste stavili folder).

### Kratak pregled

| Šta | Kada | Raspberry Pi / Linux (sa servisom) | Windows |
| --- | --- | --- | --- |
| Pokretanje | posle instalacije, posle ponovnog pokretanja bez automatskog starta | `sudo systemctl start paperclip-lite` | dvoklik na `deploy\windows\paperclip-start.bat` (prozor ostavite otvoren) |
| Zaustavljanje | pre selidbe, rezerve, ažuriranja | `sudo systemctl stop paperclip-lite` | zatvorite prozor za pokretanje (ili u njemu Ctrl+C) |
| Ponovno pokretanje | posle svake promene u `.env`, posle ažuriranja | `sudo systemctl restart paperclip-lite` | zatvorite prozor za pokretanje, ponovo pokrenite `paperclip-start.bat` |
| Radi li? | kada ima problema | `systemctl status paperclip-lite` | da li je prozor za pokretanje otvoren? Pregledač: <http://127.0.0.1:8787> |
| Pregled dnevnika | kod grešaka | `journalctl -u paperclip-lite -f` (Ctrl+C prekida) | prikazuje se u prozoru za pokretanje |
| Ažuriranje | kada postoji nova verzija (npr. posle spojenog pull request-a) | vidi dole | vidi dole |
| Provera | posle instalacije, ažuriranja, novih ključeva | `./venv/bin/python selftest.py` | `venv\Scripts\python.exe selftest.py` |
| Ključevi / podešavanja | novi ključ, drugi provajder slika | `nano .env`, pa ponovo pokrenite | `notepad .env`, pa ponovo pokrenite |
| Rezerva | redovno, pre selidbe i većih ažuriranja | kopirajte `data.db`, `workspace/`, `.env` (prvo zaustavite) | isto u folderu PaperclipLite |

### Ažuriranje (preuzimanje nove verzije)

**Raspberry Pi / Linux**, u terminalu:

```bash
cd ~/paperclip-lite
git pull
./install.sh               # potrebno samo ako se requirements.txt promenio; .env ostaje nepromenjen
sudo systemctl restart paperclip-lite
./venv/bin/python selftest.py llm     # kratka provera da li AI provajderi odgovaraju
```

**Windows**, u PowerShell-u:

1. `cd $HOME\paperclip-lite`
2. `git pull`
3. Samo ako su se paketi promenili (ili kada niste sigurni): `powershell -ExecutionPolicy Bypass -File install.ps1`
   (postojeći `.env` ostaje nepromenjen).
4. Zatvorite crni prozor za pokretanje PaperclipLite-a.
5. Ponovo pokrenite `deploy\windows\paperclip-start.bat` (dvoklik ili upišite u PowerShell).
6. Provera: `venv\Scripts\python.exe selftest.py llm`

Ako `git pull` javi „local changes would be overwritten“, sami ste promenili neki fajl programa.
`git stash` odlaže promenu na stranu, zatim ponovite `git pull`. Vaši podaci (`data.db`, `workspace/`, `.env`)
nikada nisu ugroženi, jer ih Git ne poznaje.

### Automatsko pokretanje

- **Pi:** `./install.sh --service` podešava servis; on se onda sam pokreće pri svakom podizanju sistema.
- **Windows:** Win+R, upišite `shell:startup` i tamo stavite prečicu do `deploy\windows\paperclip-start.bat`
  (i do `bildrechner-start.bat`, ako ga koristite). Windows se za to mora sam prijaviti
  ([docs/windows.md](docs/windows.md), odeljak 4).

### Menjanje podešavanja u `.env`

- Svako podešavanje stoji tačno jednom, bez `#` na početku. Redovi sa `#` su isključeni. Kod dupliranih redova
  važi prvi.
- Posle svake promene ponovo pokrenite PaperclipLite, inače važi stari stanje.
- Ključeve nikada ne kopirajte u četove, snimke ekrana ili repozitorijum. Ako je ključ ipak negde završio: opozovite ga kod provajdera i unesite novi.
- Zatim proverite sa `selftest.py`. Pojedinačne oblasti: `selftest.py llm`, `web`, `telegram`, `media`, `ocr`, `code`.

### Čitanje samoprovere

- **OK:** radi.
- **FEHLT (nedostaje):** opciono; red navodi komandu za dodavanje (na Windowsu komandu za Windows).
  Potrebno samo ako to vaši agenti koriste (npr. video, glasovni izlaz, skenirani PDF-ovi).
- **FEHLER (greška):** nešto što ste uneli ne radi, najčešće nevažeći ili istekao ključ ili servis koji
  ne radi (npr. računar za slike). Red navodi razlog.
- Pojedinačni timeout kod web servisa je često samo privremen: pokušajte kasnije.

### Računar za slike (ako se koristi)

- **Gde:** na računaru koji pravi slike (npr. laptop), u folderu `C:\bildrechner`.
- **Kada:** mora da radi dok agenti treba da prave slike.
- **Kako se podešava (jednom):** u PowerShell-u u folderu PaperclipLite
  `powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1` (preuzima program i modele).
- **Kako se pokreće:** pokrenite `C:\bildrechner\bildrechner-start.bat`, prozor ostavite otvoren. U `.env` fajlu PaperclipLite-a
  `IMAGE_PROVIDER=sdcpp` i `SDCPP_URL=...` ([uputstvo](docs/laptop-bildrechner.md)), zatim ponovo pokrenite PaperclipLite.

### Filmski studio (ako se koristi)

- **Gde:** na računaru sa Blenderom (npr. laptop). Firma sa alatom `film` mora raditi u **ovoj** instanci PaperclipLite.
- **Kada:** Blender ne mora biti otvoren, PaperclipLite ga za svaku scenu pokreće u pozadini i ponovo zatvara.
- **Provera:** `venv\Scripts\python.exe selftest.py film` (Windows) ili `./venv/bin/python selftest.py film`.
- **Koliko traje:** pri 640×360 i 12 sličica u sekundi, zavisno od laptopa, oko 1 do 5 minuta po 10 sekundi filma. Blender nikad ne radi istovremeno sa računarom za slike.

### Selidba (npr. Pi → laptop)

Korak po korak u [docs/windows.md](docs/windows.md), „Phase 2 – Umzug“ (na nemačkom). Ukratko: zaustavite oba, kopirajte `data.db`,
`workspace/` i `.env`, pokrenite na novom računaru i proverite, pa tek onda isključite stari.
Telegram unosite samo na jednom računaru.

### Šta se dešava kada nešto nedostaje

Ova lista se dopunjuje pri svakoj promeni programa. Svaki red kaže šta sistem radi i šta vi treba da uradite.

| Nedostaje | Šta sistem radi | Šta vi radite |
| --- | --- | --- |
| `.env` | PaperclipLite se pokreće bez ključeva i bez lozinke, dostupan samo sa ovog računara. Sa `HOST=0.0.0.0` pokretanje se prekida dok je `APP_TOKEN` prazan. | `./install.sh` (Pi) odnosno `install.ps1` (Windows) ga pravi sa nasumičnom lozinkom. |
| `data.db` | Pravi se nov i prazan. Firme, zadaci i pošta su nestali. | Prvo napravite rezervu (vidi Rad). Vraćajte samo iz rezerve. |
| API ključ u `.env` | Provajder se u samoproveri prijavljuje kao FEHLT i agenti ga ne koriste. Ako je unet, ali nevažeći: FEHLER sa HTTP 401. | Unesite ključ ili isključite red sa `#`. |
| `SDCPP_URL` (uz `IMAGE_PROVIDER=sdcpp`) | Zahtevi za slike ne uspevaju uz poruku „SDCPP_URL fehlt“ (nedostaje). Uz `IMAGE_FALLBACK=pollinations` pravi se besplatna zamenska slika bez referenci, uz napomenu u rezultatu. | Dodajte red u `.env`, ponovo pokrenite PaperclipLite. |
| Računar za slike nije dostupan (laptop isključen, firewall, pogrešna IP) | Kao gore: greška „Bildrechner … nicht erreichbar“ (nije dostupan), uz rezervu zamenska slika. | Uključite laptop, pokrenite `bildrechner-start.bat`, proverite IP i firewall. |
| `sd-server.exe` (Windows, računar za slike) | `bildrechner-start.bat` prikazuje „sd-server.exe fehlt“ (nedostaje) i ništa ne pokreće. | Pokrenite `deploy\windows\bildrechner-einrichten.ps1`. |
| Fajl modela (Windows, računar za slike) | Startni fajl navodi nedostajući fajl i ne pokreće se. Ako nedostaje samo veliki jezički model (`Qwen3-4B-Q4_K_M.gguf`), koristi manji, ako postoji. | Ponovo pokrenite skriptu za podešavanje; preuzima samo nedostajući fajl. |
| Windows runtime `VCOMP140.DLL` | `sd-server.exe` javlja „VCOMP140.DLL nicht gefunden“ (nije pronađen) i prekida rad. | Ponovo pokrenite skriptu za podešavanje (korak 3 instalira runtime), pa otvorite startni fajl. |
| Pravilo firewall-a za port 1234 (Windows) | Samo Pi ne može da dođe do računara za slike. Sam laptop radi dalje. | Pokrenite komandu iz [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md), odeljak 4, kao administrator. |
| `ffmpeg`, `tesseract`, `pdftoppm`, glasovni izlaz | Funkcija nedostaje. Agenti koji je traže prijavljuju grešku u rezultatu. Samoprovera prikazuje FEHLER (Pi) odnosno FEHLT (Windows). | Instalirajte program (komande u samoproveri i u [docs/windows.md](docs/windows.md)). |
| Blender (alat `film`) | `save`, `check`, `voices` i `assemble` i dalje rade. `preview` i `render` javljaju „Blender wurde nicht gefunden“ (Blender nije pronađen) uz napomenu o `BLENDER_PATH`. Samoprovera prikazuje FEHLT. | Instalirajte Blender (`winget install BlenderFoundation.Blender`) ili postavite `BLENDER_PATH` u `.env`, ponovo pokrenite. |
| `film/film.json` (scenario) | `film` javlja „film/film.json fehlt“ (nedostaje) i traži da se prvo sa `op=save` sačuva scenario. Neispravan scenario se ne čuva, odgovor navodi sve greške. | Ništa, agenti ga sami prave. Možete ga napisati i ručno ([docs/filmstudio.md](docs/filmstudio.md)). |
| Slika, muzika ili `.blend` fajl naveden u scenariju | Provera navodi scenu, lik i putanju, ništa se ne renderuje. | Stavite fajl u `assets/` ili `input/` ili ispravite putanju u scenariju. |
| Klip scene (`film/clips/`) | `assemble` navodi scene koje nedostaju i ništa ne montira. Ako se `render` prekine (vremensko ograničenje), gotove sličice ostaju sačuvane i sledeći poziv nastavlja odatle. | Ništa, agenti ponovo pozivaju `render`. |
| Govor za film | `voices`/`render` se prekidaju porukom „Keine Sprachausgabe verfügbar“ (nema govora). Scene bez dijaloga i dalje rade. | Kao kod „govora“ iznad (na Windowsu `edge-tts` + `TTS_ENGINE=edge`). |
| Telegram token ili ID čata | Telegram ostaje isključen, sve ostalo radi. Samoprovera prikazuje FEHLT. | Potrebno samo ako želite poruke na telefonu. |
| Folder ili fajl u projektu (`wissen/`, `input/`) | Folderi koji ne postoje smatraju se praznim. Agenti rade dalje bez znanja o firmi. | Napravite ili otpremite fajl ili folder u projektu. |

## Pristup sa interneta

Aplikacija namerno sluša samo na `127.0.0.1`. Umesto otvaranja porta koristite tunel.
Ovo je potrebno i ako vaš mobilni ruter ne dozvoljava dolazne veze (CGNAT).

### Opcija A (preporučeno): Tailscale, privatno, samo za vaše uređaje

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                    # otvorite link za prijavu u pregledaču
sudo tailscale serve --bg 8787       # HTTPS adresa samo u sopstvenom tailnet-u
```

Instalirajte Tailscale i na telefon/laptop, pa otvorite prikazanu adresu `https://dexter….ts.net`.
U `.env` dodajte: `TRUST_PROXY=1`, zatim ponovo pokrenite servis.
**Ne** koristite `tailscale funnel`, to bi aplikaciju stavilo na javni internet.

### Opcija B: Cloudflare Tunnel, javna adresa sa sopstvenim domenom

```bash
# instalirajte cloudflared (vidi developers.cloudflare.com/cloudflare-one/connections/connect-networks)
cloudflared tunnel login
cloudflared tunnel create paperclip
cloudflared tunnel route dns paperclip agents.vas-domen.de
# ~/.cloudflared/config.yml:  ingress: - hostname: agents.vas-domen.de  service: http://127.0.0.1:8787
cloudflared tunnel run paperclip
```

Dodatno se snažno preporučuje: stavite ispred **Cloudflare Access** (prijava e-poštom).
U `.env`: `TRUST_PROXY=1`. Komande se mogu menjati; u sumnji važi zvanično uputstvo.

Sa `TRUST_PROXY=1` aplikacija se pokreće samo ako `APP_TOKEN` ima najmanje 12 znakova.

## Rukovanje

| Radnja | Kako se radi |
|---|---|
| Napravite agenta | prevucite stavku iz palete na površinu (ili kliknite na nju) |
| Povežite | prevucite donju tačku čvora na drugi čvor (= šef → saradnik) |
| Prekinite vezu | kliknite na liniju veze |
| Pomeranje | prevucite čvor; prevlačenje pozadine = pomeranje prikaza; točkić miša = zumiranje |
| Podešavanje | kliknite čvor → panel desno |
| Dodelite zadatak | panel → kartica „Aufgaben“ (zadaci) |
| Odobravanje | bočna traka „Freigaben“ (odobrenja) |

## Kako firma radi

Šef dobija zadatak i **planira** (raspoređuje podzadatke) ili ga sam obavlja. Čim su svi
saradnici gotovi, on se ponovo budi, **čita njihove izveštaje**, vraća nedostatke uz povratnu informaciju ili
sažima sve i izveštava svog šefa. Tako se rezultat penje kroz koliko god nivoa.
Status „Wartet auf Team“ (čeka tim) znači: šef čeka svoje ljude. U kartici zadataka vidite celo stablo.

## Mogućnosti agenata (internet, slike, fajlovi)

Agenti rade u krugovima: traže alate, server ih izvršava i vraća rezultate, sve dok nisu
gotovi (najviše `PCL_MAX_TOOL_STEPS`). Prava po agentu: **pretraga interneta**, **slike**, **čitanje fajlova projekta**
(i, kao ranije, pisanje fajlova).

| Alat | Šta radi | Bez ključa |
|---|---|---|
| `web_search` | pretraga weba (zakoni, cene, konkurencija …) | DuckDuckGo; bolje: `SEARXNG_URL`, `BRAVE_API_KEY` ili `TAVILY_API_KEY` |
| `fetch_url` | čita web stranicu kao tekst | da |
| `browse_page` | otvara stranicu u pravom pregledaču (JavaScript radi), opciono sa snimkom ekrana koju agent vidi kao sliku | da, treba `./install.sh --browser` |
| `image_search` / `image_save` | traži slobodno licencirane fotografije i čuva ih u `assets/`, sa autorom i licencom | Openverse; opciono `PEXELS_API_KEY` |
| `image_generate` | pravi AI sliku kao PNG, opciono sa do 4 referentne slike iz projekta (isti likovi i stil kroz seriju), format kvadrat/vertikalno/horizontalno i ciljna putanja u `assets/`, `output/` ili `karten/`. Pravo **Slike** ili **Mediji** | Pollinations (bez ključa: bez referentnih slika; sa `POLLINATIONS_API_KEY` i Pollen kreditom: model preko `POLLINATIONS_MODEL`, sa referentnim slikama); `IMAGE_STYLE` postavlja fiksni stil crtanja; ostali: `nvidia` (FLUX preko build.nvidia.com), `cloudflare` (Workers AI, FLUX.2 klein sa referentnim slikama), `hf` (Hugging Face), model svakog preko `IMAGE_MODEL`; besplatno sa referentnim slikama na sopstvenom računaru: `IMAGE_PROVIDER=sdcpp` ([uputstvo](docs/laptop-bildrechner.md)); bolje `IMAGE_PROVIDER=openai` sa `OPENAI_API_KEY`, `gemini`, ili `openrouter` sa `OPENROUTER_API_KEY` |
| `list_files` / `read_file` | čita fajlove u folderu projekta (npr. tekstove kolega) | da |

Sve što se napravi nalazi se pod `workspace/<id-projekta>/`. U bočnoj traci **📁 Dateien** prikazuje fajlove, otvara `index.html`
kao web stranicu (izolovan sandbox) i preuzima sve kao ZIP. Link sadrži tajni ključ.

**Šabloni firmi** (🏢 pored „Projekte“): *Web agencija*, *Računovodstvo/poreska kancelarija*, *Uvoz/izvoz trgovina* prave projekat,
organigram, radna uputstva i prava u potpunosti. Sopstvene firme: napišite cilj projekta („vi ste …“, zemlja,
delatnost), podesite agente i prava. Agenti dobijaju datum i cilj projekta i treba da prvo istraže stvari koje se menjaju (zakoni,
cene) i navedu izvore.

**Bezbednost alata:** preuzimanje stranica ograničeno je na javne adrese (bez localhost-a, LAN-a, Tailscale-a,
metapodataka iz clouda; preusmeravanja se proveravaju pojedinačno). Za agente sadržaj weba važi kao nepouzdan podatak,
ali pripremljena stranica ipak može uticati na model: ne dajte agentima sa pristupom internetu shell i proveravajte rezultate.
Agenti namerno **nemaju** alate za kupovine, narudžbine, plaćanja ili slanje e-pošte; daju nacrte i preporuke.
Licence za slike (CC) često traže navođenje autora; urednik slika to upisuje u `bildnachweis.md`.

## Mediji, dokumenti i sopstveni fajlovi

Uz pravo **pravljenje medija i dokumenata** (i `ffmpeg`/fontovi na Pi-ju, vidi `install.sh`):

| Alat | Šta može |
|---|---|
| `video_edit` | seče video (`trim`), spaja (`concat`), **animaciju slajd-šou sa zumom** iz slika (`slideshow`, opciono sa zvukom), dodaje tekst/titlove/logo, menja ili meša zvuk, menja brzinu, pretvara u GIF/WebM/MP3, izvlači nepomičan kadar |
| `speak` | pretvara tekst u glas govornika (espeak-ng offline; bolje: Piper; opciono Edge glasovi), uz `voice`, `pitch`, `rate` za različite glasove |
| `film` | **animirani film uz Blender**: scenario kao JSON, likovi (pas, mačka, zec, medved, miš, čovek, sopstvene slike ili `.blend` likovi), glasovi sa pokretima usta, pokreti, kamera, slika pregleda, renderovanje scenu po scenu, montaža sa titlovima ([uputstvo](docs/filmstudio.md)) |
| `write_file` | uz pravo **pisanje fajlova**: odmah pravi poglavlja, HTML, CSV itd., tako da se u istom zadatku od njih može napraviti PDF/DOCX/EPUB |
| `make_document` | iz Markdown poglavlja **PDF, DOCX, EPUB ili HTML** (A4/A5, naslovna strana, slike, dijakritici i turski znakovi); sa `html` PDF slobodnog rasporeda iz **HTML+CSS** (pravljenje šablona, preko WeasyPrint-a, učitava samo fajlove iz projekta) |
| `video_generate` | **AI video klip** iz teksta (opciono sa početnom slikom), oko 4–10 s, preko Google Gemini API-ja (model iza Google Flow-a). Podrazumevano isključeno, uključuje se sa `VIDEO_PROVIDER=gemini` + `GEMINI_API_KEY`. **Naplaćuje se po sekundi videa**; Flow/Google One pretplata se ovde ne računa |
| `media_info` | trajanje, rezolucija, kodeci |
| `download_file` | preuzima PDF, EPUB, Office, audio, video, ZIP sa interneta u `downloads/` |
| `read_file` | čita tekst, Markdown, HTML, **PDF, DOCX, EPUB**, i duge fajlove po delovima |
| `view_image` | **vidi** slike, snimke ekrana, mape, rasporede i stranice skeniranih PDF-ova (treba model sa razumevanjem slika, npr. Claude, GPT-4o, Gemini) |

**Samokontrola:** kada agent napravi PDF, server ga posle toga prikaže kao sliku (pregled svih stranica + 1. stranica uvećano) i pošalje
mu uz obavezu da proveri svaki zahtev zadatka i ispravi greške pre nego što javi (`PCL_SELF_CHECKS`, podrazumevano 1, 0 = isključeno).

**Sopstveni fajlovi** (video za obradu, PDF-ovi, slike, rasporedi, tekstovi) otpremate u „📁 Dateien dieses Projekts“ ili ih šaljete
direktno u **💬 Chat** sa agentom (dugme 📎, prevucite ih ili nalepite sliku, više odjednom). Završe u
`input/` (ime se čisti, postojeći fajlovi se nikada ne prepisuju nego postaju `name-1.png` …, granica `PCL_MAX_UPLOAD_MB`);
u četu agent dobija **sadržaj** direktno uz poruku (tekstovi, PDF-ovi, Word kao tekst, slike kao slike, ako model razume slike;
inače prepoznavanje teksta). Sa **📂 aus input/** dodajete fajlove koji već stoje tamo, ili jednostavno upišete ime fajla u poruku, a „Als Auftrag erteilen“ (pošalji kao zadatak) to prosleđuje timu; gotovi rezultati su u `output/`, slike u `assets/`. Iskrena ograničenja: bez `video_generate` **nema AI generisanja videa** (tekst u video);
„animacija“ tada znači: scene kao slike uz AI slike + zum/pomeranje + govornik + montaža, ili prava animacija likova uz Blender preko alata `film`. Uz `video_generate` nastaju
kratki klipovi; duži filmovi se sastavljaju sa `video_edit op=concat`. MagicLight nema API: videe napravljene tamo otpremite u `input/`. Na Raspberry Pi-ju
ffmpeg radi sporo (jedan minut 720p videa može trajati nekoliko minuta), vremensko ograničenje `PCL_FFMPEG_TIMEOUT` (podrazumevano 1 sat po koraku).

**Skenirani PDF-ovi i slike (OCR):** `read_file` automatski čita skenove preko `tesseract` (`sudo apt install tesseract-ocr tesseract-ocr-deu poppler-utils`). To je sporo (oko 5–15 s po stranici na Pi-ju, granica `PCL_OCR_MAX_PAGES`) i može sadržati greške.

**Dobar glas govornika:** `./install.sh --piper` podešava Piper sa nemačkim glasom; posle toga se automatski koristi za nemačke tekstove (ostali jezici: espeak-ng).

## Čet i šabloni

- **💬 Chat kartica** (u panelu agenta): slobodan razgovor sa svakim agentom, npr. sa vođom *Gedankenwerkstatt*-a, za filozofiranje,
  razvijanje ideja i preispitivanje. „📋 Als Auftrag erteilen“ prosleđuje razgovor agentu i njegovom timu; rezultat se vraća kao objava.
  Čet radi bez alata.
- **Šabloni firmi** (🏢): Web agencija, Računovodstvo/poreska kancelarija, Uvoz/izvoz trgovina, **Animaciona agencija**, **Izdavačka kuća/agencija sadržaja**,
  **Radionica ideja**, **Istraživački biro** (pronalazi i čita PDF-ove). Pri osnivanju birate model za vođu i saradnike.

## Pošta i Telegram

Čim je **zadatak na vrhu** (onaj koji ste dali agentu, obično CEO-u) gotov, neuspešan ili
blokiran, pošta je spremna za vas: u bočnoj traci „📬 Post“ i, ako je podešeno, poruka na Telegramu sa
vrstom, zadatkom, brojevima tima i rezultatom. Lanac prava i izveštaja ispod radi kao i ranije.

**Podešavanje Telegrama (oko 2 minuta):**
1. U Telegramu `@BotFather` → `/newbot` → kopirajte token → `.env`: `TELEGRAM_BOT_TOKEN=…`
2. `sudo systemctl restart paperclip-lite`, novom botu pošaljite `/start` → on vam kaže vaš ID čata.
3. `.env`: upišite `TELEGRAM_CHAT_ID=…`, ponovo pokrenite servis. Na webu pod „Post“ postoji probna poruka.

**Rad u Telegramu:**

| Vi radite | Rezultat |
|---|---|
| Samo napišete tekst | novi zadatak šefu izabranog projekta (`@Ime Tekst` = određeni agent) |
| **Odgovorite** na poruku pošte | zadatak se ponovo obrađuje sa vašim tekstom kao uputstvom |
| Dugme ✅ ili odgovor „ok“ | zadatak se označava kao završen |
| Pošaljete fajl, fotografiju, album, video ili glasovnu poruku | završi u `input/` izabranog projekta; natpis postaje zadatak (kao odgovor na objavu: za doradu), bez teksta fajl ide vašem sledećem zadatku. Telegram botovi smeju da preuzmu fajlove do 20 MB, veće otpremite preko weba |
| `/post`, `/status`, `/ok <Br.>`, `/neu <Tekst>`, `/projekt [Br.]` | pregled odnosno kratke komande |

Aplikacija Telegram samo pita spolja, ne otvara se nijedan port (radi i iza CGNAT-a). Samo ID čata iz
`.env` sme da daje komande; koristite privatan čet, ne grupu. Odobrenja za shell komande namerno
**ne** idu preko Telegrama; tamo stiže samo napomena.

## Prava po agentu

- **Delegiranje**: sme da dodeljuje zadatke *neposrednim* saradnicima (do `PCL_MAX_DEPTH` nivoa, podrazumevano 8).
  Opciono se sami pokreću, inače ih pokrećete sami.
- **Ocenjivanje rezultata**: šef sme da vrati posao sa povratnom informacijom na doradu (najviše 2 kruga po saradniku).
- **Čitanje**: šefovi uvek vide izveštaje svojih saradnika; za to nije potrebno posebno pravo.
- **Pisanje fajlova**: samo u `workspace/<id-projekta>/`; putanje van toga se odbijaju.
- **Pokretanje koda** (podrazumevano isključeno): `run_code` pokreće Python, JavaScript, Bash, Ruby, PHP ili Lua u sandbox-u, vidi dole.
- **Predlaganje shell-a**: samo ako server ima `PCL_ALLOW_SHELL=1`, i tada uvek tek posle odobrenja.
- **Pauza**: blokira sve nove zadatke agenta.

Prava se proveravaju **na serveru**. Ako model u svom odgovoru napiše nedozvoljenu radnju, ona se ignoriše i beleži u istoriji.

## Dobavljači AI-ja i izbor modela

Za svakog agenta birate **dobavljača i model** (panel → Podešavanja). Aplikacija modele uživo preuzima od dobavljača;
sa **▶ Test** odmah proveravate ključ i model. Tako postavljate odgovarajući model po ulozi: najjači za šefove
(planiranje, provera, razmišljanje), dobri modeli za tekst ili kod za saradnike, brzi i jeftini za jednostavan posao.

| Dobavljač | Ključ u `.env` | Napomena |
|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | Sonnet, Haiku, Opus … bira se po agentu |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | jedan ključ za stotine modela (Claude, GPT, Gemini, DeepSeek, Qwen, Llama …) |
| Groq, Gemini, DeepSeek, Qwen | `GROQ_API_KEY`, `GEMINI_API_KEY`, … | više ključeva odvojenih zarezom = rotacija kada se dostigne limit |
| Mistral, NVIDIA NIM, Together, Perplexity | `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `TOGETHER_API_KEY`, `PERPLEXITY_API_KEY` | Perplexity modeli (`sonar`) sami pretražuju web |
| Hugging Face, Cloudflare Workers AI | `HF_TOKEN` odnosno `CF_ACCOUNT_ID` + `CF_API_TOKEN` | male besplatne kvote |
| Ollama | – | lokalni modeli na Pi-ju |
| Claude (CLI, vaša pretplata) / ChatGPT (Codex CLI, vaša pretplata) | – | ugrađeno: `claude -p --tools "" --strict-mcp-config --no-session-persistence` (Claude bez sopstvenih alata i konektora, samo tekst; radno uputstvo zamenjuje sistemski prompt Claude Code-a) odnosno `codex exec --skip-git-repo-check --ephemeral -` (Codex sam radi u sandbox-u samo za čitanje), model u padajućem meniju (Claude: sonnet/opus/haiku); treba `PCL_ALLOW_CLI=1` i prijavljen program na Pi-ju |
| CLI agent | – | komanda koja čita prompt sa stdin-a, npr. `claude -p --model sonnet`; treba `PCL_ALLOW_CLI=1` |

**Važno:** web prijava (OAuth, „pretplata“) kod ChatGPT-a ili Claude-a ne može se čisto koristiti kao API; preuzimanje
web sesija krši uslove korišćenja. Putevi: **API ključ** dobavljača (naplata po potrošnji, ne čet pretplata) ili
**CLI agent** sa zvaničnim CLI-jem, jednom prijavljenim. Aplikacija nema budžet: kod plaćenih API-ja i mnogo krugova sa alatima
mogu nastati troškovi; belehe po agentu vidite na čvoru.

## Bezbednost

- Stranica za prijavu sa potpisanim kolačićem (7 dana, `HttpOnly`, `SameSite=Strict`, `Secure` iza HTTPS-a).
- Posle 5 pogrešnih lozinki zaključavanje od 10 minuta po IP adresi; svi pokušaji su u dnevniku revizije.
- Pišući API pozivi moraju imati sopstveno zaglavlje (CSRF zaštita), uz CSP i dodatna zaglavlja.
- Shell i CLI agenti su podrazumevano **isključeni**. Ko zna lozinku i ima postavljeno `PCL_ALLOW_SHELL=1`,
  može da odobri komande sa pravima korisnika aplikacije. `workspace/` je radni direktorijum, ali **nije sandbox**.
- `.env`, baza podataka i radni folderi su u `.gitignore`. Ključevi nikada ne pripadaju repozitorijumu.
- Kod botova za trgovanje (NEXUS) agentima nikada ne dozvolite trgovinu bez ljudskog odobrenja.

## Znanje firme i pamćenje

- **🧠 Znanje firme** (bočna traka): ono što svi agenti projekta uvek treba da znaju (firma, klijenti, stil, cene, pravila). Stoji u
  `wissen/firmenwissen.md` u folderu projekta. Svi `.md`/`.txt` fajlovi u `wissen/` idu uz svaki zadatak i u čet (zajedno do
  `PCL_KNOWLEDGE_CHARS`, podrazumevano 8000 znakova); ostale dokumente tamo (PDF, Word …) agenti vide kao spisak i čitaju po potrebi.
- **Pamćenje po agentu**: agent na kraju zadatka može da zapamti najviše 5 trajnih činjenica (preference, odluke, klijenti,
  šta je radilo). One se prikazuju u panelu agenta pod „🧠 Gedächtnis“ (pamćenje); možete ih menjati ili brisati. Granica `PCL_MEMORY_CHARS`
  (4000); najstariji unosi prvi ispadaju. Svaka nova beleška je u dnevniku revizije.

## Ciljevi, odobrenja, upotreba (kao kod Paperclipa)

- **🎯 Ciljevi**: ciljevi i podciljevi po projektu. Pri dodeljivanju zadatka opciono birate cilj; delegirani zadaci ga nasleđuju.
  Šefovi vide ciljeve sa napretkom u promptu, a CEO-ov kontrolni obilazak to izveštava. Označeno = ostvareno.
- **Prvo pitaj** (prozor ✋ Freigaben, po projektu, podrazumevano isključeno): *Odobri plan najvišeg šefa* zadržava novi zadatak
  dok ne odobrite plan raspodele; *Odobri nove saradnike* zadržava CEO-ovo samostalno kadriranje. Odobravanje/odbijanje i preko
  Telegram dugmeta. Odbijeno = zadatak završi kao ❌ u pošti; vaš odgovor na to tera šefa da ponovo planira.
  Odobrenja za shell i dalje idu samo preko weba.
- **📊 Upotreba i troškovi**: pozivi, tokeni i procenjeni troškovi po projektu, agentu i modelu (danas, 7, 30 dana). Bez limita.
  Pretplatni CLI-ji i Ollama broje se kao 0 $; od `PCL_ABO_WARN_5H` pretplatnih poziva u 5 sati (podrazumevano 150, 0 = isključeno) stiže upozorenje na Telegramu.
  Cene su grube procene; sopstvene zadajte preko `PCL_PRICES='{"sonnet": 5}'` (US$ po 1 milion tokena, deo naziva modela).

## Testovi

```bash
./venv/bin/pip install pytest && ./venv/bin/python -m pytest -q tests
```
Radi bez interneta i bez ključeva (dobavljač `mock`, sopstvena baza).

## 🔌 Veze (webhook-ovi)

- **Izlaz:** u prozoru 🔌 Verbindungen unosite adrese (n8n, Zapier, Make, sopstvena usluga; i `http://127.0.0.1:…` na Pi-ju),
  sa opisom za agente i opcionim zaglavljima. Tajne pripadaju `.env` i koriste se kao `${NAME}`.
  Agenti sa pravom **„Darf Verbindungen nutzen“** (sme da koristi veze) zovu ih alatom `call_connection`; agent ne može da menja
  adresu ni zaglavlja, samo šalje podatke. **„Nur nach meiner Freigabe“** (samo posle mog odobrenja, podrazumevano uključeno) svaki poziv prvo stavlja pod ✋ Freigaben.
  **„Bei Post benachrichtigen“** (obavesti u pošti) šalje svaki gotov rezultat zadatka na vrhu kao JSON na adresu. Vremensko ograničenje `PCL_CONN_TIMEOUT` (30 s).
- **Ulaz:** uključite „Aufträge von außen“ (zadaci spolja), zatim `POST /hook/<projekat>/<ključ>` sa `{"text": "…", "agent": "opciono"}`
  prima zadatak za šefa (npr. iz n8n, iOS prečica ili DEXTER-a). Bez prijave; štiti ga samo ključ u adresi.
  „Neuen Schlüssel“ (novi ključ) poništava staru adresu. Dostupna je samo onoliko koliko je dostupan i sam PaperclipLite (npr. samo u tailnet-u).

## 🌐 Pravi pregledač i ▶ pokretanje koda

- **Pregledač** (`./install.sh --browser`, instalira Playwright + Chromium, oko 400 MB, samo 64-bitni sistem): agenti sa pravom
  „Internet recherchieren“ (istraživanje interneta) dobijaju `browse_page`. Stranica radi uz JavaScript; agent dobija vidljiv tekst, veze i
  po želji snimak ekrana (vidi ga kao kod `view_image`; `save` ga čuva u `assets/screenshots/`). Svaki zahtev stranice
  (skripte, okviri, XHR, WebSocket-i) mora da ide na javnu adresu; LAN/localhost je blokiran, WebRTC i preuzimanja su isključeni.
  Samo jedan pregledač u isto vreme (RAM), vremensko ograničenje `PCL_BROWSER_TIMEOUT` (30 s). Sopstveni Chromium: `PCL_BROWSER_PATH`, isključeno: `PCL_BROWSER=0`.
- **Pokretanje koda** (`./install.sh --run`, instalira bubblewrap): pravo „Darf Code ausführen“ (sme da pokreće kod, podrazumevano isključeno) daje `run_code`.
  Skripta radi izolovano: **bez interneta**, vidljivi su samo `/usr` i folder projekta (samo za čitanje pod `/projekt`),
  bez `.env`-a, bez baze, bez kućnog foldera. Ono što skripta upiše u svoj radni direktorijum završi u `output/run/<vreme>/`
  (najviše 50 fajlova/50 MB). Granice: `PCL_RUN_TIMEOUT` (60 s), `PCL_RUN_MEM_MB` (1024). Pokreće Python/Node sistema,
  dakle samo pakete instalirane preko apt-a (npr. `sudo apt install python3-pandas python3-matplotlib`). Globalno isključeno: `PCL_ALLOW_RUN=0`.
  Provera: `./venv/bin/python selftest.py run browser`.

## Paralelni rad

Istovremeno može da radi do `PCL_WORKERS` zadataka (podrazumevano 2, najviše 6), npr. više saradnika jednog šefa ili zadaci
različitih projekata. Agent nikada ne radi na dva zadatka odjednom, a istovremeno radi najviše jedan Ollama zadatak
(RAM na Pi-ju). Kod pretplatnih CLI-ja (Claude, Codex) paralelni pozivi brže dostižu limit pretplate; tada postavite `PCL_WORKERS=1`.

## Granice ove verzije

- Nema automatskog heartbeat-a po rasporedu (zadaci se pokreću ručno ili delegiranjem).
- Nema AI za tekst u video, nema OCR za skenirane/slikovne PDF-ove; CEO sam ne zapošljava nove agente (organigram pravite vi).
- Pravi pregledač (`browse_page`) čita stranice, ali ne klikće i ne popunjava formulare (bez prijava, bez kupovina). Pretraga DuckDuckGo-a bez ključa može biti ograničena ili promenjena.
- Nema budžeta: tokeni i procenjeni troškovi se samo prikazuju (📊). Limiti krugova (dorade, provere, dubina) sprečavaju beskonačne petlje.
- Sesije su proste potpisane kolačići; jedan uređaj ne može se posebno odjaviti
  (promena lozinke poništava sve sesije).


## Samoprovera

Posle instalacije i unosa ključeva `./venv/bin/python selftest.py` proverava sve stvarne stvari koje se bez interneta nisu mogle testirati:
web pretragu, čitanje stranica, pretragu slika i generator slika, SSRF zaštitu, svakog AI provajdera mini zahtevom (uključujući Ollama),
Telegram (token bota i probna poruka na vaš ID čata), ffmpeg, glasovni izlaz, PDF sa dijakriticima, OCR. Pojedinačne grupe:
`selftest.py web | llm | telegram | media | ocr | film`. Svaki red prikazuje OK, FEHLT (opciono) ili FEHLER sa konkretnom napomenom.

## Ollama (lokalni modeli)

Dobavljač „Ollama (lokal)“: ključ nije potreban, lista modela dolazi direktno iz Ollama (`ollama pull qwen2.5:3b`). U dijalogu „Firma aus Vorlage“ (firma iz šablona)
postoje dugmad „Alles lokal“ (sve lokalno) i „Nur Mitarbeiter lokal“ (samo saradnici lokalno); inače Ollama birate po agentu. Ako Ollama radi na drugom računaru
(npr. laptopu), postavite `OLLAMA_URL` na njegovu adresu. Mali modeli (3B) su na Pi-ju spori i često loše drže protokol alata;
za šefove jak model, lokalno pre svega za jednostavne saradnike ili čet.

## Claude i ChatGPT preko vaše pretplate (CLI umesto API ključa)

U `.env`: `PCL_ALLOW_CLI=1`. Programe sami instalirate i jednom prijavljujete na Pi-ju (uputstva proizvođača:
Claude Code `claude`, OpenAI Codex `codex`; prijava sa vašom pretplatom). Posle toga se „Claude (CLI, dein Abo)“ i „ChatGPT (Codex-CLI, dein Abo)“
pojavljuju u svim listama dobavljača. Server ih poziva bez shell-a, u praznom folderu i **bez naših API ključeva u okruženju**
(inače bi `claude` naplaćivao API ključ umesto pretplate). Ograničenja: sporije od API-ja (pokretanje programa po odgovoru), važe limiti pretplate
(mnogo agenata = brzo do limita), a CLI programi imaju sopstvene alate; po potrebi prilagodite komandu preko `PCL_CLI_CLAUDE` / `PCL_CLI_CODEX`.

## Model nestao? Prebacite agente

PaperclipLite svakih 6 sati (`PCL_MODEL_CHECK_HOURS`) proverava da li modeli agenata još postoje kod dobavljača i primećuje i kada poziv javi „Modell nicht gefunden“ (model nije pronađen). Tada stiže Telegram poruka, zadatak pada uz jasnu napomenu, a u meniju **⚠ Modelle** sve pogođene agente prebacujete na drugi model jednim klikom.

## Veliki timovi

Šef može da ima koliko god hoćete saradnika. U panelu šefa (Podešavanja) pod **Unterstellte Mitarbeiter** (podređeni saradnici) označite sve potvrdnim poljima i sačuvajte dodelu. Alternativno: prevucite donju tačku šefa na saradnika. Dugme **🗂 Ordnen** (poredaj) pravi ceo organigram (grupe od 6 i više saradnika u redovima po 5).

## CEO sam sastavlja svoj tim

CEO iz palete ima pravo **„Darf sein Team selbst zusammenstellen“** (sme sam da sastavi svoj tim, `recruit`). Ako još nema saradnike i dobije zadatak, analizira ga i pravi saradnike sa ulogom, radnim uputstvom i linijama izveštavanja (do 20, uključujući šefove odeljenja sa sopstvenim timom). Novi saradnici **još nemaju AI**: dodeljujete ih u meniju **⚠ Modelle** (svi odjednom) ili po agentu u podešavanjima, pa odgovorite u **Pošti** na zadatak (npr. „Weiter“ = nastavi). Posle toga CEO raspoređuje posao kao i obično. CEO novim saradnicima može da da samo web, slike, čitanje/pisanje fajlova i medije, nikada shell.

## Radno vreme i dnevni zadaci

Bočna traka **🕘 Zeitplan** (raspored): za svaki projekat postavite početak rada, kraj rada i radne dane. Za svakog saradnika možete napraviti **dnevne zadatke** (fiksno vreme, na početku ili na kraju rada, na izabranim danima u nedelji), npr. „svaki dan u 15:00 proveri web sajt“. Rezultat stiže u prikaz „Post“ kao svaka objava (i preko Telegrama). Ako je poslednji zadatak nekog rasporeda još u toku, ne pokreće se dvaput; ako je Pi u to vreme bio isključen, nadoknađuje se do 6 sati.
Na početku rada firma ponovo preuzima zadatke koji su ostali nezavršeni (nepokrenuti se pokreću, neuspešni zadaci na vrhu ponavljaju se do `PCL_MAX_RESUMES`=2 puta). Opciono firma potpuno miruje van radnog vremena. Vreme je ono sa Pi-ja; ako nije tačno, u `.env` postavite `PCL_TZ=Europe/Vienna`.

## CEO kontrolni obilazak

U prozoru **🕘 Zeitplan** **👑 CEO-Kontrollgang** (CEO kontrolni obilazak) podešava dnevni kontrolni obilazak najvišeg šefa (podrazumevano: na kraju rada; ostala vremena preko „Neue tägliche Aufgabe“ + potvrdno polje *Kontrollgang*). Sistem mu prilaže **statusni izveštaj** sa činjenicama: po saradniku danas započeto/završeno/neuspešno/otvoreno, počeci rada van radnog vremena, otvoreni zadaci bez početka rada, saradnici bez AI, nezavršeni zadaci i da li su dnevni zadaci izvršeni. CEO to procenjuje, po potrebi raspoređuje naredne zadatke svom timu i u pošti piše kontrolni izveštaj. „📋 Statusbericht ansehen“ (pogledaj statusni izveštaj) prikazuje činjenice bez CEO-a.

## Folder projekta

Svaki projekat ima **folder sa svojim imenom** pod `workspace/` (npr. `workspace/Buchverlag-Content-Agentur/`, nemački znaci se transkribuju). Ostaje isti kada se projekat preimenuje i **nikada se ne briše kada se projekat obriše**. Ako napravite novi projekat istog imena, preuzima postojeći folder sa fajlovima. Stari folderi sa brojevima (`workspace/1`, `workspace/2` …) se pri pokretanju automatski preimenuju po imenu projekta.

## Objavljivanje web stranice

U prozoru **📁 Dateien dieses Projekts** postoji **🚀 Veröffentlichen** (objavi). Objavljuje se **samo folder `www/` u folderu projekta** (`www/index.html`, uz CSS, slike … sa relativnim putanjama); sve ostalo u projektu (beleške, `output/`, `input/`, tačka-fajlovi, simboličke veze ka spoljašnjosti) ostaje nevidljivo. Ako nema foldera `www/`, isporučuje se, kao ranije, `index.html` iz foldera projekta (bez `input/` i skrivenih fajlova). Stranica trajno radi na sopstvenom portu (od 8800, `PCL_SITE_PORT_BASE`), podrazumevano samo na samom Pi-ju: `http://127.0.0.1:8800/`. Za pristup u mreži u `.env` postavite `PCL_SITE_HOST=0.0.0.0`. Agenti sa pravom „Darf die Webseite zur Veröffentlichung vorschlagen“ (sme da predloži web stranicu za objavu) mogu da zatraže odobrenje za „veröffentlichen“; stranicu na mreži tek vaš klik pod **Freigaben** pušta online. Promene agenata su odmah vidljive; posle ponovnog pokretanja stranica se sama ponovo pokreće. Za otvoreni internet ispred mora da stoji reverzni proksi sa HTTPS-om (npr. Caddy), a ne mali server.
