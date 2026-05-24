# Generated for the initial Django REST platform scaffold.

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="InvestigationCase",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("customer_id", models.CharField(db_index=True, max_length=128)),
                ("case_type", models.CharField(choices=[("fraud", "Fraud"), ("complaint", "Complaint"), ("mixed", "Mixed")], db_index=True, max_length=32)),
                ("summary", models.TextField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("channel", models.CharField(default="unknown", max_length=64)),
                ("status", models.CharField(choices=[("received", "Received"), ("investigating", "Investigating"), ("awaiting_approval", "Awaiting Approval"), ("approved", "Approved"), ("rejected", "Rejected"), ("closed", "Closed")], db_index=True, default="received", max_length=32)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("risk_score", models.PositiveSmallIntegerField(default=0)),
                ("recommended_action", models.CharField(blank=True, choices=[("approve_refund", "Approve Refund"), ("deny_claim", "Deny Claim"), ("escalate", "Escalate"), ("request_more_information", "Request More Information")], max_length=64)),
                ("recommendation_rationale", models.TextField(blank=True)),
                ("requires_human_approval", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="KnowledgeDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(db_index=True, max_length=256)),
                ("title", models.CharField(max_length=512)),
                ("content", models.TextField()),
                ("embedding", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor", models.CharField(db_index=True, default="system", max_length=256)),
                ("action", models.CharField(db_index=True, max_length=128)),
                ("resource_type", models.CharField(db_index=True, max_length=64)),
                ("resource_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="EvidenceDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(max_length=256)),
                ("title", models.CharField(max_length=512)),
                ("content", models.TextField()),
                ("score", models.FloatField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("case", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evidence", to="investigations.investigationcase")),
            ],
            options={"ordering": ["-score", "title"]},
        ),
        migrations.CreateModel(
            name="AgentFinding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("agent", models.CharField(max_length=128)),
                ("risk_score", models.PositiveSmallIntegerField(default=0)),
                ("summary", models.TextField()),
                ("signals", models.JSONField(blank=True, default=list)),
                ("explanation", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("case", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="findings", to="investigations.investigationcase")),
            ],
        ),
        migrations.CreateModel(
            name="ApprovalDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("approved", models.BooleanField()),
                ("reviewer", models.CharField(max_length=256)),
                ("notes", models.TextField()),
                ("decided_at", models.DateTimeField(auto_now_add=True)),
                ("case", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="approval", to="investigations.investigationcase")),
            ],
        ),
        migrations.AddIndex(model_name="knowledgedocument", index=models.Index(fields=["source"], name="investigat_source_5c310e_idx")),
    ]
