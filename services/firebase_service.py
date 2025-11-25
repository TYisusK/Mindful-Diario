import os
import json
import requests
from typing import Optional, Tuple, Dict, Any

import firebase_admin
from firebase_admin import credentials, firestore, auth as admin_auth
from firebase_admin import firestore as admin_fs
from typing import Optional, Tuple, Dict, Any



class FirebaseService:
    def __init__(self):
        """
        Configuración de Firebase y Cloudinary usando variables de entorno (.env).

        Añade algo como esto a tu archivo .env:

        # Firebase Web
        FIREBASE_WEB_API_KEY=...
        FIREBASE_PROJECT_ID=...

        # Firebase Admin (service account)
        FIREBASE_ADMIN_TYPE=...
        FIREBASE_ADMIN_PROJECT_ID=...
        FIREBASE_ADMIN_PRIVATE_KEY_ID=...
        FIREBASE_ADMIN_PRIVATE_KEY=...
        FIREBASE_ADMIN_CLIENT_EMAIL=...
        FIREBASE_ADMIN_CLIENT_ID=...
        FIREBASE_ADMIN_AUTH_URI=...
        FIREBASE_ADMIN_TOKEN_URI=...
        FIREBASE_ADMIN_AUTH_PROVIDER_X509_CERT_URL=...
        FIREBASE_ADMIN_CLIENT_X509_CERT_URL=...
        FIREBASE_ADMIN_UNIVERSE_DOMAIN=...

        # Cloudinary (opcional)
        CLOUDINARY_CLOUD_NAME=...
        CLOUDINARY_API_KEY=...
        CLOUDINARY_API_SECRET=...
        """
        # Firebase Web
        self.api_key = os.getenv("FIREBASE_WEB_API_KEY")
        self.project_id = os.getenv("FIREBASE_PROJECT_ID")

        if not self.api_key or not self.project_id:
            raise RuntimeError("Faltan FIREBASE_WEB_API_KEY o FIREBASE_PROJECT_ID en el entorno (.env).")

        # Firebase Admin: construir el dict de credenciales a partir del entorno
        admin_env_map = {
            "type": "FIREBASE_ADMIN_TYPE",
            "project_id": "FIREBASE_ADMIN_PROJECT_ID",
            "private_key_id": "FIREBASE_ADMIN_PRIVATE_KEY_ID",
            "private_key": "FIREBASE_ADMIN_PRIVATE_KEY",
            "client_email": "FIREBASE_ADMIN_CLIENT_EMAIL",
            "client_id": "FIREBASE_ADMIN_CLIENT_ID",
            "auth_uri": "FIREBASE_ADMIN_AUTH_URI",
            "token_uri": "FIREBASE_ADMIN_TOKEN_URI",
            "auth_provider_x509_cert_url": "FIREBASE_ADMIN_AUTH_PROVIDER_X509_CERT_URL",
            "client_x509_cert_url": "FIREBASE_ADMIN_CLIENT_X509_CERT_URL",
            "universe_domain": "FIREBASE_ADMIN_UNIVERSE_DOMAIN",
        }

        cred_info = {}
        missing = []
        for json_key, env_name in admin_env_map.items():
            value = os.getenv(env_name)
            if not value:
                missing.append(env_name)
            else:
                cred_info[json_key] = value

        if missing:
            raise RuntimeError(
                "Faltan variables de entorno para Firebase Admin: " + ", ".join(missing)
            )

        # La private_key suele venir con \n en una sola línea dentro del .env
        # Esto la regresa al formato multi-línea esperado por firebase_admin.
        if "private_key" in cred_info:
            cred_info["private_key"] = cred_info["private_key"].replace("\\n", "\n")

        # Inicializa Admin SDK (una sola vez)
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_info)
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()

        # Cloudinary (opcional, por si lo necesitas en otros servicios)
        self.cloudinary_cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        self.cloudinary_api_key = os.getenv("CLOUDINARY_API_KEY")
        self.cloudinary_api_secret = os.getenv("CLOUDINARY_API_SECRET")

# ---------- AUTH (REST) ----------
    def _endpoint(self, path: str) -> str:
        return f"https://identitytoolkit.googleapis.com/v1/{path}?key={self.api_key}"

    def sign_up(self, email: str, password: str) -> Tuple[str, str]:
        url = self._endpoint("accounts:signUp")
        data = {"email": email, "password": password, "returnSecureToken": True}
        r = requests.post(url, json=data, timeout=20)
        if r.status_code != 200:
            raise ValueError(r.json().get("error", {}).get("message", "SIGN_UP_FAILED"))
        j = r.json()
        return j["idToken"], j["localId"]

    def sign_in(self, email: str, password: str):
        """
        Inicia sesión con correo/contraseña.
        Lanza un ValueError con el código de error de Firebase si falla.
        """
        url = self._endpoint("accounts:signInWithPassword")
        data = {"email": email, "password": password, "returnSecureToken": True}
        r = requests.post(url, json=data, timeout=20)
        if r.status_code != 200:
            try:
                err = r.json().get("error", {})
                code = err.get("message", "SIGN_IN_FAILED")
            except Exception:
                code = "SIGN_IN_FAILED"
            raise ValueError(code)
        j = r.json()
        return j["idToken"], j["localId"]

    # ---------- GOOGLE SIGN IN ----------
    def sign_in_with_google(self, id_token: str) -> Tuple[str, str, Dict[str, Any]]:
        url = self._endpoint("accounts:signInWithIdp")
        data = {
            "postBody": f"id_token={id_token}&providerId=google.com",
            "requestUri": "http://localhost",
            "returnIdpCredential": True,
            "returnSecureToken": True,
        }
        r = requests.post(url, json=data, timeout=20)
        if r.status_code != 200:
            raise ValueError(r.json().get("error", {}).get("message", "GOOGLE_SIGN_IN_FAILED"))
        j = r.json()
        return j["idToken"], j["localId"], j

    # ---------- PERFIL ----------
   
    def create_user_profile(self, uid: str, email: str, username: Optional[str] = None) -> None:
        doc_ref = self.db.collection("users").document(uid)
        doc_ref.set(
            {"email": email, "username": username, "type": "normal", "createdAt": firestore.SERVER_TIMESTAMP},
            merge=True,
        )

    def get_user_profile(self, uid: str) -> Optional[dict]:
        doc = self.db.collection("users").document(uid).get()
        return doc.to_dict() if doc.exists else None
    
    
    # services/firebase_service.py (añade o revisa estas funciones)

    def create_professional_profile(
        self, uid: str, email: str, username: str,
        full_name: str, specialty: str, cedula: str, phone: str,
        photo_url: str | None = None
    ):
        doc_ref = self.db.collection("users").document(uid)
        payload = {
            "email": email,
            "username": username,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "professional": {
                "type": "profesional",
                "fullName": full_name,
                "specialty": specialty,
                "cedula": cedula,
                "phone": phone,
            }
        }
        if photo_url:
            payload["professional"]["photoUrl"] = photo_url
        doc_ref.set(payload, merge=True)

    # Dentro de class FirebaseService: (agrega estos métodos si no existen)

    def update_user_photo(self, uid: str, photo_url: str):
        """Actualiza professional.photoUrl (no toca otros campos)."""
        doc_ref = self.db.collection("users").document(uid)
        doc_ref.set({"professional": {"photoUrl": photo_url}}, merge=True)

    def update_professional_profile(self, uid: str, data: dict):
        """
        Actualiza parcial el subdocumento professional con los campos dados.
        Ej: {"purpose": "...", "level": "Licenciatura", "state": "Jalisco", ...}
        """
        doc_ref = self.db.collection("users").document(uid)
        # anidar dentro de 'professional'
        payload = {"professional": {}}
        for k, v in data.items():
            payload["professional"][k] = v
        doc_ref.set(payload, merge=True)



    # ---------- DIAGNÓSTICOS ----------
    def diagnostics_collection(self, uid: str):
        return self.db.collection("users").document(uid).collection("diagnostics")

    def add_diagnostic(self, uid: str, data: dict) -> str:
        doc = {**data, "createdAt": admin_fs.SERVER_TIMESTAMP}
        doc_ref = self.diagnostics_collection(uid).add(doc)[1]
        return doc_ref.id

    def update_diagnostic(self, uid: str, diagnostic_id: str, data: dict):
        self.diagnostics_collection(uid).document(diagnostic_id).update(data)

    def list_diagnostics(self, uid: str, limit: int = 30):
        q = self.diagnostics_collection(uid).order_by(
            "createdAt", direction=firestore.Query.DESCENDING
        ).limit(limit)
        return [{**doc.to_dict(), "id": doc.id} for doc in q.stream()]

    # ---------- NOTES ----------
    def notes_collection(self, uid: str):
        return self.db.collection("users").document(uid).collection("notes")

    def add_note(self, uid: str, title: str, content: str) -> str:
        doc = {
            "title": title.strip()[:80] or "Sin título",
            "content": content.strip()[:4000],
            "createdAt": admin_fs.SERVER_TIMESTAMP,
            "updatedAt": admin_fs.SERVER_TIMESTAMP,
        }
        ref = self.notes_collection(uid).add(doc)[1]
        return ref.id

    def update_note(self, uid: str, note_id: str, title: str, content: str):
        self.notes_collection(uid).document(note_id).update({
            "title": (title or "").strip()[:80] or "Sin título",
            "content": (content or "").strip()[:4000],
            "updatedAt": admin_fs.SERVER_TIMESTAMP,
        })

    def delete_note(self, uid: str, note_id: str):
        self.notes_collection(uid).document(note_id).delete()

    def get_note(self, uid: str, note_id: str):
        d = self.notes_collection(uid).document(note_id).get()
        return ({**d.to_dict(), "id": d.id} if d.exists else None)

    def list_notes(self, uid: str, limit: int = 100):
        q = (self.notes_collection(uid)
            .order_by("updatedAt", direction=firestore.Query.DESCENDING)
            .limit(limit))
        return [{**doc.to_dict(), "id": doc.id} for doc in q.stream()]

    # ---------- RECOMMENDATIONS (UNA POR DÍA) ----------
    def recommendation_doc(self, uid: str, date_key: str):
        """Referencia al documento de recomendación de ese día."""
        return self.db.collection("users").document(uid).collection("recommendations").document(date_key)

    def upsert_recommendation_for_date(self, uid: str, date_key: str, text: str, meta: dict | None = None):
        """Guarda o reemplaza la recomendación del día actual."""
        payload = {
            "date": date_key,
            "text": (text or "").strip(),
            "meta": meta or {},
            "updatedAt": admin_fs.SERVER_TIMESTAMP,
            "createdAt": admin_fs.SERVER_TIMESTAMP,
        }
        self.recommendation_doc(uid, date_key).set(payload, merge=False)

    def get_recommendation_for_date(self, uid: str, date_key: str):
        """Obtiene la recomendación de un día específico."""
        doc = self.recommendation_doc(uid, date_key).get()
        return ({**doc.to_dict(), "id": doc.id} if doc.exists else None)

    def list_recommendations(self, uid: str, limit: int = 60):
        """Lista el historial de recomendaciones, ordenadas por fecha descendente."""
        q = (self.db.collection("users")
            .document(uid)
            .collection("recommendations")
            .order_by("date", direction=firestore.Query.DESCENDING)
            .limit(limit))
        return [{**d.to_dict(), "id": d.id} for d in q.stream()]

    def delete_recommendation(self, uid: str, date_key: str):
        """Elimina una recomendación de un día específico."""
        self.recommendation_doc(uid, date_key).delete()

    def delete_recommendations_all(self, uid: str):
        """Borra todas las recomendaciones del usuario (uso administrativo)."""
        batch = self.db.batch()
        for d in self.db.collection("users").document(uid).collection("recommendations").stream():
            batch.delete(d.reference)
        batch.commit()
