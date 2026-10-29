@echo off
rem Bildrechner fuer PaperclipLite: stable-diffusion.cpp sd-server mit FLUX.2 klein 4B (nur CPU)
rem Liegt in C:\bildrechner\ neben sd-server.exe, Modelle in C:\bildrechner\modelle\
cd /d "%~dp0"
sd-server.exe ^
  --listen-ip 0.0.0.0 --listen-port 1234 ^
  --diffusion-model modelle\flux-2-klein-4b-Q4_0.gguf ^
  --llm modelle\Qwen3-4B-Q4_K_M.gguf ^
  --vae modelle\full_encoder_small_decoder.safetensors ^
  --diffusion-fa --vae-tiling -t 4 -v
pause
