# pages/login_page.py
import re
import json
import flet as ft
from dataclasses import asdict
from urllib.parse import urlparse, parse_qs

from services.firebase_service import FirebaseService
from models.user_model import User
from theme import BG, INK, MUTED, rounded_card, primary_button, ghost_button
from firebase_admin import auth as admin_auth

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
LOGO_URL = "https://i.postimg.cc/ryBnj3pm/logo.png"


class LoginView(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/login", bgcolor=BG, padding=0)
        self.scroll = ft.ScrollMode.AUTO

        self.fb = FirebaseService()
        self._busy = False

        # ----- ¿Forzar flujo profesional? (/login?role=pro)
        self.force_pro = False
        try:
            if page and page.route:
                q = parse_qs(urlparse(page.route).query or "")
                self.force_pro = (q.get("role", [""])[0].lower() == "pro")
                print(f"[Login] force_pro={self.force_pro} (route={page.route})")
        except Exception as ex:
            print(f"[Login] No pude parsear querystring: {ex}")

        # ---------- helpers de estilo ----------
        def field_wrap(child: ft.Control):
            return ft.Container(
                content=child,
                padding=12,
                border_radius=14,
                bgcolor="#F1ECFF",
                shadow=ft.BoxShadow(
                    blur_radius=12, spread_radius=1,
                    color=ft.Colors.with_opacity(0.06, "black"),
                ),
            )

        def focus_on(c: ft.Container):
            c.bgcolor = "#EAE2FF"
            c.shadow = ft.BoxShadow(
                blur_radius=20, spread_radius=2,
                color=ft.Colors.with_opacity(0.12, "#6C54D8"),
            )

        def focus_off(c: ft.Container):
            c.bgcolor = "#F1ECFF"
            c.shadow = ft.BoxShadow(
                blur_radius=12, spread_radius=1,
                color=ft.Colors.with_opacity(0.06, "black"),
            )

        # ---------- campos ----------
        self.email = ft.TextField(
            label="Correo electrónico",
            keyboard_type=ft.KeyboardType.EMAIL,
            border_radius=12,
            border_color="transparent",
            hint_text="tucorreo@ejemplo.com",
            on_submit=self._submit_from_field,
        )
        self.password = ft.TextField(
            label="Contraseña",
            password=True,
            can_reveal_password=True,
            border_radius=12,
            border_color="transparent",
            hint_text="••••••••",
            on_submit=self._submit_from_field,
        )

        self.email_wrap = field_wrap(self.email)
        self.pass_wrap = field_wrap(self.password)

        self.email.on_focus = lambda e: (focus_on(self.email_wrap), self.update())
        self.email.on_blur = lambda e: (focus_off(self.email_wrap), self.update())
        self.password.on_focus = lambda e: (focus_on(self.pass_wrap), self.update())
        self.password.on_blur = lambda e: (focus_off(self.pass_wrap), self.update())

        # errores
        self.email_err = ft.Text("", size=11, color="#E5484D", visible=False)
        self.pass_err = ft.Text("", size=11, color="#E5484D", visible=False)

        # loader
        self.spinner = ft.ProgressRing(width=18, height=18, visible=False)

        # ---------- encabezado ----------
        self.logo = ft.Image(src=LOGO_URL, width=64, height=64, fit=ft.ImageFit.CONTAIN)
        brand = ft.Text("Mindful+", size=16, weight=ft.FontWeight.W_600, color=INK)

        self.title = ft.Text("Bienvenido de vuelta 💜", size=22, weight=ft.FontWeight.W_700, color=INK)
        subtitle = ft.Text(
            "Tu espacio para sentirte mejor. Inicia sesión para continuar.",
            size=12, color=MUTED, text_align=ft.TextAlign.CENTER,
        )

        # ---------- acciones ----------
        actions = ft.Row(
            [primary_button("Entrar", self.on_login), self.spinner],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
        )
        signup = ghost_button("¿No tienes cuenta? Regístrate", lambda e: e.page.go("/register"))

        # ---------- card ----------
        card_body = ft.Column(
            [
                ft.Container(content=ft.Row([self.logo], alignment=ft.MainAxisAlignment.CENTER)),
                ft.Container(content=brand, alignment=ft.alignment.center),
                ft.Container(height=6),
                self.title,
                subtitle,
                ft.Container(height=16),
                self.email_wrap, self.email_err,
                self.pass_wrap, self.pass_err,
                ft.Container(height=10),
                actions,
                ft.Container(height=6),
                signup,
                ft.Container(height=8),
                ft.Text(
                    "Recuerda: un pequeño paso hoy también cuenta. 🌱",
                    size=11, color=MUTED, text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            tight=True,
        )
        card = rounded_card(card_body, 22)

        # ---------- background decor ----------
        gradient_bg = ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=["#F7F5FF", "#F4F2FF", "#F7F5FF"],
            ),
        )

        # Burbujas: se reposicionan por pantalla en adjust_sizes()
        self.bubble_1 = ft.Container(border_radius=9999,
                         bgcolor=ft.Colors.with_opacity(0.18, "#C5B6FF"))
        self.bubble_2 = ft.Container(border_radius=9999,
                         bgcolor=ft.Colors.with_opacity(0.14, "#B2A4FF"))
        self.bubble_3 = ft.Container(border_radius=9999,
                         bgcolor=ft.Colors.with_opacity(0.12, "#D8CCFF"))

        # contenedor central con tamaño dinámico
        # Usamos expand=False por defecto y ajustamos el ancho en adjust_sizes()
        self.card_container = ft.Container(width=480, content=card, expand=False)

        # Guardamos el container central en self para poder ajustar padding desde adjust_sizes()
        self.center_scroll = ft.Container(
            expand=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=28),
            content=ft.Column(
                [
                    ft.Row([self.card_container], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Container(height=28),
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

        # ¡No recortar! así los círculos pueden “abrazar” los bordes
        root = ft.Stack(
            controls=[gradient_bg, self.bubble_1, self.bubble_2, self.bubble_3, self.center_scroll],
            expand=True,
            clip_behavior=ft.ClipBehavior.NONE,
        )
        self.controls = [root]

        # ---------- responsividad: breakpoints + posición de burbujas ----------
        def adjust_sizes():
            w = page.width or 1024
            h = page.height or 768

            # Si la pantalla es muy angosta, usar casi todo el ancho disponible
            if w < 480:
                target = int(w * 0.96)
                # mantener margen a los lados ajustando padding
                self.center_scroll.padding = ft.padding.symmetric(horizontal=8, vertical=20)
            else:
                # ancho del card: 32–38% del viewport en desktop, con límites
                if w >= 1400:
                    target = int(w * 0.34)
                elif w >= 1100:
                    target = int(w * 0.36)
                elif w >= 860:
                    target = int(w * 0.38)
                else:
                    target = int(w * 0.70)
                # limitar dentro de un rango razonable
                target = max(320, min(target, 640))
                self.center_scroll.padding = ft.padding.symmetric(horizontal=16, vertical=28)

            # Asignar ancho y asegurar que no expand a menos que queramos
            self.card_container.width = target
            self.card_container.expand = False

            # tamaño de logo / título según tamaño
            if w >= 1200:
                self.logo.width = self.logo.height = 72
                self.title.size = 24
            elif w >= 860:
                self.logo.width = self.logo.height = 68
                self.title.size = 23
            elif w >= 480:
                self.logo.width = self.logo.height = 64
                self.title.size = 22
            else:
                # móvil pequeño: reducir aún más
                self.logo.width = self.logo.height = 56
                self.title.size = 20

            # ----- Burbujas dependientes de viewport -----
            # Ocultar burbujas en pantallas muy pequeñas para evitar solapamientos
            show_bubbles = (w >= 420 and h >= 380)
            self.bubble_1.visible = show_bubbles
            self.bubble_2.visible = show_bubbles
            self.bubble_3.visible = show_bubbles

            if show_bubbles:
                # Top-left grande
                b1 = int(min(w, h) * 0.38)
                self.bubble_1.width = self.bubble_1.height = b1
                self.bubble_1.left = -int(b1 * 0.25)
                self.bubble_1.top = -int(b1 * 0.25)

                # Top-right media
                b2 = int(min(w, h) * 0.22)
                self.bubble_2.width = self.bubble_2.height = b2
                self.bubble_2.right = int(w * 0.05)
                self.bubble_2.top = int(h * 0.12)

                # Bottom-left muy grande
                b3 = int(min(w, h) * 0.48)
                self.bubble_3.width = self.bubble_3.height = b3
                self.bubble_3.left = int(w * 0.06)
                self.bubble_3.bottom = -int(b3 * 0.18)

        # llamada inicial y en cambios de tamaño
        adjust_sizes()
        page.on_resized = lambda e: (adjust_sizes(), page.update())

    # ---------- helpers ----------
    def _toast(self, page: ft.Page, msg: str, error: bool = False):
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="#E5484D" if error else "#2ECC71")
        page.snack_bar.open = True
        page.update()

    def _set_busy(self, busy: bool, page: ft.Page):
        self._busy = busy
        self.spinner.visible = busy
        self.email.disabled = busy
        self.password.disabled = busy
        page.update()

    def _submit_from_field(self, e: ft.ControlEvent):
        if not self._busy:
            self.on_login(e)

    # ---------- validación ----------
    def _validate(self) -> bool:
        ok = True
        self.email_err.visible = False
        self.pass_err.visible = False
        self.email_err.value = ""
        self.pass_err.value = ""

        email = (self.email.value or "").strip()
        password = (self.password.value or "")

        if not email:
            self.email_err.value = "Ingresa tu correo."
            self.email_err.visible = True
            ok = False
        elif not EMAIL_RE.match(email):
            self.email_err.value = "Formato de correo no válido."
            self.email_err.visible = True
            ok = False

        if not password:
            self.pass_err.value = "Ingresa tu contraseña."
            self.pass_err.visible = True
            ok = False

        self.update()
        return ok

    # ---------- código de error ----------
    def _extract_firebase_error_code(self, ex: Exception) -> str:
        if ex.args and isinstance(ex.args[0], str):
            s = ex.args[0].strip()
            if s:
                return s.upper()
        return "UNKNOWN"

    # ---------- login ----------
    def on_login(self, e: ft.ControlEvent):
        page = e.page
        if self._busy:
            return
        if not self._validate():
            return

        email = (self.email.value or "").strip()
        password = self.password.value or ""

        self._set_busy(True, page)

        try:
            print(f"[Login] Autenticando email={email} ...")
            id_token, uid = self.fb.sign_in(email, password)
            print(f"[Login] OK uid={uid}")

            profile = self.fb.get_user_profile(uid) or {}
            print(f"[Login] Perfil leído: {profile}")

            # Decide destino: /pro si es profesional o si viene forzado por querystring
            is_pro = (profile.get("type") == "profesional") or bool(profile.get("professional"))
            dest = "/pro" if (is_pro or self.force_pro) else "/home"
            print(f"[Login] is_pro={is_pro}, force_pro={self.force_pro}, dest={dest}")

            user = User(uid=uid, email=email, username=profile.get("username"), id_token=id_token)
            user_dict = asdict(user)

            # Guardar en la sesión actual
            page.session.set("user", user_dict)
            # Guardar también en el storage del cliente (sobrevive recargas / offline)
            page.client_storage.set("user", json.dumps(user_dict))

            self._toast(page, f"Bienvenid@, {user.username or user.email} 🌿")
            page.go(dest)


        except Exception as ex:
            code = self._extract_firebase_error_code(ex)
            print(f"[Login] Error sign_in code={code} raw={ex}")

            self.email_err.visible = False
            self.pass_err.visible = False
            self.email_err.value = ""
            self.pass_err.value = ""

            if code in ("INVALID_LOGIN_CREDENTIALS", "INVALID_PASSWORD"):
                # Distinguir: correo existe o no
                try:
                    admin_auth.get_user_by_email(email)
                    self.pass_err.value = "Contraseña incorrecta."
                    self.pass_err.visible = True
                    self._toast(page, "Contraseña incorrecta.", error=True)
                    print("[Login] Contraseña incorrecta para email existente.")
                except admin_auth.UserNotFoundError:
                    self.email_err.value = "Este correo no está registrado."
                    self.email_err.visible = True
                    self._toast(page, "Correo no encontrado.", error=True)
                    print("[Login] Correo no registrado.")
                except Exception as ex2:
                    self._toast(page, "Credenciales inválidas.", error=True)
                    print(f"[Login] Lookup admin_auth falló: {ex2}")

            elif code == "EMAIL_NOT_FOUND":
                self.email_err.value = "Este correo no está registrado."
                self.email_err.visible = True
                self._toast(page, "Correo no encontrado.", error=True)
                print("[Login] EMAIL_NOT_FOUND.")

            elif code == "USER_DISABLED":
                self.email_err.value = "Tu cuenta está deshabilitada."
                self.email_err.visible = True
                self._toast(page, "Cuenta deshabilitada.", error=True)
                print("[Login] USER_DISABLED.")

            elif code == "TOO_MANY_ATTEMPTS_TRY_LATER":
                self.pass_err.value = "Demasiados intentos. Inténtalo más tarde."
                self.pass_err.visible = True
                self._toast(page, "Demasiados intentos. Inténtalo más tarde.", error=True)
                print("[Login] TOO_MANY_ATTEMPTS_TRY_LATER.")

            elif code == "INVALID_EMAIL":
                self.email_err.value = "Correo inválido."
                self.email_err.visible = True
                self._toast(page, "Correo inválido.", error=True)
                print("[Login] INVALID_EMAIL.")

            else:
                self._toast(page, "No fue posible iniciar sesión. Revisa tus datos.", error=True)
                print("[Login] Error desconocido.")

            self.update()

        finally:
            self._set_busy(False, page)
