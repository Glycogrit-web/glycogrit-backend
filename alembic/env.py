"""
Alembic Environment Configuration
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import Base and all models
from app.core.database import Base
from app.core.config import settings

# Import all models so Alembic can detect them
from app.models import User, Event, EventActivity, Registration, Payment, UserActivityLog
from app.models.strava_connection import StravaConnection
from app.models.activity_progress import ActivityProgress
from app.models.user_reward import UserReward

# Import DDD module models
# from app.modules.users.domain.user import User as UserDDD  # Commented out - file doesn't exist
# from app.modules.activities.domain.activity import UserActivityLog as ActivityDDD  # Commented out - file doesn't exist
# from app.modules.activities.domain.activity_progress import ActivityProgress as ProgressDDD  # Commented out - file doesn't exist
from app.modules.registrations.domain.registration import Registration as RegistrationDDD
from app.modules.registrations.domain.event_registration_tier import EventRegistrationTier
from app.modules.registrations.domain.registration_tier import RegistrationTier
from app.modules.events.domain.event import Event as EventDDD, EventActivity as EventActivityDDD
from app.modules.payments.domain.payment import Payment as PaymentDDD
from app.modules.payments.domain.payment_link import PaymentLink
from app.modules.payments.domain.settlement import Settlement, PaymentSettlement
# from app.modules.payments.domain.webhook_event import WebhookEvent as PaymentWebhook  # Wrong import path
from app.modules.fitness_trackers.domain.connection import FitnessConnection
# from app.modules.certificates.domain.certificate import UserReward  # Duplicate table - using app.models.user_reward.UserReward instead
from app.modules.gallery.domain.photo import GalleryPhoto
from app.modules.webhooks.domain.webhook_event import WebhookEvent
# from app.modules.shipping.domain.shiprocket_order import ShiprocketOrder  # File doesn't exist
from app.modules.coupons.domain.coupon import Coupon  # Added missing import

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with environment variable
config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
