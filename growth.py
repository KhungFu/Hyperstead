"""Hyperstead: Welten und Wachstum.

Eine Welt ist nur ein Paket aus Begriffen, Symbolen, Farben und Stufennamen fuer die Oberflaeche.
Die KI-Agenten sehen nie Spielbegriffe, ihre Prompts bleiben neutral (Auftrag, Bericht, Team).
Punkte werden aus dem Audit-Log berechnet (append-only), daher bekommen alte Projekte ihre Punkte
automatisch nachgeruestet und nichts muss mitgezaehlt werden.
"""

DEFAULT_WORLD = "tycoon"

# Punkte je Ereignis
POINTS = {"done_first": 10, "done_revised": 5, "inbox_closed": 20, "task_failed": -3, "inbox_rework": -5}

# Stufen: ab Punkten, Teamgroesse und Tiefe, die die Fuehrung SELBST anwerben darf (None = keine Grenze)
STAGE_POINTS = [0, 100, 300, 700, 1500]
STAGE_TEAM = [8, 12, 18, 25, None]
STAGE_DEPTH = [2, 3, 4, 5, None]

# Raenge der Agenten nach eigenen abgenommenen Lieferungen
RANK_AT = [0, 5, 20, 60]

WORLDS = {
    "guild": {
        "name": "Gilde", "tagline": "Gründe deine Gilde, bau dein Königreich.",
        "stages": [["🛖", "Hütte"], ["🏡", "Weiler"], ["🏘️", "Dorf"], ["🏰", "Burg"], ["👑", "Königreich"]],
        "ranks": [["🌱", "Lehrling"], ["🔧", "Geselle"], ["⚒️", "Meister"], ["⭐", "Großmeister"]],
        "words": {"owner": "König:in", "top": "Burgherr", "lead": "Zunftmeister:in", "member": "Zunftmitglied",
                  "team": "Zunft", "teams": "Zünfte", "task": "Schriftrolle", "tasks": "Schriftrollen",
                  "done": "besiegelt", "project": "Gilde", "world": "Gildenstadt", "points": "Ruhm"},
        "buildings": ["Schreibstube", "Alchemistenlabor", "Malerstube", "Handelskontor", "Schmiede", "Bibliothek"],
        "colors": {"accent": "#b8892b", "accent2": "#2f5d3a", "ground": "#efe4c9", "ground_dark": "#2a241b"},
    },
    "tycoon": {
        "name": "Tycoon", "tagline": "Von der Garage zum Konzern.",
        "stages": [["🛠️", "Garage"], ["🏚️", "Werkstatt"], ["🏪", "Laden"], ["🏢", "Firmensitz"], ["🏙️", "Konzern"]],
        "ranks": [["🌱", "Neuling"], ["🔧", "Profi"], ["⚙️", "Experte"], ["⭐", "Legende"]],
        "words": {"owner": "Gründer:in", "top": "Boss", "lead": "Raumleitung", "member": "Mitarbeiter:in",
                  "team": "Raum", "teams": "Räume", "task": "Ticket", "tasks": "Tickets",
                  "done": "abgenommen", "project": "Firma", "world": "Firmengelände", "points": "Umsatzpunkte"},
        "buildings": ["Schreibraum", "Labor", "Studio", "Handelsbüro", "Werkstatt", "Archiv"],
        "colors": {"accent": "#14b8a6", "accent2": "#1e3a5f", "ground": "#e8eef3", "ground_dark": "#0f1a26"},
    },
    "gizmo": {
        "name": "Gizmo-Stadt", "tagline": "Eine kleine Stadt, die für dich arbeitet.",
        "stages": [["⛺", "Lager"], ["🏡", "Dorf"], ["🏘️", "Kleinstadt"], ["🏛️", "Stadt"], ["🌆", "Metropole"]],
        "ranks": [["🌱", "Neuling"], ["🔩", "Bastler"], ["🤖", "Meister-Gizmo"], ["⭐", "Legende"]],
        "words": {"owner": "Stadtgründer:in", "top": "Bürgermeister:in", "lead": "Werkmeister:in", "member": "Gizmo",
                  "team": "Gebäude", "teams": "Gebäude", "task": "Arbeitszettel", "tasks": "Arbeitszettel",
                  "done": "geliefert", "project": "Stadt", "world": "Stadtplan", "points": "Stadtpunkte"},
        "buildings": ["Druckerei", "Tüftellabor", "Atelier", "Markthalle", "Fabrik", "Rathaus"],
        "colors": {"accent": "#f97316", "accent2": "#7c3aed", "ground": "#f3f0fa", "ground_dark": "#17141f"},
    },
}


def world_ok(w):
    return w if w in WORLDS else DEFAULT_WORLD


def stage_of(points):
    s = 0
    for i, at in enumerate(STAGE_POINTS):
        if points >= at:
            s = i
    return s


def rank_of(done):
    r = 0
    for i, at in enumerate(RANK_AT):
        if done >= at:
            r = i
    return r


def points_from_events(done_rounds, closed, failed, rework):
    """done_rounds: Liste der rounds-Werte je erledigter Lieferung. Nie unter 0."""
    p = sum(POINTS["done_first"] if not r else POINTS["done_revised"] for r in done_rounds)
    p += closed * POINTS["inbox_closed"] + failed * POINTS["task_failed"] + rework * POINTS["inbox_rework"]
    return max(0, p)


def stage_info(points, world=DEFAULT_WORLD, max_depth=8):
    w = WORLDS[world_ok(world)]
    s = stage_of(points)
    nxt = STAGE_POINTS[s + 1] if s + 1 < len(STAGE_POINTS) else None
    low = STAGE_POINTS[s]
    return {
        "stage": s, "stage_count": len(STAGE_POINTS), "icon": w["stages"][s][0], "name": w["stages"][s][1],
        "points": points, "from": low, "next": nxt,
        "next_name": w["stages"][s + 1][1] if nxt is not None else None,
        "next_icon": w["stages"][s + 1][0] if nxt is not None else None,
        "progress": 1.0 if nxt is None else round((points - low) / float(nxt - low), 3),
        "team_limit": STAGE_TEAM[s], "depth_limit": STAGE_DEPTH[s] if STAGE_DEPTH[s] is not None else max_depth,
    }


def rank_info(done, world=DEFAULT_WORLD):
    w = WORLDS[world_ok(world)]
    r = rank_of(done)
    nxt = RANK_AT[r + 1] if r + 1 < len(RANK_AT) else None
    return {"rank": r, "icon": w["ranks"][r][0], "name": w["ranks"][r][1], "done": done, "next": nxt}
