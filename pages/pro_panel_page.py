# pages/pro_panel_page.py
import flet as ft
from typing import Optional, Dict, Any
from components.app_header import AppHeader
from theme import BG, INK, MUTED, rounded_card, primary_button, ghost_button
from services.firebase_service import FirebaseService

LEVEL_ABBR = {
    "Licenciatura": "Lic.",
    "Maestría": "Mtra./Mtro.",
    "Ingeniería": "Ing.",
    "Doctorado": "Dr./Dra.",
}

def _safe(d: Optional[Dict[str, Any]], key: str, default=""):
    return (d or {}).get(key) or default

def _compose_display_name(level: Optional[str], full_name: Optional[str]) -> str:
    if level in LEVEL_ABBR and full_name:
        return f"{LEVEL_ABBR[level]} {full_name}"
    return full_name or ""

def _chip(text: str, icon: Optional[str] = None):
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=9999,
        bgcolor="#F2EEFF",
        border=ft.border.all(1, "#E2DAFF"),
        content=ft.Row(
            [
                *( [ft.Icon(icon, size=16, color="#6C54D8")] if icon else [] ),
                ft.Text(text, size=12, color="#5A4D8F"),
            ],
            spacing=6,
            tight=True,
        ),
    )

def ProPanelView(page: ft.Page):
    sess_user = page.session.get("user")
    if not sess_user or not sess_user.get("uid"):
        return ft.View(route="/pro", controls=[ft.Text("Inicia sesión para continuar")], bgcolor=BG)

    uid = sess_user["uid"]
    fb = FirebaseService()

    # --- Cargar perfil ---
    profile = fb.get_user_profile(uid) or {}
    pro: Dict[str, Any] = profile.get("professional") or {}

    photo_url = _safe(pro, "photoUrl", None)
    full_name = _safe(pro, "fullName")
    specialty = _safe(pro, "specialty")
    cedula = _safe(pro, "cedula")
    phone = _safe(pro, "phone")
    purpose = _safe(pro, "purpose")
    level = _safe(pro, "level")  # Licenciatura / Maestría / Ingeniería / Doctorado
    state = _safe(pro, "state")
    municipality = _safe(pro, "municipality")

    has_complete_extra = all([purpose, level, state, municipality])

    # ---------- Banner superior ----------
    banner = ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=16),
        border_radius=16,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=["#F5F2FF", "#F0EEFF", "#F7F6FF"],
        ),
        border=ft.border.all(1, "#E6E0FF"),
        shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.08, "#000000")),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.VERIFIED_USER_ROUNDED, color="#6C54D8"),
                ft.Column(
                    [
                        ft.Text("Tu espacio profesional", size=16, weight=ft.FontWeight.W_600, color=INK),
                        ft.Text(
                            "Administra tus datos y mantén tu perfil actualizado para conectar mejor con las personas.",
                            size=12,
                            color=MUTED,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    # ---------- Tarjeta de perfil (izquierda) ----------
    if photo_url:
        avatar = ft.Container(
            width=128, height=128,
            border_radius=100,
            bgcolor="#EEE7FF",
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Image(src=photo_url, fit=ft.ImageFit.COVER),
        )
    else:
        initials = (full_name or profile.get("username") or "M")[0:1].upper()
        avatar = ft.Container(
            width=128, height=128,
            border_radius=100,
            bgcolor="#EDE7FF",
            alignment=ft.alignment.center,
            content=ft.Text(initials, size=46, weight=ft.FontWeight.W_700, color="#6C54D8"),
        )

    display_name = _compose_display_name(level, full_name) or (profile.get("username") or profile.get("email") or "")
    subtitle_prof = specialty or "Añade tu especialidad"

    left_card = rounded_card(
        ft.Column(
            [
                ft.Container(alignment=ft.alignment.center, content=avatar),
                ft.Container(height=12),
                ft.Text(display_name, size=20, weight=ft.FontWeight.W_700, color=INK, text_align=ft.TextAlign.CENTER),
                ft.Text(subtitle_prof, size=13, color=MUTED, text_align=ft.TextAlign.CENTER),
                ft.Container(height=14),
                ft.Row(
                    [
                        _chip(f"Cédula: {cedula or '—'}", ft.Icons.BADGE_OUTLINED),
                        _chip(f"Tel: {phone or '—'}", ft.Icons.PHONE_OUTLINED),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                    wrap=True,
                ),
                ft.Container(height=8),
                ft.Row(
                    [
                        _chip((state or "—"), ft.Icons.LOCATION_ON_OUTLINED),
                        _chip((municipality or "—"), ft.Icons.MAP_OUTLINED),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                    wrap=True,
                ),
                ft.Container(height=16),
                primary_button("Editar perfil", lambda e: e.page.go("/pro/edit")),
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        18,
    )

    # ---------- Detalles y propósito (derecha) ----------
    if not has_complete_extra:
        callout = ft.Container(
            bgcolor="#FFF7E6",
            border=ft.border.all(1, "#FFD599"),
            border_radius=12,
            padding=12,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO, color="#D17B00"),
                    ft.Text(
                        "Tu perfil está incompleto. Agrega tu ubicación, nivel y propósito.",
                        color="#7A4B00",
                    ),
                    ft.Container(expand=True),
                    ghost_button("Completar ahora", lambda e: e.page.go("/pro/edit")),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
        )
    else:
        callout = ft.Container()

    purpose_card = rounded_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Propósito profesional", size=16, weight=ft.FontWeight.W_600, color=INK),
                        ft.Container(expand=True),
                        ghost_button("Editar", lambda e: e.page.go("/pro/edit")),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    purpose or "Describe brevemente cómo piensas ayudar desde Mindful+.",
                    color=INK if purpose else MUTED,
                    size=13,
                ),
            ],
            spacing=10,
        ),
        16,
    )

    grid_info = rounded_card(
        ft.Column(
            [
                ft.Text("Resumen de tu perfil", size=16, weight=ft.FontWeight.W_600, color=INK),
                ft.Container(height=6),
                ft.Row(
                    [
                        ft.Column(
                            [ft.Text("Nombre completo", size=12, color=MUTED),
                             ft.Text(full_name or "—", size=14, color=INK)],
                            spacing=4, expand=True,
                        ),
                        ft.Column(
                            [ft.Text("Nivel", size=12, color=MUTED),
                             ft.Text(level or "—", size=14, color=INK)],
                            spacing=4, expand=True,
                        ),
                    ],
                    spacing=16,
                ),
                ft.Row(
                    [
                        ft.Column(
                            [ft.Text("Estado", size=12, color=MUTED),
                             ft.Text(state or "—", size=14, color=INK)],
                            spacing=4, expand=True,
                        ),
                        ft.Column(
                            [ft.Text("Municipio", size=12, color=MUTED),
                             ft.Text(municipality or "—", size=14, color=INK)],
                            spacing=4, expand=True,
                        ),
                    ],
                    spacing=16,
                ),
            ],
            spacing=10,
        ),
        16,
    )

    right_column = ft.Column(
        [callout, purpose_card, grid_info],
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    # ---------- Layout responsivo ----------
    gradient_bg = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
            colors=["#F8F7FF", "#F7F6FF", "#FAF9FF"],
        ),
    )

    content_wrap = ft.Container(
        expand=True,
        padding=20,
        content=ft.Column(
            [
                ft.Container(height=4),
                banner,
                ft.Container(height=16),
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            col={"xs": 12, "sm": 12, "md": 5, "lg": 4, "xl": 4},
                            content=left_card,
                        ),
                        ft.Container(
                            col={"xs": 12, "sm": 12, "md": 7, "lg": 8, "xl": 8},
                            content=right_column,
                        ),
                    ],
                    columns=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Container(height=8),
            ],
            spacing=0,
            expand=False,
        ),
    )

    body = ft.Container(
        expand=True,
        bgcolor=BG,
        content=ft.Stack(
            [gradient_bg, ft.Container(content=content_wrap, expand=True)],
            expand=True,
        ),
    )

    main_col = ft.Column([body], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

    view = ft.View(
        route="/pro",
        bgcolor=BG,
        controls=[AppHeader(page, active_route="home"), main_col],
    )

    # ---------- Ajuste seguro (solo cuando la View ya esté montada) ----------
    def _adjust():
        # Aquí podrías adaptar tamaños dependiendo de page.width/page.height si lo necesitas.
        # No llames view.update() aquí; usa page.update() en el on_resized.
        pass

    # Ejecutar después de montar la vista
    try:
        page.invoke_later(_adjust)
    except Exception:
        # si invoke_later no existe en tu versión, puedes ignorar; el on_resized hará el ajuste
        pass

    page.on_resized = lambda e: ( _adjust(), page.update() )

    return view
