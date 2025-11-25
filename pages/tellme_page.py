from components.app_header import AppHeader
import os
import json
import threading
import requests
import flet as ft

from theme import BG, INK, MUTED, rounded_card
from ui_helpers import shell_header

# Endpoint del modelo Gemini
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


def TellMeView(page: ft.Page):
    """
    Vista de chat Mindful+ con Gemini.
    Fluida y con memoria de contexto (últimos mensajes).
    """

    # ---------- Sesión ----------
    sess_user = page.session.get("user") if page.session else None
    username = "amig@"
    if isinstance(sess_user, dict):
        username = (
            sess_user.get("username")
            or (sess_user.get("email") or "amig@z").split("@")[0]
            or "amig@"
        )

    # ---------- Encabezado ----------
    header = shell_header("Mindful+ chat", "Un espacio seguro para conversar 💜")

    # ---------- UI ----------
    chat = ft.ListView(
        expand=True,
        spacing=12,
        padding=12,
        auto_scroll=True,
    )

    input_field = ft.TextField(
        hint_text="Escribe aquí…",
        expand=True,
        border_radius=20,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=10),
        bgcolor="#f9f8ff",
    )

    send_btn = ft.IconButton(
        icon=ft.Icons.SEND_ROUNDED, tooltip="Enviar", icon_color="#5B4BDB"
    )

    # ---------- Memoria del chat ----------
    conversation_history = []  # lista de mensajes [("user", "..."), ("assistant", "...")]

    # ---------- Helpers ----------
    def add_message(text, is_user=False):
        """Muestra un mensaje en el chat visual."""
        max_width = min(420, page.width * 0.75 if page.width else 380)
        color_bg = "#5B4BDB" if is_user else "#EDE7FF"
        color_text = "white" if is_user else INK
        align = ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START

        bubble = ft.Container(
            content=ft.Text(text, color=color_text, selectable=True),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            bgcolor=color_bg,
            border_radius=20,
            width=max_width,
        )

        chat.controls.append(ft.Row([bubble], alignment=align))
        page.update()

    # Burbuja de "escribiendo..."
    typing_row = ft.Row(
        controls=[
            ft.Container(
                bgcolor="#F4F1FF",
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                content=ft.Row(
                    [
                        ft.ProgressRing(width=14, height=14, color="#5B4BDB"),
                        ft.Text("Mindful+ está escribiendo...", size=12, color=MUTED),
                    ],
                    spacing=8,
                    alignment=ft.MainAxisAlignment.START,
                ),
            )
        ],
        alignment=ft.MainAxisAlignment.START,
    )

    # ---------- Comunicación con Gemini ----------
    def call_gemini(prompt: str):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "⚠️ No se encontró la API key (.env)."

        # Prepara contexto (últimos 6 turnos)
        recent_context = conversation_history[-6:]
        context_text = ""
        for role, msg in recent_context:
            if role == "user":
                context_text += f"Usuario: {msg}\n"
            else:
                context_text += f"Mindful+: {msg}\n"

        # Instrucción de sistema
        system_prompt = (
            "Eres Mindful+, un acompañante emocional cálido y empático. "
            "Responde con amabilidad, comprensión y sin juicios. "
            "No te presentes en cada mensaje, solo continúa la conversación "
            "como un amigo que recuerda lo anterior.\n\n"
        )

        headers = {"Content-Type": "application/json"}
        url = f"{GEMINI_URL}?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": system_prompt
                            + context_text
                            + f"Usuario: {prompt}\nMindful+:"
                        }
                    ]
                }
            ]
        }

        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=25)
            r.raise_for_status()
            j = r.json()
            return j["candidates"][0]["content"]["parts"][0]["text"]
        except requests.exceptions.RequestException:
            # Sin internet o problema de red
            return "❌ No hay internet, el chat no está disponible por el momento."
        except Exception as e:
            return f"💜 Lo siento, hubo un error al procesar tu mensaje: {e}"

    # ---------- Lógica de envío ----------
    def send_message(e=None):
        text = input_field.value.strip()
        if not text:
            return

        # Mostrar el mensaje del usuario
        add_message(text, is_user=True)
        conversation_history.append(("user", text))

        # Desactivar entrada y mostrar animación
        input_field.value = ""
        input_field.disabled = True
        send_btn.disabled = True
        chat.controls.append(typing_row)
        page.update()

        # Hilo de procesamiento
        def task():
            reply = call_gemini(text)
            conversation_history.append(("assistant", reply))

            def finish():
                if typing_row in chat.controls:
                    chat.controls.remove(typing_row)
                add_message(reply, is_user=False)
                input_field.disabled = False
                send_btn.disabled = False
                input_field.focus()
                page.update()

            try:
                page.invoke_later(finish)
            except Exception:
                finish()

        threading.Thread(target=task, daemon=True).start()

    send_btn.on_click = send_message
    input_field.on_submit = send_message

    # ---------- Mensaje inicial ----------
    intro = (
        f"Hola {username} 🌿 Soy Mindful+, tu acompañante emocional. "
        "Cuéntame cómo te sientes hoy 💜"
    )
    add_message(intro, is_user=False)
    conversation_history.append(("assistant", intro))

    # ---------- Estructura ----------
    layout = ft.Column(
        [
            rounded_card(ft.Column([header], spacing=6), 16),
            ft.Container(chat, border_radius=16, bgcolor="white", expand=True),
            ft.Container(
                content=ft.Row(
                    [input_field, send_btn],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor="#F9F8FF",
                padding=10,
                border_radius=30,
                shadow=ft.BoxShadow(
                    blur_radius=6,
                    color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
                ),
            ),
        ],
        spacing=12,
        expand=True,
    )

    # ---------- Vista final ----------
    return ft.View(
        route="/tellme",
        bgcolor=BG,
        controls=[AppHeader(page, active_route="tellme"), layout],
    )
