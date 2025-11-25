# pages/pro_edit_profile_page.py
import json
import os
import re
import threading
import time
import uuid
import requests
import flet as ft
from typing import Dict, List, Any

from components.app_header import AppHeader
from theme import BG, INK, MUTED, rounded_card, primary_button, ghost_button
from services.firebase_service import FirebaseService

UPLOADER_URL = "https://mindful-imagenes.onrender.com"  # tu microservicio FastAPI

LEVELS = ["Licenciatura", "Maestría", "Ingeniería", "Doctorado"]

FALLBACK_ESTADOS = {
    "Aguascalientes": ["Aguascalientes", "Jesús María"],
    "Baja California": ["Tijuana", "Mexicali"],
    "Ciudad de México": ["Álvaro Obregón", "Benito Juárez", "Coyoacán", "Iztapalapa"],
}

def load_estados_mx() -> Dict[str, List[str]]:
    try:
        # buscar en raíz del proyecto
        root = os.path.dirname(os.path.abspath(__file__))
        for up in range(4):
            candidate = os.path.join(root, *[".."] * up, "estados.json")
            if os.path.exists(candidate):
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Normaliza: claves title-case, municipios lista de str
                    norm = {}
                    for k, v in data.items():
                        try:
                            norm[str(k)] = [str(x) for x in v]
                        except Exception:
                            pass
                    return norm or FALLBACK_ESTADOS
    except Exception:
        pass
    return FALLBACK_ESTADOS


def ProEditProfileView(page: ft.Page):
    sess_user = page.session.get("user")
    if not sess_user or not sess_user.get("uid"):
        return ft.View(route="/pro/edit", controls=[ft.Text("Inicia sesión para continuar")], bgcolor=BG)

    uid = sess_user["uid"]
    fb = FirebaseService()

    estados_map = load_estados_mx()
    estados_list = sorted(list(estados_map.keys()))

    # Cargar perfil actual
    profile = fb.get_user_profile(uid) or {}
    pro = (profile.get("professional") or {})

    photo_url = (pro.get("photoUrl") or "").strip()
    full_name = (pro.get("fullName") or "").strip()
    specialty = (pro.get("specialty") or "").strip()
    cedula = (pro.get("cedula") or "").strip()
    phone = (pro.get("phone") or "").strip()
    purpose = (pro.get("purpose") or "").strip()
    level = (pro.get("level") or "").strip()
    state = (pro.get("state") or "").strip()
    municipality = (pro.get("municipality") or "").strip()

    # -------- Controles --------
    title = ft.Text("Editar perfil profesional", size=20, weight=ft.FontWeight.W_700, color=INK)
    subtitle = ft.Text("Actualiza tu foto, datos y ubicación.", size=12, color=MUTED)

    # Foto + botón
    img = ft.Image(src=photo_url or None, width=120, height=120, fit=ft.ImageFit.COVER, border_radius=80, visible=bool(photo_url))
    btn_upload = ft.TextButton("Subir / Cambiar foto", icon=ft.Icons.CLOUD_UPLOAD, on_click=lambda e: open_web_uploader())

    # Campos
    f_full_name = ft.TextField(label="Nombre completo", value=full_name, border_radius=12)
    f_specialty = ft.TextField(label="Especialidad", value=specialty, border_radius=12)
    f_cedula = ft.TextField(label="Cédula (México: 5–10 dígitos)", value=cedula, border_radius=12)
    f_phone = ft.TextField(label="Celular (10 dígitos)", value=phone, keyboard_type=ft.KeyboardType.PHONE, border_radius=12)
    f_purpose = ft.TextField(label="Propósito", value=purpose, border_radius=12, multiline=True, max_lines=3)

    f_level = ft.Dropdown(
        label="Nivel",
        options=[ft.dropdown.Option(x) for x in LEVELS],
        value=level or None,
        border_radius=12,
    )

    f_state = ft.Dropdown(
        label="Estado",
        options=[ft.dropdown.Option(x) for x in estados_list],
        value=(state if state in estados_map else None),
        border_radius=12,
        on_change=lambda e: on_state_change(),
    )

    def municipio_options_for(selected_state: str) -> List[ft.dropdown.Option]:
        if not selected_state or selected_state not in estados_map:
            return []
        return [ft.dropdown.Option(x) for x in estados_map[selected_state]]

    f_municipio = ft.Dropdown(
        label="Municipio",
        options=municipio_options_for(state),
        value=(municipality if municipality and state in estados_map and municipality in estados_map[state] else None),
        border_radius=12,
    )

    def on_state_change():
        sel = f_state.value
        f_municipio.options = municipio_options_for(sel)
        # reset value if not valid
        if f_municipio.value not in [opt.key for opt in f_municipio.options]:
            f_municipio.value = None
        page.update()

    # Errores mínimos
    err = ft.Text("", size=11, color="#E5484D", visible=False)

    # Guardar
    def save_changes(_):
        # Validaciones simples
        err.visible = False; err.value = ""
        nm = (f_full_name.value or "").strip()
        sp = (f_specialty.value or "").strip()
        cd = (f_cedula.value or "").strip()
        ph = (f_phone.value or "").strip()
        pu = (f_purpose.value or "").strip()
        lv = f_level.value or ""
        st = f_state.value or ""
        mn = f_municipio.value or ""
        ph_ok = re.fullmatch(r"\d{10}", ph or "")
        cd_ok = re.fullmatch(r"\d{5,10}", cd or "")

        if not nm or not sp:
            err.value = "Nombre completo y especialidad son obligatorios."
            err.visible = True; page.update(); return
        if not cd_ok:
            err.value = "La cédula debe ser 5–10 dígitos."
            err.visible = True; page.update(); return
        if not ph_ok:
            err.value = "El celular debe tener 10 dígitos."
            err.visible = True; page.update(); return
        if not (st and mn):
            err.value = "Selecciona estado y municipio."
            err.visible = True; page.update(); return

        fb.update_professional_profile(
            uid,
            {
                "fullName": nm,
                "specialty": sp,
                "cedula": cd,
                "phone": ph,
                "purpose": pu,
                "level": lv,
                "state": st,
                "municipality": mn,
            },
        )
        page.snack_bar = ft.SnackBar(ft.Text("Perfil actualizado ✅"))
        page.snack_bar.open = True
        page.update()
        page.go("/pro")

    actions = ft.Row(
        [
            primary_button("Guardar cambios", save_changes),
            ghost_button("Cancelar", lambda e: e.page.go("/pro")),
        ],
        alignment=ft.MainAxisAlignment.START,
        spacing=12,
    )

    card = rounded_card(
        ft.Column(
            [
                ft.Row([title], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                subtitle,
                ft.Container(height=8),
                ft.Row(
                    [img, btn_upload],
                    spacing=20,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=10),
                f_full_name,
                f_specialty,
                f_cedula,
                f_phone,
                f_level,
                f_state,
                f_municipio,
                f_purpose,
                err,
                ft.Container(height=10),
                actions,
            ],
            spacing=10,
        ),
        18,
    )

    body = ft.Container(
        content=ft.Column([card], scroll=ft.ScrollMode.AUTO),
        padding=20,
        bgcolor=BG,
        expand=True,
    )

    # -------- Uploader con microservicio (mismo patrón de tu Register) --------
    _polling = {"on": False}
    _session_id = {"val": None}

    def open_web_uploader():
        s = uuid.uuid4().hex
        _session_id["val"] = s
        url = f"{UPLOADER_URL}/uploader?session={s}&folder=mindful/profesionistas"
        page.launch_url(url)
        if not _polling["on"]:
            _polling["on"] = True
            threading.Thread(target=poll_loop, daemon=True).start()
        page.snack_bar = ft.SnackBar(ft.Text("Sube tu foto y regresa. Estoy esperando la URL…"))
        page.snack_bar.open = True
        page.update()

    def poll_loop():
        while _polling["on"] and _session_id["val"]:
            try:
                r = requests.get(f"{UPLOADER_URL}/poll", params={"session": _session_id["val"]}, timeout=4)
                j = r.json()
                url = j.get("url")
                if url:
                    def finish():
                        nonlocal photo_url
                        photo_url = url
                        img.src = url
                        img.visible = True
                        # guardo inmediato la foto en Firestore
                        fb.update_user_photo(uid, url)
                        page.update()
                        page.snack_bar = ft.SnackBar(ft.Text("Foto actualizada ✅"))
                        page.snack_bar.open = True
                        page.update()
                    try:
                        page.invoke_later(finish)
                    except Exception:
                        finish()
                    _polling["on"] = False
                    _session_id["val"] = None
                    break
            except Exception:
                pass
            time.sleep(1.0)

    return ft.View(
        route="/pro/edit",
        bgcolor=BG,
        controls=[AppHeader(page, active_route="home"), body],
    )
