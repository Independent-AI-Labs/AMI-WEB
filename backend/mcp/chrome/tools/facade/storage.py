"""Browser storage facade tool for downloads and screenshots."""

from pathlib import Path
from typing import Literal, cast

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse


async def browser_storage_tool(
    manager: ChromeManager,
    action: Literal[
        "list_downloads",
        "clear_downloads",
        "wait_for_download",
        "list_screenshots",
        "clear_screenshots",
        "set_download_behavior",
    ],
    # Instance selection
    instance_id: str | None = None,
    # Download-specific parameters
    filename: str | None = None,
    timeout: int = 30,
    # CDP download behavior parameters
    behavior: str = "allow",  # allow, deny, allowAndName, default
    download_path: str | None = None,
) -> BrowserResponse:
    """Manage downloads and screenshots storage.

    Args:
        manager: Chrome manager instance
        action: Action to perform
        instance_id: Optional browser instance ID
        filename: Filename to wait for (wait_for_download)
        timeout: Timeout in seconds (wait_for_download)
        behavior: Download behavior for CDP (set_download_behavior)
        download_path: Download path for CDP (set_download_behavior)

    Returns:
        BrowserResponse with action-specific data
    """
    logger.debug(f"browser_storage: action={action}, instance_id={instance_id}")

    # Get instance for actions that need it
    instance = None
    if action in {
        "list_downloads",
        "clear_downloads",
        "wait_for_download",
        "set_download_behavior",
    }:
        instance = await manager.get_instance_or_current(instance_id)
        if not instance:
            return BrowserResponse(
                success=False, error="Browser instance not available"
            )

    match action:
        case "list_downloads":
            if not instance:
                return BrowserResponse(
                    success=False, error="Browser instance not available"
                )
            downloads = instance.list_downloads()
            return BrowserResponse(
                success=True, data={"downloads": downloads, "count": len(downloads)}
            )
        case "clear_downloads":
            if not instance:
                return BrowserResponse(
                    success=False, error="Browser instance not available"
                )
            count = instance.clear_downloads()
            return BrowserResponse(success=True, data={"cleared": count})
        case "wait_for_download":
            if not instance:
                return BrowserResponse(
                    success=False, error="Browser instance not available"
                )
            file_path = instance.wait_for_download(filename, timeout)
            if file_path:
                return BrowserResponse(
                    success=True,
                    data={
                        "filepath": str(file_path),
                        "filename": file_path.name,
                        "found": True,
                    },
                )
            return BrowserResponse(
                success=False, error=f"Download not completed within {timeout}s"
            )
        case "set_download_behavior":
            if not instance:
                return BrowserResponse(
                    success=False, error="Browser instance not available"
                )
            if not instance.driver:
                return BrowserResponse(success=False, error="Browser not initialized")
            # Use Chrome DevTools Protocol to set download behavior
            params: dict[str, str] = {"behavior": behavior}
            if download_path:
                params["downloadPath"] = download_path
            try:
                instance.driver.execute_cdp_cmd("Browser.setDownloadBehavior", params)
                return BrowserResponse(
                    success=True, data={"behavior": behavior, "path": download_path}
                )
            except Exception as e:
                logger.error(f"Failed to set download behavior: {e}")
                return BrowserResponse(
                    success=False, error=f"Failed to set download behavior: {e}"
                )
        case "list_screenshots":
            screenshot_dir = Path(
                manager.config.get(
                    "backend.storage.screenshot_dir", "./data/screenshots"
                )
            )
            if not screenshot_dir.exists():
                return BrowserResponse(
                    success=True, data={"screenshots": [], "count": 0}
                )
            screenshots = []
            for file in screenshot_dir.iterdir():
                if file.is_file() and file.suffix in {".png", ".jpg", ".jpeg", ".webp"}:
                    stat = file.stat()
                    screenshots.append(
                        {
                            "name": file.name,
                            "path": str(file),
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                        },
                    )
            # Sort by modified time, most recent first
            screenshots = sorted(
                screenshots, key=lambda x: cast(float, x["modified"]), reverse=True
            )
            return BrowserResponse(
                success=True,
                data={"screenshots": screenshots, "count": len(screenshots)},
            )
        case "clear_screenshots":
            screenshot_dir = Path(
                manager.config.get(
                    "backend.storage.screenshot_dir", "./data/screenshots"
                )
            )
            if not screenshot_dir.exists():
                return BrowserResponse(success=True, data={"cleared": 0})
            count = 0
            for file in screenshot_dir.iterdir():
                if file.is_file() and file.suffix in {".png", ".jpg", ".jpeg", ".webp"}:
                    try:
                        file.unlink()
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete {file}: {e}")
            return BrowserResponse(success=True, data={"cleared": count})
