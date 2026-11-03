# ☁️ Dateien hochladen: GitHub, Google Drive, OneDrive, Telegram

PaperclipLite kann fertige Dateien aus einem Projekt hochladen:

- **Du selbst:** 📁 Dateien → Knopf ☁️ neben der Datei → Ziel und Ordner wählen → Hochladen. Danach bekommst du den Link.
- **Agenten:** nur mit dem Recht **„Darf in die Cloud hochladen“** (setzt nur du, der CEO kann es nicht vergeben).
  Jeder Upload eines Agenten wartet unter ✋ Freigaben auf deinen Klick (dazu kommt eine Telegram-Nachricht). Der Link steht dann im Auftrag.
- **Am Handy:** `/datei` im Telegram-Chat zeigt die neuesten Dateien des Projekts als Knöpfe, `/datei plan` sucht nach „plan“.
  Telegram nimmt Dateien bis 50 MB.

Das Fenster **☁️ Cloud** in der Seitenleiste zeigt, welcher Dienst bereit ist, und legt den **Zielordner je Projekt** fest
(Standard: `PaperclipLite/<Projektname>`). Nennst du einem Agenten im Auftrag einen Ordner, legt er ihn darunter an.
Beim Hochladen von Hand gilt der Ordner, den du im Dialog eintippst.

Alle Zugangsdaten stehen in `.env`. Die Anmeldung bei Google und Microsoft speichert PaperclipLite in `tokens/`
neben `.env` (nicht in der Datenbank, nicht im Projektordner, Agenten sehen den Ordner nicht). Pi und Laptop melden sich je
einmal selbst an. Nach jeder Änderung an `.env` PaperclipLite neu starten.

## GitHub (ca. 5 Minuten)

1. **Ablage-Repo anlegen:** github.com → oben rechts **+** → **New repository** → Name z. B. `paperclip-ablage` →
   **Private** → **Add a README file** anhaken (das Repo darf nicht leer sein) → **Create repository**.
2. **Token anlegen:** github.com → Profilbild → **Settings** → ganz unten **Developer settings** → **Personal access tokens** →
   **Fine-grained tokens** → **Generate new token**.
   - Name: `PaperclipLite`, Ablauf: z. B. 1 Jahr.
   - **Repository access:** *Only select repositories* → `paperclip-ablage`.
   - **Permissions → Repository permissions → Contents:** *Read and write*.
   - **Generate token**, den Token (beginnt mit `github_pat_`) kopieren. Er wird nur einmal angezeigt.
3. In `.env`:
   ```
   GITHUB_UPLOAD_TOKEN=github_pat_...
   GITHUB_UPLOAD_REPO=DEIN-NAME/paperclip-ablage
   # GITHUB_UPLOAD_BRANCH=main        # leer = Standard-Branch des Repos
   # GITHUB_UPLOAD_RELEASE=paperclip-ablage   # Release für Dateien über 50 MB
   ```

Dateien bis 50 MB landen als Datei im Repo (gleicher Name = neue Version, die alte bleibt in der Historie).
Größere Dateien (Filme) hängt PaperclipLite an ein Release namens `paperclip-ablage` (bis 2 GB je Datei).

Bitte **nicht** das Repo `paperclip-lite` selbst nehmen, sonst landen Ergebnisse zwischen dem Programmcode.

## Google Drive (ca. 10 Minuten, einmalig)

1. <https://console.cloud.google.com> öffnen, oben **Projekt auswählen → Neues Projekt** → Name `PaperclipLite` → Erstellen.
2. **APIs & Dienste → Bibliothek** → „Google Drive API“ suchen → **Aktivieren**.
3. **APIs & Dienste → OAuth-Zustimmungsbildschirm** (heißt auch „Google Auth Platform“):
   App-Name `PaperclipLite`, deine E-Mail, Zielgruppe **Extern**. Unter **Datenzugriff** nichts eintragen.
   Danach unter **Zielgruppe** auf **App veröffentlichen** („In Produktion“). Sonst läuft die Anmeldung nach 7 Tagen ab.
   Eine Prüfung durch Google ist nicht nötig, weil PaperclipLite nur das kleinste Drive-Recht nutzt.
4. **Clients → Client erstellen** → Typ **Fernseher und Geräte mit begrenzter Eingabe** → Name `PaperclipLite` → Erstellen.
   Client-ID und Clientschlüssel kopieren.
5. In `.env`:
   ```
   GDRIVE_CLIENT_ID=....apps.googleusercontent.com
   GDRIVE_CLIENT_SECRET=GOCSPX-...
   # GDRIVE_FOLDER_ID=     # optional: ID eines Ordners, den PaperclipLite selbst angelegt hat, als Startpunkt
   ```
6. PaperclipLite neu starten → **☁️ Cloud → Google Drive → Anmelden**. Es erscheint ein Code. Öffne
   <https://www.google.com/device> am Handy oder PC, gib den Code ein und erlaube den Zugriff.
   Google zeigt evtl. „Google hat diese App nicht überprüft“ → **Erweitert → Weiter zu PaperclipLite**.

**Wichtig:** Google erlaubt Geräten ohne Tastatur nur das Recht `drive.file`. PaperclipLite sieht daher nur Dateien
und Ordner, die es selbst angelegt hat, nicht den Rest deines Drive. Ordner, die du von Hand angelegt hast, sieht es nicht:
Gib einfach den Pfad an (z. B. `Kunden/Müller`), PaperclipLite legt die Ordner selbst an und benutzt sie danach wieder.

## OneDrive (ca. 5 Minuten, einmalig)

1. <https://entra.microsoft.com> mit deinem Microsoft-Konto öffnen → **Anwendungen → App-Registrierungen → Neue Registrierung**.
   - Name `PaperclipLite`.
   - Kontotypen: **Nur persönliche Microsoft-Konten** (bei einem Firmenkonto: „Konten in einem beliebigen Organisationsverzeichnis und
     persönliche Microsoft-Konten“ und in `.env` `ONEDRIVE_TENANT=common`).
   - Umleitungs-URI leer lassen → **Registrieren**.
2. **Authentifizierung → Erweiterte Einstellungen → Öffentliche Clientflows zulassen: Ja** → Speichern.
3. Auf der Übersichtsseite die **Anwendungs-ID (Client)** kopieren und in `.env` eintragen:
   ```
   ONEDRIVE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```
4. PaperclipLite neu starten → **☁️ Cloud → OneDrive → Anmelden** → <https://www.microsoft.com/link> öffnen, Code eingeben, zustimmen.

PaperclipLite darf in deinem ganzen OneDrive schreiben (Recht `Files.ReadWrite`), damit du jeden Ordner angeben kannst.
Fehlende Ordner legt OneDrive an, eine Datei mit gleichem Namen wird ersetzt. Die Anmeldung erneuert sich bei jeder Nutzung.
Nach 90 Tagen ohne Upload musst du dich neu anmelden.

## Telegram

Nichts weiter einzurichten, wenn `TELEGRAM_BOT_TOKEN` und `TELEGRAM_CHAT_ID` schon gesetzt sind (siehe README, „Post und Telegram“).
Dateien gehen nur auf deinen Klick (☁️ im Web, `/datei` im Chat) oder nach deiner Freigabe an deinen Chat.

## Probleme

| Meldung | Lösung |
| --- | --- |
| „nicht eingerichtet: … fehlt in .env“ | Zeile in `.env` eintragen, neu starten. |
| „noch nicht angemeldet“ | ☁️ Cloud → Anmelden. |
| „Anmeldung abgelaufen oder widerrufen“ | ☁️ Cloud → Neu anmelden. Bei Google prüfen, ob die App „In Produktion“ steht. |
| GitHub „HTTP 401“ | Token abgelaufen oder falsch kopiert. Neuen Token anlegen. |
| GitHub „HTTP 403“ oder „HTTP 404“ | Token hat keinen Zugriff auf das Repo oder `Contents` steht nicht auf *Read and write*. |
| „größer als 50 MB, Telegram nimmt das nicht“ | Google Drive, OneDrive oder GitHub nehmen. |
