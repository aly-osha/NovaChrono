"""
Close compliance gap G-1 (schema §1, SRS FR-3): users.email must be
VARCHAR(255) UNIQUE NOT NULL.

AbstractUser inherits `email` as unique=False, so nothing stopped two
accounts from sharing an address. Registration blocked duplicates in
RegisterForm.clean_email, but the profile-edit form did not, and the
database itself did not.

This adds the UNIQUE constraint at the storage layer (the real fix — forms
are only advisory) and widens the column to the documented VARCHAR(255).

Existing rows were checked before this migration ran: no duplicate and no
blank emails, so the constraint applies cleanly.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_alter_user_is_active"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                max_length=255, unique=True, verbose_name="email address"
            ),
        ),
    ]
