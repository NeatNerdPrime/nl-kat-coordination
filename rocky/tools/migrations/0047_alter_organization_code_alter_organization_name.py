# Generated by Django 5.1.10 on 2025-07-11 11:06

from django.db import migrations, models

import tools.fields


class Migration(migrations.Migration):
    dependencies = [("tools", "0046_alter_organization_options")]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="code",
            field=tools.fields.LowerCaseSlugField(
                allow_unicode=True,
                help_text="A short code containing only lower-case unicode letters, numbers, hyphens or underscores that will be used in URLs and paths.",
                max_length=32,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="name",
            field=models.CharField(help_text="The name of the organization.", max_length=126, unique=True),
        ),
    ]
