# Bildrechner für PaperclipLite einrichten (Windows 10/11, ohne Grafikkarte)
# Laedt stable-diffusion.cpp (sd-server.exe) und die drei Modelldateien nach C:\bildrechner
# und legt dort bildrechner-start.bat ab. Kann jederzeit erneut laufen: Vorhandenes wird übersprungen.
#
# Aufruf in PowerShell im PaperclipLite-Ordner:
#   powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1
# Weniger RAM-Verbrauch (kleineres Sprachmodell):  ... bildrechner-einrichten.ps1 -Klein
param(
  [string]$Ziel = "C:\bildrechner",
  [switch]$Klein
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Schritt($t) { Write-Host ""; Write-Host "== $t" -ForegroundColor Cyan }
function Fehler($t) { Write-Host ""; Write-Host "FEHLER: $t" -ForegroundColor Red; exit 1 }
function Ok($t) { Write-Host "   ok: $t" -ForegroundColor Green }

$curl = (Get-Command curl.exe -ErrorAction SilentlyContinue)
if (-not $curl) { Fehler "curl.exe fehlt (ab Windows 10 Version 1803 eingebaut). Bitte Windows aktualisieren." }

function Laden($url, $datei, $mindestMB) {
  if (Test-Path $datei) {
    Ok "$(Split-Path $datei -Leaf) ist schon da"
    return
  }
  # Download in eine .part-Datei, erst danach umbenennen: so gilt eine vorhandene Datei immer als vollstaendig.
  $teil = "$datei.part"
  Write-Host "   lade $(Split-Path $datei -Leaf) ... (kann je nach Leitung lange dauern)"
  # -C - setzt einen abgebrochenen Download fort
  & $curl.Source -L --fail --retry 5 --retry-delay 5 -C - -o $teil $url
  if ($LASTEXITCODE -ne 0) {
    Fehler "Download von $url fehlgeschlagen (curl-Code $LASTEXITCODE). Internet prüfen und das Skript einfach erneut starten, es macht dort weiter."
  }
  if ((Get-Item $teil).Length -lt $mindestMB * 1MB) {
    Remove-Item -Force $teil
    Fehler "$(Split-Path $datei -Leaf) ist zu klein, der Download ist kaputt. Skript erneut starten."
  }
  Move-Item -Force $teil $datei
  Ok (Split-Path $datei -Leaf)
}

Schritt "1/6 Prüfen: Speicher und Platz"
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
Write-Host "   Arbeitsspeicher: $ramGB GB"
if ($ramGB -lt 7.5) { Fehler "Mindestens 8 GB Arbeitsspeicher nötig." }
New-Item -ItemType Directory -Force -Path $Ziel, "$Ziel\modelle" | Out-Null
$lw = (Get-Item $Ziel).PSDrive.Name
$freiGB = [math]::Round((Get-PSDrive $lw).Free / 1GB, 1)
# Platzbedarf nur für das, was noch fehlt (beim erneuten Start ist schon vieles da)
$bedarf = 0.5
if (-not (Test-Path "$Ziel\sd-server.exe")) { $bedarf += 0.5 }
if (-not (Test-Path "$Ziel\modelle\flux-2-klein-4b-Q4_0.gguf")) { $bedarf += 2.5 }
if (-not (Test-Path "$Ziel\modelle\Qwen3-4B-Q4_K_M.gguf") -and -not (Test-Path "$Ziel\modelle\Qwen3-4B-Q3_K_M.gguf")) { $bedarf += 2.5 }
if (-not (Test-Path "$Ziel\modelle\full_encoder_small_decoder.safetensors")) { $bedarf += 0.3 }
Write-Host "   Freier Platz auf ${lw}: $freiGB GB (nötig noch etwa $bedarf GB)"
if ($freiGB -lt $bedarf) { Fehler "Auf Laufwerk $lw sind nur $freiGB GB frei, nötig sind noch etwa $bedarf GB." }
Ok "genug Speicher und Platz"

Schritt "2/6 Programm stable-diffusion.cpp (sd-server.exe)"
if (Test-Path "$Ziel\sd-server.exe") {
  Ok "sd-server.exe ist schon da (zum Aktualisieren löschen und Skript erneut starten)"
} else {
  try {
    $rel = Invoke-RestMethod "https://api.github.com/repos/leejet/stable-diffusion.cpp/releases/latest" -Headers @{ "User-Agent" = "paperclip-lite" }
  } catch { Fehler "GitHub nicht erreichbar: $($_.Exception.Message)" }
  # Nur CPU (ohne cuda/rocm/vulkan). Aeltere Versionen hiessen win-avx2-x64.
  $asset = $rel.assets | Where-Object { $_.name -match "bin-win-cpu-x64\.zip$" } | Select-Object -First 1
  if (-not $asset) { $asset = $rel.assets | Where-Object { $_.name -match "bin-win-avx2-x64\.zip$" } | Select-Object -First 1 }
  if (-not $asset) {
    Fehler ("In Version $($rel.tag_name) keine Windows-CPU-Datei gefunden. Von Hand: https://github.com/leejet/stable-diffusion.cpp/releases " +
            "-> Assets -> Datei mit 'bin-win-cpu-x64.zip' im Namen laden und nach $Ziel entpacken.")
  }
  Write-Host "   Version $($rel.tag_name): $($asset.name)"
  $zip = Join-Path $env:TEMP $asset.name
  Laden $asset.browser_download_url $zip 1
  $tmp = Join-Path $env:TEMP "sdcpp-entpackt"
  if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
  Expand-Archive -Path $zip -DestinationPath $tmp -Force
  $exe = Get-ChildItem -Path $tmp -Recurse -Filter "sd-server.exe" | Select-Object -First 1
  if (-not $exe) { Fehler "In $($asset.name) ist keine sd-server.exe. Der Aufbau der Release-Datei hat sich geändert, bitte melden." }
  Copy-Item -Path (Join-Path $exe.DirectoryName "*") -Destination $Ziel -Recurse -Force
  Remove-Item -Recurse -Force $tmp
  Remove-Item -Force $zip
  Ok "sd-server.exe nach $Ziel entpackt"
}

Schritt "3/6 Laufzeit für sd-server (Visual C++, VCOMP140.DLL)"
if (Test-Path "$env:WINDIR\System32\VCOMP140.DLL") {
  Ok "Laufzeit ist schon installiert"
} else {
  $redist = Join-Path $env:TEMP "vc_redist.x64.exe"
  Write-Host "   fehlt: Microsoft Visual C++ Laufzeit. Windows fragt gleich nach Administrator-Rechten (Ja klicken)."
  Laden "https://aka.ms/vs/17/release/vc_redist.x64.exe" $redist 10
  try {
    $p = Start-Process -FilePath $redist -ArgumentList "/install", "/quiet", "/norestart" -Verb RunAs -Wait -PassThru
  } catch { Fehler "Installation abgebrochen. Datei von Hand starten: $redist (Doppelklick)" }
  if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) { Fehler "Installation der Laufzeit meldet Code $($p.ExitCode). Datei von Hand starten: $redist" }
  if (-not (Test-Path "$env:WINDIR\System32\VCOMP140.DLL")) { Fehler "VCOMP140.DLL fehlt auch nach der Installation. Windows-Updates prüfen oder melden." }
  Ok "Laufzeit installiert"
}

Schritt "4/6 Modelle (zusammen ca. 5 GB)"
Laden "https://huggingface.co/leejet/FLUX.2-klein-4B-GGUF/resolve/main/flux-2-klein-4b-Q4_0.gguf" "$Ziel\modelle\flux-2-klein-4b-Q4_0.gguf" 2200
if ($Klein) {
  Laden "https://huggingface.co/unsloth/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q3_K_M.gguf" "$Ziel\modelle\Qwen3-4B-Q3_K_M.gguf" 1900
  # Die Startdatei nimmt das groessere Modell, solange es da ist
  if (Test-Path "$Ziel\modelle\Qwen3-4B-Q4_K_M.gguf") { Remove-Item -Force "$Ziel\modelle\Qwen3-4B-Q4_K_M.gguf"; Ok "größeres Sprachmodell entfernt" }
} else {
  Laden "https://huggingface.co/unsloth/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf" "$Ziel\modelle\Qwen3-4B-Q4_K_M.gguf" 2300
}
Laden "https://huggingface.co/black-forest-labs/FLUX.2-small-decoder/resolve/main/full_encoder_small_decoder.safetensors" "$Ziel\modelle\full_encoder_small_decoder.safetensors" 200

Schritt "5/6 Startdatei"
Copy-Item -Path (Join-Path $PSScriptRoot "bildrechner-start.bat") -Destination "$Ziel\bildrechner-start.bat" -Force
Ok "$Ziel\bildrechner-start.bat"

Schritt "6/6 Firewall (nur nötig, wenn der Pi oder andere Rechner Bilder bestellen)"
if (Get-NetFirewallRule -DisplayName "Bildrechner sd-server" -ErrorAction SilentlyContinue) {
  Ok "Firewall-Regel ist schon da"
} else {
  Write-Host "   Windows fragt gleich nach Administrator-Rechten (Ja klicken). Ablehnen ist ok, wenn nur dieser Laptop Bilder bestellt."
  try {
    Start-Process netsh -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList 'advfirewall firewall add rule name="Bildrechner sd-server" dir=in action=allow protocol=TCP localport=1234 profile=private'
    if (-not (Get-NetFirewallRule -DisplayName "Bildrechner sd-server" -ErrorAction SilentlyContinue)) { throw "nicht angelegt" }
    Ok "Firewall-Regel angelegt (Port 1234, nur privates Netz)"
  } catch {
    Write-Host "   übersprungen. Später in einer Eingabeaufforderung als Administrator:" -ForegroundColor Yellow
    Write-Host '   netsh advfirewall firewall add rule name="Bildrechner sd-server" dir=in action=allow protocol=TCP localport=1234 profile=private'
  }
}

Write-Host ""
Write-Host "Fertig. So geht es weiter:" -ForegroundColor Green
Write-Host "  1. Doppelklick auf $Ziel\bildrechner-start.bat  (Fenster offen lassen, erster Start 1-2 Minuten)"
Write-Host "  2. 1-2 Minuten warten, dann im Browser http://127.0.0.1:1234 öffnen: es muss eine Seite erscheinen"
Write-Host "  3. In der .env von PaperclipLite:  IMAGE_PROVIDER=sdcpp  und  SDCPP_URL=http://127.0.0.1:1234"
Write-Host "     (auf dem Pi stattdessen SDCPP_URL=http://<IP dieses Laptops>:1234, IP mit: ipconfig)"
Write-Host "  4. PaperclipLite neu starten, dann prüfen:  venv\Scripts\python.exe selftest.py web"
