from io import StringIO

from alembic import command
from alembic.config import Config


def test_alembic_offline_upgrade_renders_phase_1_5_hardening() -> None:
    output = StringIO()
    config = Config("alembic.ini", output_buffer=output)

    command.upgrade(config, "head", sql=True)

    rendered_sql = output.getvalue()
    assert "0002_phase_1_5_hardening" in rendered_sql
    assert "ON DELETE CASCADE" in rendered_sql
    assert "ck_transaction_uploads_row_counts" in rendered_sql
    assert "ck_transactions_currency_length" in rendered_sql
