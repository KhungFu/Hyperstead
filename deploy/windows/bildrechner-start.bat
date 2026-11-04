@echo off
rem Bildrechner fuer Hyperstead: stable-diffusion.cpp sd-server mit FLUX.2 klein 4B (nur CPU)
rem Einrichten: deploy\windows\bildrechner-einrichten.ps1 (legt diese Datei nach C:\bildrechner\)
cd /d "%~dp0"
if not exist sd-server.exe (
  echo FEHLER: sd-server.exe fehlt in %~dp0
  echo Erst einrichten, in PowerShell im Hyperstead-Ordner:
  echo   powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1
  pause
  exit /b 1
)
set "LLM=modelle\Qwen3-4B-Q4_K_M.gguf"
if not exist "%LLM%" set "LLM=modelle\Qwen3-4B-Q3_K_M.gguf"
for %%F in (modelle\flux-2-klein-4b-Q4_0.gguf "%LLM%" modelle\full_encoder_small_decoder.safetensors) do (
  if not exist %%F (
    echo FEHLER: Modelldatei %%F fehlt. bildrechner-einrichten.ps1 erneut ausfuehren.
    pause
    exit /b 1
  )
)
echo Bildrechner startet (1-2 Minuten). Fenster offen lassen. Bereit, wenn http://127.0.0.1:1234 im Browser eine Seite zeigt.
sd-server.exe ^
  --listen-ip 0.0.0.0 --listen-port 1234 ^
  --diffusion-model modelle\flux-2-klein-4b-Q4_0.gguf ^
  --llm "%LLM%" ^
  --vae modelle\full_encoder_small_decoder.safetensors ^
  --diffusion-fa --vae-tiling -t 4 -v
pause
