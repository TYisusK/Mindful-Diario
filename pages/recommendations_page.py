from components.app_header import AppHeader
import flet as ft
import asyncio, threading
from datetime import datetime, timedelta
import pytz
from google.cloud.firestore_v1 import base_query as bq
from firebase_admin import firestore

from theme import BG, INK, MUTED, rounded_card, primary_button
from ui_helpers import date_scroller, shell_header
from services.firebase_service import FirebaseService
from services.gemini_service import GeminiService


def RecommendationsView(page: ft.Page):
    fb = FirebaseService()
    gem = GeminiService()

    sess_user = page.session.get("user")
    if not isinstance(sess_user, dict) or not sess_user.get("uid"):
        return ft.View(
            route="/recommendations",
            controls=[AppHeader(page, active_route='recommendations'), ft.Text("Inicia sesión para continuar")],
            bgcolor=BG
        )

    uid = sess_user["uid"]
    display_name = sess_user.get("username") or (sess_user.get("email") or "").split("@")[0] or "la persona usuaria"

    tz = pytz.timezone("America/Mexico_City")
    now_local = datetime.now(tz)
    active_key = now_local.strftime("%Y-%m-%d")

    header = shell_header("Recomendación del día", "Tu acompañante de Mindful 💜")

    # UI
    status = ft.Text("", color=MUTED)
    scroller_row = ft.Row([])
    list_col = ft.Column(spacing=10)

    # === UTILS ===
    def toast(msg: str, error: bool = False):
        page.snack_bar = ft.SnackBar(
            ft.Text(msg),
            bgcolor="#E5484D" if error else "#2ECC71"
        )
        page.snack_bar.open = True
        page.update()

    def set_status(txt=""):
        status.value = txt
        page.update()

    def today_key():
        tz = pytz.timezone("America/Mexico_City")
        now_local = datetime.now(tz)
        return tz, now_local, now_local.strftime("%Y-%m-%d")

    # === SHOW DETAIL ===
    def show_recommendation_detail(date_key: str, text: str):
        overlay = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            alignment=ft.alignment.center,
            content=ft.Container(
                width=400,
                height=500,
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=16,
                content=ft.Column(
                    [
                        ft.Text(f"Recomendación del {date_key}", size=18, weight=ft.FontWeight.W_700, color=INK),
                        ft.Container(
                            height=380,
                            content=ft.Column(
                                [
                                    ft.Text(
                                        text or "(Sin contenido)",
                                        size=13,
                                        color=INK,
                                        selectable=True,
                                        text_align=ft.TextAlign.JUSTIFY,
                                    )
                                ],
                                scroll=ft.ScrollMode.AUTO,
                            ),
                        ),
                        ft.ElevatedButton(
                            "Cerrar",
                            bgcolor="#D9D9D9",
                            color=INK,
                            on_click=lambda e: close_overlay(),
                        ),
                    ],
                    spacing=12,
                    alignment=ft.MainAxisAlignment.START,
                ),
            ),
        )

        def close_overlay():
            page.overlay.clear()
            page.update()

        page.overlay.append(overlay)
        page.update()

    # === LOAD DATA ===
    async def load_today_and_history():
        set_status("Cargando recomendaciones…")
        tz, now_local, dkey = today_key()

        # Recomendación de hoy
        today = await asyncio.to_thread(fb.get_recommendation_for_date, uid, dkey)
        if today and today.get("text"):
            today_text.value = today["text"]
        else:
            today_text.value = "Aún no hay recomendación de hoy. Presiona “Generar recomendación”."

        # Historial
        recs = await asyncio.to_thread(fb.list_recommendations, uid, 120)
        list_col.controls.clear()

        for doc in recs:
            date_key = doc.get("date")
            text = (doc.get("text") or "").strip()
            preview = text[:120] + ("…" if len(text) > 120 else "")
            if not date_key or not text:
                continue

            list_col.controls.append(
                ft.Container(
                    on_click=lambda e, dk=date_key, t=text: show_recommendation_detail(dk, t),
                    content=ft.Column(
                        [
                            ft.Text(date_key, size=15, weight=ft.FontWeight.W_600, color=INK),
                            ft.Text(preview, size=12, color=MUTED),
                        ],
                        spacing=4,
                    ),
                    padding=14,
                    bgcolor="#EDE7FF",
                    border_radius=16,
                )
            )

        if not list_col.controls:
            list_col.controls.append(ft.Text("No hay recomendaciones pasadas aún.", color=MUTED))

        page.update()
        set_status("")

    # === GENERAR HOY ===
    async def generate_today():
        set_status("Generando recomendación…")

        tz, now_local, dkey = today_key()
        start_local = tz.localize(datetime(now_local.year, now_local.month, now_local.day, 0, 0, 0))
        end_local = start_local + timedelta(days=1)
        start_utc = start_local.astimezone(pytz.utc)
        end_utc = end_local.astimezone(pytz.utc)

        # Notas y diagnósticos
        notes_ref = fb.db.collection("users").document(uid).collection("notes")
        qn = (notes_ref
              .where(filter=bq.FieldFilter("updatedAt", ">=", start_utc))
              .where(filter=bq.FieldFilter("updatedAt", "<", end_utc))
              .order_by("updatedAt", direction=firestore.Query.DESCENDING)
              .limit(30))
        notes_today = [{"id": d.id, **(d.to_dict() or {})} for d in qn.stream()]

        diags_ref = fb.db.collection("users").document(uid).collection("diagnostics")
        qd = (diags_ref
              .where(filter=bq.FieldFilter("createdAt", ">=", start_utc))
              .where(filter=bq.FieldFilter("createdAt", "<", end_utc))
              .order_by("createdAt", direction=firestore.Query.DESCENDING)
              .limit(3))
        diags_today = [{"id": d.id, **(d.to_dict() or {})} for d in qd.stream()]

        if not notes_today and not diags_today:
            toast("Aún no hay datos suficientes (escribe una nota o haz tu diagnóstico).", error=True)
            set_status("")
            return

        try:
            msg = await asyncio.to_thread(
                gem.generate_professional_recommendation,
                notes_today, diags_today, display_name, 550, 0.8, 0.9, 40
            )
        except Exception:
            msg = "Hoy te recomiendo tomarte un momento para respirar profundamente y agradecer algo bueno de tu día 💜."
            toast("Error con Gemini, usando respaldo.", error=False)

        await asyncio.to_thread(
            fb.upsert_recommendation_for_date,
            uid, dkey, msg,
            {"source": "gemini-2.0-flash", "notesCount": len(notes_today), "diagsCount": len(diags_today)}
        )

        today_text.value = msg
        toast("Recomendación del día guardada ✅")
        await load_today_and_history()

    def on_generate(_):
        try:
            page.run_task(generate_today)
        except Exception:
            threading.Thread(target=lambda: asyncio.run(generate_today()), daemon=True).start()

    # === UI SECTIONS ===
    today_text = ft.Text(
        "Cargando recomendación de hoy…",
        size=13,
        color=INK,
        selectable=True,
        text_align=ft.TextAlign.JUSTIFY,
    )

    today_card = rounded_card(
        ft.Column(
            [
                header,
                ft.Text(datetime.now(tz).strftime("%Y-%m-%d"), size=12, color=MUTED),
                today_text,
                ft.Row([primary_button("Generar recomendación", on_generate)], alignment=ft.MainAxisAlignment.START),
                status,
            ],
            spacing=10,
        ),
        16,
    )

    history_card = rounded_card(
        ft.Column(
            [
                ft.Text("Recomendaciones pasadas", size=15, weight=ft.FontWeight.W_600, color=INK),
                list_col,
            ],
            spacing=8,
        ),
        16,
    )

       # === LAYOUT FINAL ===
    # Usamos ListView para permitir scroll con scrollbar visible
    scrollable_content = ft.ListView(
        controls=[
            today_card,
            ft.Container(height=20),
            history_card,
        ],
        expand=True,
        spacing=20,
        padding=20,
        auto_scroll=False,
    )

    body = ft.Container(
        content=scrollable_content,
        bgcolor=BG,
        expand=True,
    )

    # === BOOT ===
    async def boot():
        await load_today_and_history()

    try:
        page.run_task(boot)
    except Exception:
        threading.Thread(target=lambda: asyncio.run(boot()), daemon=True).start()

    return ft.View(
        route="/recommendations",
        controls=[AppHeader(page, active_route='recommendations'), body],
        bgcolor=BG,
        scroll=ft.ScrollMode.ADAPTIVE,  # extra seguridad para navegadores
    )

    # === BOOT ===
    async def boot():
        await load_today_and_history()

    try:
        page.run_task(boot)
    except Exception:
        threading.Thread(target=lambda: asyncio.run(boot()), daemon=True).start()

    return ft.View(
    
        route="/recommendations",
        controls=[AppHeader(page, active_route='recommendations'), body],
        bgcolor=BG
    )
