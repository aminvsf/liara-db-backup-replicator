import sys

from config import config
from liara.exceptions import LiaraAPIError
from respositories import DatabaseRepository
from services import Replicator
from utilities.logger import logger


def main():
    logger.info("Starting Liara DB Backup Replicator...")

    try:
        databases = DatabaseRepository().list()
    except LiaraAPIError as exc:
        logger.error("Failed to fetch databases from the Liara API: %s", exc.message)
        sys.exit(1)

    target_databases = []
    if target_database_names := config.liara.target_databases:
        for target_database_name in target_database_names:
            try:
                target_databases.append(
                    next(d for d in databases if d.name == target_database_name)
                )
            except StopIteration:
                log_msg = "Database '%s' not found in your Liara account."
                if not config.liara.team_id:
                    log_msg += " Did you forget to set 'liara.team_id' in your 'config.toml' file?"
                logger.error(log_msg, target_database_name)
                sys.exit(1)
    elif databases:
        target_databases = databases
    else:
        log_msg = "No databases found in your Liara account."
        if not config.liara.team_id:
            log_msg += (
                " Did you forget to set 'liara.team_id' in your 'config.toml' file?"
            )
        logger.info(log_msg)
        sys.exit(0)
    logger.info(
        "Target database(s) for replication: %s",
        ", ".join(d.name for d in target_databases),
    )

    for database in target_databases:
        Replicator(database).run()

    logger.info("Database backup replication process finished.")


if __name__ == "__main__":
    main()
