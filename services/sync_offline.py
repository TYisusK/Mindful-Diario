# services/sync_offline.py
import asyncio
from services.firebase_service import FirebaseService
from services import offline_queue


async def sync_offline_actions(page):
    """
    Llamar cuando el usuario vuelva a estar "online".
    Intenta subir todo lo que haya en la cola.
    """
    if not offline_queue.has_pending(page):
        return

    fb = FirebaseService()
    pending = offline_queue.pop_all(page)
    still_pending = []

    for action in pending:
        typ = action.get("type")
        payload = action.get("payload") or {}
        uid = action.get("uid")

        try:
            # --- NOTAS OFFLINE ---
            if typ == "note":
                fb.add_note(
                    uid,
                    payload.get("title", ""),
                    payload.get("content", ""),
                )

            # --- DIAGNÓSTICOS OFFLINE ---
            elif typ == "diagnostic":
                # Aquí el payload es el mismo que guardamos en diagnostic_page
                fb.add_diagnostic(uid, payload)

            # Aquí podrías agregar más tipos:
            # elif typ == "otra_cosa":
            #     fb.algo(uid, **payload)

        except Exception as e:
            # Si falla, lo regresamos a la cola para intentar más tarde
            print("[SYNC] Error al sincronizar acción:", typ, e)
            still_pending.append(action)

    # Re-graba lo que no se pudo enviar
    if still_pending:
        for a in still_pending:
            offline_queue.queue_action(page, a)
