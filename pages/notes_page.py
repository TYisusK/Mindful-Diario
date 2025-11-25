from components.app_header import AppHeader
import flet as ft
import asyncio
import pytz
from datetime import datetime, timedelta
from google.cloud.firestore_v1 import base_query as bq
from firebase_admin import firestore

from theme import BG, INK, MUTED, rounded_card, primary_button
from ui_helpers import shell_header, scroll_view
from services.firebase_service import FirebaseService


def NotesView(page: ft.Page):
    fb = FirebaseService()

    sess_user = page.session.get("user")
    if not isinstance(sess_user, dict) or not sess_user.get("uid"):
        return ft.View(
            route="/notes",
            controls=[AppHeader(page, active_route='notes'), ft.Text("Inicia sesión para continuar")],
            bgcolor=BG
        )
    uid = sess_user["uid"]

    header = shell_header("Mis notas", "Organiza y expresa lo que sientes")

    tz = pytz.timezone("America/Mexico_City")

    status = ft.Text("", color=MUTED)
    list_col = ft.Column(spacing=10)

    # Filtro activo: "all", "today", "week", "month", "custom"
    active_filter = {"type": "all", "start": None, "end": None}
    filter_label = ft.Text("Todas las notas", size=14, weight=ft.FontWeight.W_500, color=INK)

    # --- UI helpers ---
    def toast(msg: str, error: bool = False):
        print(f"[TOAST] {msg}")
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="#E5484D" if error else "#2ECC71")
        page.snack_bar.open = True
        page.update()

    def set_status(txt=""):
        status.value = txt
        print(f"[STATUS] {txt}")
        page.update()

    # --- Fecha utils ---
    def ts_to_key(ts):
        now_local = datetime.now(tz)
        if ts is None:
            return now_local.strftime("%Y-%m-%d")
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=pytz.utc)
        dt_local = ts.astimezone(tz)
        return dt_local.strftime("%Y-%m-%d")

    def format_date_header(date_key: str):
        """Convierte '2024-11-24' en un formato legible"""
        try:
            dt = datetime.strptime(date_key, "%Y-%m-%d")
            now = datetime.now()
            
            if dt.date() == now.date():
                return "Hoy"
            elif dt.date() == (now - timedelta(days=1)).date():
                return "Ayer"
            else:
                # Formato: "24 de noviembre"
                months = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                return f"{dt.day} de {months[dt.month - 1]}"
        except:
            return date_key

    # --- Bottom Sheet de Filtros ---
    def show_filter_sheet():
        now_local = datetime.now(tz)
        
        def apply_filter(filter_type: str, label: str, start_date=None, end_date=None):
            active_filter["type"] = filter_type
            active_filter["start"] = start_date
            active_filter["end"] = end_date
            filter_label.value = label
            close_sheet()
            try:
                page.run_task(load_notes)
            except Exception:
                asyncio.run(load_notes())

        # Opciones de filtro rápido
        quick_filters = [
            {
                "label": "Todas las notas",
                "icon": ft.Icons.ALL_INCLUSIVE,
                "action": lambda: apply_filter("all", "Todas las notas")
            },
            {
                "label": "Hoy",
                "icon": ft.Icons.TODAY,
                "action": lambda: apply_filter(
                    "today",
                    "Hoy",
                    now_local.replace(hour=0, minute=0, second=0, microsecond=0),
                    now_local
                )
            },
            {
                "label": "Esta semana",
                "icon": ft.Icons.DATE_RANGE,
                "action": lambda: apply_filter(
                    "week",
                    "Esta semana",
                    now_local - timedelta(days=now_local.weekday()),
                    now_local
                )
            },
            {
                "label": "Este mes",
                "icon": ft.Icons.CALENDAR_MONTH,
                "action": lambda: apply_filter(
                    "month",
                    "Este mes",
                    now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                    now_local
                )
            },
        ]

        # Crear botones de filtro
        filter_buttons = []
        for f in quick_filters:
            btn = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(f["icon"], color=INK, size=20),
                        ft.Text(f["label"], size=15, color=INK),
                    ],
                    spacing=12,
                ),
                padding=16,
                on_click=lambda e, action=f["action"]: action(),
                ink=True,
                border_radius=8,
            )
            filter_buttons.append(btn)

        # Sección de rango personalizado
        start_date_field = ft.TextField(
            label="Fecha inicio",
            hint_text="YYYY-MM-DD",
            width=140,
            height=50,
        )
        end_date_field = ft.TextField(
            label="Fecha fin",
            hint_text="YYYY-MM-DD",
            width=140,
            height=50,
        )

        def apply_custom_range():
            try:
                start_str = start_date_field.value
                end_str = end_date_field.value
                
                if not start_str or not end_str:
                    toast("Ingresa ambas fechas", error=True)
                    return
                
                start_dt = datetime.strptime(start_str, "%Y-%m-%d")
                end_dt = datetime.strptime(end_str, "%Y-%m-%d")
                
                if start_dt > end_dt:
                    toast("La fecha de inicio debe ser anterior a la final", error=True)
                    return
                
                start_local = tz.localize(start_dt.replace(hour=0, minute=0, second=0))
                end_local = tz.localize(end_dt.replace(hour=23, minute=59, second=59))
                
                apply_filter(
                    "custom",
                    f"{start_str} - {end_str}",
                    start_local,
                    end_local
                )
            except ValueError:
                toast("Formato de fecha inválido. Usa YYYY-MM-DD", error=True)

        custom_section = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Rango personalizado", size=14, weight=ft.FontWeight.W_600, color=INK),
                    ft.Row([start_date_field, end_date_field], spacing=12),
                    ft.ElevatedButton(
                        "Aplicar rango",
                        on_click=lambda e: apply_custom_range(),
                        bgcolor="#7C3AED",
                        color="white",
                    ),
                ],
                spacing=12,
            ),
            padding=ft.padding.only(top=20, bottom=10),
        )

        sheet_content = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(
                            "Filtrar notas",
                            size=18,
                            weight=ft.FontWeight.W_700,
                            color=INK
                        ),
                        padding=ft.padding.only(bottom=16),
                    ),
                    ft.Column(filter_buttons, spacing=4),
                    custom_section,
                ],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
            bgcolor=ft.Colors.WHITE,
            border_radius=ft.border_radius.only(top_left=16, top_right=16),
        )

        bottom_sheet = ft.BottomSheet(
            content=sheet_content,
            open=True,
            bgcolor=ft.Colors.TRANSPARENT,
        )

        def close_sheet():
            bottom_sheet.open = False
            page.update()

        page.overlay.append(bottom_sheet)
        page.update()
        print("[FILTER] Bottom sheet mostrado")

    # --- Cargar notas ---
    async def load_notes():
        set_status("Cargando notas…")
        print(f"[LOAD] Cargando con filtro: {active_filter}")

        notes_ref = fb.db.collection("users").document(uid).collection("notes")
        
        # Aplicar filtro de fecha si existe
        if active_filter["type"] != "all" and active_filter["start"] and active_filter["end"]:
            start_utc = active_filter["start"].astimezone(pytz.utc)
            end_utc = active_filter["end"].astimezone(pytz.utc)
            q = (
                notes_ref.where(filter=bq.FieldFilter("updatedAt", ">=", start_utc))
                .where(filter=bq.FieldFilter("updatedAt", "<=", end_utc))
                .order_by("updatedAt", direction=firestore.Query.DESCENDING)
                .limit(500)
            )
        else:
            # Todas las notas
            q = notes_ref.order_by("updatedAt", direction=firestore.Query.DESCENDING).limit(500)

        docs = list(q.stream())

        list_col.controls.clear()
        print(f"[LOAD] {len(docs)} notas encontradas.")

        if not docs:
            list_col.controls.append(
                ft.Container(
                    content=ft.Text("No hay notas para este período", color=MUTED, size=14),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )
            page.update()
            set_status("")
            return

        today_key = datetime.now(tz).strftime("%Y-%m-%d")

        # Agrupar notas por fecha
        notes_by_date = {}
        for d in docs:
            data = d.to_dict() or {}
            created_at = data.get("createdAt")
            date_key = ts_to_key(created_at)
            
            if date_key not in notes_by_date:
                notes_by_date[date_key] = []
            
            notes_by_date[date_key].append((d.id, data))

        # --- Modal para ver nota ---
        def show_note_detail(note_title: str, note_content: str):
            overlay = ft.Container(
                bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
                alignment=ft.alignment.center,
                content=ft.Container(
                    width=min(page.width - 40, 400) if page.width else 400,
                    height=min(page.height - 100, 500) if page.height else 500,
                    padding=20,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=16,
                    content=ft.Column(
                        [
                            ft.Text(note_title, size=18, weight=ft.FontWeight.W_700, color=INK),
                            ft.Container(
                                expand=True,
                                content=ft.Column(
                                    [
                                        ft.Text(
                                            note_content or "(Sin contenido)",
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

        # Renderizar notas agrupadas por fecha
        for date_key in sorted(notes_by_date.keys(), reverse=True):
            # Header de fecha
            list_col.controls.append(
                ft.Container(
                    content=ft.Text(
                        format_date_header(date_key),
                        size=16,
                        weight=ft.FontWeight.W_700,
                        color=INK,
                    ),
                    padding=ft.padding.only(top=20, bottom=8, left=4),
                )
            )

            # Notas de esa fecha
            for note_id, data in notes_by_date[date_key]:
                title = (data.get("title") or "Sin título")[:120]
                content = (data.get("content") or "").strip()
                created_at = data.get("createdAt")
                created_key = ts_to_key(created_at)
                is_same_day = (created_key == today_key)

                if is_same_day:
                    # ✅ Hoy: Editar / Eliminar
                    edit_btn = ft.IconButton(
                        icon=ft.Icons.EDIT,
                        tooltip="Editar",
                        icon_size=20,
                        on_click=lambda e, nid=note_id: page.go(f"/note_editor?id={nid}&date={date_key}"),
                    )
                    del_btn = ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        tooltip="Eliminar",
                        icon_size=20,
                        on_click=lambda e, nid=note_id: on_delete_note(nid, created_key),
                    )
                    action_row = ft.Row([edit_btn, del_btn], alignment=ft.MainAxisAlignment.END, spacing=0)
                else:
                    # 👁️ Anteriores: solo ver modal
                    view_btn = ft.IconButton(
                        icon=ft.Icons.REMOVE_RED_EYE_OUTLINED,
                        tooltip="Ver nota completa",
                        icon_size=20,
                        on_click=lambda e, t=title, c=content: show_note_detail(t, c),
                    )
                    action_row = ft.Row([view_btn], alignment=ft.MainAxisAlignment.END)

                list_col.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=INK),
                                ft.Text(
                                    content[:200] + ("…" if len(content) > 200 else ""),
                                    size=12,
                                    color=MUTED,
                                    max_lines=3,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                action_row,
                            ],
                            spacing=6,
                        ),
                        padding=14,
                        bgcolor="#EDE7FF",
                        border_radius=16,
                    )
                )

        page.update()
        set_status("")

    # --- Eliminar nota ---
    async def delete_async(note_id: str):
        print(f"[DELETE] Ejecutando delete_async para {note_id}")
        try:
            await asyncio.to_thread(fb.delete_note, uid, note_id)
            print("[DELETE] Eliminación completada en Firestore.")
            toast("Nota eliminada ✅")
            await load_notes()
        except Exception as ex:
            print("[ERROR] Durante delete_async:", ex)
            toast(f"Error al eliminar: {ex}", error=True)
        finally:
            set_status("")

    def on_delete_note(note_id: str, created_key: str):
        print(f"[CLICK] Intento de eliminar {note_id}, creado={created_key}")
        today_key = datetime.now(tz).strftime("%Y-%m-%d")

        if created_key != today_key:
            print(f"[BLOCKED] Eliminación denegada: creado={created_key}, hoy={today_key}")
            toast("Solo puedes eliminar notas del mismo día en que fueron creadas.", error=True)
            return

        overlay = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            alignment=ft.alignment.center,
            content=ft.Container(
                width=320,
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=12,
                content=ft.Column([
                    ft.Text("Eliminar nota", size=18, weight=ft.FontWeight.W_700, color=INK),
                    ft.Text("Esta acción no se puede deshacer.\n¿Quieres continuar?", size=13, color=MUTED),
                    ft.Row(
                        [
                            ft.ElevatedButton("Cancelar", on_click=lambda e: close_overlay(False), bgcolor="#D9D9D9", color=INK),
                            ft.ElevatedButton("Eliminar", on_click=lambda e: close_overlay(True), bgcolor="#E5484D", color="white"),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=10,
                    ),
                ], spacing=16),
            ),
        )

        def close_overlay(ok: bool):
            page.overlay.clear()
            page.update()
            if ok:
                set_status("Eliminando…")
                try:
                    page.run_task(lambda: delete_async(note_id))
                except Exception:
                    asyncio.run(delete_async(note_id))

        page.overlay.append(overlay)
        page.update()

    # --- Layout principal ---
    filter_button = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.FILTER_LIST, color="#7C3AED", size=20),
                filter_label,
                ft.Icon(ft.Icons.ARROW_DROP_DOWN, color="#7C3AED", size=20),
            ],
            spacing=8,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        bgcolor="#F3F4F6",
        border_radius=12,
        on_click=lambda e: show_filter_sheet(),
        ink=True,
    )

    actions = ft.Row(
        [
            primary_button("Nueva nota", lambda _: page.go("/note_editor")),
            filter_button,
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        wrap=True,
    )

    # Use shared scroll_view wrapper so the content becomes scrollable
    body = scroll_view(
        rounded_card(ft.Column([header, actions, list_col, status], spacing=12), 16),
        page=page,
    )

    # --- Boot ---
    async def boot():
        print("[BOOT] Iniciando NotesView...")
        await load_notes()
        print("[BOOT] Listo.")

    try:
        page.run_task(boot)
    except Exception as ex:
        print("[ERROR] boot run_task:", ex)
        asyncio.run(boot())

    return ft.View(
        route="/notes",
        controls=[AppHeader(page, active_route='notes'), body],
        bgcolor=BG
    )