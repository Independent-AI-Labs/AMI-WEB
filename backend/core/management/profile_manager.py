"""Browser profile management using Chrome's native profile system."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from ...utils.exceptions import ProfileError


class ProfileManager:
    """Manages browser profiles using Chrome's native user-data-dir structure."""

    def __init__(self, base_dir: str = "./data/browser_profiles"):
        self.base_dir = Path(base_dir)
        # Don't create directory in __init__, create it when actually needed

        # Create a metadata file to track profiles
        self.metadata_file = self.base_dir / "profiles.json"
        self.profiles: dict[str, dict[str, Any]] = {}

    def _load_metadata(self) -> dict[str, dict[str, Any]]:
        """Load profile metadata."""
        if self.metadata_file.exists():
            with self.metadata_file.open() as f:
                return json.load(f)
        return {}

    def _save_metadata(self) -> None:
        """Save profile metadata."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with self.metadata_file.open("w") as f:
            json.dump(self.profiles, f, indent=2)

    def _ensure_initialized(self) -> None:
        """Ensure the profile manager is initialized."""
        if not self.profiles and self.metadata_file.exists():
            self.profiles = self._load_metadata()

    def create_profile(self, name: str, description: str = "") -> Path:
        self._ensure_initialized()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        """Create a new browser profile directory."""
        if name in self.profiles:
            raise ProfileError(f"Profile {name} already exists")

        profile_dir = self.base_dir / name
        profile_dir.mkdir(exist_ok=True)

        # Store metadata
        self.profiles[name] = {
            "description": description,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
        }
        self._save_metadata()

        logger.info(f"Created profile {name} at {profile_dir}")
        return profile_dir

    def get_profile_dir(self, name: str) -> Path:
        """Get the directory path for a profile."""
        if name not in self.profiles:
            # Auto-create if doesn't exist
            return self.create_profile(name)

        # Update last used
        self.profiles[name]["last_used"] = datetime.now().isoformat()
        self._save_metadata()

        return self.base_dir / name

    def delete_profile(self, name: str) -> bool:
        """Delete a profile and its data."""
        if name not in self.profiles:
            return False

        profile_dir = self.base_dir / name
        if profile_dir.exists():
            shutil.rmtree(profile_dir)

        del self.profiles[name]
        self._save_metadata()

        logger.info(f"Deleted profile {name}")
        return True

    def list_profiles(self) -> list[dict[str, Any]]:
        """List all profiles."""
        result = []
        for name, metadata in self.profiles.items():
            profile_dir = self.base_dir / name
            result.append(
                {
                    "name": name,
                    "description": metadata.get("description", ""),
                    "created_at": metadata.get("created_at"),
                    "last_used": metadata.get("last_used"),
                    "exists": profile_dir.exists(),
                },
            )
        return result

    def copy_profile(self, source: str, dest: str) -> Path:
        """Copy a profile to a new name."""
        if source not in self.profiles:
            raise ProfileError(f"Source profile {source} not found")
        if dest in self.profiles:
            raise ProfileError(f"Destination profile {dest} already exists")

        source_dir = self.base_dir / source
        dest_dir = self.base_dir / dest

        if source_dir.exists():
            shutil.copytree(source_dir, dest_dir)

        # Copy metadata
        self.profiles[dest] = {
            **self.profiles[source],
            "created_at": datetime.now().isoformat(),
            "description": f"Copy of {source}",
        }
        self._save_metadata()

        logger.info(f"Copied profile {source} to {dest}")
        return dest_dir
