# pages/splash_view.py
import flet as ft
import asyncio
from theme import BG, INK

# Enlace directo del logo (termina en .png/.jpg)
LOGO_URL = "https://i.postimg.cc/ryBnj3pm/logo.png"

def SplashView(page: ft.Page):
    """
    Splash fullscreen: logo grande centrado (X/Y), parpadeo suave y responsivo.
    """

    # ---------- Controles ----------
    logo_img = ft.Image(
        src=LOGO_URL,
        width=220,
        height=220,
        fit=ft.ImageFit.CONTAIN,
        opacity=1.0,
        error_content=ft.Container(
            width=220,
            height=220,
            bgcolor="#EDE7FF",
            border_radius=110,
            alignment=ft.alignment.center,
            content=ft.Text("M+", weight=ft.FontWeight.W_700, size=60, color="#5A00D0"),
        ),
    )

    title = ft.Text("Mindful+", size=30, weight=ft.FontWeight.W_700, color=INK)

    # Columna centrada dentro de un contenedor expandido para asegurar centrado absoluto
    center_column = ft.Column(
        [logo_img, title],
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,  # centra verticalmente la columna
        expand=True,                             # ocupa todo el alto para poder centrar
    )

    root = ft.Container(
        bgcolor=BG,
        alignment=ft.alignment.center,  # por si acaso, doble seguridad de centrado
        expand=True,
        content=center_column,
    )

    # ---------- Responsivo (logo grande) ----------
    def adjust_size():
        w = page.width or 800
        h = page.height or 600
        base = min(w, h)
        # Más grande: 32% del lado menor, limitado entre 160 y 420 px
        size = int(max(160, min(420, base * 0.32)))
        logo_img.width = logo_img.height = size

        # Título también escala sutilmente
        title.size = int(max(22, min(40, base * 0.045)))
        page.update()

    adjust_size()

    prev_on_resized = getattr(page, "on_resized", None)

    def _on_resized(e: ft.ControlEvent):
        adjust_size()
        if callable(prev_on_resized):
            try:
                prev_on_resized(e)
            except Exception:
                pass

    page.on_resized = _on_resized

    # ---------- Parpadeo suave ----------
    stop_blink = {"v": False}

    async def blink():
        try:
            while not stop_blink["v"]:
                logo_img.opacity = 0.6
                page.update()
                await asyncio.sleep(0.42)
                logo_img.opacity = 1.0
                page.update()
                await asyncio.sleep(0.42)
        except Exception:
            pass

    # ---------- Decidir ruta destino ----------
    stored_user = None
    try:
        stored_user = page.client_storage.get("user")
    except Exception:
        pass
    session_user = page.session.get("user")
    target_route = "/home" if (session_user or stored_user) else "/"

    async def boot():
        task_blink = asyncio.create_task(blink())
        await asyncio.sleep(1.1)
        stop_blink["v"] = True
        try:
            await task_blink
        except Exception:
            pass
        page.go(target_route)

    try:
        page.run_task(boot)
    except Exception:
        import threading, asyncio as aio
        threading.Thread(target=lambda: aio.run(boot()), daemon=True).start()

    return ft.View(route="/splash", controls=[root], bgcolor=BG)
