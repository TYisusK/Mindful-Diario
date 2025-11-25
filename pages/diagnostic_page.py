from components.app_header import AppHeader

import flet as ft
import asyncio, threading
import requests
from theme import BG, INK, MUTED, rounded_card, primary_button
from services.firebase_service import FirebaseService
from services.diagnostic_utils import EMOTIONS, DAY_TAGS, compute_score_and_diagnosis
from services.gemini_service import GeminiService
from services import offline_queue
from ui_helpers import scroll_view, shell_header, two_col_grid

DEBUG = True

def DiagnosticView(page: ft.Page):
    fb = FirebaseService()
    gem = GeminiService()

    sess_user = page.session.get("user")
    if not isinstance(sess_user, dict) or not sess_user.get("uid"):
        return ft.View(controls=[AppHeader(page, active_route='diagnostic'), ft.Text("Inicia sesión para continuar")], route="/diagnostic", bgcolor=BG)
    uid = sess_user["uid"]

    def log(msg: str):
        if DEBUG: print(f"[Diagnostic] {msg}")

    def toast(msg: str, error: bool = False):
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="#E5484D" if error else "#2ECC71")
        page.snack_bar.open = True
        page.update()

    # pass `page` so header can adjust sizes responsively
    header = shell_header("Diagnóstico diario", "Cuéntame cómo estás para acompañarte", page=page)

    mood_group = ft.RadioGroup(
        content=ft.Row(controls=[ft.Radio(value=str(i), label=str(i)) for i in range(1,6)], spacing=12),
        value="3",
    )

    emotions_boxes = [ft.Checkbox(label=e, value=False) for e in EMOTIONS]
    emotions_grid = two_col_grid([ft.Container(cb) for cb in emotions_boxes], page=page)

    tags_boxes = [ft.Checkbox(label=t, value=(t=="buen día")) for t in DAY_TAGS]
    tags_grid = two_col_grid([ft.Container(cb) for cb in tags_boxes], page=page)

    note = ft.TextField(label="Nota breve (opcional)", hint_text="Escribe algo corto...", max_length=160, border_radius=16)
    sleep = ft.Slider(min=1, max=24, divisions=23, value=7, label="{value}h")

    status = ft.Text("", color=MUTED)
    spinner = ft.ProgressRing(visible=False)

    section1 = rounded_card(ft.Column([
        ft.Text("1) ¿Cómo te sientes hoy? (1 = muy mal, 5 = excelente)", color=INK, weight=ft.FontWeight.W_600),
        mood_group,
    ], spacing=10), 16)

    section2 = rounded_card(ft.Column([
        ft.Text("2) ¿Qué emociones sientes? (elige varias)", color=INK, weight=ft.FontWeight.W_600),
        emotions_grid,
    ], spacing=10), 16)

    section3 = rounded_card(ft.Column([
        ft.Text("3) Tu día (elige varias)", color=INK, weight=ft.FontWeight.W_600),
        tags_grid,
        note,
    ], spacing=10), 16)

    section4 = rounded_card(ft.Column([
        ft.Text("4) Sueño (horas)", color=INK, weight=ft.FontWeight.W_600),
        sleep,
    ], spacing=10), 16)

    def set_loading(is_loading: bool, msg: str = ""):
        for cb in emotions_boxes + tags_boxes:
            cb.disabled = is_loading
        mood_group.disabled = is_loading
        note.disabled = is_loading
        spinner.visible = is_loading
        status.value = msg
        page.update()

    async def run_flow():
        try:
            set_loading(True, "Guardando…")
            log("Flow start")

            # --- Leer valores de la UI ---
            try:
                sel_mood = int(mood_group.value or "3")
            except Exception:
                sel_mood = 3

            sel_emotions = [cb.label for cb in emotions_boxes if cb.value]
            sel_tags = [cb.label for cb in tags_boxes if cb.value]
            sel_note = (note.value or "").strip()
            sel_sleep = int(round(sleep.value))

            log(f"Inputs -> mood={sel_mood}, emotions={sel_emotions}, tags={sel_tags}, note='{sel_note}', sleep={sel_sleep}")

            # --- Scoring local (100% offline) ---
            score, diagnosis = compute_score_and_diagnosis(sel_mood, sel_emotions, sel_sleep)
            log(f"Scoring -> score={score}, diagnosis={diagnosis}")

            # Documento base para Firestore
            payload = {
                "mood": sel_mood,
                "emotions": sel_emotions,
                "dayTags": sel_tags,
                "note": sel_note[:160],
                "sleepHours": sel_sleep,
                "score": score,
                "diagnosis": diagnosis,
            }

            # --- Paso 1: guardar diagnóstico en Firestore ---
            try:
                # Le ponemos un timeout para no quedarnos colgados 60s
                doc_id = await asyncio.wait_for(
                    asyncio.to_thread(fb.add_diagnostic, uid, payload),
                    timeout=8.0,  # segundos, ajústalo si quieres
                )
                log(f"Firestore OK -> doc_id={doc_id}")

            except asyncio.TimeoutError as ex:
                # Timeout -> lo tomamos como offline y encolamos
                log(f"Firestore TIMEOUT (OFFLINE) -> {ex}")
                offline_queue.queue_action(page, {
                    "type": "diagnostic",
                    "uid": uid,
                    "payload": payload,
                })
                set_loading(False, "")
                toast("Sin conexión: tu diagnóstico se guardó offline y se sincronizará después ✅")
                page.go("/home")
                return

            except Exception as ex:
                # CUALQUIER otro error al guardar lo tratamos como offline
                log(f"Firestore OFFLINE/ERROR (queue) -> {ex}")
                offline_queue.queue_action(page, {
                    "type": "diagnostic",
                    "uid": uid,
                    "payload": payload,
                })
                set_loading(False, "")
                toast("Sin conexión: tu diagnóstico se guardó offline y se sincronizará después ✅")
                page.go("/home")
                return


            # --- Paso 2: frase del día con Gemini (solo online, no se reintenta offline) ---
            set_loading(True, "Generando frase del día…")
            try:
                phrase = await asyncio.to_thread(
                    gem.phrase_for_diagnostic,
                    diagnosis,
                    sel_emotions,
                    sel_tags,
                    sel_note,
                    120,
                )
                log(f"Gemini OK -> '{phrase}'")
            except Exception as ex:
                phrase = "Sigue adelante: cada paso cuenta."
                log(f"Gemini ERROR -> {ex}")
                toast(f"Gemini: {ex}", error=False)

            # --- Paso 3: actualizar el diagnóstico con la frase ---
            set_loading(True, "Actualizando…")
            try:
                await asyncio.to_thread(
                    fb.update_diagnostic,
                    uid,
                    doc_id,
                    {"phrase": phrase, "phraseChars": len(phrase), "model": "gemini-2.0-flash"},
                )
                log("Firestore update OK")
            except Exception as ex:
                log(f"Firestore update ERROR -> {ex}")
                # El diagnóstico base ya está guardado; solo falló la actualización

            toast("Diagnóstico guardado ✅")
            set_loading(False, "¡Listo!")
            page.go("/home")

        except Exception as ex:
            log(f"Flow FATAL -> {ex}")
            set_loading(False, "")
            toast(f"Error: {ex}", error=True)


    def on_submit(_):
        try:
            page.run_task(run_flow)
        except Exception as ex:
            print(f"[Diagnostic] run_task falla: {ex}. Hilo fallback.")
            threading.Thread(target=lambda: asyncio.run(run_flow()), daemon=True).start()

    # Make submit button expand to fill available width on mobile for a better touch target
    submit_btn = primary_button("Guardar diagnóstico", on_submit)
    submit_container = ft.Container(submit_btn, expand=True)
    submit_row = ft.Row([submit_container, spinner], alignment=ft.MainAxisAlignment.START)


    body = scroll_view(
        rounded_card(ft.Column([header, section1, section2, section3, section4, submit_row, status], spacing=16), 16),
        page=page,
    )

    # --- Responsiveness: update grids and expand flags on resize ---
    def on_resize(e):
        try:
            # rebuild grids so two_col_grid can read the current page.width
            new_emotions = two_col_grid([ft.Container(cb) for cb in emotions_boxes], page=page)
            section2.content.controls[1] = new_emotions

            new_tags = two_col_grid([ft.Container(cb) for cb in tags_boxes], page=page)
            section3.content.controls[1] = new_tags

            # make note expand on small screens
            if page.width and page.width <= 600:
                note.expand = True
            else:
                note.expand = False

            # ensure submit button remains full-width on mobile
            submit_container.expand = True

            page.update()
        except Exception:
            pass

    page.on_resize = on_resize

    return ft.View(controls=[AppHeader(page, active_route='diagnostic'), body], route="/diagnostic", bgcolor=BG)
