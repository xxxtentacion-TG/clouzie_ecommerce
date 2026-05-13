import random
import string
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def generate_referral_codes(apps, schema_editor):
    """Backfill unique referral codes for all existing users."""
    CustomUser = apps.get_model('accounts', 'CustomUser')
    chars = string.ascii_uppercase + string.digits
    existing_codes = set(
        CustomUser.objects.exclude(referral_code='')
        .values_list('referral_code', flat=True)
    )
    for user in CustomUser.objects.filter(referral_code=''):
        while True:
            code = ''.join(random.choices(chars, k=8))
            if code not in existing_codes:
                existing_codes.add(code)
                user.referral_code = code
                user.save(update_fields=['referral_code'])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_customuser_is_admin_user'),
    ]

    operations = [
        # Step 1: Add field WITHOUT unique constraint so existing rows can be empty
        migrations.AddField(
            model_name='customuser',
            name='referral_code',
            field=models.CharField(blank=True, max_length=20, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customuser',
            name='referral_reward_given',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='customuser',
            name='referred_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='referrals',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # Step 2: Populate unique codes for all existing users
        migrations.RunPython(generate_referral_codes, migrations.RunPython.noop),

        # Step 3: Now it's safe to add the unique constraint
        migrations.AlterField(
            model_name='customuser',
            name='referral_code',
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
    ]
