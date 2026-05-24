import pytest
from rest_framework.test import APIClient

from investigations.models import InvestigationCase


@pytest.mark.django_db
def test_create_high_risk_case_requires_approval() -> None:
    client = APIClient()
    response = client.post(
        "/api/cases/",
        {
            "customer_id": "cust_123",
            "case_type": "fraud",
            "summary": "Customer reports unauthorized card dispute after stolen device.",
            "amount": "1200.00",
            "currency": "USD",
            "channel": "mobile",
            "metadata": {"merchant": "EXAMPLE STORE", "device_mismatch": True},
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == InvestigationCase.Status.AWAITING_APPROVAL
    assert body["requires_human_approval"] is True
    assert body["evidence"]
    assert {finding["agent"] for finding in body["findings"]} == {
        "fraud_investigator",
        "complaints_specialist",
    }


@pytest.mark.django_db
def test_approval_closes_human_gate() -> None:
    client = APIClient()
    created = client.post(
        "/api/cases/",
        {
            "customer_id": "cust_456",
            "case_type": "mixed",
            "summary": "Complaint about unauthorized transactions causing customer harm.",
            "amount": "850.00",
            "currency": "USD",
            "channel": "web",
            "metadata": {},
        },
        format="json",
    ).json()

    response = client.post(
        f"/api/cases/{created['id']}/approval/",
        {
            "approved": True,
            "reviewer": "ops.lead@example.com",
            "notes": "Evidence supports remediation and escalation.",
        },
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == InvestigationCase.Status.APPROVED
    assert body["approval"]["approved"] is True


@pytest.mark.django_db
def test_get_missing_case_returns_404() -> None:
    client = APIClient()
    response = client.get("/api/cases/00000000-0000-0000-0000-000000000000/")

    assert response.status_code == 404
