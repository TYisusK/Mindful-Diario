# services/gemini_service.py
import os, json, requests

DEFAULT_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
DEBUG = True  # logs en consola


class GeminiService:
    def __init__(self, api_key: str | None = None, model_url: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or "TU_API_KEY_AQUI"
        self.url = (model_url or DEFAULT_URL) + f"?key={self.api_key}"

    # --------------------------
    # FRASE BREVE DE DIAGNÓSTICO
    # --------------------------
    def phrase_for_diagnostic(
        self,
        diagnosis: str,
        emotions: list[str],
        day_tags: list[str],
        note: str | None,
        char_limit: int = 120
    ) -> str:
        prompt = f"""Eres un coach amable y directo. Genera UNA sola frase breve, en español, motivadora y empática.
Debe tener MÁXIMO {char_limit} caracteres y NO incluir emojis.
Perfil del día:
- Diagnóstico: {diagnosis}
- Emociones: {', '.join(emotions) if emotions else 'ninguna'}
- Situaciones del día: {', '.join(day_tags) if day_tags else 'ninguna'}
- Nota breve: {note or 'sin nota'}

Responde SOLO con la frase final (sin comillas ni prefacios)."""

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        if DEBUG:
            print("[Gemini] POST", self.url)
        r = requests.post(
            self.url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        if DEBUG:
            print("[Gemini] status:", r.status_code)
        r.raise_for_status()
        j = r.json()
        if DEBUG:
            print("[Gemini] body(head):", str(j)[:300], "...")
        try:
            text = j["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            text = ""
        return (text or "Sigue adelante: cada paso cuenta.").strip()[:char_limit].rstrip()

    # --------------------------
    # RECOMENDACIÓN COMPLETA (una por día)
    # --------------------------
    def generate_professional_recommendation(
        self,
        notes_today: list[dict],
        diags_today: list[dict],
        author_name: str | None = None,
        char_limit: int = 600,
        temperature: float = 0.8,
        top_p: float = 0.9,
        top_k: int = 40,
    ) -> str:
        """
        Genera UNA recomendación completa (texto único) basada en notas y diagnósticos del día.
        """
        # --------- compilar contexto ---------
        def snip(s: str, n: int = 240):
            s = (s or "").strip().replace("\n", " ")
            return s[:n].rstrip()

        notes_summary = "\n".join(
            [f"- {snip(n.get('title','Sin título'))}: {snip(n.get('content',''), 400)}" for n in notes_today]
        ) or "Sin notas hoy."

        diags_summary_lines = []
        for d in diags_today[:3]:
            mood = d.get("mood")
            diag = d.get("diagnosis")
            emos = ", ".join(d.get("emotions", [])[:4])
            tags = ", ".join(d.get("dayTags", [])[:4])
            diags_summary_lines.append(
                f"- Estado emocional: {diag or 'Sin diagnóstico'} (ánimo {mood or '?'} /5, emociones [{emos}], día [{tags}])"
            )
        diags_summary = "\n".join(diags_summary_lines) or "Sin diagnósticos hoy."

        name = author_name or "la persona usuaria"

        # --------- construir prompt ---------
        prompt = f"""
Eres la asistente empática y profesional de la app de bienestar mental Mindful.
Tu nombre es *Asistente de Mindful*. Hablas con tono cálido, humano y reflexivo.

Tu tarea:
Basándote en las siguientes observaciones del usuario llamado {name},
genera UNA sola recomendación general para hoy, con un enfoque de bienestar emocional.

Debe:
- Comenzar con "Hola, soy la asistente de Mindful..."
- Redactarse como un texto único, 1 o 2 párrafos (máximo {char_limit} caracteres).
- Reconocer el estado emocional del usuario.
- Sugerir acciones concretas y amables (autocuidado, respiración, descanso, conexión social).
- Cerrar con una nota positiva, de esperanza o motivación.
- NO usar emojis, ni viñetas, ni listas.

Notas del día:
{notes_summary}

Diagnósticos recientes:
{diags_summary}

Responde SOLO con el texto final (sin comillas ni introducciones adicionales).
"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "max_output_tokens": 800,
            },
        }

        if DEBUG:
            print("[Gemini] POST (recomendación única):", self.url)
        r = requests.post(
            self.url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if DEBUG:
            print("[Gemini] status:", r.status_code)
        r.raise_for_status()
        j = r.json()
        if DEBUG:
            print("[Gemini] body(head):", str(j)[:300], "...")

        try:
            text = j["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            text = ""

        if not text:
            text = (
                "Hola, soy la asistente de Mindful. Hoy te recomiendo tomarte un momento "
                "para respirar, reflexionar sobre tus emociones y cuidar de ti. "
                "Recuerda que incluso los pequeños pasos cuentan para tu bienestar."
            )

        if DEBUG:
            print("[Gemini] Response (preview):", text[:180], "...")
        return text.strip()
