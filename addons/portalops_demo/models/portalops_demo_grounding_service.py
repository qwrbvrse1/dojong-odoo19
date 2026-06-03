import json
import logging
import urllib.error
import urllib.request

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_RESOLVE_NAMES_URL = "https://mapstools.googleapis.com/v1alpha:resolveNames"
_PLACES_DETAILS_URL = "https://places.googleapis.com/v1/{place_name}"


class PortalOpsDemoGroundingService(models.AbstractModel):
    _name = "portalops.demo.grounding.service"
    _description = "PortalOps Demo Grounding Service"

    def _get_api_key(self):
        return self.env["ir.config_parameter"].sudo().get_str(
            "portalops_demo.google_maps_grounding_api_key",
            "",
        )

    def _build_query_text(self, location):
        parts = [
            location.address_line or "",
            location.city or "",
            location.state_code or "",
            location.postal_code or "",
            location.country_code or "",
        ]
        text = ", ".join(part for part in parts if part)
        return text or location.name

    def _extract_place_payload(self, payload):
        if not isinstance(payload, dict):
            return {}

        results = payload.get("results") or []
        if not results or not isinstance(results[0], dict):
            return {}

        entity = results[0].get("entity") or {}
        google_maps_links = entity.get("googleMapsLinks") or {}
        location = entity.get("location") or {}
        plus_code = entity.get("plusCode") or {}
        place_resource = entity.get("place") or ""

        place_id = entity.get("id") or entity.get("placeId") or ""
        place_url = google_maps_links.get("placeUrl") or entity.get("googleMapsUri") or ""
        latitude = location.get("latitude")
        longitude = location.get("longitude")
        global_code = plus_code.get("globalCode") or plus_code.get("global_code") or ""

        return {
            "place_id": place_id,
            "place_url": place_url,
            "latitude": latitude,
            "longitude": longitude,
            "plus_code": global_code,
            "confidence": (results[0].get("confidence") or "").lower(),
            "raw_entity": entity,
            "place_resource": place_resource,
        }

    def _fetch_place_details(self, api_key, place_resource):
        if not place_resource:
            return {}

        request_obj = urllib.request.Request(
            _PLACES_DETAILS_URL.format(place_name=place_resource),
            headers={
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "id,location,googleMapsUri,plusCode",
                "Accept": "application/json",
            },
            method="GET",
        )
        with urllib.request.urlopen(request_obj, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        location = payload.get("location") or {}
        plus_code = payload.get("plusCode") or {}
        return {
            "place_id": payload.get("id") or "",
            "place_url": payload.get("googleMapsUri") or "",
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "plus_code": plus_code.get("globalCode") or "",
        }

    def resolve_location(self, location):
        location.ensure_one()
        api_key = self._get_api_key()
        if not api_key:
            location.write(
                {
                    "grounding_status": "not_configured",
                    "grounding_last_error": "Missing Maps Grounding Lite API key.",
                }
            )
            return {"ok": False, "error": "missing_api_key"}

        query_text = self._build_query_text(location)
        body = json.dumps(
            {
                "queries": [{"text": query_text}],
                "regionCode": location.country_code or "US",
            }
        ).encode("utf-8")

        headers = {
            "X-Goog-Api-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        request_obj = urllib.request.Request(
            _RESOLVE_NAMES_URL,
            data=body,
            headers=headers,
            method="POST",
        )

        location.write({"grounding_status": "pending", "grounding_last_error": False})

        try:
            with urllib.request.urlopen(request_obj, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            message = f"Grounding request failed with HTTP {exc.code}: {detail}"
            _logger.warning(message)
            location.write(
                {
                    "grounding_status": "failed",
                    "grounding_last_error": message,
                }
            )
            return {"ok": False, "error": "http_error", "detail": message}
        except urllib.error.URLError as exc:
            message = f"Grounding request failed: {exc.reason}"
            _logger.warning(message)
            location.write(
                {
                    "grounding_status": "failed",
                    "grounding_last_error": message,
                }
            )
            return {"ok": False, "error": "network_error", "detail": message}

        extracted = self._extract_place_payload(payload)
        if extracted.get("place_resource") and (
            not extracted.get("place_id")
            or extracted.get("latitude") is None
            or extracted.get("longitude") is None
            or not extracted.get("place_url")
        ):
            try:
                place_details = self._fetch_place_details(api_key, extracted["place_resource"])
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                message = f"Place details request failed with HTTP {exc.code}: {detail}"
                _logger.warning(message)
                location.write(
                    {
                        "grounding_status": "failed",
                        "grounding_last_error": message,
                    }
                )
                return {"ok": False, "error": "place_details_http_error", "detail": message}
            except urllib.error.URLError as exc:
                message = f"Place details request failed: {exc.reason}"
                _logger.warning(message)
                location.write(
                    {
                        "grounding_status": "failed",
                        "grounding_last_error": message,
                    }
                )
                return {"ok": False, "error": "place_details_network_error", "detail": message}

            extracted.update({k: v for k, v in place_details.items() if v not in (None, "")})

        if not extracted.get("place_id") or extracted.get("latitude") is None or extracted.get("longitude") is None or not extracted.get("place_url"):
            location.write(
                {
                    "grounding_status": "failed",
                    "grounding_last_error": "Grounding response did not include a stable place match.",
                }
            )
            return {"ok": False, "error": "no_match", "payload": payload}

        location.write(
            {
                "google_place_id": extracted["place_id"],
                "google_maps_place_url": extracted["place_url"],
                "latitude": extracted["latitude"],
                "longitude": extracted["longitude"],
                "plus_code": extracted["plus_code"],
                "grounding_status": "resolved",
                "grounding_last_error": False,
                "grounding_last_resolved_at": fields.Datetime.now(),
            }
        )
        return {"ok": True, "payload": extracted}

    def resolve_location_by_slug(self, slug):
        location = self.env["portalops.demo.location"].sudo().search([("slug", "=", slug)], limit=1)
        if not location:
            raise UserError(f"Unknown PortalOps demo location slug: {slug}")
        return self.resolve_location(location)
