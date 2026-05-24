from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_high_risk_case_requires_approval() -> None:
    response = client.post(
        "/cases",
        json={
            "customer_id": "cust_123",
            "case_type": "fraud",
            "summary": "Customer reports unauthorized card dispute after stolen device.",
            "amount": 1200.0,
            "currency": "USD",
            "channel": "mobile",
            "metadata": {"merchant": "EXAMPLE STORE"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "awaiting_approval"
    assert body["recommendation"]["requires_human_approval"] is True
    assert body["evidence"]
    assert {finding["agent"] for finding in body["findings"]} == {
        "fraud_investigator",
        "complaints_specialist",
    }


def test_approval_closes_human_gate() -> None:
    created = client.post(
        "/cases",
        json={
            "customer_id": "cust_456",
            "case_type": "mixed",
            "summary": "Complaint about unauthorized transactions causing customer harm.",
            "amount": 850.0,
            "currency": "USD",
            "channel": "web",
            "metadata": {},
        },
    ).json()

    response = client.post(
        f"/cases/{created['id']}/approval",
        json={
            "approved": True,
            "reviewer": "ops.lead@example.com",
            "notes": "Evidence supports remediation and escalation.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["approval"]["approved"] is True


def test_get_missing_case_returns_404() -> None:
    response = client.get("/cases/not-a-real-case")

    assert response.status_code == 404
