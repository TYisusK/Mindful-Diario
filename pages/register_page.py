import re
import uuid
import time
import threading
import requests
import flet as ft

from services.firebase_service import FirebaseService
from theme import BG, INK, MUTED, rounded_card, primary_button, ghost_button

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
LOGO_URL = "https://i.postimg.cc/ryBnj3pm/logo.png"

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

# URL del microservicio (ajústalo si corre en otro host/puerto)
UPLOADER_URL = "https://mindful-imagenes.onrender.com"


class RegisterView(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/register", bgcolor=BG, padding=0)
        self.page = page
        self.scroll = ft.ScrollMode.AUTO

        self.fb = FirebaseService()
        self._busy = False

        # --- rol ---
        self.role = ft.SegmentedButton(
            segments=[
                ft.Segment(value="normal", label=ft.Text("Usuario")),
                ft.Segment(value="profesional", label=ft.Text("Profesionista")),
            ],
            selected={"normal"},
            on_change=lambda e: self._toggle_role(),
        )

        # --- datos básicos ---
        self.username = ft.TextField(label="Nombre de usuario", border_radius=12, hint_text="¿Cómo te llamamos?")
        self.email = ft.TextField(label="Correo electrónico", keyboard_type=ft.KeyboardType.EMAIL, border_radius=12)
        self.password = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, border_radius=12)

        self.u_err = ft.Text("", size=11, color="#E5484D", visible=False)
        self.e_err = ft.Text("", size=11, color="#E5484D", visible=False)
        self.p_err = ft.Text("", size=11, color="#E5484D", visible=False)

        # --- profesional ---
        self.full_name = ft.TextField(label="Nombre completo", border_radius=12)
        self.specialty = ft.Dropdown(
            label="Especialidad",
            options=[ft.dropdown.Option(s) for s in SPECIALTIES],
            border_radius=12,
        )
        self.cedula = ft.TextField(label="Número de cédula (México)", border_radius=12)
        self.phone = ft.TextField(label="Celular (10 dígitos)", keyboard_type=ft.KeyboardType.PHONE, border_radius=12)

        # URL (oculta al usuario; la rellenamos al subir)
        self.photo_url = ft.TextField(label="URL de foto", border_radius=12, visible=False)

        # preview
        self.img = ft.Image(src=None, width=120, height=120, fit=ft.ImageFit.COVER, border_radius=80, visible=False)

        self.pro_err = ft.Text("", size=11, color="#E5484D", visible=False)

        # Botón subir en PWA/WEB -> abre modal embebido con IFrame
        self.btn_web_upload = ft.TextButton("Subir foto (PWA / Web)", on_click=lambda _: self._open_upload_inline())

        # loader
        self.spinner = ft.ProgressRing(width=18, height=18, visible=False)

        # encabezado
        logo = ft.Image(src=LOGO_URL, width=64, height=64, fit=ft.ImageFit.CONTAIN)
        title = ft.Text("Crear una cuenta 🌱", size=22, weight=ft.FontWeight.W_700, color=INK)
        subtitle = ft.Text("Elige tu rol y completa tus datos.", size=12, color=MUTED)

        self.pro_section = ft.Column(
            [
                ft.Text("Datos de profesionista", size=14, weight=ft.FontWeight.W_600, color=INK),
                ft.Row([self.img], alignment=ft.MainAxisAlignment.START),
                self.btn_web_upload,
                self.photo_url,
                self.full_name,
                self.specialty,
                self.cedula,
                self.phone,
                self.pro_err,
            ],
            spacing=8,
            visible=False,
        )

        actions = ft.Row(
            [primary_button("Crear cuenta", self.on_signup), self.spinner],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
        )
        back = ghost_button("¿Ya tienes cuenta? Inicia sesión", lambda e: self.page.go("/login"))

        card_body = ft.Column(
            [
                ft.Row([logo], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=6),
                title,
                subtitle,
                ft.Container(height=4),
                ft.Text("Rol", size=12, color=MUTED),
                self.role,
                ft.Container(height=8),

                ft.Text("Datos básicos", size=14, weight=ft.FontWeight.W_600, color=INK),
                self.username, self.u_err,
                self.email, self.e_err,
                self.password, self.p_err,

                ft.Container(height=8),
                self.pro_section,

                ft.Container(height=12),
                actions,
                ft.Container(height=6),
                back,
                ft.Container(height=8),
                ft.Text(
                    "Si te registras como profesionista, tu información será verificada.",
                    size=11, color=MUTED, text_align=ft.TextAlign.CENTER
                ),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            tight=True,
        )

        self.card_container = ft.Container(width=520, content=rounded_card(card_body, 22))
        self.controls = [
            ft.Stack(
                [
                    ft.Container(
                        expand=True,
                        gradient=ft.LinearGradient(
                            begin=ft.alignment.top_center,
                            end=ft.alignment.bottom_center,
                            colors=["#F7F5FF", "#F4F2FF", "#F7F5FF"],
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        padding=ft.padding.symmetric(horizontal=16, vertical=28),
                        content=ft.Column(
                            [ft.Row([self.card_container], alignment=ft.MainAxisAlignment.CENTER)],
                            scroll=ft.ScrollMode.AUTO,
                        ),
                    ),
                ],
                expand=True,
            )
        ]

        def adjust():
            w = page.width or 1024
            if w >= 1400: target = int(w * 0.36)
            elif w >= 1100: target = int(w * 0.38)
            elif w >= 860: target = int(w * 0.42)
            else: target = int(w * 0.92)
            self.card_container.width = max(380, min(target, 640))
            # si hay modal abierto, también recalcular (opcional)
            if getattr(self, "_uploader_dialog", None) and self._uploader_dialog.open:
                self._resize_modal()

        adjust()
        page.on_resized = lambda e: (adjust(), page.update())

        # estado de polling y modal
        self._polling = False
        self._current_session = None
        self._uploader_dialog: ft.AlertDialog | None = None

    # ---------- helpers ----------
    def _toggle_role(self):
        sel = list(self.role.selected)[0]
        self.pro_section.visible = (sel == "profesional")
        self.update()

    def _toast(self, msg: str, error: bool = False):
        self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="#E5484D" if error else "#2ECC71")
        self.page.snack_bar.open = True
        self.page.update()

    def _set_busy(self, busy: bool):
        self._busy = busy
        self.spinner.visible = busy
        for c in (self.username, self.email, self.password, self.full_name, self.specialty, self.cedula, self.phone):
            c.disabled = busy
        self.update()

    # ---------- validaciones ----------
    def _validate(self) -> bool:
        ok = True
        for t in (self.u_err, self.e_err, self.p_err, self.pro_err):
            t.visible = False; t.value = ""

        u = (self.username.value or "").strip()
        e = (self.email.value or "").strip()
        p = self.password.value or ""
        is_pro = list(self.role.selected)[0] == "profesional"

        if len(u) < 2:
            self.u_err.value = "Ingresa un nombre de usuario válido."
            self.u_err.visible = True; ok = False
        if not EMAIL_RE.match(e):
            self.e_err.value = "Correo inválido."
            self.e_err.visible = True; ok = False
        if len(p) < 6:
            self.p_err.value = "Contraseña (mínimo 6 caracteres)."
            self.p_err.visible = True; ok = False

        if is_pro:
            fn = (self.full_name.value or "").strip()
            sp = self.specialty.value or ""
            cd = (self.cedula.value or "").strip()
            ph = (self.phone.value or "").strip()
            if not (fn and sp and cd and ph):
                self.pro_err.value = "Completa todos los datos del perfil profesional."
                self.pro_err.visible = True; ok = False
            if not re.fullmatch(r"\d{5,10}", cd or ""):
                self.pro_err.value = "Cédula inválida (5 a 10 dígitos)."
                self.pro_err.visible = True; ok = False
            if not re.fullmatch(r"\d{10}", ph or ""):
                self.pro_err.value = "El celular debe tener 10 dígitos."
                self.pro_err.visible = True; ok = False

        self.update()
        return ok

    # ---------- Modal con IFrame (PWA/WEB embebido) ----------
    def _open_upload_inline(self):
        session_id = uuid.uuid4().hex
        self._current_session = session_id

        iframe_url = f"{UPLOADER_URL}/uploader?session={session_id}"

        # Intentar IFrame (0.28+). Si no existe, fallback a pestaña externa.
        try:
            iframe = ft.IFrame(src=iframe_url, width=800, height=520)
        except AttributeError:
            self.page.launch_url(iframe_url)
            self._toast("Sube tu foto en la pestaña y vuelve. Estoy esperando la URL…")
            if not self._polling:
                self._polling = True
                threading.Thread(target=self._poll_loop, daemon=True).start()
            return

        def _close_dialog(_=None):
            if self._uploader_dialog and self._uploader_dialog.open:
                self._uploader_dialog.open = False
                self.page.update()

        header = ft.Row(
            controls=[
                ft.Text("Subir foto", size=16, weight=ft.FontWeight.W_600),
                ft.IconButton(ft.Icons.CLOSE, on_click=_close_dialog, tooltip="Cerrar")
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        self._iframe_control = iframe  # guardamos referencia para futuros resize

        modal_body = ft.Container(
            content=ft.Column(
                controls=[
                    header,
                    ft.Container(content=self._iframe_control, expand=True, height=520, border_radius=12, bgcolor="#FFFFFF"),
                    ft.Text("Tu imagen se vinculará automáticamente cuando finalice la subida.",
                            size=12, color=MUTED),
                ],
                spacing=10,
                expand=True
            ),
            width=min(self.page.width or 900, 900),
            height=min(self.page.height or 650, 650),
            bgcolor="#F7F5FF",
            border_radius=16,
            padding=14,
        )

        self._uploader_dialog = ft.AlertDialog(modal=True, content=modal_body)
        self.page.dialog = self._uploader_dialog
        self._uploader_dialog.open = True
        self.page.update()

        self._toast("Sube tu foto en la ventana y espera un momento…")
        if not self._polling:
            self._polling = True
            threading.Thread(target=self._poll_loop, daemon=True).start()

    def _resize_modal(self):
        # Llama esto en on_resized para adaptar modal/iframe
        if not self._uploader_dialog:
            return
        # ajusta envolvente
        wrapper: ft.Container = self._uploader_dialog.content  # type: ignore
        wrapper.width = min(self.page.width or 900, 900)
        wrapper.height = min(self.page.height or 650, 650)
        # ajusta iframe alto visible
        # (si quieres, puedes hacer que el alto sea wrapper.height - cabecera - paddings)
        # por simplicidad, mantenemos 520px para contenidos < 650px de alto
        self.page.update()

    # ---------- Polling al microservicio ----------
    def _poll_loop(self):
        while self._polling and self._current_session:
            try:
                r = requests.get(f"{UPLOADER_URL}/poll", params={"session": self._current_session}, timeout=4)
                j = r.json()
                url = j.get("url")
                if url:
                    def finish():
                        self.photo_url.value = url
                        self.img.src = url
                        self.img.visible = True
                        self.update()
                        if self._uploader_dialog and self._uploader_dialog.open:
                            self._uploader_dialog.open = False
                            self.page.update()
                        self._toast("Imagen vinculada ✅")
                    try:
                        self.page.invoke_later(finish)
                    except Exception:
                        finish()
                    self._polling = False
                    self._current_session = None
                    break
            except Exception:
                pass
            time.sleep(1.0)

    # ---------- Registro ----------
    def _extract_code(self, ex: Exception) -> str:
        if ex.args and isinstance(ex.args[0], str):
            return ex.args[0].strip().upper()
        return "UNKNOWN"

    def on_signup(self, _):
        if self._busy:
            return
        if not self._validate():
            return

        u = (self.username.value or "").strip()
        e = (self.email.value or "").strip()
        p = self.password.value or ""
        is_pro = list(self.role.selected)[0] == "profesional"

        self._set_busy(True)
        try:
            id_token, uid = self.fb.sign_up(e, p)

            if is_pro:
                self.fb.create_professional_profile(
                    uid, e, u,
                    (self.full_name.value or "").strip(),
                    self.specialty.value or "",
                    (self.cedula.value or "").strip(),
                    (self.phone.value or "").strip(),
                    photo_url=((self.photo_url.value or "").strip() or None),
                )
                self._toast("Cuenta de profesionista creada ✅")
                self.page.go("/login?role=pro")
            else:
                self.fb.create_user_profile(uid, e, u)
                self._toast("Cuenta creada ✅")
                self.page.go("/login")

        except Exception as ex:
            code = self._extract_code(ex)
            if code == "EMAIL_EXISTS":
                self.e_err.value = "Este correo ya está registrado."
                self.e_err.visible = True
                self._toast("Este correo ya está registrado.", error=True)
            elif code in ("INVALID_EMAIL",):
                self.e_err.value = "Correo inválido."
                self.e_err.visible = True
                self._toast("Correo inválido.", error=True)
            elif code in ("WEAK_PASSWORD", "WEAK_PASSWORD : PASSWORD_SHORT", "PASSWORD_SHORT"):
                self.p_err.value = "La contraseña es demasiado corta."
                self.p_err.visible = True
                self._toast("Contraseña demasiado corta.", error=True)
            else:
                self._toast("No se pudo crear la cuenta.", error=True)
            self.update()
        finally:
            self._set_busy(False)
