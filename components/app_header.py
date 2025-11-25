import os
import uuid
import time
import threading
import requests
import flet as ft
from theme import INK, BG

UPLOADER_URL = os.getenv("UPLOADER_URL", "https://mindful-imagenes.onrender.com")


def AppHeader(page: ft.Page, active_route: str, force_mobile: bool = False):
    """
    Mobile-first header suitable for mobile and web.

    - Top header: hamburger (left), title (center), actions (right).
    - Desktop: shows nav icons grouped at the right plus notifications.
    - Mobile: shows a bottom nav bar with main actions; hamburger menu
      contains quick links (Inicio, Ayuda, Estadísticas, Cerrar sesión).
    The header rebuilds its controls on `page.on_resized` so layout adapts.
    """

    # ---------- helpers: session / navigation ----------
    def ensure_session() -> bool:
        user = page.session.get("user")
        if user:
            return True
        stored = page.client_storage.get("user")
        if stored:
            page.session.set("user", stored)
            return True
        return False

    def go_to(route: str):
        if not ensure_session() and route not in ("/", "/login", "/register", "/welcome"):
            page.snack_bar = ft.SnackBar(ft.Text("Inicia sesión primero 🪄"), bgcolor="#E5484D")
            page.snack_bar.open = True
            page.update()
            page.go("/login")
            return
        page.go(route)

    def toast(msg: str):
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    # ---------- push notifications button ----------
    def _push_button():
        if not ensure_session():
            return ft.Container()

        def start_push(_):
            try:
                sess = page.session.get("user") or {}
                uid = sess.get("uid", "")
                role = sess.get("role") or ("profesional" if page.route.startswith("/pro") else "normal")
                if not uid:
                    toast("No encuentro tu sesión. Vuelve a iniciar.")
                    page.go("/login")
                    return

                session_id = uuid.uuid4().hex
                page.launch_url(f"{UPLOADER_URL}/notify?session={session_id}&uid={uid}&role={role}")
                toast("Abre la pestaña y acepta notificaciones. Estoy esperando confirmación…")

                def poll():
                    for _ in range(60):
                        try:
                            r = requests.get(f"{UPLOADER_URL}/notify/poll", params={"session": session_id}, timeout=5)
                            if r.ok and r.json().get("ready"):
                                def ok():
                                    toast("Notificaciones activadas ✅")
                                try:
                                    page.invoke_later(ok)
                                except Exception:
                                    ok()
                                return
                        except Exception:
                            pass
                        time.sleep(1)

                    def ko():
                        toast("No se confirmó la activación (tiempo agotado).")
                    try:
                        page.invoke_later(ko)
                    except Exception:
                        ko()

                threading.Thread(target=poll, daemon=True).start()
            except Exception as ex:
                toast(f"No pude iniciar la activación: {ex}")

        return ft.IconButton(icon=ft.Icons.NOTIFICATIONS_ACTIVE, icon_color="#5A00D0", tooltip="Activar notificaciones", on_click=start_push)

    # ---------- nav items ----------
    nav_items = [
        ("home", ft.Icons.HOME_OUTLINED, "Inicio", "/home"),
        ("diagnostic", ft.Icons.PSYCHOLOGY_OUTLINED, "Diagnóstico", "/diagnostic"),
        ("notes", ft.Icons.NOTE_ALT_OUTLINED, "Notas", "/notes"),
        ("recommendations", ft.Icons.LIGHTBULB_OUTLINED, "Recomendaciones", "/recommendations"),
        ("tellme", ft.Icons.FORUM_OUTLINED, "Tell Me +", "/tellme"),
        ("help", ft.Icons.SUPPORT_AGENT, "Ayuda profesional", "/help"),
    ]

    # ---------- viewport helper ----------
    def is_small():
        try:
            return bool(force_mobile) or ((page.width or 1024) <= 600)
        except Exception:
            return bool(force_mobile)

    # ---------- build nav row (desktop) ----------
    def build_nav_row():
        buttons = []
        for route, icon, label, path in nav_items:
            buttons.append(
                ft.IconButton(
                    icon=icon,
                    tooltip=label,
                    icon_color=("#5A00D0" if route == active_route else INK),
                    on_click=lambda e, r=path: go_to(r),
                )
            )
        return ft.Row(buttons, spacing=6, alignment=ft.MainAxisAlignment.END, scroll=ft.ScrollMode.AUTO)

    # ---------- menu (hamburger) ----------
    menu_open = {"value": False}

    def close_menu():
        glass = menu_open["value"]
        if isinstance(glass, ft.Control) and glass in page.overlay:
            page.overlay.remove(glass)
        menu_open["value"] = False
        page.update()

    def logout(_):
        page.session.clear()
        page.client_storage.remove("user")
        close_menu()
        page.go("/login")

    def show_menu():
        # Always show full menu inside the hamburger; header keeps only notifications
        menu_open["value"] = True
        menu_list = [
            ("🏠", "Inicio", "/home"),
            ("🧠", "Diagnóstico", "/diagnostic"),
            ("📒", "Notas", "/notes"),
            ("💡", "Recomendaciones", "/recommendations"),
            ("✨", "Tell Me +", "/tellme"),
            ("👩‍⚕️", "Ayuda profesional", "/help"),
            ("📊", "Estadísticas", "/stats"),
            ("🚪", "Cerrar sesión", "logout"),
        ]

        chips = ft.Column(
            [
                ft.Container(
                    on_click=(lambda e, r=p: (logout(e) if r == "logout" else (close_menu(), go_to(r)))),
                    content=ft.Row([ft.Text(emoji, size=16), ft.Text(lbl, size=13, color=INK)], spacing=10),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor="#F6F1FF",
                    border_radius=12,
                )
                for emoji, lbl, p in menu_list
            ],
            spacing=6,
        )

        # Position the menu differently on small screens: show as a bottom sheet
        if is_small():
            # Use the exact same `chips` column (no modification) but show it
            # as a bottom sheet on small screens. Keep content identical.
            w = page.width or 360
            panel = ft.Container(
                content=chips,
                alignment=ft.alignment.bottom_center,
                padding=ft.padding.only(bottom=12, left=12, right=12, top=12),
                bgcolor="#FFFFFF",
                border_radius=ft.border_radius.only(top_left=16, top_right=16),
                width=(w - 24) if w and w > 0 else None,
            )
            glass = ft.Container(bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.BLACK), content=panel, on_click=lambda _: close_menu())
        else:
            panel = ft.Container(alignment=ft.alignment.top_left, padding=ft.padding.only(top=58, left=12), content=chips)
            glass = ft.Container(bgcolor=ft.Colors.with_opacity(0.01, ft.Colors.BLACK), content=panel, on_click=lambda _: close_menu())
        page.overlay.append(glass)
        page.update()
        menu_open["value"] = glass

    def toggle_menu(_=None):
        if not menu_open["value"]:
            show_menu()
        else:
            close_menu()

    # ---------- header / bottom nav builders ----------
    def make_header():
        w = page.width if getattr(page, 'width', None) is not None else 1024
        title_size = 18 if w >= 760 else 16

        menu_btn = ft.IconButton(icon=ft.Icons.MENU, on_click=toggle_menu)
        title = ft.Text("Mindful+", size=title_size, weight=ft.FontWeight.W_700, color=INK)

        # For the requested mobile-first layout, keep the top header minimal:
        # only the notifications button is visible on the right; all other
        # navigation actions live inside the hamburger menu.
        right = ft.Row([_push_button()], alignment=ft.MainAxisAlignment.END, spacing=8)

        return ft.Container(
            bgcolor="#EDE7FF",
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            content=ft.Row([
                menu_btn,
                ft.Container(content=title, alignment=ft.alignment.center),
                ft.Container(expand=True),
                right,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.15, "black")),
        )

    def make_bottom_nav():
        w = page.width if getattr(page, 'width', None) is not None else 1024
        icon_sz = 20 if w < 480 else 22
        bottom_items = [nav_items[0], nav_items[1], nav_items[2], nav_items[3]]
        items = []
        for route, icon, label, path in bottom_items:
            items.append(
                ft.Container(
                    content=ft.Column([
                        ft.IconButton(icon=icon, icon_size=icon_sz, icon_color=("#5A00D0" if route == active_route else INK), on_click=lambda e, r=path: go_to(r)),
                        ft.Text(label if w >= 360 else "", size=10, color=INK),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(horizontal=6, vertical=4),
                )
            )

        return ft.Container(
            bgcolor="#FFFFFF",
            padding=ft.padding.symmetric(horizontal=6, vertical=6),
            content=ft.Row(items, alignment=ft.MainAxisAlignment.SPACE_AROUND),
            visible=is_small(),
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.06, "black")),
        )

    # build initial
    header_top = make_header()
    bottom_nav = make_bottom_nav()
    wrapper = ft.Column([header_top, bottom_nav], spacing=0)

    prev_on_resized = getattr(page, "on_resized", None)

    def _on_resized(e):
        try:
            if callable(prev_on_resized):
                prev_on_resized(e)
        except Exception:
            pass
        try:
            # rebuild components and replace in wrapper
            new_header = make_header()
            new_bottom = make_bottom_nav()
            wrapper.controls[0] = new_header
            wrapper.controls[1] = new_bottom
            page.update()
        except Exception:
            pass

    page.on_resized = _on_resized

    return wrapper
