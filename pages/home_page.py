from components.app_header import AppHeader
import flet as ft
from datetime import datetime, timedelta
import pytz
from google.cloud import firestore as gcfirestore

from theme import BG, INK, MUTED, rounded_card
from services.firebase_service import FirebaseService
from ui_helpers import scroll_view, shell_header, two_col_grid


def HomeView(page: ft.Page):
    sess_user = page.session.get("user")
    if isinstance(sess_user, dict):
        name = (sess_user.get("username") or (sess_user.get("email") or "").split("@")[0] or "Unknown")
        uid = sess_user.get("uid")
    else:
        name = "Unknown"
        uid = None

    fb = FirebaseService()

    # --- Detectar tamaño de pantalla ---
    def is_mobile():
        return page.width and page.width <= 600
    
    def is_tablet():
        return page.width and 600 < page.width <= 1024

    # --- Header ---
    header = shell_header(f"Hola {name}", "Tu espacio para sentirte mejor", page=page)

    # --- Frase del día ---
    phrase_title = ft.Text(
        "Frase del día ✨",
        size=20 if is_mobile() else 18,
        weight=ft.FontWeight.W_600,
        color=INK
    )
    
    phrase_text = ft.Text(
        "Cargando…",
        size=15 if is_mobile() else 13,
        color=MUTED,
        selectable=True,
        max_lines=None,  # Sin límite para mejor legibilidad
        text_align=ft.TextAlign.CENTER if is_mobile() else ft.TextAlign.LEFT,
    )
    
    spinner = ft.ProgressRing(visible=True, width=20, height=20)

    def set_phrase(text: str, loading: bool):
        phrase_text.value = text
        spinner.visible = loading
        page.update()

    async def load_phrase_for_today():
        if not uid:
            set_phrase("Inicia sesión para ver tu frase del día.", loading=False)
            return
        try:
            tz = pytz.timezone("America/Mexico_City")
            now_local = datetime.now(tz)
            start_local = tz.localize(datetime(now_local.year, now_local.month, now_local.day, 0, 0, 0))
            end_local = start_local + timedelta(days=1)
            start_utc = start_local.astimezone(pytz.utc)
            end_utc = end_local.astimezone(pytz.utc)

            ref = fb.db.collection("users").document(uid).collection("diagnostics")
            q = (
                ref.where("createdAt", ">=", start_utc)
                .where("createdAt", "<", end_utc)
                .order_by("createdAt", direction=gcfirestore.Query.DESCENDING)
                .limit(1)
            )
            docs = list(q.stream())
            if not docs:
                set_phrase("Aún no haces un diagnóstico hoy. Hazlo para obtener tu frase.", loading=False)
                return
            doc = docs[0].to_dict() or {}
            phrase = doc.get("phrase")
            if phrase:
                set_phrase(phrase, loading=False)
            else:
                set_phrase("Guardaste tu diagnóstico hoy. La frase está en proceso…", loading=False)
        except Exception as ex:
            set_phrase(f"No se pudo cargar la frase: {ex}", loading=False)

    def on_refresh(_):
        try:
            page.run_task(load_phrase_for_today)
        except Exception:
            import asyncio, threading
            threading.Thread(target=lambda: asyncio.run(load_phrase_for_today()), daemon=True).start()

    # Construcción responsiva de la tarjeta de frase
    if is_mobile():
        phrase_card_content = ft.Column(
            [
                ft.Container(content=phrase_title, alignment=ft.alignment.center),
                phrase_text,
                ft.Container(content=spinner, alignment=ft.alignment.center)
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    else:
        phrase_card_content = ft.Column(
            [
                ft.Row(
                    [phrase_title, spinner],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                phrase_text
            ],
            spacing=12
        )

    phrase_card = rounded_card(phrase_card_content, 16)

    # --- Acciones ---
    def action_card(title: str, subtitle: str, on_click=None, emoji: str = "•"):
        # Tamaños responsivos
        title_size = 16 if is_mobile() else 15
        subtitle_size = 13 if is_mobile() else 12
        card_padding = 20 if is_mobile() else 16
        # For harmony: fixed height across cards and consistent padding.
        card_height = 140 if is_mobile() else 120

        # Allow long titles/subtitles to wrap naturally by removing
        # max_lines/overflow and letting the container size itself.
        return ft.Container(
            on_click=on_click,
            content=ft.Column(
                [
                    ft.Text(
                        f"{emoji} {title}",
                        size=title_size,
                        weight=ft.FontWeight.W_600,
                        color=INK,
                        # allow wrapping
                        max_lines=None,
                    ),
                    ft.Text(
                        subtitle,
                        size=subtitle_size,
                        color=MUTED,
                        max_lines=None,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=card_padding,
            bgcolor="#EDE7FF",
            border_radius=16,
            # Let the height adapt to content so long texts are visible
            expand=True,
        )

    grid_items = [
        action_card(
            "¿Cómo te sientes?",
            "Habla y expresa todo lo que sientes",
            on_click=lambda _: page.go("/diagnostic"),
            emoji="📝"
        ),
        action_card(
            "Mis notas",
            "Escribir todo lo que sientes es algo bueno",
            on_click=lambda _: page.go("/notes"),
            emoji="📒"
        ),
        action_card(
            "Recomendaciones",
            "¿Qué puedo hacer para sentirme mejor?",
            on_click=lambda _: page.go("/recommendations"),
            emoji="💡"
        ),
        action_card(
            "Tell Me +",
            "Habla con tu asistente Mindful+",
            on_click=lambda _: page.go("/tellme"),
            emoji="✨"
        ),
    ]
    
    grid = two_col_grid(grid_items, page=page)

    # --- Espaciado responsivo ---
    content_spacing = 20 if is_mobile() else 16
    
    # --- Contenedor principal con padding responsivo ---
    main_content = rounded_card(
        ft.Column(
            [header, phrase_card, grid],
            spacing=content_spacing
        ),
        16,
    )
    
    # Wrapper con padding lateral responsivo
    content_wrapper = ft.Container(
        content=main_content,
        padding=ft.padding.symmetric(
            horizontal=12 if is_mobile() else 16,
            vertical=8
        )
    )

    # --- Estructura principal con scroll ---
    body = scroll_view(content_wrapper, page=page)

    # Cargar frase automáticamente al abrir
    on_refresh(None)

    # --- Función para actualizar cuando cambie el tamaño ---
    def on_resize(e):
        # Actualizar tamaños de texto
        phrase_title.size = 20 if is_mobile() else 18
        phrase_text.size = 15 if is_mobile() else 13
        phrase_text.text_align = ft.TextAlign.CENTER if is_mobile() else ft.TextAlign.LEFT
        
        # Actualizar espaciado
        content_spacing_new = 20 if is_mobile() else 16
        main_content.content.spacing = content_spacing_new
        
        # Actualizar padding del wrapper
        content_wrapper.padding = ft.padding.symmetric(
            horizontal=12 if is_mobile() else 16,
            vertical=8
        )
        
        page.update()
    
    page.on_resize = on_resize

    return ft.View(
        route="/home",
        bgcolor=BG,
        controls=[AppHeader(page, active_route='home'), body]
    )