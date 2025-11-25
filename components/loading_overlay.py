# components/loading_overlay.py
import flet as ft

_OVERLAY_KEY = "__mindful_loading__"

# Usa el mismo logo remoto por consistencia
LOGO_URL = "https://i.postimg.cc/ryBnj3pm/logo.png"

def show_loading(page: ft.Page, text: str = "Cargando…"):
    """Muestra un overlay de carga suave sobre toda la pantalla."""
    if getattr(page, _OVERLAY_KEY, None):
        return

    overlay = ft.Container(
        bgcolor=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
        alignment=ft.alignment.center,
        content=ft.Container(
            padding=20,
            bgcolor="white",
            border_radius=18,
            shadow=ft.BoxShadow(
                blur_radius=16, color=ft.Colors.with_opacity(0.28, ft.Colors.BLACK)
            ),
            content=ft.Column(
                [
                    ft.Image(
                        src=LOGO_URL,
                        width=56,
                        height=56,
                        fit=ft.ImageFit.CONTAIN,
                        error_content=ft.Container(
                            width=56,
                            height=56,
                            bgcolor="#EDE7FF",
                            border_radius=28,
                            alignment=ft.alignment.center,
                            content=ft.Text("M+", weight=ft.FontWeight.W_700, size=18, color="#5A00D0"),
                        ),
                    ),
                    ft.Container(height=8),
                    ft.Text(text, size=14),
                    ft.Container(height=10),
                    ft.ProgressRing(height=26, width=26, stroke_width=3),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
            width=220,
        ),
    )

    page.overlay.append(overlay)
    setattr(page, _OVERLAY_KEY, overlay)
    page.update()


def hide_loading(page: ft.Page):
    """Oculta el overlay de carga si está visible."""
    overlay = getattr(page, _OVERLAY_KEY, None)
    if overlay and overlay in page.overlay:
        page.overlay.remove(overlay)
    if hasattr(page, _OVERLAY_KEY):
        delattr(page, _OVERLAY_KEY)
    page.update()
