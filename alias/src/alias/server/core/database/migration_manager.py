# -*- coding: utf-8 -*-
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import re

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from loguru import logger


class MigrationManager:
    def __init__(
        self,
        alembic_config_path: Path,
        script_location: Path,
        db_uri: str,
        engine=None,
    ) -> None:
        self.db_uri = self._convert_db_uri(db_uri)
        self.alembic_cfg = self._create_alembic_config(
            config_path=alembic_config_path,
            script_location=script_location,
            db_uri=self.db_uri,
        )
        self.engine = engine

    def _convert_db_uri(self, uri: str) -> str:
        """Convert database URI to async version"""
        if uri.startswith("postgresql://"):
            return uri.replace("postgresql://", "postgresql+asyncpg://")
        elif uri.startswith("sqlite://"):
            return uri.replace("sqlite://", "sqlite+aiosqlite://")
        return uri

    def _create_alembic_config(
        self,
        config_path: Path,
        script_location: Path,
        db_uri: str,
    ) -> Config:
        if not Path(config_path).exists():
            raise FileNotFoundError(f"Alembic config not found: {config_path}")
        if not Path(script_location).exists():
            raise FileNotFoundError(
                f"Script location not found: {script_location}",
            )

        cfg = Config(str(config_path))
        cfg.set_main_option("script_location", str(script_location))
        cfg.set_main_option("sqlalchemy.url", db_uri)
        return cfg

    def _clean_message(self, message: str) -> str:
        """Clean migration message for filename"""
        clean = "".join(c if c.isalnum() else "_" for c in message)
        clean = "_".join(filter(None, clean.split("_")))
        return clean.lower()

    async def create(self, message: str, autogenerate: bool = True) -> bool:
        try:
            clean_message = self._clean_message(message)
            command.revision(
                self.alembic_cfg,
                message=clean_message,
                autogenerate=autogenerate,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            return False

    async def get_current_revision(self) -> Optional[str]:
        try:
            async with self.engine.connect() as connection:

                def get_revision(sync_conn):
                    context = MigrationContext.configure(sync_conn)
                    return context.get_current_revision()

                return await connection.run_sync(get_revision)

        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None

    async def init_alembic_version(self, revision: str = "head") -> bool:
        try:
            logger.info(f"Stamping database with revision: {revision}")
            async with self.engine.begin() as conn:
                await conn.run_sync(
                    lambda ctx: command.stamp(self.alembic_cfg, revision),
                )
            logger.info("✅ Database stamped successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Database stamp failed: {e}")
            return False

    async def upgrade(self, revision: str = "head") -> bool:
        try:
            logger.info(f"Upgrading database to revision: {revision}")
            async with self.engine.begin() as conn:
                await conn.run_sync(
                    lambda ctx: command.upgrade(self.alembic_cfg, revision),
                )

            current_revision = await self.get_current_revision()
            logger.info(
                f"✅ Database upgrade to {current_revision} "
                f"completed successfully",
            )
            return True
        except Exception as e:
            import traceback

            logger.error(
                f"❌ Database upgrade failed: {e}, "
                f"traceback: {traceback.format_exc()}",
            )
            return False

    def _get_revision_date(self, file_path: str) -> datetime:
        try:
            match = re.match(r"(\d{14})_.+\.py", Path(file_path).name)
            if match:
                date_str = match.group(1)
                return datetime.strptime(date_str, "%Y%m%d%H%M%S")
        except Exception:
            pass
        return datetime.fromtimestamp(0)

    def get_all_revisions(self) -> List[Dict[str, str]]:
        try:
            script_directory = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = []

            for script in script_directory.walk_revisions():
                revisions.append(
                    {
                        "revision": script.revision,
                        "down_revision": script.down_revision,
                        "message": script.doc,
                        "created_date": self._get_revision_date(script.path),
                    },
                )

            revisions.sort(key=lambda x: x["created_date"], reverse=True)
            return revisions
        except Exception as e:
            logger.error(f"Failed to get all revisions: {e}")
            return []

    async def downgrade(self, steps: int = 1) -> bool:
        try:
            current_revision = await self.get_current_revision()
            if not current_revision:
                logger.warning("No current revision found")
                return False

            revisions = self.get_all_revisions()
            if not revisions:
                logger.warning("No revisions found")
                return False

            current_index = next(
                (
                    i
                    for i, rev in enumerate(revisions)
                    if rev["revision"] == current_revision
                ),
                None,
            )

            if current_index is None:
                logger.warning(
                    f"Current revision {current_revision} "
                    f"not found in history",
                )
                return False

            if current_index + steps >= len(revisions):
                target_revision = "base"
            else:
                target_revision = revisions[current_index + steps]["revision"]

            logger.info(
                f"Downgrading database from {current_revision} "
                f"to {target_revision}",
            )
            async with self.engine.begin() as conn:
                await conn.run_sync(
                    lambda ctx: command.downgrade(
                        self.alembic_cfg,
                        target_revision,
                    ),
                )
            logger.info(
                f"✅ Database downgrade {target_revision} "
                f"completed successfully",
            )
            return True

        except Exception as e:
            logger.error(f"❌ Database downgrade failed: {e}")
            return False
