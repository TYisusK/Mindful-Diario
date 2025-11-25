# pages/help_page.py
import json
import os
import re
import uuid
import flet as ft
from typing import Dict, List, Optional, Any

from components.app_header import AppHeader
from theme import BG, INK, MUTED, rounded_card, primary_button, ghost_button
from services.firebase_service import FirebaseService

LEVEL_ABBR = {
    "Licenciatura": "Lic.",
    "Maestría": "Mtra./Mtro.",
    "Ingeniería": "Ing.",
    "Doctorado": "Dr./Dra.",
}

SPECIALTIES = [
    "Psicología clínica",
    "Psicoterapia cognitivo-conductual",
    "Psicoterapia humanista",
    "Psicoanálisis",
    "Neuropsicología",
    "Psicología infantil",
    "Tanatología",
    "Psicología educativa",
    "Psiquiatría (Médica)",
]

def _compose_display_name(level: Optional[str], full_name: Optional[str], fallback: str = "") -> str:
    base = full_name or fallback or ""
    if level in LEVEL_ABBR and base:
        return f"{LEVEL_ABBR[level]} {base}"
    return base

def _mx10(phone: str) -> str:
    digits = re.sub(r"\D+", "", phone or "")
    return digits[-10:] if len(digits) >= 10 else digits

def _load_estados() -> Dict[str, List[str]]:
    candidates = ["estados.json", "estados", "data/estados.json"]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                clean = {}
                for k, v in data.items():
                    if isinstance(v, list):
                        clean[str(k)] = [str(x) for x in v]
                return clean
            except Exception:
                pass
    # fallback mínimo
    return {
        "Ciudad de México": [
            "Álvaro Obregón", "Benito Juárez", "Coyoacán", "Cuauhtémoc", "Gustavo A. Madero",
            "Iztapalapa", "Miguel Hidalgo", "Tlalpan", "Tláhuac", "Xochimilco"
        ],
        "Jalisco": ["Guadalajara", "Zapopan", "Tlaquepaque", "Tonala"],
        "Nuevo León": ["Monterrey", "San Nicolás", "San Pedro", "Guadalupe"],
    }

def HelpView(page: ft.Page):
    fb = FirebaseService()
    estados_map = _load_estados()

    # --------- URGENTE (solo llamar) ----------
    def _call_urgent(_=None):
        page.launch_url("tel:+528009112000")

    urgent = rounded_card(
        ft.ResponsiveRow(
            [
                ft.Container(
                    col={"xs": 12, "sm": 12, "md": 7, "lg": 8},
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.SUPPORT_AGENT, color="#D22B2B"),
                            ft.Column(
                                [
                                    ft.Text("¿Necesitas ayuda urgente?", size=16, weight=ft.FontWeight.W_700, color="#A32020"),
                                    ft.Text("Línea de la Vida: 800 911 2000", size=12, color="#B54545"),
                                ],
                                spacing=2,
                                tight=True,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    col={"xs": 12, "sm": 12, "md": 5, "lg": 4},
                    alignment=ft.alignment.center_right,
                    content=ft.Row(
                        [
                            ft.FilledTonalButton("Llamar", icon=ft.Icons.CALL, on_click=_call_urgent),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ),
            ],
            columns=12,
        ),
        16,
    )

    # --------- FILTROS (reactivos + limpiar) ----------
    list_col = ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    state_dd = ft.Dropdown(
        label="Estado",
        hint_text="Selecciona un estado",
        options=[ft.dropdown.Option(s) for s in sorted(estados_map.keys())],
        border_radius=12,
        width=300,
        value=None,
        autofocus=False,
    )
    muni_dd = ft.Dropdown(
        label="Municipio",
        hint_text="Selecciona un municipio",
        options=[],
        border_radius=12,
        width=300,
        value=None,
    )
    spec_dd = ft.Dropdown(
        label="Especialidad",
        hint_text="Selecciona especialidad",
        options=[ft.dropdown.Option(s) for s in SPECIALTIES],
        border_radius=12,
        width=300,
        value=None,
    )

    def _force_rerender(ctrl: ft.Control):
        # Cambiar key obliga a Flet a reconstruir el control y actualizar el texto visible del dropdown.
        ctrl.key = str(uuid.uuid4())

    def _reload_municipios():
        muni_dd.value = None
        sel = state_dd.value
        opts = estados_map.get(sel, [])
        muni_dd.options = [ft.dropdown.Option(m) for m in opts]
        _force_rerender(muni_dd)
        page.update()

    def _clear_state(_=None):
        state_dd.value = None
        muni_dd.value = None
        muni_dd.options = []
        _force_rerender(state_dd)
        _force_rerender(muni_dd)
        _fetch_and_render()

    def _clear_muni(_=None):
        muni_dd.value = None
        _force_rerender(muni_dd)
        _fetch_and_render()

    def _clear_spec(_=None):
        spec_dd.value = None
        _force_rerender(spec_dd)
        _fetch_and_render()

    # barra de filtros
    filter_bar = rounded_card(
        ft.Column(
            [
                ft.Text("Filtrar profesionales", size=16, weight=ft.FontWeight.W_600, color=INK),
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            col={"xs": 12, "sm": 6, "md": 4},
                            content=ft.Row(
                                [
                                    state_dd,
                                    ft.IconButton(ft.Icons.CLOSE, tooltip="Limpiar estado", on_click=_clear_state),
                                ],
                                spacing=6,
                            ),
                        ),
                        ft.Container(
                            col={"xs": 12, "sm": 6, "md": 4},
                            content=ft.Row(
                                [
                                    muni_dd,
                                    ft.IconButton(ft.Icons.CLOSE, tooltip="Limpiar municipio", on_click=_clear_muni),
                                ],
                                spacing=6,
                            ),
                        ),
                        ft.Container(
                            col={"xs": 12, "sm": 6, "md": 4},
                            content=ft.Row(
                                [
                                    spec_dd,
                                    ft.IconButton(ft.Icons.CLOSE, tooltip="Limpiar especialidad", on_click=_clear_spec),
                                ],
                                spacing=6,
                            ),
                        ),
                        ft.Container(
                            col={"xs": 12},
                            content=ft.Row(
                                [
                                    ghost_button("Limpiar todo", lambda e: _clear_all()),
                                ],
                                alignment=ft.MainAxisAlignment.END,
                            ),
                        ),
                    ],
                    columns=12,
                ),
            ],
            spacing=12,
        ),
        16,
    )

    def _clear_all():
        state_dd.value = None
        muni_dd.value = None
        spec_dd.value = None
        muni_dd.options = []
        _force_rerender(state_dd)
        _force_rerender(muni_dd)
        _force_rerender(spec_dd)
        _fetch_and_render()

    # --------- ACTIONS: abrir detalle, whatsapp, llamada ----------
    def _whatsapp(num10: str):
        if not num10:
            return
        page.launch_url(f"https://wa.me/52{num10}")

    def _call(num10: str):
        if not num10:
            return
        page.launch_url(f"tel:+52{num10}")

    def _to_dict(doc) -> Dict[str, Any]:
        d = doc.to_dict() or {}
        pro = d.get("professional") or {}
        pro["_username"] = d.get("username") or d.get("email")
        return pro

    def _apply_filters(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        s = spec_dd.value
        st = state_dd.value
        m = muni_dd.value
        out = []
        for p in data:
            if s and (p.get("specialty") != s):
                continue
            if st and (p.get("state") != st):
                continue
            if m and (p.get("municipality") != m):
                continue
            out.append(p)
        return out

    # --------- DETALLE DE PROFESIONAL (Dialog) ----------
    detail_dlg = ft.AlertDialog(modal=True)

    def _open_detail(p: Dict[str, Any]):
        photo = p.get("photoUrl")
        full_name = p.get("fullName")
        level = p.get("level")
        specialty = p.get("specialty")
        cedula = p.get("cedula")
        phone = p.get("phone")
        purpose = p.get("purpose")
        state = p.get("state")
        municipality = p.get("municipality")
        username = p.get("_username")

        display = _compose_display_name(level, full_name, username)
        phone10 = _mx10(phone or "")

        avatar = (
            ft.Container(
                width=92, height=92, border_radius=60, bgcolor="#EEE7FF",
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Image(src=photo, fit=ft.ImageFit.COVER),
            )
            if photo else
            ft.Container(
                width=92, height=92, border_radius=60, bgcolor="#EDE7FF",
                alignment=ft.alignment.center,
                content=ft.Text((display[:1] or "M").upper(), size=30, color="#6C54D8", weight=ft.FontWeight.W_700),
            )
        )

        info = ft.Column(
            [
                ft.Text(display or "Profesional", size=18, weight=ft.FontWeight.W_700, color=INK),
                ft.Row([ft.Icon(ft.Icons.PSYCHOLOGY, size=16, color="#6C54D8"),
                        ft.Text(specialty or "—", size=13, color=INK)], spacing=6),
                ft.Row([ft.Icon(ft.Icons.BADGE_OUTLINED, size=16, color="#6C54D8"),
                        ft.Text(f"Cédula: {cedula or '—'}", size=13, color=INK)], spacing=6),
                ft.Row([ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=16, color="#6C54D8"),
                        ft.Text(f"{state or '—'}{', ' if municipality else ''}{municipality or ''}", size=13, color=INK)], spacing=6),
                ft.Row([ft.Icon(ft.Icons.CALL, size=16, color="#6C54D8"),
                        ft.Text(f"+52 {phone10 or '—'}", size=13, color=INK)], spacing=6),
                ft.Container(height=6),
                ft.Text("Propósito", size=13, weight=ft.FontWeight.W_600, color=INK),
                ft.Text(purpose or "—", size=13, color=MUTED),
            ],
            spacing=6,
        )

        actions = ft.Row(
            [
                ft.FilledTonalButton("WhatsApp", icon=ft.Icons.CHAT, on_click=lambda e: _whatsapp(phone10)),
                ft.OutlinedButton("Llamar", icon=ft.Icons.CALL, on_click=lambda e: _call(phone10)),
                ghost_button("Cerrar", lambda e: _close_detail()),
            ],
            spacing=10,
        )

        detail_dlg.title = ft.Row(
            [ft.Text("Perfil profesional", weight=ft.FontWeight.W_700, color=INK, size=16)],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        detail_dlg.content = ft.Container(
            width=520,
            content=ft.Column(
                [
                    ft.Row([avatar, info], spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
                    ft.Container(height=12),
                    actions,
                ],
                tight=True,
                spacing=10,
            ),
        )
        page.dialog = detail_dlg
        detail_dlg.open = True
        page.update()

    def _close_detail():
        detail_dlg.open = False
        page.update()

    # --------- Render listado ----------
    def _pro_card(pro: Dict[str, Any]):
        photo = pro.get("photoUrl")
        full_name = pro.get("fullName")
        specialty = pro.get("specialty")
        cedula = pro.get("cedula")
        level = pro.get("level")
        phone = pro.get("phone")
        state = pro.get("state")
        municipality = pro.get("municipality")
        username = pro.get("_username")

        display = _compose_display_name(level, full_name, username)
        phone10 = _mx10(phone or "")

        avatar = (
            ft.Container(
                width=64, height=64, border_radius=40, bgcolor="#EEE7FF",
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Image(src=photo, fit=ft.ImageFit.COVER),
            )
            if photo else
            ft.Container(
                width=64, height=64, border_radius=40, bgcolor="#EDE7FF",
                alignment=ft.alignment.center,
                content=ft.Text((display[:1] or "M").upper(), size=22, color="#6C54D8", weight=ft.FontWeight.W_700),
            )
        )

        chips = ft.Row(
            [
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=9999,
                    bgcolor="#F2EEFF",
                    border=ft.border.all(1, "#E2DAFF"),
                    content=ft.Row(
                        [ft.Icon(ft.Icons.PSYCHOLOGY, size=16, color="#6C54D8"),
                         ft.Text(specialty or "—", size=12, color="#5A4D8F")],
                        spacing=6,
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=9999,
                    bgcolor="#F2EEFF",
                    border=ft.border.all(1, "#E2DAFF"),
                    content=ft.Row(
                        [ft.Icon(ft.Icons.BADGE_OUTLINED, size=16, color="#6C54D8"),
                         ft.Text(f"Cédula: {cedula or '—'}", size=12, color="#5A4D8F")],
                        spacing=6,
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=9999,
                    bgcolor="#F2EEFF",
                    border=ft.border.all(1, "#E2DAFF"),
                    content=ft.Row(
                        [ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=16, color="#6C54D8"),
                         ft.Text(f"{state or '—'}{', ' if municipality else ''}{municipality or ''}", size=12, color="#5A4D8F")],
                        spacing=6,
                    ),
                ),
            ],
            spacing=8,
            wrap=True,
        )

        base_card = rounded_card(
            ft.Row(
                [
                    avatar,
                    ft.Column(
                        [
                            ft.Text(display or "Profesional", size=16, weight=ft.FontWeight.W_700, color=INK),
                            chips,
                            ft.Row(
                                [
                                    ft.FilledTonalButton("WhatsApp", icon=ft.Icons.CHAT, on_click=lambda e: _whatsapp(phone10)),
                                    ft.OutlinedButton("Llamar", icon=ft.Icons.CALL, on_click=lambda e: _call(phone10)),
                                ],
                                spacing=10,
                            ),
                        ],
                        spacing=8,
                        expand=True,
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            16,
        )

        # Click para ver detalle en dialog
        return ft.GestureDetector(content=base_card, on_tap=lambda e, p=pro: _open_detail(p))

    def _fetch_and_render(_=None):
        list_col.controls.clear()
        list_col.controls.append(
            ft.Container(padding=12, content=ft.Row([ft.ProgressRing()], alignment=ft.MainAxisAlignment.CENTER))
        )
        page.update()

        try:
            q = fb.db.collection("users").where("professional.type", "==", "profesional")
            pros = [_to_dict(doc) for doc in q.stream()]
        except Exception:
            pros = []
            try:
                for d in fb.db.collection("users").stream():
                    dd = d.to_dict() or {}
                    if isinstance(dd.get("professional"), dict) and dd["professional"].get("type") == "profesional":
                        pros.append(_to_dict(d))
            except Exception:
                pros = []

        pros = _apply_filters(pros)

        list_col.controls.clear()
        if not pros:
            list_col.controls.append(
                ft.Container(
                    padding=20,
                    border_radius=14,
                    bgcolor="#F8F8FF",
                    border=ft.border.all(1, "#ECEBFF"),
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.SEARCH_OFF, color="#7D7AA8"),
                            ft.Text("No encontramos resultados con esos filtros.", color="#7D7AA8"),
                        ],
                        spacing=8,
                    ),
                )
            )
        else:
            for p in pros:
                list_col.controls.append(_pro_card(p))

        page.update()

    # filtros reactivos
    state_dd.on_change = lambda e: (_reload_municipios(), _fetch_and_render())
    muni_dd.on_change = lambda e: _fetch_and_render()
    spec_dd.on_change = lambda e: _fetch_and_render()

    # --------- LAYOUT raíz ----------
    gradient_bg = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
            colors=["#F8F7FF", "#F7F6FF", "#FAF9FF"],
        ),
    )

    content = ft.Container(
        expand=True,
        padding=20,
        content=ft.Column(
            [
                urgent,
                ft.Container(height=12),
                filter_bar,
                ft.Container(height=8),
                list_col,
                ft.Container(height=8),
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )

    body = ft.Container(
        expand=True,
        bgcolor=BG,
        content=ft.Stack([gradient_bg, content], expand=True),
    )

    view = ft.View(
        route="/help",
        bgcolor=BG,
        controls=[AppHeader(page, active_route="help"), body],
    )

    try:
        page.invoke_later(_fetch_and_render)
    except Exception:
        _fetch_and_render()

    return view
