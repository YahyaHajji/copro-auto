from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


class LicenseApiError(RuntimeError):
    def __init__(self, message: str, code: str = "api_error") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ActivationResponse:
    token: str
    activation_secret: str


class LicenseApiClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, endpoint: str, payload: dict) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8")).get("detail", {})
            except (json.JSONDecodeError, UnicodeDecodeError):
                detail = {}
            if isinstance(detail, dict):
                raise LicenseApiError(str(detail.get("message", "Activation refusée.")), str(detail.get("code", "http_error"))) from exc
            raise LicenseApiError(str(detail or "Activation refusée."), "http_error") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LicenseApiError("Serveur de licence inaccessible. Vérifiez la connexion Internet.", "network_error") from exc
        if not isinstance(data, dict):
            raise LicenseApiError("Réponse invalide du serveur de licence.")
        return data

    def activate(
        self, license_key: str, device_hash: str, device_label: str, app_version: str,
        *, metadata: dict[str, str] | None = None,
    ) -> ActivationResponse:
        payload = {
            "license_key": license_key.strip(), "device_hash": device_hash,
            "device_label": device_label, "app_version": app_version,
        }
        payload.update(metadata or {})
        data = self._post("/v1/activate", payload)
        return ActivationResponse(token=str(data["token"]), activation_secret=str(data["activation_secret"]))

    def refresh(
        self, activation_id: str, activation_secret: str, device_hash: str, app_version: str,
        *, metadata: dict[str, str] | None = None,
    ) -> str:
        payload = {
            "activation_id": activation_id, "activation_secret": activation_secret,
            "device_hash": device_hash, "app_version": app_version,
        }
        payload.update(metadata or {})
        data = self._post("/v1/refresh", payload)
        return str(data["token"])

    def deactivate(self, activation_id: str, activation_secret: str) -> None:
        self._post("/v1/deactivate", {"activation_id": activation_id, "activation_secret": activation_secret})

    def status(self, activation_id: str, activation_secret: str) -> dict:
        return self._post("/v1/status", {"activation_id": activation_id, "activation_secret": activation_secret})
