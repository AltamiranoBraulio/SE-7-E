import json
import os
import random
import re
from typing import Dict, List, Tuple

KB_FILE = "knowledge_base.json"

# -----------------------------
# Utilidades de texto y similitud
# -----------------------------
def normalize(text: str) -> str:
    text = text.lower().strip()
    # quitar tildes simples y caracteres no alfanuméricos (conservar espacios)
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ü": "u", "ñ": "n"
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def jaccard_tokens(a: str, b: str) -> float:
    ta = set(normalize(a).split())
    tb = set(normalize(b).split())
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0

# -----------------------------
# Base de conocimiento
# Estructura: {"intents": [{"patterns": [...], "responses": [...]}]}
# -----------------------------
def default_kb() -> Dict:
    return {
        "startup_lines": [
            "Hola 👋",
            "¿Cómo estás?",
            "¿De qué te gustaría hablar?"
        ],
        "intents": [
            {
                "patterns": ["hola", "buenas", "hey", "que onda", "que tal"],
                "responses": ["¡Hola! ¿En qué puedo ayudarte?", "¡Hey! ¿Qué tema te interesa hoy?"]
            },
            {
                "patterns": ["como estas", "que tal estas"],
                "responses": ["¡A toda máquina! ¿Y tú?", "Muy bien, listo para ayudarte."]
            },
            {
                "patterns": ["de que te gustaria hablar", "temas", "sugerencias"],
                "responses": ["Podemos hablar de motores, electrónica, IA, emprendimiento… tú eliges."]
            },

            # --- Dominio de ejemplo: mejores motores tuning de la historia ---
            {
                "patterns": [
                    "mejores motores tuning de la historia",
                    "cuales son los mejores motores para tuning",
                    "top motores para modificar",
                    "mejor motor para tuneo"
                ],
                "responses": [
                    "Algunos clásicos del tuning: Toyota 2JZ-GTE, Nissan RB26DETT, Honda B16/B18/K20, Mitsubishi 4G63T, VW 1.8T/2.0T, GM LS (LS1/LS3), Ford Coyote 5.0, BMW S54/S55, Subaru EJ20/EJ25.",
                    "Lista rápida: 2JZ-GTE, RB26DETT, 4G63T, K20, LS3, Coyote 5.0, 1.8T VAG. ¿Quieres pros/contras de alguno?"
                ]
            },
            {
                "patterns": [
                    "por que el 2jz es tan bueno",
                    "ventajas del 2jz",
                    "2jz gte fuerte"
                ],
                "responses": [
                    "El 2JZ-GTE es famoso por su bloque de hierro súper robusto, bielas fuertes, culata eficiente y soporte aftermarket enorme; aguanta potencias altas con preparación adecuada."
                ]
            },
            {
                "patterns": [
                    "rb26 vs 2jz",
                    "comparacion rb26 2jz",
                    "cual es mejor rb26 o 2jz"
                ],
                "responses": [
                    "RB26DETT: sonido icónico, alto potencial pero requiere cariño en lubricación; 2JZ-GTE: más robusto de serie, fácil de llevar a potencias altas. La elección depende de presupuesto, disponibilidad y objetivo."
                ]
            }
        ]
    }

def load_kb() -> Dict:
    if not os.path.exists(KB_FILE):
        kb = default_kb()
        save_kb(kb)
        return kb
    with open(KB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_kb(kb: Dict) -> None:
    with open(KB_FILE, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

# -----------------------------
# Motor de conversación
# -----------------------------
def find_best_intent(user_msg: str, kb: Dict, threshold: float = 0.45) -> Tuple[int, float, str]:
    """
    Devuelve (índice_intent, similitud, pattern_ganador) o (-1, 0.0, "")
    """
    best_idx, best_sim, best_pat = -1, 0.0, ""
    for i, intent in enumerate(kb.get("intents", [])):
        for pat in intent.get("patterns", []):
            sim = jaccard_tokens(user_msg, pat)
            if sim > best_sim:
                best_idx, best_sim, best_pat = i, sim, pat
    if best_sim >= threshold:
        return best_idx, best_sim, best_pat
    return -1, best_sim, best_pat

def respond_from_intent(intent: Dict) -> str:
    responses = intent.get("responses", [])
    if not responses:
        return "No tengo una respuesta guardada aún."
    return random.choice(responses)

def acquire_new_knowledge(user_msg: str, kb: Dict) -> str:
    print("\n🤖 No encontré una respuesta exacta para tu pregunta.")
    print("Para enseñarme, escribe la respuesta que te gustaría que yo diga la próxima vez.")
    print("(O presiona Enter sin texto para saltar.)")
    new_resp = input("Tu respuesta deseada: ").strip()
    if not new_resp:
        return "Entendido. Sigamos."

    print("\n¿Quieres guardar también una o más frases de activación (patrones) para asociar esta respuesta?")
    print("Si dejas vacío, usaré tu pregunta actual como patrón.")
    pat_line = input("Patrones separados por ';' (opcional): ").strip()
    if pat_line:
        patterns = [p.strip() for p in pat_line.split(";") if p.strip()]
    else:
        patterns = [user_msg]

    # normalizar duplicados: si ya existe un intent con el mismo patrón, agrega la respuesta
    attached = False
    for intent in kb["intents"]:
        if any(normalize(p) == normalize(pt) for p in patterns for pt in intent.get("patterns", [])):
            intent.setdefault("responses", []).append(new_resp)
            attached = True
            break

    if not attached:
        kb["intents"].append({
            "patterns": patterns,
            "responses": [new_resp]
        })

    save_kb(kb)
    return "¡Gracias! He aprendido una nueva asociación."

def chat_loop():
    kb = load_kb()

    print("===========================================")
    print("  Mini Sistema Experto con Aprendizaje 🧠  ")
    print("===========================================\n")

    # Líneas precargadas (3)
    for line in kb.get("startup_lines", []):
        print(f"🤖 {line}")

    print("\nEscribe 'salir' para terminar.\n")

    while True:
        user = input("Tú: ").strip()
        if not user:
            continue
        if user.lower() in {"salir", "exit", "quit"}:
            print("🤖 ¡Hasta luego!")
            break

        idx, sim, pat = find_best_intent(user, kb)
        if idx >= 0:
            intent = kb["intents"][idx]
            answer = respond_from_intent(intent)
            print(f"🤖 {answer}  (match≈{sim:.2f})")
        else:
            # No hubo match suficiente → adquirir conocimiento
            msg = acquire_new_knowledge(user, kb)
            print(f"🤖 {msg}")

if __name__ == "__main__":
    chat_loop()
#Para activar menciona motores de carreras, hablame sobre el 2jz gte, 2jz