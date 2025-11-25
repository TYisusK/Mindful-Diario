# pages/welcome_page.py
import flet as ft
from theme import PRIMARY, PRIMARY_DIM, BG, INK, rounded_card, primary_button, ghost_button

# Compatibilidad de íconos (nuevas vs viejas versiones)
try:
    ICONS = ft.icons
except AttributeError:
    ICONS = ft.Icons

def WelcomeView(page: ft.Page):
    logo = ft.Container(
        width=88,
        height=88,
        bgcolor=PRIMARY_DIM,
        border_radius=44,
        alignment=ft.alignment.center,
        content=ft.Icon(ICONS.SPA, size=44, color="#FFFFFF"),  # <- sin ft.colors
    )

    title = ft.Text("Mindful", size=26, weight=ft.FontWeight.W_700, color=INK)
    subtitle = ft.Text(
        "Respira, centra tu atención y cuida tu bienestar.",
        size=13,
        color="#7A778A",
        text_align=ft.TextAlign.CENTER,
    )

    cta = ft.Column(
        [
            primary_button("Iniciar sesión", lambda _: page.go("/login")),
            ghost_button("Registrarse", lambda _: page.go("/register")),
        ],
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    card_content = ft.Column(
        [
            logo,
            ft.Container(height=8),
            title,
            subtitle,
            ft.Container(height=10),
            cta,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
    )

    card = rounded_card(card_content, pad=24)

    body = ft.Container(
        expand=True,
        bgcolor=BG,
        content=ft.Column(
            [
                ft.Container(height=40),
                card,
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=20,
    )

    return ft.View(
        route="/",
        bgcolor=BG,
        controls=[body],
    )
