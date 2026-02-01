import os
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

config = context.config
fileConfig(config.config_file_name)

def run_migrations_offline():
    url = os.getenv("HYPERCODE_DB_URL")
    context.configure(url=url, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    conf = config.get_section(config.config_ini_section)
    conf["sqlalchemy.url"] = os.getenv("HYPERCODE_DB_URL")
    connectable = engine_from_config(conf, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
