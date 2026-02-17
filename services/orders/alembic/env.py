import os
from logging.config import fileConfig

from alembic import context

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.config import settings as app_settings
from app.database import Base

target_metadata = Base.metadata

# Ensure sqlalchemy.url is set (allow alembic to read from config or environment)
sqlalchemy_url = config.get_main_option("sqlalchemy.url")
if not sqlalchemy_url:
    sqlalchemy_url = (
        os.environ.get("POSTGRES_ORDERS_URL") or app_settings.postgres_orders_url
    )
    config.set_main_option("sqlalchemy.url", sqlalchemy_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from app.database import engine

    connectable = engine

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
