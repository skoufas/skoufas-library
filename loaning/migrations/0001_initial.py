# Generated by Django 4.1.7 on 2023-02-18 16:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("books", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("first_name", models.CharField(max_length=200, verbose_name="first name")),
                ("middle_name", models.CharField(max_length=200, null=True, verbose_name="middle name")),
                ("surname", models.CharField(max_length=200, verbose_name="surname")),
                ("id_number", models.CharField(max_length=200, verbose_name="id number")),
                ("id_type", models.CharField(max_length=200, verbose_name="id type")),
                ("phone_number", models.CharField(max_length=200, verbose_name="phone number")),
                ("email", models.CharField(max_length=200, verbose_name="email")),
                ("address", models.CharField(max_length=200, verbose_name="address")),
            ],
            options={
                "verbose_name": "Customer",
                "verbose_name_plural": "Customers",
                "ordering": ["surname", "middle_name", "first_name"],
            },
        ),
        migrations.CreateModel(
            name="Loan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start", models.DateField(verbose_name="start")),
                ("expected_end", models.DateField(verbose_name="expected end")),
                ("end", models.DateField(blank=True, verbose_name="end")),
                ("note", models.CharField(blank=True, max_length=4096, verbose_name="note")),
                (
                    "customer",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="loaning.customer",
                        verbose_name="customer",
                    ),
                ),
                (
                    "entry_number",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="books.entrynumber", verbose_name="Entry number"
                    ),
                ),
            ],
            options={
                "verbose_name": "Loan",
                "verbose_name_plural": "Loans",
                "ordering": ["end", "expected_end", "entry_number", "customer"],
            },
        ),
        migrations.AddConstraint(
            model_name="customer",
            constraint=models.UniqueConstraint(
                fields=("surname", "middle_name", "first_name", "phone_number"), name="unique_name_and_number"
            ),
        ),
        migrations.AddConstraint(
            model_name="customer",
            constraint=models.UniqueConstraint(fields=("id_type", "id_number"), name="unique_id_document"),
        ),
        migrations.AddConstraint(
            model_name="loan",
            constraint=models.UniqueConstraint(
                fields=("customer", "entry_number", "start"), name="unique_custome_entry_number_start"
            ),
        ),
    ]
