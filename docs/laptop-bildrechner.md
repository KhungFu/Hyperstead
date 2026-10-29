# Eigener Bildrechner auf einem Windows-Laptop

PaperclipLite kann Bilder auf einem eigenen Rechner im Heimnetz erzeugen lassen. Das kostet nichts, geht mit
Referenzbildern (gleiche Figuren über eine Serie) und braucht keine Grafikkarte. Dafür ist es langsam:
auf einem Laptop mit i5-8250U und 8 GB RAM sind mehrere Minuten je Bild zu erwarten.

Software: [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) (`sd-server`).
Modell: FLUX.2 klein 4B (Apache 2.0, auch kommerziell nutzbar), auf 4 Bit verkleinert.

## Was du brauchst

- Windows 10/11, 64 Bit, mindestens 8 GB RAM, etwa 6 GB freier Platz
- Laptop und Pi im selben Netz (oder beide in Tailscale)
- Laptop am Strom, Energiesparen aus

## 1. Programm herunterladen

1. Auf <https://github.com/leejet/stable-diffusion.cpp/releases> die neueste Version öffnen.
2. Unter „Assets“ die ZIP-Datei mit `win-avx2-x64` im Namen laden (ohne `cuda`/`rocm`).
3. Nach `C:\bildrechner\` entpacken. Darin muss `sd-server.exe` liegen.

## 2. Modelle herunterladen (zusammen ca. 5,2 GB)

In `C:\bildrechner\modelle\` speichern:

| Datei | Größe | Link |
| --- | --- | --- |
| `flux-2-klein-4b-Q4_0.gguf` | 2,46 GB | <https://huggingface.co/leejet/FLUX.2-klein-4B-GGUF/resolve/main/flux-2-klein-4b-Q4_0.gguf> |
| `Qwen3-4B-Q4_K_M.gguf` | 2,5 GB | <https://huggingface.co/unsloth/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf> |
| `full_encoder_small_decoder.safetensors` | 250 MB | <https://huggingface.co/black-forest-labs/FLUX.2-small-decoder/resolve/main/full_encoder_small_decoder.safetensors> |

Reicht der Speicher nicht (Absturz, „out of memory“): statt `Qwen3-4B-Q4_K_M.gguf` die kleinere
`Qwen3-4B-Q3_K_M.gguf` (2,08 GB) nehmen und in der Startdatei den Namen ändern.

## 3. Startdatei

`deploy/windows/bildrechner-start.bat` aus dem PaperclipLite-Ordner nach `C:\bildrechner\` kopieren und
doppelklicken. Das Fenster muss offen bleiben. Beim ersten Start lädt es die Modelle (1–2 Minuten).

Erst wenn im Fenster steht, dass der Server lauscht, Anfragen schicken: Eine Anfrage während des Ladens kann hängen bleiben
([bekannter Fehler](https://github.com/leejet/stable-diffusion.cpp/issues/2081)), dann das Fenster schließen und neu starten.

Test im Browser auf dem Laptop: <http://127.0.0.1:1234> sollte eine Seite zeigen.

Autostart: Win+R, `shell:startup` eingeben, eine Verknüpfung zur `.bat` hineinlegen.

## 4. Firewall und Energiesparen (Eingabeaufforderung als Administrator)

```bat
netsh advfirewall firewall add rule name="Bildrechner sd-server" dir=in action=allow protocol=TCP localport=1234 profile=private
powercfg /change standby-timeout-ac 0
```

Das Heimnetz muss in Windows als **privates** Netzwerk eingestellt sein. `sd-server` hat kein Passwort:
den Port 1234 nie im Router freigeben.

## 5. IP-Adresse des Laptops

`ipconfig` in der Eingabeaufforderung, Zeile „IPv4-Adresse“, z. B. `192.168.1.50`. Im Router am besten
eine feste Adresse für den Laptop einstellen, sonst ändert sie sich irgendwann.

## 6. PaperclipLite auf dem Pi

In `.env`:

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://192.168.1.50:1234
IMAGE_STYLE=farbige Buntstiftzeichnung auf Pastellflaeche, sichtbare Strichstruktur
# optional, wenn der Laptop aus ist:
# IMAGE_FALLBACK=pollinations
```

Dann `sudo systemctl restart paperclip-lite` und `./venv/bin/python selftest.py web`.
Der Selbsttest erzeugt ein Bild und eins mit Referenz, das dauert entsprechend.

Weitere Schalter: `SDCPP_SIZE` (längste Bildseite, Standard 1024; 768 ist etwa doppelt so schnell),
`SDCPP_STEPS` (Standard 4), `SDCPP_CFG` (Standard 1.0), `SDCPP_TIMEOUT` (Sekunden, Standard 1800).

## Grenzen

- Die verkleinerte 4B-Fassung zeichnet einfacher als Gemini oder GPT-Image. Für Buntstift-Illustrationen
  reicht sie meist, feine Details und Schrift im Bild gelingen schlecht.
- Referenzbilder halten Figuren ähnlich, aber nicht perfekt gleich. Ein klares Referenzbild je Figur
  (Ganzkörper, neutraler Hintergrund) hilft am meisten.
- Mit Referenzbildern rechnet er länger als ohne.
- PaperclipLite schickt immer nur ein Bild gleichzeitig an den Laptop.
