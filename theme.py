# theme.py
import flet as ft

PRIMARY = "#8B75F3"
PRIMARY_DIM = "#B5A7F9"
BG = "#F8F7FC"
INK = "#1E1B2E"
MUTED = "#6B6A75"

def rounded_card(content: ft.Control, pad: int = 16):
    return ft.Container(
        content=content,
        padding=pad,
        bgcolor="#FFFFFF",
        border_radius=24,
    )

def primary_button(text: str, on_click):
    return ft.ElevatedButton(
        text,
        on_click=on_click,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=22),
            padding=ft.Padding(16, 10, 16, 10),
            color="#FFFFFF",      # <- sin ft.colors
            bgcolor=PRIMARY,
        ),
    )

def ghost_button(text: str, on_click):
    return ft.OutlinedButton(
        text,
        on_click=on_click,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=22),
            padding=ft.Padding(16, 10, 16, 10),
            color=PRIMARY,
            side=ft.BorderSide(1, PRIMARY),
        ),
    )
