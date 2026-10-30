# PaperclipLite

🌐 Languages: [Deutsch](README.md) · **English** · [Türkçe](README.tr.md) · [Srpski](README.sr.md) · [Bosanski](README.bs.md) · [Hrvatski](README.hr.md)

An agent team as a node editor, self-hosted, light enough for a Raspberry Pi.
Create a project, drag agents onto the canvas, connect them (boss → employee), set the AI provider, work instructions and rights per node, and assign tasks.

> The detailed guides in `docs/` are currently written in German only.

## Installation

PaperclipLite is a Python program (Flask + SQLite) and runs on several systems. Several installations
can run in parallel; each has its own companies and data.

| System | Status | Guide |
| --- | --- | --- |
| Raspberry Pi / Linux (Debian, Ubuntu) | main system, full feature set | below |
| Windows 10/11 | works, without `run_code`, some features need extra programs | [docs/windows.md](docs/windows.md) |
| macOS | untested, basic functions should work | below (by hand) |
| Own image computer (e.g. an old laptop without a graphics card) | free images with reference images for PaperclipLite | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) |

Moving from one computer to another: stop PaperclipLite and copy `data.db`, the folder `workspace/` and `.env`
([example Pi → Windows](docs/windows.md)).

### Raspberry Pi / Linux

```bash
git clone https://github.com/KhungFu/paperclip-lite && cd paperclip-lite
./install.sh --service     # venv, dependencies, .env with a random password, systemd service
nano .env                  # enter API keys, then: sudo systemctl restart paperclip-lite
```

Without the service: `./install.sh`, then `./venv/bin/python app.py` → http://127.0.0.1:8787.
The login password is in `.env` (`APP_TOKEN`). Update, restart, backup: [Operations](#operations-who-does-what-where-when-how).
More features (video, OCR, compilers, browser): `./install.sh --all`.

### Windows

PowerShell in the PaperclipLite folder:

```powershell
git clone https://github.com/KhungFu/paperclip-lite; cd paperclip-lite
powershell -ExecutionPolicy Bypass -File install.ps1
notepad .env
deploy\windows\paperclip-start.bat
```

What is missing under Windows, autostart and running in parallel with the Pi: [docs/windows.md](docs/windows.md).
Update later: `git pull`, then restart.

### macOS (untested)

```bash
git clone https://github.com/KhungFu/paperclip-lite && cd paperclip-lite
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env       # set APP_TOKEN=<long password>, add API keys
./venv/bin/python app.py   # http://127.0.0.1:8787
```

`install.sh` is built for Debian/Ubuntu (apt), so on macOS do it by hand as above. Extra programs via Homebrew
(`brew install ffmpeg tesseract poppler`). `run_code` only exists on Linux.

### Images on your own computer

A computer on the home network (even without a graphics card, at least 8 GB RAM) can generate free images with
reference images for PaperclipLite. In `.env`, keep exactly these two lines active (only one `IMAGE_PROVIDER=` line without `#`):

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://<IP of the image computer>:1234    # on the image computer itself: http://127.0.0.1:1234
```

Setup: [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md).

### Animated films with Blender

If Blender is installed on the computer that runs PaperclipLite, the agents make cartoon films: characters with their own
voices and mouth movement, scenes, camera, subtitles, a finished film with sound (tool `film`, company template „🐶 Animationsstudio“).
If PaperclipLite does not find Blender by itself, add it to `.env`:

```
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```

Guide and script format (German): [docs/filmstudio.md](docs/filmstudio.md).

## Operations: who does what, where, when, how

**Who:** the owner of the computer (you) does all of this, not the agents. The commands run in the
PaperclipLite folder: on the Pi in the terminal (`cd ~/paperclip-lite`), on Windows in PowerShell
(`cd $HOME\paperclip-lite`, or wherever you put the folder).

### Quick overview

| What | When | Raspberry Pi / Linux (with service) | Windows |
| --- | --- | --- | --- |
| Start | after installation, after a restart without autostart | `sudo systemctl start paperclip-lite` | double-click `deploy\windows\paperclip-start.bat` (keep the window open) |
| Stop | before a move, a backup, an update | `sudo systemctl stop paperclip-lite` | close the start window (or press Ctrl+C in it) |
| Restart | after every change to `.env`, after an update | `sudo systemctl restart paperclip-lite` | close the start window, start `paperclip-start.bat` again |
| Is it running? | when there are problems | `systemctl status paperclip-lite` | is the start window open? Browser: <http://127.0.0.1:8787> |
| View the log | on errors | `journalctl -u paperclip-lite -f` (Ctrl+C stops it) | shown in the start window |
| Update | when there is a new version (e.g. after a merged pull request) | see below | see below |
| Check | after installation, an update, new keys | `./venv/bin/python selftest.py` | `venv\Scripts\python.exe selftest.py` |
| Keys / settings | new key, other image provider | `nano .env`, then restart | `notepad .env`, then restart |
| Back up | regularly, before a move and big updates | copy `data.db`, `workspace/`, `.env` (stop first) | the same in the PaperclipLite folder |

### Update (get the new version)

**Raspberry Pi / Linux**, in the terminal:

```bash
cd ~/paperclip-lite
git pull
./install.sh               # only needed if requirements.txt changed; .env stays unchanged
sudo systemctl restart paperclip-lite
./venv/bin/python selftest.py llm     # quick check that the AI providers answer
```

**Windows**, in PowerShell:

1. `cd $HOME\paperclip-lite`
2. `git pull`
3. Only if packages changed (or when in doubt): `powershell -ExecutionPolicy Bypass -File install.ps1`
   (the existing `.env` stays unchanged).
4. Close the black start window of PaperclipLite.
5. Start `deploy\windows\paperclip-start.bat` again (double-click or type it in PowerShell).
6. Check: `venv\Scripts\python.exe selftest.py llm`

If `git pull` says „local changes would be overwritten“, you changed a file of the program yourself.
`git stash` sets the change aside, then repeat `git pull`. Your data (`data.db`, `workspace/`, `.env`)
is never affected, because Git does not know them.

### Start automatically

- **Pi:** `./install.sh --service` sets up the service; it then starts by itself at every boot.
- **Windows:** Win+R, type `shell:startup`, and put a shortcut to `deploy\windows\paperclip-start.bat` there
  (and to `bildrechner-start.bat`, if you use it). Windows must sign in by itself for this
  ([docs/windows.md](docs/windows.md), section 4).

### Change settings in `.env`

- Each setting appears exactly once, without `#` at the start. Lines starting with `#` are switched off. With duplicate lines
  the first one counts.
- After every change, restart PaperclipLite, otherwise the old state still applies.
- Never copy keys into chats, screenshots or the repository. If a key has ended up somewhere by accident: revoke it with the provider and enter a new one.
- Then check with `selftest.py`. Single areas: `selftest.py llm`, `web`, `telegram`, `media`, `ocr`, `code`.

### Reading the self-test

- **OK:** works.
- **FEHLT (missing):** optional; the line names the command to install it (on Windows the Windows command).
  Only needed if your agents use it (e.g. video, speech output, scanned PDFs).
- **FEHLER (error):** something you entered does not work, usually an invalid or expired key or a service that is not
  running (e.g. the image computer). The line gives the reason.
- A single timeout at a web service is often only temporary: try again later.

### Image computer (if used)

- **Where:** on the computer that makes the images (e.g. a laptop), folder `C:\bildrechner`.
- **When:** it must run as long as agents should generate images.
- **Set up (once):** in PowerShell in the PaperclipLite folder
  `powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1` (downloads the program and the models).
- **How:** start `C:\bildrechner\bildrechner-start.bat`, keep the window open. In the `.env` of PaperclipLite
  `IMAGE_PROVIDER=sdcpp` and `SDCPP_URL=...` ([guide](docs/laptop-bildrechner.md)), then restart PaperclipLite.

### Film studio (if used)

- **Where:** on the computer with Blender (e.g. the laptop). The company with the `film` tool must run in **this** PaperclipLite instance.
- **When:** Blender does not need to be open, PaperclipLite starts it in the background for each scene and closes it again.
- **Check:** `venv\Scripts\python.exe selftest.py film` (Windows) or `./venv/bin/python selftest.py film`.
- **How long:** at 640×360 and 12 frames/s, depending on the laptop, about 1 to 5 minutes per 10 seconds of film. Blender never runs at the same time as the image computer.

### Moving (e.g. Pi → laptop)

Step by step in [docs/windows.md](docs/windows.md), „Phase 2 – Umzug“ (German). In short: stop both, copy `data.db`,
`workspace/` and `.env`, start on the new computer and check, and only then switch off the old one.
Only enter Telegram on one computer.

### What happens when something is missing

This list is extended with every change to the program. Each row says what the system does and what you have to do.

| Missing | What the system does | What you do |
| --- | --- | --- |
| `.env` | PaperclipLite starts without keys and without a password, reachable only from this computer. With `HOST=0.0.0.0` the start is aborted as long as `APP_TOKEN` is empty. | `./install.sh` (Pi) or `install.ps1` (Windows) creates it with a random password. |
| `data.db` | Is created new and empty. Companies, tasks and posts are gone. | Back it up first (see Operations). Only copy back from a backup. |
| API key in `.env` | The provider is reported as FEHLT in the self-test and the agents do not use it. If it is set but invalid: FEHLER with HTTP 401. | Enter the key, or switch the line off with `#`. |
| `SDCPP_URL` (with `IMAGE_PROVIDER=sdcpp`) | Image requests fail with „SDCPP_URL fehlt“ (SDCPP_URL missing). With `IMAGE_FALLBACK=pollinations` a free replacement image without references is made, with a note in the result. | Add the line to `.env`, restart PaperclipLite. |
| Image computer not reachable (laptop off, firewall, wrong IP) | As above: error „Bildrechner … nicht erreichbar“ (not reachable), with the fallback a replacement image. | Switch on the laptop, start `bildrechner-start.bat`, check the IP and the firewall. |
| `sd-server.exe` (Windows, image computer) | `bildrechner-start.bat` shows „sd-server.exe fehlt“ (missing) and starts nothing. | Run `deploy\windows\bildrechner-einrichten.ps1`. |
| Model file (Windows, image computer) | The start file names the missing file and does not start. If only the large language model (`Qwen3-4B-Q4_K_M.gguf`) is missing, it uses the smaller one if present. | Run the set-up script again; it only downloads the missing file. |
| Windows runtime `VCOMP140.DLL` | `sd-server.exe` reports „VCOMP140.DLL nicht gefunden“ (not found) and aborts. | Run the set-up script again (step 3 installs the runtime), then open the start file. |
| Firewall rule for port 1234 (Windows) | Only the Pi cannot reach the image computer. The laptop itself keeps working. | Run the command from [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md), section 4, as administrator. |
| `FAL_KEY` (with `VIDEO_PROVIDER=fal`) | Video generation reports „VIDEO_PROVIDER=fal, aber FAL_KEY fehlt“. The self-test shows FEHLT (missing). | Enter the fal.ai key in `.env`, or leave `VIDEO_PROVIDER` empty. |
| `ffmpeg`, `tesseract`, `pdftoppm`, speech output | The function is missing. Agents that need it report the error in the result. The self-test shows FEHLER (Pi) or FEHLT (Windows). | Install the program (commands in the self-test and in [docs/windows.md](docs/windows.md)). |
| Blender (tool `film`) | `save`, `check`, `voices` and `assemble` still work. `preview` and `render` report „Blender wurde nicht gefunden“ (Blender not found) with a hint about `BLENDER_PATH`. The self-test shows FEHLT. | Install Blender (`winget install BlenderFoundation.Blender`) or set `BLENDER_PATH` in `.env`, restart. |
| `film/film.json` (script) | `film` reports „film/film.json fehlt“ (missing) and asks to save a script with `op=save` first. A faulty script is not saved, the answer lists all errors. | Nothing, the agents create it themselves. You can also write it by hand ([docs/filmstudio.md](docs/filmstudio.md)). |
| Image, music or `.blend` file named in the script | The check names scene, character and path, nothing is rendered. | Put the file into `assets/` or `input/` or fix the path in the script. |
| Clip of a scene (`film/clips/`) | `assemble` names the missing scenes and cuts nothing. If `render` stops (time limit), the finished frames are kept and the next call continues there. | Nothing, the agents call `render` again. |
| Speech output for the film | `voices`/`render` stop with „Keine Sprachausgabe verfügbar“ (no speech output). Scenes without any dialogue still work. | As for „speech output“ above (on Windows `edge-tts` + `TTS_ENGINE=edge`). |
| Telegram token or chat ID | Telegram stays off, everything else runs. The self-test shows FEHLT. | Only needed if you want messages on your phone. |
| A folder or file in the project (`wissen/`, `input/`) | Folders that do not exist count as empty. The agents keep working without company knowledge. | Create or upload the file or folder in the project. |

## Access from the internet

The app deliberately listens only on `127.0.0.1`. Instead of opening a port, you use a tunnel.
This is also needed if your mobile router does not allow incoming connections (CGNAT).

### Option A (recommended): Tailscale, private, only for your devices

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                    # open the login link in the browser
sudo tailscale serve --bg 8787       # HTTPS address only inside your own tailnet
```

Install Tailscale on your phone/laptop too, then open the shown address `https://dexter….ts.net`.
Add to `.env`: `TRUST_PROXY=1`, then restart the service.
**Do not** use `tailscale funnel`, that would put the app on the public internet.

### Option B: Cloudflare Tunnel, public address with your own domain

```bash
# install cloudflared (see developers.cloudflare.com/cloudflare-one/connections/connect-networks)
cloudflared tunnel login
cloudflared tunnel create paperclip
cloudflared tunnel route dns paperclip agents.your-domain.de
# ~/.cloudflared/config.yml:  ingress: - hostname: agents.your-domain.de  service: http://127.0.0.1:8787
cloudflared tunnel run paperclip
```

Strongly recommended in addition: put **Cloudflare Access** (e-mail login) in front.
In `.env`: `TRUST_PROXY=1`. The commands may change; in doubt, the official guide applies.

With `TRUST_PROXY=1` the app only starts if `APP_TOKEN` has at least 12 characters.

## Operation

| Action | How |
|---|---|
| Create an agent | drag the entry from the palette onto the canvas (or click it) |
| Connect | drag the lower dot of a node onto another node (= boss → employee) |
| Disconnect | click the connecting line |
| Move | drag a node; drag the background = move the view; mouse wheel = zoom |
| Settings | click a node → panel on the right |
| Assign a task | panel → tab „Aufgaben“ (tasks) |
| Approve | sidebar „Freigaben“ (approvals) |

## How the company works

A boss receives a task and **plans** (distributes sub-tasks) or does it himself. As soon as all
employees are finished, he wakes up again, **reads their reports**, returns defects with feedback or
summarises everything and reports to his own boss. This is how the result moves up through any number of levels.
The status „Wartet auf Team“ (waiting for team) means: the boss is waiting for his people. In the tasks tab you see the whole tree.

## Agent abilities (internet, images, files)

Agents work in rounds: they request tools, the server runs them and returns the results, until they
are finished (max. `PCL_MAX_TOOL_STEPS`). Rights per agent: **research the internet**, **images**, **read project files**
(plus, as before, write files).

| Tool | What it does | Without key |
|---|---|---|
| `web_search` | web search (laws, prices, competition …) | DuckDuckGo; better: `SEARXNG_URL`, `BRAVE_API_KEY` or `TAVILY_API_KEY` |
| `fetch_url` | read a web page as text | yes |
| `browse_page` | open a page in a real browser (JavaScript runs), optionally with a screenshot the agent sees as an image | yes, needs `./install.sh --browser` |
| `image_search` / `image_save` | search freely licensed photos and save them in `assets/`, with author and licence | Openverse; optional `PEXELS_API_KEY` |
| `image_generate` | create an AI image as PNG, optionally with up to 4 reference images from the project (same characters and style across a series), format square/portrait/landscape and target path in `assets/`, `output/` or `karten/`. Right **Images** or **Media** | Pollinations (without key: no reference images; with `POLLINATIONS_API_KEY` and Pollen credit: model via `POLLINATIONS_MODEL`, with reference images); `IMAGE_STYLE` sets a fixed drawing style; others: `nvidia` (FLUX via build.nvidia.com), `cloudflare` (Workers AI, FLUX.2 klein with reference images), `hf` (Hugging Face), model each via `IMAGE_MODEL`; free with reference images on your own computer: `IMAGE_PROVIDER=sdcpp` ([guide](docs/laptop-bildrechner.md)); better `IMAGE_PROVIDER=openai` with `OPENAI_API_KEY`, `gemini`, or `openrouter` with `OPENROUTER_API_KEY` |
| `list_files` / `read_file` | read files in the project folder (e.g. colleagues' texts) | yes |

Everything created lies under `workspace/<project-id>/`. In the sidebar, **📁 Dateien** shows the files, opens `index.html`
as a web page (isolated sandbox) and downloads everything as a ZIP. The link contains a secret key.

**Company templates** (🏢 next to „Projekte“): *Web agency*, *Accounting/tax office*, *Import/export trade* create project,
organisation chart, work instructions and rights completely. Your own companies: write a project goal („you are a …“, country,
industry), set agents and rights. The agents receive the date and the project goal and should first research things that change (laws,
prices) and name their sources.

**Tool security:** page fetches are limited to public addresses (no localhost, LAN, Tailscale,
cloud metadata; redirects are checked one by one). For the agents, web content counts as untrusted data,
but a prepared page can still influence a model: do not give agents with internet access a shell, and check results.
Agents deliberately have **no** tools for purchases, orders, payments or sending e-mail; they deliver drafts and recommendations.
Image licences (CC) often require attribution; the picture editor writes it into `bildnachweis.md`.

## Media, documents and your own files

With the right **create media & documents** (and `ffmpeg`/fonts on the Pi, see `install.sh`):

| Tool | What it can do |
|---|---|
| `video_edit` | cut a video (`trim`), join (`concat`), **slideshow animation with zoom** from images (`slideshow`, optionally with sound), overlay text/subtitles/logo, replace or mix sound, change speed, convert to GIF/WebM/MP3, extract a still frame |
| `speak` | text to speaker audio (espeak-ng offline; better: Piper; optional Edge voices), with `voice`, `pitch`, `rate` for different voices |
| `film` | **animated film with Blender**: script as JSON, characters (dog, cat, rabbit, bear, mouse, human, your own images or `.blend` characters), voices with mouth movement, movements, camera, preview image, rendering scene by scene, editing with subtitles ([guide](docs/filmstudio.md)) |
| `write_file` | with the right **write files**: creates chapters, HTML, CSV etc. immediately, so that a PDF/DOCX/EPUB can be made from them in the same task |
| `make_document` | from Markdown chapters **PDF, DOCX, EPUB or HTML** (A4/A5, cover, images, umlauts and Turkish characters); with `html` a PDF with free layout from **HTML+CSS** (rebuild templates, via WeasyPrint, loads only files from the project) |
| `video_generate` | **AI video clip** from text (optionally with a start image), about 4–10 s. Providers: Google's Gemini API (the model behind Google Flow, start image possible) or fal.ai (`VIDEO_PROVIDER=fal` + `FAL_KEY`, default model Kling, text only). Off by default, switch on with `VIDEO_PROVIDER=gemini` or `fal`. **Costs per second of video**; a Flow/Google One subscription does not count here |
| `media_info` | duration, resolution, codecs |
| `download_file` | download PDFs, EPUB, Office, audio, video, ZIP from the internet into `downloads/` |
| `read_file` | reads text, Markdown, HTML, **PDF, DOCX, EPUB**, also long files in sections |
| `view_image` | **sees** images, screenshots, maps, layouts and pages of scanned PDFs (needs a model with image understanding, e.g. Claude, GPT-4o, Gemini) |

**Self-check:** if an agent creates a PDF, the server then renders it as an image (overview of all pages + page 1 large) and sends it
back to him with the duty to check every requirement of the task and fix errors before he reports (`PCL_SELF_CHECKS`, default 1, 0 = off).

**Your own files** (videos to edit, PDFs, images, layouts, texts) you upload in „📁 Dateien dieses Projekts“ or send
directly in the **💬 Chat** with an agent (📎 button, drag them in or paste an image, several at once). They land in
`input/` (name cleaned up, existing files are never overwritten but become `name-1.png` …, limit `PCL_MAX_UPLOAD_MB`); in the chat
the agent gets the **content** directly with the message (texts, PDFs, Word as text, images as images, if the model understands images;
otherwise text recognition). With **📂 aus input/** you attach files that are already there, or you simply write the file name into the message, and „Als Auftrag erteilen“ (give as task) passes it to the team; finished results lie in `output/`, images in `assets/`. Honest limits: without `video_generate` there is **no AI video generation**
(text to video); „animation“ then means: scene images by image AI + zoom/pan + speaker + cut, or real character animation with Blender via `film`. With `video_generate`
short clips arise; longer films are put together with `video_edit op=concat`. MagicLight has no API: upload videos made there to `input/`. On the Raspberry Pi
ffmpeg is slow (one minute of 720p video can take several minutes), time limit `PCL_FFMPEG_TIMEOUT` (default 1 hour per step).

**Scanned PDFs and images (OCR):** `read_file` reads scans automatically via `tesseract` (`sudo apt install tesseract-ocr tesseract-ocr-deu poppler-utils`). This is slow (about 5–15 s per page on the Pi, limit `PCL_OCR_MAX_PAGES`) and can contain errors.

**Good speaker voice:** `./install.sh --piper` sets up Piper with a German voice; it is then used automatically for German texts (other languages: espeak-ng).

## Chat and templates

- **💬 Chat tab** (in the agent panel): free conversation with any agent, e.g. with the head of the *Gedankenwerkstatt*, for philosophising,
  developing ideas and questioning. „📋 Als Auftrag erteilen“ hands the conversation to the agent and his team; the result comes back as a post.
  The chat runs without tools.
- **Company templates** (🏢): Web agency, Accounting/tax office, Import/export trade, **Animation agency**, **Book publisher/content agency**,
  **Thought workshop**, **Research office** (finds and reads PDFs). When founding, you choose the model for the head and the employees.

## Post and Telegram

As soon as a **top-level task** (the one you gave to an agent, usually the CEO) is finished, failed or
blocked, a post is ready for you: sidebar „📬 Post“ and, if set up, a Telegram message with the
type, the task, team figures and the result. The chain of rights and reports underneath runs as before.

**Set up Telegram (about 2 minutes):**
1. In Telegram: `@BotFather` → `/newbot` → copy the token → `.env`: `TELEGRAM_BOT_TOKEN=…`
2. `sudo systemctl restart paperclip-lite`, write `/start` to the new bot → it tells you your chat ID.
3. `.env`: enter `TELEGRAM_CHAT_ID=…`, restart the service. In the web under „Post“ there is a test message.

**Using Telegram:**

| You do | Result |
|---|---|
| Just write text | new task to the head of the chosen project (`@Name Text` = a specific agent) |
| **Reply** to a post message | the task is reworked with your text as instruction |
| Button ✅ or reply „ok“ | task marked as done |
| Send a file, photo, album, video or voice message | lands in `input/` of the chosen project; the caption becomes the task (when replying to a post: for revision); without text the file goes to your next task. Telegram bots may only download files up to 20 MB, larger ones: upload on the web |
| `/post`, `/status`, `/ok <no.>`, `/neu <Text>`, `/projekt [no.]` | overview or short commands |

The app only polls Telegram outwards, no port is opened (works behind CGNAT too). Only the chat ID from
`.env` may give commands; use a private chat, not a group. Approvals for shell commands deliberately do
**not** go through Telegram; there only a note arrives.

## Rights per agent

- **Delegate**: may hand tasks to *direct* employees (up to `PCL_MAX_DEPTH` levels, default 8).
  Optionally they start automatically, otherwise you start them yourself.
- **Judge results**: the boss may return work with feedback for revision (max. 2 rounds per employee).
- **Read**: bosses always see the reports of their employees; no separate right is needed for this.
- **Write files**: only in `workspace/<project-id>/`; paths outside are refused.
- **Run code** (default off): `run_code` starts Python, JavaScript, Bash, Ruby, PHP or Lua in a sandbox, see below.
- **Suggest shell**: only if the server has `PCL_ALLOW_SHELL=1`, and then always only after approval.
- **Pause**: blocks all new tasks of the agent.

The rights are checked **on the server**. If a model writes a forbidden action into its
answer, it is ignored and logged in the history.

## AI providers and model choice

For each agent you choose **provider and model** (panel → settings). The app fetches the model list live from the provider;
with **▶ Test** you check key and model immediately. This is how you set the right model per role: the strongest for bosses
(planning, checking, thinking), good text or code models for employees, fast cheap ones for simple work.

| Provider | Key in `.env` | Note |
|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | Sonnet, Haiku, Opus … selectable per agent |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | one key for hundreds of models (Claude, GPT, Gemini, DeepSeek, Qwen, Llama …) |
| Groq, Gemini, DeepSeek, Qwen | `GROQ_API_KEY`, `GEMINI_API_KEY`, … | several keys separated by commas = rotation when a limit is hit |
| Mistral, NVIDIA NIM, Together, Perplexity | `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `TOGETHER_API_KEY`, `PERPLEXITY_API_KEY` | Perplexity models (`sonar`) search the web themselves |
| Hugging Face, Cloudflare Workers AI | `HF_TOKEN` or `CF_ACCOUNT_ID` + `CF_API_TOKEN` | small free quotas |
| Ollama | – | local models on the Pi |
| Claude (CLI, your subscription) / ChatGPT (Codex CLI, your subscription) | – | built in: `claude -p --tools "" --strict-mcp-config --no-session-persistence` (Claude without its own tools and without connectors, text only; the work instruction replaces the Claude Code system prompt) or `codex exec --skip-git-repo-check --ephemeral -` (Codex runs in a read-only sandbox by itself), model in the drop-down (Claude: sonnet/opus/haiku); needs `PCL_ALLOW_CLI=1` and the signed-in program on the Pi |
| CLI agent | – | a command that reads the prompt from stdin, e.g. `claude -p --model sonnet`; needs `PCL_ALLOW_CLI=1` |

**Important:** A web login (OAuth, „subscription“) of ChatGPT or Claude cannot be used cleanly as an API; taking over
web sessions violates the terms of use. Ways: the provider's **API key** (billed per use, not the chat subscription) or the
**CLI agent** with the official CLI, signed in once. The app has no budget: with paid APIs and many tool rounds
costs can arise; you see the tokens per agent on the node.

## Security

- Login page with a signed cookie (7 days, `HttpOnly`, `SameSite=Strict`, `Secure` behind HTTPS).
- After 5 wrong passwords a 10-minute lock per IP; all attempts are in the audit log.
- Writing API calls need their own header (CSRF protection), plus CSP and further headers.
- Shell and CLI agents are **off** by default. Anyone who knows the password and has set `PCL_ALLOW_SHELL=1`
  can approve commands with the rights of the app user. `workspace/` is the working directory, but **no sandbox**.
- `.env`, database and work folders are in `.gitignore`. Keys never belong in the repository.
- For trading bots (NEXUS): never let agents trade without human approval.

## Company knowledge and memory

- **🧠 Company knowledge** (sidebar): what all agents of a project should always know (company, customers, style, prices, rules). It is stored in
  `wissen/firmenwissen.md` in the project folder. All `.md`/`.txt` files in `wissen/` go into every task and into the chat (together up to
  `PCL_KNOWLEDGE_CHARS`, default 8000 characters); other documents there (PDF, Word …) the agents see as a list and read when needed.
- **Memory per agent**: at the end of a task an agent can remember up to 5 lasting facts (preferences, decisions, customers,
  what worked). They are shown in the agent panel under „🧠 Gedächtnis“ (memory); you can change or clear them. Limit `PCL_MEMORY_CHARS`
  (4000); the oldest entries drop out first. Every new note is in the audit log.

## Goals, approvals, usage (as in Paperclip)

- **🎯 Goals**: goals and sub-goals per project. When assigning a task you optionally choose the goal; delegated tasks inherit it.
  Bosses see the goals with progress in the prompt, the CEO's inspection round reports it. Tick off = reached.
- **Ask first** (window ✋ Freigaben, per project, default off): *Approve the plan of the top boss* holds a new task
  until you approve the distribution plan; *Approve new employees* holds the CEO's self-staffing. Approve/reject also via a
  Telegram button. Rejected = the task lands as ❌ in the post; your reply to it makes the boss plan again.
  Shell approvals still only go through the web.
- **📊 Usage & costs**: calls, tokens and estimated costs per project, agent and model (today, 7, 30 days). No limit.
  Subscription CLIs and Ollama count as 0 $; from `PCL_ABO_WARN_5H` subscription calls in 5 hours (default 150, 0 = off) a Telegram warning arrives.
  Prices are rough estimates; your own via `PCL_PRICES='{"sonnet": 5}'` (US$ per 1 million tokens, part of the model name).

## Tests

```bash
./venv/bin/pip install pytest && ./venv/bin/python -m pytest -q tests
```
Runs without internet and without keys (provider `mock`, own database).

## 🔌 Connections (webhooks)

- **Outgoing:** in the window 🔌 Verbindungen you enter addresses (n8n, Zapier, Make, your own service; also `http://127.0.0.1:…` on the Pi),
  with a description for the agents and optional headers. Secrets belong in `.env` and are used as `${NAME}`.
  Agents with the right **„Darf Verbindungen nutzen“** (may use connections) call them with the tool `call_connection`; the agent cannot change
  the address or headers, it only sends data. **„Nur nach meiner Freigabe“** (only after my approval, default on) puts every call first under ✋ Freigaben.
  **„Bei Post benachrichtigen“** (notify on post) sends every finished result of a top-level task as JSON to the address. Time limit `PCL_CONN_TIMEOUT` (30 s).
- **Incoming:** switch on „Aufträge von außen“ (tasks from outside); then `POST /hook/<project>/<key>` with `{"text": "…", "agent": "optional"}`
  accepts a task for the boss (e.g. from n8n, iOS shortcuts or DEXTER). No login; protected only by the key in the address.
  „Neuen Schlüssel“ (new key) invalidates the old address. It is only reachable as far as PaperclipLite itself is (e.g. only in the tailnet).

## 🌐 Real browser and ▶ run code

- **Browser** (`./install.sh --browser`, installs Playwright + Chromium, about 400 MB, 64-bit system only): agents with the right
  „Internet recherchieren“ get `browse_page`. The page runs with JavaScript; the agent gets the visible text, the links and
  on request a screenshot (it sees it as with `view_image`; `save` puts it in `assets/screenshots/`). Every request of the page
  (scripts, frames, XHR, WebSockets) must go to a public address; LAN/localhost is blocked, WebRTC and downloads are off.
  Only one browser at a time (RAM), time limit `PCL_BROWSER_TIMEOUT` (30 s). Own Chromium: `PCL_BROWSER_PATH`, off: `PCL_BROWSER=0`.
- **Run code** (`./install.sh --run`, installs bubblewrap): the right „Darf Code ausführen“ (may run code, default off) gives `run_code`.
  The script runs sealed off: **no internet**, only `/usr` and the project folder (read-only under `/projekt`) are visible,
  no `.env`, no database, no home. What the script writes into its work directory lands in `output/run/<time>/`
  (max. 50 files/50 MB). Limits: `PCL_RUN_TIMEOUT` (60 s), `PCL_RUN_MEM_MB` (1024). It runs the system's Python/Node,
  so only packages installed via apt (e.g. `sudo apt install python3-pandas python3-matplotlib`). Off globally: `PCL_ALLOW_RUN=0`.
  Check: `./venv/bin/python selftest.py run browser`.

## Parallel work

Up to `PCL_WORKERS` tasks run at the same time (default 2, at most 6), e.g. several employees of one boss or tasks
of different projects. An agent never works on two tasks at once, and at most one Ollama task runs at a time
(RAM on the Pi). With subscription CLIs (Claude, Codex) parallel calls hit the subscription limit faster; then set `PCL_WORKERS=1`.

## Limits of this version

- No automatic heartbeat by schedule (tasks start manually or by delegation).
- No text-to-video AI, no scanned/image PDFs (OCR), no hiring of new agents by the CEO on his own (you create the organisation chart).
- The real browser (`browse_page`) reads pages but does not click and does not fill in forms (no logins, no purchases). The DuckDuckGo search without key can be limited or changed.
- No budget: tokens and estimated costs are only shown (📊). The round limits (revisions, check passes, depth) prevent endless loops.
- Sessions are simple signed cookies; a single device cannot be signed out specifically
  (changing the password invalidates all sessions).


## Self-test

After installation and entering the keys, `./venv/bin/python selftest.py` checks everything real that could not be tested without internet:
web search, reading pages, image search and image generator, SSRF protection, every AI provider with a mini request (incl. Ollama), Telegram
(bot token and test message to your chat ID), ffmpeg, speech output, PDF with umlauts, OCR. Single groups:
`selftest.py web | llm | telegram | media | ocr | film`. Each line shows OK, FEHLT (optional) or FEHLER with a concrete note.

## Ollama (local models)

Provider „Ollama (lokal)“: no key needed, the model list comes directly from Ollama (`ollama pull qwen2.5:3b`). In the dialog „Firma aus Vorlage“
there are the buttons „Alles lokal“ (everything local) and „Nur Mitarbeiter lokal“ (only employees local); otherwise you choose Ollama per agent. If Ollama runs on another computer
(e.g. the laptop), set `OLLAMA_URL` to its address. Small models (3B) are slow on the Pi and often keep the tool protocol
poorly; for bosses a strong model, locally rather for simple employees or the chat.

## Claude and ChatGPT via your subscription (CLI instead of API key)

In `.env`: `PCL_ALLOW_CLI=1`. You install the programs yourself on the Pi and sign in once (manufacturers' guides:
Claude Code `claude`, OpenAI Codex `codex`; sign-in with your subscription). Then „Claude (CLI, dein Abo)“ and „ChatGPT (Codex-CLI, dein Abo)“
appear in all provider lists. The server calls them without a shell, in an empty folder and **without our API keys in the environment**
(otherwise `claude` would bill the API key instead of the subscription). Limits: slower than the API (program start per answer), subscription limits apply
(many agents = quickly at the limit), and the CLI programs have their own tools – adjust the command if needed via `PCL_CLI_CLAUDE` / `PCL_CLI_CODEX`.

## Model gone? Switch agents

PaperclipLite checks every 6 hours (`PCL_MODEL_CHECK_HOURS`) whether the agents' models still exist at the provider, and also notices when a call reports „model not found“. Then a Telegram message arrives, the task fails with a clear note, and in the menu **⚠ Modelle** you switch all affected agents to another model with one click.

## Large teams

A boss can have any number of employees. In the boss's panel (settings) you select all of them under **Unterstellte Mitarbeiter** (subordinate employees) with tick boxes and save the assignment. Alternatively: drag the lower dot of the boss onto an employee. The button **🗂 Ordnen** (arrange) creates the whole organisation chart (groups of 6 or more employees in rows of 5).

## CEO assembles his team himself

The CEO from the palette has the right **„Darf sein Team selbst zusammenstellen“** (may assemble his team himself, `recruit`). If he has no employees yet and gets a task, he analyses it and creates employees with role, work instruction and reporting lines (up to 20, also department heads with their own team). The new ones have **no AI yet**: you assign them in the menu **⚠ Modelle** (all at once) or per agent in the settings, and then reply in the **Post** to the task (e.g. „Weiter“ = continue). After that the CEO distributes the work as usual. The CEO can give the new ones only web, images, read/write files and media, never shell.

## Opening hours and daily tasks

Sidebar **🕘 Zeitplan** (schedule): for each project set start of work, end of work and working days. For each employee you can create **daily tasks** (fixed time, at start of work or at end of work, on chosen weekdays), e.g. „every day at 15:00 check the website“. The result comes into the view „Post“ like every post (and via Telegram). If the last task of a schedule is still running, it is not started twice; if the Pi was off at the time, up to 6 hours are caught up.
At the start of work the company takes up unfinished tasks again (not started ones start, failed top-level tasks are retried up to `PCL_MAX_RESUMES`=2 times). Optionally the company rests completely outside opening hours. The time is that of the Pi; if it is wrong, set `PCL_TZ=Europe/Vienna` in `.env`.

## CEO inspection round

In the window **🕘 Zeitplan** the **👑 CEO-Kontrollgang** (CEO inspection round) sets up a daily inspection round of the top boss (default: at end of work; further times via „Neue tägliche Aufgabe“ + tick *Kontrollgang*). The system attaches a **status report** with facts: per employee today started/finished/failed/open, starts outside opening hours, open tasks without a start of work, employees without AI, unfinished tasks and whether the daily tasks ran. The CEO assesses this, distributes follow-up tasks to his team if needed and writes an inspection report into the post. „📋 Statusbericht ansehen“ (view status report) shows the facts without the CEO.

## Project folder

Each project has a **folder with its name** under `workspace/` (e.g. `workspace/Buchverlag-Content-Agentur/`, umlauts are transcribed). It stays the same when the project is renamed and is **never deleted when a project is deleted**. If you create a new project with the same name, it takes over the existing folder with its files. Old number folders (`workspace/1`, `workspace/2` …) are renamed automatically to the project name at start.

## Publish a web page

In the window **📁 Dateien dieses Projekts** there is **🚀 Veröffentlichen** (publish). Only the folder `www/` in the project folder is published (`www/index.html`, plus CSS, images … with relative paths); everything else in the project (notes, `output/`, `input/`, dotfiles, symlinks to the outside) stays invisible. If there is no `www/` folder, the `index.html` of the project folder is served as before (without `input/` and hidden files). The page runs permanently on its own port (from 8800, `PCL_SITE_PORT_BASE`), by default only on the Pi itself: `http://127.0.0.1:8800/`. For access on the network set `PCL_SITE_HOST=0.0.0.0` in `.env`. Agents with the right „Darf die Webseite zur Veröffentlichung vorschlagen“ (may propose the web page for publication) can request an approval for „publish“; only your click under **Freigaben** puts the page online. Changes by the agents are visible immediately; after a restart the page runs again automatically. For the open internet a reverse proxy with HTTPS belongs in front (e.g. Caddy), not the small server.
