# Generated by Django 3.1.13 on 2021-07-02 15:37

from django.db import migrations, models
import django.db.models.deletion
import nautobot.extras.models.customfields
import nautobot.extras.utils
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0008_jobresult__custom_field_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="ComputedField",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("created", models.DateField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("label", models.CharField(max_length=100)),
                ("description", models.CharField(blank=True, max_length=200)),
                ("template", models.TextField(max_length=500)),
                ("fallback_value", models.CharField(max_length=500)),
                ("weight", models.PositiveSmallIntegerField(default=100)),
                (
                    "content_type",
                    models.ForeignKey(
                        limit_choices_to=nautobot.extras.utils.FeatureQuery("custom_fields"),
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "ordering": ["weight", "slug"],
                "unique_together": {("content_type", "label")},
            },
            managers=[
                ("objects", nautobot.extras.models.customfields.ComputedFieldManager()),
            ],
        ),
    ]
