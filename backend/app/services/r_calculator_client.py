"""
HTTP client for the r-calculator Plumber service.

The r-calculator service lives on the internal Docker network.
FastAPI never exposes it to the outside world.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

R_CALCULATOR_URL = os.getenv("R_CALCULATOR_URL", "http://r-calculator:8000")
FIT_TIMEOUT_SECONDS = 60.0


class RCalculatorClient:
    """Thin httpx wrapper around the R/Plumber curve fitting service."""

    def __init__(self, base_url: str = R_CALCULATOR_URL) -> None:
        self._base_url = base_url

    def health(self) -> Dict[str, Any]:
        try:
            resp = httpx.get(f"{self._base_url}/health", timeout=5.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"R calculator service unavailable: {exc}",
            )

    def fit(
        self,
        compounds: List[Dict[str, Any]],
        config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        POST /fit to the R service. Synchronous — blocks until all compounds are fitted.

        Args:
            compounds: List of compound dicts, each with:
                sample_id, points ([{conc, response, point_id}]),
                model ("4PL"), constraints (optional)
            config: Dict with r_squared_threshold, inactive_threshold, concentration_unit

        Returns:
            List of fit result dicts from R.

        Raises:
            HTTPException 503 on R service down or timeout.
        """
        payload = {"compounds": compounds, "config": config}
        logger.info(
            "Sending fit request to R service",
            extra={"compound_count": len(compounds), "url": self._base_url},
        )
        try:
            resp = httpx.post(
                f"{self._base_url}/fit",
                json=payload,
                timeout=FIT_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning(
                "R service fit timed out",
                extra={"timeout_s": FIT_TIMEOUT_SECONDS, "compound_count": len(compounds)},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Curve fitting timed out. Try with fewer compounds or re-try later.",
            )
        except httpx.ConnectError as exc:
            logger.error("R service connection failed", extra={"error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Calculation service is unavailable. Contact your administrator.",
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "R service returned error status",
                extra={"status_code": exc.response.status_code},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Calculation service error: {exc.response.status_code}",
            )

        results = resp.json()
        logger.info(
            "R service fit complete",
            extra={
                "total": len(results),
                "succeeded": sum(1 for r in results if r.get("success")),
                "failed": sum(1 for r in results if not r.get("success")),
            },
        )
        return results

    def full_svg(
        self,
        points: List[Dict[str, Any]],
        model: str,
        excluded_point_ids: List[str],
        x_label: str,
        y_label: str,
        title: str,
    ) -> str:
        """POST /svg/full — returns a full-size SVG string for PDF export."""
        payload = {
            "points": points,
            "model": model,
            "excluded_point_ids": excluded_point_ids,
            "x_label": x_label,
            "y_label": y_label,
            "title": title,
        }
        try:
            resp = httpx.post(
                f"{self._base_url}/svg/full",
                json=payload,
                timeout=30.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"SVG generation failed: {exc}",
            )
        return resp.json()["svg"]
