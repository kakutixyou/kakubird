"""Download ZIP archives created by ProjectBuildService."""

from __future__ import annotations

import logging
import os
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Any, Optional, Sequence

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


logger = logging.getLogger(__name__)

ZIP_MEDIA_TYPE = "application/zip"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ZIP_ROOT = PROJECT_ROOT / "generated_zips"
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")


class ArchiveLookupError(ValueError):
    """Base error for an archive request that must not be served."""


class InvalidArchiveNameError(ArchiveLookupError):
    """Raised when a request does not contain one safe ZIP basename."""


class ArchiveNotFoundError(ArchiveLookupError):
    """Raised when a safe archive name does not resolve to a readable ZIP."""


def resolve_configured_zip_root(zip_root: Optional[str] = None) -> Path:
    """Use one absolute ZIP root shared with ProjectBuildService."""

    configured = (
        zip_root
        or os.getenv("PROJECT_ZIP_OUTPUT_ROOT")
        or str(DEFAULT_ZIP_ROOT)
    )
    return Path(configured).expanduser().resolve()


class ProjectArchiveStore:
    """Resolve generated archives without allowing access outside one root."""

    def __init__(
        self,
        zip_root: Optional[str] = None,
        *,
        max_archive_bytes: int = 1024 * 1024 * 1024,
        verify_zip: bool = True,
    ) -> None:
        raw_root = resolve_configured_zip_root(zip_root)
        if raw_root.is_symlink():
            raise ValueError("ZIP保存先にシンボリックリンクは使用できません。")

        self.zip_root = raw_root
        self.max_archive_bytes = max(1, int(max_archive_bytes))
        self.verify_zip = bool(verify_zip)

    def resolve(self, archive_name: str) -> Path:
        """Return a safe archive path or raise a lookup error."""

        safe_name = self.validate_name(archive_name)

        logger.info(
            "Project ZIP lookup archive=%s zip_root=%s",
            safe_name,
            self.zip_root,
        )

        if not self.zip_root.is_dir() or self.zip_root.is_symlink():
            logger.warning("Project ZIP root is unavailable: %s", self.zip_root)
            raise ArchiveNotFoundError("ZIPファイルが見つかりません。")

        candidate = self.zip_root / safe_name
        if candidate.is_symlink():
            raise ArchiveNotFoundError("ZIPファイルが見つかりません。")

        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(self.zip_root)
        except (OSError, ValueError) as exc:
            logger.warning("Project ZIP was not found: %s", candidate)
            raise ArchiveNotFoundError("ZIPファイルが見つかりません。") from exc

        if not resolved.is_file() or resolved.suffix.casefold() != ".zip":
            raise ArchiveNotFoundError("ZIPファイルが見つかりません。")

        try:
            size = resolved.stat().st_size
        except OSError as exc:
            raise ArchiveNotFoundError("ZIPファイルが見つかりません。") from exc

        if size <= 0 or size > self.max_archive_bytes:
            raise ArchiveNotFoundError("ZIPファイルをダウンロードできません。")

        if self.verify_zip and not zipfile.is_zipfile(resolved):
            raise ArchiveNotFoundError("ZIPファイルをダウンロードできません。")

        logger.info(
            "Project ZIP download ready archive=%s bytes=%s",
            safe_name,
            size,
        )
        return resolved

    @staticmethod
    def validate_name(archive_name: str) -> str:
        """Validate, but never rewrite, a URL-provided filename."""

        name = str(archive_name or "").strip()
        if (
            not name
            or len(name) > 160
            or name != unicodedata.normalize("NFKC", name)
            or name.startswith(".")
            or not name.casefold().endswith(".zip")
            or name.casefold() == ".zip"
            or name != Path(name).name
            or "/" in name
            or "\\" in name
            or ".." in name
            or _CONTROL_CHARACTER.search(name)
        ):
            raise InvalidArchiveNameError("ZIPファイル名が不正です。")
        return name


def create_project_download_router(
    zip_root: Optional[str] = None,
    *,
    dependencies: Optional[Sequence[Any]] = None,
    max_archive_bytes: int = 1024 * 1024 * 1024,
    verify_zip: bool = True,
) -> APIRouter:
    """Create the generated-project download router."""

    store = ProjectArchiveStore(
        zip_root,
        max_archive_bytes=max_archive_bytes,
        verify_zip=verify_zip,
    )

    logger.info("Project ZIP download root: %s", store.zip_root)

    project_router = APIRouter(
        prefix="/api/projects",
        tags=["projects"],
        dependencies=list(dependencies or []),
    )

    @project_router.get(
        "/download/{archive_name}",
        response_class=FileResponse,
        summary="生成済みプロジェクトZIPをダウンロード",
        responses={
            400: {"description": "不正なZIPファイル名"},
            404: {"description": "ZIPファイルが存在しない、または配信できない"},
        },
    )
    def download_project_archive(archive_name: str) -> FileResponse:
        try:
            archive_path = store.resolve(archive_name)
        except InvalidArchiveNameError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ArchiveNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return FileResponse(
            path=str(archive_path),
            media_type=ZIP_MEDIA_TYPE,
            filename=archive_path.name,
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    return project_router


router = create_project_download_router()


__all__ = [
    "ArchiveLookupError",
    "ArchiveNotFoundError",
    "InvalidArchiveNameError",
    "ProjectArchiveStore",
    "create_project_download_router",
    "resolve_configured_zip_root",
    "router",
]
