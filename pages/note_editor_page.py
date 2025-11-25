import flet as ft
import asyncio, urllib.parse as urlparse
import pytz
from datetime import datetime
from firebase_admin import firestore
from services.firebase_service import FirebaseService
from services import offline_queue
import requests
from theme import BG, MUTED, rounded_card, primary_button
from ui_helpers import shell_header

    
def NoteEditorView(page: ft.Page):
    fb = FirebaseService()
    sess_user = page.session.get("user")
    if not isinstance(sess_user, dict) or not sess_user.get("uid"):
        return ft.View(route="/note_editor", controls=[ft.Text("Inicia sesión para continuar")], bgcolor=BG)
    uid = sess_user["uid"]

    tz = pytz.timezone("America/Mexico_City")
    today_key = datetime.now(tz).strftime("%Y-%m-%d")

    header = shell_header("Escribir nota", "Expresa lo que sientes hoy")

    # params
    params = {}
    if "?" in page.route:
        q = page.route.split("?", 1)[1]
        params = dict(urlparse.parse_qsl(q))
    note_id = params.get("id")

    back_btn = ft.IconButton(
        icon=ft.Icons.ARROW_BACK,
        icon_color="#5A00D0",
        tooltip="Volver a notas",
        on_click=lambda e: page.go("/notes")
    )

    header = shell_header("Escribir nota", "Expresa lo que sientes hoy")
    title = ft.TextField(label="Título (opcional)", multiline=False, border_radius=16)
    content = ft.TextField(label="Escribe tu nota", multiline=True, min_lines=8, max_lines=20, border_radius=16)
    status = ft.Text("", color=MUTED)

    def toast(msg: str, error: bool = False):
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="#E5484D" if error else "#2ECC71")
        page.snack_bar.open = True
        page.update()

    def set_status(s=""):
        status.value = s
        page.update()

    async def load_existing():
        if not note_id:
            return True  # creando nueva → permitido
        try:
            d = await asyncio.to_thread(fb.get_note, uid, note_id)
            if not d:
                toast("Nota no encontrada.", error=True)
                return False

            created_at = d.get("createdAt")
            if created_at is None:
                editable = True
            else:
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=pytz.utc)
                created_key = created_at.astimezone(tz).strftime("%Y-%m-%d")
                editable = (created_key == today_key)

            title.value = d.get("title") or ""
            content.value = d.get("content") or ""
            title.disabled = not editable
            content.disabled = not editable

            if not editable:
                toast("Las notas solo pueden editarse el día en que se crearon (solo lectura).", error=False)
            page.update()
            return editable
        except Exception as ex:
            toast(f"Error cargando nota: {ex}", error=True)
            return False

    async def save_async():
        ttl = (title.value or "").strip()
        body = (content.value or "").strip()
        if not ttl and not body:
            toast("Escribe algo para guardar.", error=True)
            return

        set_status("Guardando…")
        try:
            # Intento normal: guardar en Firebase (online)
            if note_id:
                await asyncio.to_thread(fb.update_note, uid, note_id, ttl, body)
            else:
                await asyncio.to_thread(fb.add_note, uid, ttl, body)

            toast("Nota guardada ✅")
            page.go("/notes")

        except requests.exceptions.RequestException:
            # Error de red → guardamos la nota en cola offline
            offline_queue.queue_action(page, {
                "type": "note",
                "uid": uid,
                "payload": {
                    "title": ttl,
                    "content": body,
                },
            })
            toast("Sin conexión: la nota se guardó offline y se subirá más tarde ✅")
            page.go("/notes")

        except Exception as ex:
            # Otro error que no es de red
            toast(f"Error al guardar: {ex}", error=True)

        finally:
            set_status("")


    async def boot():
        editable = await load_existing()
        # botón según editable
        save_btn = primary_button("Guardar", lambda _: (page.run_task(save_async) if editable else toast("Solo lectura", True)))
        form = ft.Column([title, content, ft.Row([save_btn], alignment=ft.MainAxisAlignment.START), status], spacing=12)
        body = ft.Container(content=rounded_card(ft.Column([header, form], spacing=12), 16), padding=20, bgcolor=BG)
        page.views[-1].controls.clear()
        page.views[-1].controls.append(body)
        page.update()

    v = ft.View(route="/note_editor", controls=[ft.Container()], bgcolor=BG)
    try:
        page.run_task(boot)
    except Exception:
        asyncio.run(boot())
    return v
