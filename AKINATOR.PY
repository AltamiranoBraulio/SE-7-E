# -*- coding: utf-8 -*-
"""
Akinator de coches — con aprendizaje, persistencia y galería + preguntas GUI (Tkinter)
- Ventana: carrusel de imágenes con flechas (foto + nombre + progreso)
- Botón "Empezar preguntas": dentro de la MISMA ventana aparece el cuestionario Sí/No
- La predicción (resultado) también se muestra en la MISMA ventana (con imagen)
- En paralelo: imprime catálogo completo en la terminal (nombre + imagen)
- Modo aprendizaje opcional al inicio (agregar coche + pregunta especial si hay duplicado)
- Persistencia en 'knowledge.json'
Requisitos: Python 3.8+, Pillow (pip install pillow)
"""

from typing import List, Dict, Tuple
from pathlib import Path
import json
import io

# --- GUI ---
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# --- Carga imágenes desde URL con headers (evitar 403) ---
try:
    import urllib.request as urlreq
except Exception:
    urlreq = None

DB_PATH = Path("knowledge.json")
MAX_IMG_SIZE = (800, 500)  # ancho, alto máximos dentro de la ventana

# --------------------------
# Utilidades de I/O (CLI)
# --------------------------
def ask_yesno(prompt: str) -> int:
    while True:
        ans = input(f"{prompt} (sí/no): ").strip().lower()
        ans = ans.replace("í", "i")
        if ans in {"si", "s", "y", "yes"}:
            return 1
        if ans in {"no", "n"}:
            return 0
        print("  → Responde 'sí' o 'no' (o 's'/'n').")

def ask_text(prompt: str, allow_empty: bool = False) -> str:
    while True:
        s = input(prompt).strip()
        if s or allow_empty:
            return s
        print("  → No puede estar vacío.")

def hamming(a: Tuple[int, ...], b: Tuple[int, ...]) -> int:
    return sum(x != y for x, y in zip(a, b))

def bits_to_key5(bits5: Tuple[int, int, int, int, int]) -> str:
    return "-".join(str(x) for x in bits5)

def parse_bits_str(bits_str: str) -> Tuple[int, ...]:
    return tuple(int(x) for x in bits_str.split("-"))

# ------------------------------------
# Carga / guardado de base de datos
# ------------------------------------
def seed_initial_db() -> Dict:
    cars = [
        {"name": "Ferrari F40", "bits": "1-1-0-1-1", "img": None},
        {"name": "Lamborghini Diablo", "bits": "1-1-1-0-1", "img": None},
        {"name": "Porsche 959", "bits": "1-1-1-1-1", "img": None},
        {"name": "McLaren F1", "bits": "1-1-0-0-1-1", "img": None},
        {"name": "Pagani Zonda  c12", "bits": "1-1-0-0-1-0", "img": None},
        {"name": "corvette c8 zr1", "bits": "0-0-0-1-1", "img": None},
        {"name": "Bugatti Veyron", "bits": "1-0-1-1-1", "img": None},
        {"name": "Maserati MC12", "bits": "1-0-0-0-1", "img": None},
        {"name": "Alfa Romeo 8C Competizione", "bits": "1-0-0-0-0", "img": None},
        {"name": "corvette e ray", "bits": "0-0-1-0-1", "img": None},
        {"name": "BMW M3 E30", "bits": "1-1-0-0-0", "img": None},
        {"name": "acura ", "bits": "0-0-1-1-1", "img": None},
        {"name": "Audi R8", "bits": "1-0-1-0-1", "img": None},
        {"name": "Jeep wilis", "bits": "0-1-1-0-0", "img": None},
        {"name": "Koenigsegg Agera RS", "bits": "1-0-0-1-1", "img": None},
        {"name": "M3 e92", "bits": "1-0-0-1-0", "img": None},
        {"name": "Ford GT40 (1964)", "bits": "0-1-0-0-1-1", "img": None},
        {"name": "Honda NSX (1990)", "bits": "0-1-0-0-1-0", "img": None},
        {"name": "Chevrolet Corvette C1", "bits": "0-1-0-0-0", "img": None},
        {"name": "Dodge Challenger Hellcat (2015)", "bits": "0-0-0-1-0", "img": None},
        {"name": "Nissan GT-R R35(1999)", "bits": "0-1-1-1-0", "img": None},
        {"name": "Toyota Supra MK4 (1993)", "bits": "0-1-0-1-0-0", "img": None},
        {"name": "Mazda RX-7 FD (1992)", "bits": "0-1-0-1-0-1", "img": None},
        {"name": "Apollo IE ", "bits": "0-0-0-0-1", "img": None},
        {"name": "Mitsubishi Lancer Evolution IX ", "bits": "0-0-1-1-0", "img": None},
        {"name": "golf mk4 tdi", "bits": "1-1-0-1-0", "img": None},
        {"name": "Audi RS4 B7", "bits": "1-0-1-0-0", "img": None},
        {"name": "Lexus LFA (2010)", "bits": "0-0-0-0-0", "img": None},
        {"name": "audi rs3 8v", "bits": "1-0-1-1-0", "img": None},
        {"name": "Tesla model s plaid", "bits": "0-0-1-0-0", "img": None},
        {"name": "Ford Sierra RS Cosworth (4x4)", "bits": "1-1-1-1-0", "img": None},
        {"name": "Mercedes-Benz G500 W463", "bits": "1-1-1-0-0", "img": None},
    ]
    duplex_rules = {
        "1-1-0-0-1": {"question": "¿El coche tiene un asiento central en el habitáculo?"},
        "0-1-0-0-1": {"question": "¿El coche fue diseñado originalmente para competir en Le Mans?"},
        "0-1-0-1-0": {"question": "¿El coche utiliza un motor rotativo (Wankel)?"},
    }
    return {"cars": cars, "duplex_rules": duplex_rules}

def load_db() -> Dict:
    if DB_PATH.exists():
        try:
            return json.loads(DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    db = seed_initial_db()
    save_db(db)
    return db

def save_db(db: Dict):
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

# ------------------------------------
# Núcleo del sistema experto (lógica)
# ------------------------------------
Q_BASE = [
    "1) ¿Tu coche es europeo?",
    "2) ¿Tu coche fue lanzado antes del año 2000?",
    "3) ¿Tu coche es AWD o 4x4?",
    "4) ¿Tu coche es turbo o supercargado?",
    "5) ¿Tu coche usa motor trasero?",
]

def show_catalog_cli(cars: List[Dict]):
    print("\n=== Catálogo de coches disponibles (también hay galería GUI) ===")
    for i, c in enumerate(cars, 1):
        img = f"  [imagen: {c['img']}]" if c.get("img") else ""
        print(f"{i:2d}. {c['name']}{img}")
    print("================================================================\n")

def find_candidates(db: Dict, bits5: Tuple[int, int, int, int, int]) -> List[Dict]:
    res = []
    for c in db["cars"]:
        cb = parse_bits_str(c["bits"])
        if cb[:5] == bits5:
            res.append(c)
    return res

def tiebreak_with_rule(db: Dict, bits5: Tuple[int, int, int, int, int], candidates: List[Dict], ans6: int) -> List[Dict]:
    filtered = []
    for c in candidates:
        cb = parse_bits_str(c["bits"])
        if len(cb) == 6 and cb[5] == ans6:
            filtered.append(c)
    if not filtered:
        # mantener los sin 6º bit si no se pudo filtrar explícitamente
        filtered = [c for c in candidates if len(parse_bits_str(c["bits"])) == 5] or candidates
    return filtered

def suggest_nearest(db: Dict, bits5: Tuple[int, int, int, int, int], k: int = 6) -> List[Tuple[int, Dict]]:
    scored = []
    for c in db["cars"]:
        cb = parse_bits_str(c["bits"])[:5]
        scored.append((hamming(bits5, cb), c))
    scored.sort(key=lambda x: x[0])
    return scored[:k]

# ------------------------------------
# Carga de imagen robusta
# ------------------------------------
def load_image(img_path_or_url: str, max_size=(800, 500)) -> Image.Image:
    """
    Carga imagen desde ruta local o URL con headers y reintentos.
    Redimensiona manteniendo proporción. Lanza excepción si no se puede.
    """
    if not img_path_or_url:
        raise FileNotFoundError("Sin ruta/URL")

    data = None
    p = Path(img_path_or_url)

    if p.exists():
        # Ruta local
        data = p.read_bytes()
    elif img_path_or_url.startswith(("http://", "https://")) and urlreq is not None:
        # URL remota con User-Agent y reintentos
        last_err = None
        for attempt in range(3):
            try:
                req = urlreq.Request(
                    img_path_or_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                                      "Chrome/121.0 Safari/537.36"
                    },
                )
                with urlreq.urlopen(req, timeout=20) as r:
                    data = r.read()
                break
            except Exception as e:
                last_err = e
        if data is None:
            raise RuntimeError(f"No se pudo descargar la imagen: {img_path_or_url} ({last_err})")
    else:
        raise FileNotFoundError(f"No es ruta local ni URL válida: {img_path_or_url}")

    try:
        im = Image.open(io.BytesIO(data))
        im = im.convert("RGB")
        im.thumbnail(max_size, Image.LANCZOS)
        return im
    except Exception as e:
        raise RuntimeError(f"Error abriendo imagen ({img_path_or_url}): {e}")

def make_placeholder(name: str, size=(800, 500)) -> Image.Image:
    """Genera un placeholder simple con el nombre del coche."""
    from PIL import ImageDraw, ImageFont
    im = Image.new("RGB", size, (24, 24, 24))
    draw = ImageDraw.Draw(im)
    txt = f"Sin imagen\n{name}"
    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        font = ImageFont.load_default()
    w, h = draw.multiline_textsize(txt, font=font)
    draw.multiline_text(((size[0]-w)//2, (size[1]-h)//2), txt, fill=(220, 220, 220), font=font, align="center")
    return im

# ------------------------------------
# Ventana GUI todo-en-uno (galería + preguntas + resultado)
# ------------------------------------
def game_window(db: Dict):
    """
    Una sola ventana:
    1) Galería (carrusel) con imágenes y botón "Empezar preguntas"
    2) Cuestionario de 5 preguntas Sí/No (y posible 6ª por regla)
    3) Resultado mostrado con imagen y nombre
    """
    cars = db["cars"]
    rules = db.get("duplex_rules", {})
    N = len(cars)

    root = tk.Tk()
    root.title("Akinator de coches — Galería y preguntas")

    # ---------- FRAMES ----------
    container = ttk.Frame(root, padding=10)
    container.pack(fill="both", expand=True)

    gallery_frame = ttk.Frame(container)
    quiz_frame = ttk.Frame(container)
    result_frame = ttk.Frame(container)

    for f in (gallery_frame, quiz_frame, result_frame):
        f.grid(row=0, column=0, sticky="nsew")

    container.columnconfigure(0, weight=1)
    container.rowconfigure(0, weight=1)

    # ---------- GALERÍA ----------
    # Widgets galería
    g_img_label = ttk.Label(gallery_frame)
    g_img_label.pack(pady=8)

    g_name_label = ttk.Label(gallery_frame, font=("Segoe UI", 16, "bold"))
    g_name_label.pack(pady=6)

    g_progress_label = ttk.Label(gallery_frame, font=("Segoe UI", 10))
    g_progress_label.pack(pady=2)

    g_controls = ttk.Frame(gallery_frame)
    g_controls.pack(pady=10)

    g_btn_prev = ttk.Button(g_controls, text="⬅ Anterior")
    g_btn_next = ttk.Button(g_controls, text="Siguiente ➡")
    g_btn_prev.grid(row=0, column=0, padx=6)
    g_btn_next.grid(row=0, column=1, padx=6)

    g_start_btn = ttk.Button(gallery_frame, text="Empezar preguntas", state="disabled")
    g_start_btn.pack(pady=8)

    g_status = ttk.Label(gallery_frame, anchor="w", relief="sunken")
    g_status.pack(fill="x")

    # Estado galería
    idx = {"i": 0}
    img_cache_gallery: List[ImageTk.PhotoImage] = [None] * N

    def gallery_render():
        i = idx["i"]
        car = cars[i]
        g_name_label.config(text=car["name"])
        g_progress_label.config(text=f"{i+1} / {N}")

        # Imagen
        if car.get("img"):
            try:
                im = load_image(car["img"], MAX_IMG_SIZE)
            except Exception as e:
                print(f"[IMG] {car['name']}: {e}")
                im = make_placeholder(car["name"], MAX_IMG_SIZE)
        else:
            im = make_placeholder(car["name"], MAX_IMG_SIZE)

        img_cache_gallery[i] = ImageTk.PhotoImage(im)
        g_img_label.config(image=img_cache_gallery[i])

        # Botón empezar activo sólo en el último
        if i == N - 1:
            g_start_btn.config(state="normal")
            g_status.config(text="Has llegado al final. Puedes empezar el juego.")
        else:
            g_start_btn.config(state="disabled")
            g_status.config(text="Navega con las flechas. Al final podrás empezar.")

    def gallery_prev():
        idx["i"] = (idx["i"] - 1) % N
        gallery_render()

    def gallery_next():
        idx["i"] = (idx["i"] + 1) % N
        gallery_render()

    g_btn_prev.config(command=gallery_prev)
    g_btn_next.config(command=gallery_next)

    def gallery_key(event):
        if event.keysym in ("Left", "a", "A"):
            gallery_prev()
        elif event.keysym in ("Right", "d", "D"):
            gallery_next()
        elif event.keysym in ("Return", "space"):
            if idx["i"] == N - 1 and g_start_btn["state"] == "normal":
                to_quiz()

    root.bind("<Key>", gallery_key)

    def to_quiz():
        # Cambia a frame de preguntas
        quiz_render(reset=True)
        quiz_frame.tkraise()

    g_start_btn.config(command=to_quiz)

    # ---------- QUIZ ----------
    # Estado quiz
    quiz_state = {
        "q_idx": 0,            # índice de pregunta base 0..4
        "answers": [],         # respuestas 1/0 de las 5 base
        "special_key": None,   # clave 5 bits si hay regla especial
        "special_q": None,     # texto de la pregunta especial
        "special_ans": None,   # respuesta 1/0 a la especial
        "bits5": None,         # tupla bits5
        "candidates": None,    # candidatos por bits5
    }

    q_title = ttk.Label(quiz_frame, text="Preguntas", font=("Segoe UI", 18, "bold"))
    q_title.pack(pady=(0,8))

    q_text = ttk.Label(quiz_frame, text="", wraplength=720, font=("Segoe UI", 14))
    q_text.pack(pady=10)

    q_progress = ttk.Label(quiz_frame, text="", font=("Segoe UI", 10))
    q_progress.pack()

    q_btns = ttk.Frame(quiz_frame)
    q_btns.pack(pady=14)

    q_yes = ttk.Button(q_btns, text="Sí", width=14)
    q_no  = ttk.Button(q_btns, text="No", width=14)
    q_yes.grid(row=0, column=0, padx=8)
    q_no.grid(row=0, column=1, padx=8)

    q_status = ttk.Label(quiz_frame, anchor="w", relief="sunken")
    q_status.pack(fill="x", pady=(8,0))

    def quiz_render(reset=False):
        if reset:
            quiz_state["q_idx"] = 0
            quiz_state["answers"] = []
            quiz_state["special_key"] = None
            quiz_state["special_q"] = None
            quiz_state["special_ans"] = None
            quiz_state["bits5"] = None
            quiz_state["candidates"] = None

        # Si aún estamos en preguntas base
        if quiz_state["q_idx"] < 5:
            q_text.config(text=Q_BASE[quiz_state["q_idx"]])
            q_progress.config(text=f"Pregunta {quiz_state['q_idx']+1} de 5")
            q_status.config(text="Responde con Sí o No.")
            q_yes.config(state="normal")
            q_no.config(state="normal")
            return

        # Ya contestó 5 -> calcular bits5 y ver candidatos / posible especial
        if quiz_state["bits5"] is None:
            bits5 = tuple(quiz_state["answers"])
            quiz_state["bits5"] = bits5
            candidates = find_candidates(db, bits5)
            quiz_state["candidates"] = candidates
            key = bits_to_key5(bits5)

            if key in rules:
                # hay pregunta especial
                quiz_state["special_key"] = key
                quiz_state["special_q"] = rules[key]["question"]
                # formular especial
                q_text.config(text=quiz_state["special_q"])
                q_progress.config(text="Pregunta especial (desempate)")
                q_status.config(text="Responde con Sí o No.")
                q_yes.config(state="normal")
                q_no.config(state="normal")
                return

            # si no hay especial, mostrar resultado directo
            show_result(bits5, candidates, special_used=False)
            return

        # Si ya se formuló especial y falta responder, no hacemos nada aquí.
        # El flujo continúa en on_yes/on_no

    def on_yes():
        # Si estamos en base
        if quiz_state["q_idx"] < 5:
            quiz_state["answers"].append(1)
            quiz_state["q_idx"] += 1
            quiz_render()
            return

        # Si estamos en especial
        if quiz_state["special_q"] is not None and quiz_state["special_ans"] is None:
            quiz_state["special_ans"] = 1
            bits5 = quiz_state["bits5"]
            cand = quiz_state["candidates"] or []
            filtered = tiebreak_with_rule(db, bits5, cand, ans6=1)
            show_result(bits5, filtered, special_used=True)
            return

    def on_no():
        # Base
        if quiz_state["q_idx"] < 5:
            quiz_state["answers"].append(0)
            quiz_state["q_idx"] += 1
            quiz_render()
            return

        # Especial
        if quiz_state["special_q"] is not None and quiz_state["special_ans"] is None:
            quiz_state["special_ans"] = 0
            bits5 = quiz_state["bits5"]
            cand = quiz_state["candidates"] or []
            filtered = tiebreak_with_rule(db, bits5, cand, ans6=0)
            show_result(bits5, filtered, special_used=True)
            return

    q_yes.config(command=on_yes)
    q_no.config(command=on_no)

    # ---------- RESULTADO ----------
    r_title = ttk.Label(result_frame, text="Resultado", font=("Segoe UI", 18, "bold"))
    r_title.pack(pady=(0,8))

    r_img_label = ttk.Label(result_frame)
    r_img_label.pack(pady=6)

    r_name_label = ttk.Label(result_frame, font=("Segoe UI", 16, "bold"))
    r_name_label.pack(pady=6)

    r_extra = ttk.Label(result_frame, font=("Segoe UI", 11), wraplength=720, justify="center")
    r_extra.pack(pady=4)

    r_back_btn = ttk.Button(result_frame, text="Volver a galería")
    r_back_btn.pack(pady=10)

    r_status = ttk.Label(result_frame, anchor="w", relief="sunken")
    r_status.pack(fill="x")

    img_cache_result: List[ImageTk.PhotoImage] = [None]  # una ranura

    def show_result(bits5: Tuple[int, int, int, int, int], candidates: List[Dict], special_used: bool):
        # Construir textos
        if len(candidates) == 1:
            car = candidates[0]
            r_name_label.config(text=car["name"])
            # Imagen del coche predicho
            if car.get("img"):
                try:
                    im = load_image(car["img"], MAX_IMG_SIZE)
                except Exception as e:
                    print(f"[IMG RESULT] {car['name']}: {e}")
                    im = make_placeholder(car["name"], MAX_IMG_SIZE)
            else:
                im = make_placeholder(car["name"], MAX_IMG_SIZE)
            img_cache_result[0] = ImageTk.PhotoImage(im)
            r_img_label.config(image=img_cache_result[0])

            txt = f"Binario detectado: {bits5}"
            if special_used:
                txt += " + (desempate aplicado)"
            r_extra.config(text=txt)
            r_status.config(text="¡Hecho! Si quieres, vuelve a la galería para revisar los coches.")
        elif len(candidates) > 1:
            # Varios candidatos: listarlos
            names = "\n".join(f"• {c['name']}" for c in candidates)
            r_name_label.config(text="Hay más de un candidato posible")
            r_img_label.config(image="")
            r_extra.config(text=f"Candidatos:\n{names}\n\nSugerencia: agrega más preguntas especiales para este patrón.")
            r_status.config(text=f"Patrón {bits5} produjo múltiples resultados.")
        else:
            # Sin coincidencias exactas: sugerencias
            r_name_label.config(text="No encontré coincidencias exactas")
            r_img_label.config(image="")
            nearest = suggest_nearest(db, bits5, k=6)
            sug = "\n".join(f"• {c['name']} (dist={dist}, binario={parse_bits_str(c['bits'])[:5]})"
                            for dist, c in nearest)
            r_extra.config(text=f"Sugerencias cercanas:\n{sug}")
            r_status.config(text=f"Patrón {bits5} no tiene coincidencias exactas.")

        result_frame.tkraise()

    def back_to_gallery():
        gallery_frame.tkraise()
        gallery_render()

    r_back_btn.config(command=back_to_gallery)

    # Render inicial
    gallery_frame.tkraise()
    gallery_render()

    root.mainloop()

# ------------------------------------
# Modo aprendizaje (agregar coche)
# ------------------------------------
def find_candidates_cli(db: Dict, bits5: Tuple[int, int, int, int, int]) -> List[Dict]:
    # (utilidad separada si quieres en futuro usar CLI para jugar)
    return find_candidates(db, bits5)

def add_new_car_flow(db: Dict):
    print("\n🔧 MODO APRENDIZAJE — Agregar coche nuevo")
    name = ask_text("Nombre del coche: ")
    img = ask_text("URL o ruta de imagen (opcional, deja vacío): ", allow_empty=True) or None

    print("\nAhora responde las 5 preguntas base para tu coche:")
    # reusar CLI para aprendizaje
    bits5 = []
    for q in Q_BASE:
        bits5.append(ask_yesno(q))
    bits5 = tuple(bits5)
    key5 = bits_to_key5(bits5)

    existing = find_candidates(db, bits5)
    has_rule = key5 in db.get("duplex_rules", {})

    if not existing:
        new_bits = "-".join(str(x) for x in bits5)
        db["cars"].append({"name": name, "bits": new_bits, "img": img})
        print(f"✅ Añadido sin duplicados: {name}  ({new_bits})")
        save_db(db)
        return

    print(f"⚠️ Encontré {len(existing)} coche(s) con el mismo binario 5 bits: {key5}")
    for c in existing:
        print("   -", c["name"])

    if has_rule:
        q = db["duplex_rules"][key5]["question"]
        print("\nSe usará la pregunta especial existente para asignar el 6º bit:")
        ans6 = ask_yesno(q)
        new_bits = "-".join(str(x) for x in bits5 + (ans6,))
        db["cars"].append({"name": name, "bits": new_bits, "img": img})
        print(f"✅ Añadido con 6º bit por regla existente: {name}  ({new_bits})")
        save_db(db)
        return

    print("\nNo existe aún una pregunta especial para este binario.")
    qtext = ask_text("Escribe la PREGUNTA ESPECIAL (sí/no) para diferenciar este grupo: ")
    print("\nResponde la pregunta especial para TU coche nuevo:")
    ans6_new = ask_yesno(qtext)

    # FIX: clave correcta
    db.setdefault("duplex_rules", {})
    db["duplex_rules"][key5] = {"question": qtext}
    new_bits = "-".join(str(x) for x in bits5 + (ans6_new,))
    db["cars"].append({"name": name, "bits": new_bits, "img": img})
    print(f"✅ Añadido con nueva regla y 6º bit: {name}  ({new_bits})")

    print("\nOpcional: asigna el 6º bit (sí/no) a los coches existentes de este grupo.")
    for c in existing:
        cb = parse_bits_str(c["bits"])
        if len(cb) == 6:
            continue
        print(f"\nPara: {c['name']}")
        ans6_old = ask_yesno(qtext)
        c["bits"] = "-".join(str(x) for x in bits5 + (ans6_old,))
        print(f"   → Guardado: {c['name']} ({c['bits']})")

    save_db(db)
    print("\n💾 Cambios guardados en knowledge.json")

# ------------------------------------
# Main
# ------------------------------------
def main():
    db = load_db()

    # Mantener la lista en terminal
    show_catalog_cli(db["cars"])

    print("👋 ¿Quieres agregar un coche nuevo a la base antes de abrir la ventana?")
    if ask_yesno("¿Agregar coche ahora?") == 1:
        add_new_car_flow(db)

    # Abrir ventana todo-en-uno (galería + preguntas + resultado)
    game_window(db)

if __name__ == "__main__":
    main()
