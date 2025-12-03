# -*- coding: utf-8 -*-
"""Database migration management script"""
# pylint: disable=W0401, R0912, R0915, W0614
import asyncio
from alias.server.services.database_service import DatabaseService
from alias.server.models import *  # noqa: F403, F401


async def main():
    """Main CLI interface with improved error handling"""
    import argparse
    import sys
    from loguru import logger

    parser = argparse.ArgumentParser(description="Database Migration Manager")
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
    )

    # Create migration
    create_parser = subparsers.add_parser(
        "create",
        help="Create new migration",
    )
    create_parser.add_argument("message", help="Migration message")
    create_parser.add_argument(
        "--no-autogenerate",
        action="store_true",
        help="Disable autogenerate",
    )

    # Upgrade
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database")
    upgrade_parser.add_argument(
        "--revision",
        default="head",
        required=False,
        help="Target revision (default: head)",
    )
    upgrade_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be upgraded without executing",
    )

    # Downgrade
    downgrade_parser = subparsers.add_parser(
        "downgrade",
        help="Downgrade database",
    )
    downgrade_parser.add_argument(
        "--steps",
        default=1,
        type=int,
        required=False,
        help="Number of steps to downgrade (default: 1)",
    )
    downgrade_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downgraded without executing",
    )

    # Status command
    _ = subparsers.add_parser(
        "status",
        help="Show migration status",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    service = DatabaseService()

    try:
        # Initialize database connection
        await service.init_database()

        if args.command == "create":
            success = await service.create_migration(
                args.message,
                not args.no_autogenerate,
            )
            if success:
                logger.info("✅ Migration created successfully")
            else:
                logger.error("❌ Failed to create migration")
                sys.exit(1)

        elif args.command == "upgrade":
            if args.dry_run:
                logger.info("🔍 Dry run mode - showing what would be upgraded")
                # Here add logic to display migrations that would be executed
                return

            success = await service.upgrade(args.revision)
            if success:
                logger.info("✅ Database upgrade completed successfully")
            else:
                logger.error("❌ Database upgrade failed")
                sys.exit(1)

        elif args.command == "downgrade":
            if args.dry_run:
                logger.info(
                    "🔍 Dry run mode - showing what would be downgraded",
                )
                # Here add logic to display downgrades that would be executed
                return

            success = await service.downgrade(args.steps)
            if success:
                logger.info("✅ Database downgrade completed successfully")
            else:
                logger.error("❌ Database downgrade failed")
                sys.exit(1)

        elif args.command == "status":
            current_revision = (
                await service.migration_manager.get_current_revision()
            )
            if current_revision:
                logger.info(f"Current revision: {current_revision}")
            else:
                logger.warning("No current revision found")

            revisions = service.migration_manager.get_all_revisions()
            if revisions:
                logger.info(f"Total migrations: {len(revisions)}")
                for rev in revisions:
                    logger.info(f"  - {rev['revision']}: {rev['message']}")
            else:
                logger.warning("No migrations found")

    except Exception as e:
        logger.error(f"❌ Migration operation failed: {e}")
        sys.exit(1)
    finally:
        # Ensure database connection is properly closed
        try:
            await service.dispose()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
