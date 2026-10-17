"""Reagent entry on an experiment template.

The template names the default catalog reagents. Creating an experiment copies
that list onto the entry. It is a prefill, not a limit: on a template experiment
and on an ad hoc experiment the lab tech can record a lot of any active reagent.
Inactive reagents, and expired or QC-rejected lots, stay refused.
"""
import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient


def _login(client, username, password):
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _name(prefix):
    return f"{prefix} {uuid.uuid4().hex[:6]}"


def _reagent(client, headers, **extra):
    body = {"name": _name("Reagent"), "unit": "mL"}
    body.update(extra)
    response = client.post("/v1/reagents", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _lot(client, headers, reagent_id, **extra):
    body = {
        "reagent_id": reagent_id,
        "lot_number": _name("Lot"),
        "expiration_date": str(date.today() + timedelta(days=30)),
        "quantity_received": "10",
        "qc_status": "released",
        "released": True,
        "unit": "mL",
    }
    body.update(extra)
    response = client.post("/v1/reagent-lots", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _template(client, headers, reagent_ids):
    response = client.post(
        "/v1/experiment-templates",
        headers=headers,
        json={
            "name": _name("Reagent tpl"),
            "template_definition": {
                "experiment_name": "Reagent experiment",
                "entries": [
                    {
                        "entry_type": "reagent",
                        "name": "Reagents",
                        "config": {"allowed_reagent_ids": [str(item) for item in reagent_ids]},
                    }
                ],
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _experiment(client, headers, template_id):
    response = client.post(
        "/v1/experiments",
        headers=headers,
        json={"name": _name("Exp"), "experiment_template_id": template_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_update_reagent_entry(client: TestClient, test_admin_user):
    headers = _login(client, "admin", "adminpassword")
    first = _reagent(client, headers)
    second = _reagent(client, headers)
    created = _template(client, headers, [first["id"]])
    entry = created["template_definition"]["entries"][0]
    assert entry["entry_type"] == "reagent"
    assert entry["predefined_entry_key"] == "reagents"
    assert entry["config"]["allowed_reagent_ids"] == [first["id"]]

    updated = client.patch(
        f"/v1/experiment-templates/{created['id']}",
        headers=headers,
        json={
            "template_definition": {
                "experiment_name": "Reagent experiment",
                "entries": [
                    {
                        "entry_type": "reagent",
                        "name": "Reagents",
                        "config": {"allowed_reagent_ids": [second["id"], first["id"]]},
                    }
                ],
            }
        },
    )
    assert updated.status_code == 200, updated.text
    ids = updated.json()["template_definition"]["entries"][0]["config"]["allowed_reagent_ids"]
    assert ids == [second["id"], first["id"]]
    assert updated.json()["template_definition"]["entries"][0]["predefined_entry_key"] == "reagents"


def test_reagent_entry_validation(client: TestClient, test_admin_user):
    headers = _login(client, "admin", "adminpassword")
    active = _reagent(client, headers)
    inactive = _reagent(client, headers)
    retired = client.patch(
        f"/v1/reagents/{inactive['id']}", headers=headers, json={"active": False}
    )
    assert retired.status_code == 200, retired.text

    def post_ids(raw_ids):
        return client.post(
            "/v1/experiment-templates",
            headers=headers,
            json={
                "name": _name("Bad tpl"),
                "template_definition": {
                    "experiment_name": "Bad",
                    "entries": [
                        {
                            "entry_type": "reagent",
                            "name": "Reagents",
                            "config": {"allowed_reagent_ids": raw_ids},
                        }
                    ],
                },
            },
        )

    empty = post_ids([])
    assert empty.status_code == 422
    assert empty.json()["detail"]["code"] == "reagent_entry_invalid"

    unknown = post_ids([str(uuid.uuid4())])
    assert unknown.status_code == 422
    assert unknown.json()["detail"]["code"] == "reagent_entry_invalid"

    retired_on_template = post_ids([inactive["id"]])
    assert retired_on_template.status_code == 422
    assert retired_on_template.json()["detail"]["code"] == "reagent_entry_invalid"

    ok = post_ids([active["id"]])
    assert ok.status_code == 201, ok.text


def test_template_prefills_default_reagents(client: TestClient, test_admin_user):
    headers = _login(client, "admin", "adminpassword")
    first = _reagent(client, headers)
    second = _reagent(client, headers)
    template = _template(client, headers, [first["id"], second["id"]])
    experiment = _experiment(client, headers, template["id"])
    entries = client.get(f"/v1/experiments/{experiment['id']}/entries", headers=headers)
    assert entries.status_code == 200, entries.text
    reagent_entries = [row for row in entries.json()["entries"] if row["entry_type"] == "reagent"]
    assert len(reagent_entries) == 1
    assert reagent_entries[0]["predefined_entry_key"] == "reagents"
    assert reagent_entries[0]["config"]["allowed_reagent_ids"] == [first["id"], second["id"]]


def test_experiment_use_accepts_off_template_active_reagent(client: TestClient, test_admin_user):
    headers = _login(client, "admin", "adminpassword")
    allowed = _reagent(client, headers)
    other = _reagent(client, headers)
    good = _lot(client, headers, allowed["id"])
    expired = _lot(client, headers, allowed["id"])
    rejected = _lot(client, headers, allowed["id"])
    off_template = _lot(client, headers, other["id"])

    patched_exp = client.patch(
        f"/v1/reagent-lots/{expired['id']}",
        headers=headers,
        json={"expiration_date": str(date.today() - timedelta(days=1))},
    )
    assert patched_exp.status_code == 200, patched_exp.text
    patched_rej = client.patch(
        f"/v1/reagent-lots/{rejected['id']}",
        headers=headers,
        json={"qc_status": "rejected"},
    )
    assert patched_rej.status_code == 200, patched_rej.text
    assert patched_rej.json()["released"] is True
    assert patched_rej.json()["qc_status"] == "rejected"

    template = _template(client, headers, [allowed["id"]])
    experiment = _experiment(client, headers, template["id"])
    entries = client.get(
        f"/v1/experiments/{experiment['id']}/entries", headers=headers
    )
    assert entries.status_code == 200, entries.text
    reagent_entries = [row for row in entries.json()["entries"] if row["entry_type"] == "reagent"]
    assert len(reagent_entries) == 1
    assert reagent_entries[0]["config"]["allowed_reagent_ids"] == [allowed["id"]]
    assert reagent_entries[0]["predefined_entry_key"] == "reagents"

    accepted = client.post(
        "/v1/reagent-uses",
        headers=headers,
        json={
            "reagent_lot_id": off_template["id"],
            "experiment_id": experiment["id"],
            "quantity_used": "1",
        },
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["experiment_id"] == experiment["id"]
    assert accepted.json()["reagent_lot_id"] == off_template["id"]
    off_remaining = client.get(f"/v1/reagent-lots/{off_template['id']}", headers=headers)
    assert off_remaining.status_code == 200, off_remaining.text
    assert float(off_remaining.json()["quantity_remaining"]) == 9
    still_defaults = client.get(f"/v1/experiments/{experiment['id']}/entries", headers=headers)
    assert still_defaults.status_code == 200, still_defaults.text
    reagent_entries = [
        row for row in still_defaults.json()["entries"] if row["entry_type"] == "reagent"
    ]
    assert reagent_entries[0]["config"]["allowed_reagent_ids"] == [allowed["id"]]

    expired_use = client.post(
        "/v1/reagent-uses",
        headers=headers,
        json={
            "reagent_lot_id": expired["id"],
            "experiment_id": experiment["id"],
            "quantity_used": "1",
        },
    )
    assert expired_use.status_code == 422
    assert "expired" in expired_use.json()["detail"]

    rejected_use = client.post(
        "/v1/reagent-uses",
        headers=headers,
        json={
            "reagent_lot_id": rejected["id"],
            "experiment_id": experiment["id"],
            "quantity_used": "1",
        },
    )
    assert rejected_use.status_code == 422
    assert "rejected" in rejected_use.json()["detail"]

    recorded = client.post(
        "/v1/reagent-uses",
        headers=headers,
        json={
            "reagent_lot_id": good["id"],
            "experiment_id": experiment["id"],
            "quantity_used": "2",
        },
    )
    assert recorded.status_code == 201, recorded.text
    body = recorded.json()
    assert body["experiment_id"] == experiment["id"]
    assert body["reagent_lot_id"] == good["id"]
    assert float(body["quantity_used"]) == 2


def test_template_edit_leaves_prefilled_reagents(client: TestClient, test_admin_user):
    headers = _login(client, "admin", "adminpassword")
    original = _reagent(client, headers)
    added_later = _reagent(client, headers)
    original_lot = _lot(client, headers, original["id"])
    later_lot = _lot(client, headers, added_later["id"])
    template = _template(client, headers, [original["id"]])
    experiment = _experiment(client, headers, template["id"])

    updated = client.patch(
        f"/v1/experiment-templates/{template['id']}",
        headers=headers,
        json={
            "template_definition": {
                "experiment_name": "Reagent experiment",
                "entries": [
                    {
                        "entry_type": "reagent",
                        "name": "Reagents",
                        "config": {"allowed_reagent_ids": [added_later["id"]]},
                    }
                ],
            }
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["template_definition"]["entries"][0]["config"]["allowed_reagent_ids"] == [
        added_later["id"]
    ]

    entries = client.get(f"/v1/experiments/{experiment['id']}/entries", headers=headers)
    assert entries.status_code == 200, entries.text
    reagent_entries = [row for row in entries.json()["entries"] if row["entry_type"] == "reagent"]
    assert reagent_entries[0]["config"]["allowed_reagent_ids"] == [original["id"]]

    kept = client.post(
        "/v1/reagent-uses",
        headers=headers,
        json={
            "reagent_lot_id": original_lot["id"],
            "experiment_id": experiment["id"],
            "quantity_used": "1",
        },
    )
    assert kept.status_code == 201, kept.text
    added = client.post(
        "/v1/reagent-uses",
        headers=headers,
        json={
            "reagent_lot_id": later_lot["id"],
            "experiment_id": experiment["id"],
            "quantity_used": "1",
        },
    )
    assert added.status_code == 201, added.text
    assert added.json()["reagent_lot_id"] == later_lot["id"]
    later_remaining = client.get(f"/v1/reagent-lots/{later_lot['id']}", headers=headers)
    assert later_remaining.status_code == 200, later_remaining.text
    assert float(later_remaining.json()["quantity_remaining"]) == 9
    unchanged = client.get(f"/v1/experiments/{experiment['id']}/entries", headers=headers)
    assert unchanged.status_code == 200, unchanged.text
    reagent_entries = [row for row in unchanged.json()["entries"] if row["entry_type"] == "reagent"]
    assert reagent_entries[0]["config"]["allowed_reagent_ids"] == [original["id"]]


def _reagent_ids_on(client, headers, experiment_id):
    entries = client.get(f"/v1/experiments/{experiment_id}/entries", headers=headers)
    assert entries.status_code == 200, entries.text
    reagent_entries = [row for row in entries.json()["entries"] if row["entry_type"] == "reagent"]
    return reagent_entries


def test_added_reagent_is_saved_and_reloads_on_template_and_ad_hoc(client: TestClient, test_admin_user):
    headers = _login(client, "admin", "adminpassword")
    default = _reagent(client, headers)
    extra = _reagent(client, headers)
    inactive = _reagent(client, headers)
    retired = client.patch(f"/v1/reagents/{inactive['id']}", headers=headers, json={"active": False})
    assert retired.status_code == 200, retired.text

    template = _template(client, headers, [default["id"]])
    experiment = _experiment(client, headers, template["id"])
    added = client.post(
        f"/v1/experiments/{experiment['id']}/reagents",
        headers=headers,
        json={"reagent_id": extra["id"]},
    )
    assert added.status_code == 201, added.text
    assert added.json()["allowed_reagent_ids"] == [default["id"], extra["id"]]
    reloaded = _reagent_ids_on(client, headers, experiment["id"])
    assert len(reloaded) == 1
    assert reloaded[0]["config"]["allowed_reagent_ids"] == [default["id"], extra["id"]]

    duplicate = client.post(
        f"/v1/experiments/{experiment['id']}/reagents",
        headers=headers,
        json={"reagent_id": extra["id"]},
    )
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["allowed_reagent_ids"] == [default["id"], extra["id"]]
    reloaded = _reagent_ids_on(client, headers, experiment["id"])
    assert reloaded[0]["config"]["allowed_reagent_ids"] == [default["id"], extra["id"]]

    refused = client.post(
        f"/v1/experiments/{experiment['id']}/reagents",
        headers=headers,
        json={"reagent_id": inactive["id"]},
    )
    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "reagent_inactive"
    reloaded = _reagent_ids_on(client, headers, experiment["id"])
    assert reloaded[0]["config"]["allowed_reagent_ids"] == [default["id"], extra["id"]]

    ad_hoc = client.post("/v1/experiments", headers=headers, json={"name": _name("Ad hoc")})
    assert ad_hoc.status_code == 201, ad_hoc.text
    ad_hoc_id = ad_hoc.json()["id"]
    assert _reagent_ids_on(client, headers, ad_hoc_id) == []
    created = client.post(
        f"/v1/experiments/{ad_hoc_id}/reagents",
        headers=headers,
        json={"reagent_id": default["id"]},
    )
    assert created.status_code == 201, created.text
    assert created.json()["allowed_reagent_ids"] == [default["id"]]
    reloaded = _reagent_ids_on(client, headers, ad_hoc_id)
    assert len(reloaded) == 1
    assert reloaded[0]["predefined_entry_key"] == "reagents"
    assert reloaded[0]["config"]["allowed_reagent_ids"] == [default["id"]]

    again = client.post(
        f"/v1/experiments/{ad_hoc_id}/reagents",
        headers=headers,
        json={"reagent_id": default["id"]},
    )
    assert again.status_code == 200, again.text
    assert again.json()["allowed_reagent_ids"] == [default["id"]]
    assert len(_reagent_ids_on(client, headers, ad_hoc_id)) == 1

    blocked = client.post(
        f"/v1/experiments/{ad_hoc_id}/reagents",
        headers=headers,
        json={"reagent_id": inactive["id"]},
    )
    assert blocked.status_code == 422
    assert blocked.json()["detail"]["code"] == "reagent_inactive"
    reloaded = _reagent_ids_on(client, headers, ad_hoc_id)
    assert reloaded[0]["config"]["allowed_reagent_ids"] == [default["id"]]


def test_ad_hoc_experiment_records_active_reagent(client: TestClient, test_admin_user):
    headers = _login(client, "admin", "adminpassword")
    reagent = _reagent(client, headers)
    lot = _lot(client, headers, reagent["id"])
    created = client.post(
        "/v1/experiments",
        headers=headers,
        json={"name": _name("Ad hoc")},
    )
    assert created.status_code == 201, created.text
    experiment = created.json()
    assert experiment.get("experiment_template_id") is None
    entries = client.get(f"/v1/experiments/{experiment['id']}/entries", headers=headers)
    assert entries.status_code == 200, entries.text
    assert entries.json()["entries"] == []

    recorded = client.post(
        "/v1/reagent-uses",
        headers=headers,
        json={
            "reagent_lot_id": lot["id"],
            "experiment_id": experiment["id"],
            "quantity_used": "1",
        },
    )
    assert recorded.status_code == 201, recorded.text
    assert recorded.json()["experiment_id"] == experiment["id"]
    remaining = client.get(f"/v1/reagent-lots/{lot['id']}", headers=headers).json()["quantity_remaining"]
    assert float(remaining) == 9

    retired = client.patch(f"/v1/reagents/{reagent['id']}", headers=headers, json={"active": False})
    assert retired.status_code == 200, retired.text
    refused = client.post(
        "/v1/reagent-uses",
        headers=headers,
        json={
            "reagent_lot_id": lot["id"],
            "experiment_id": experiment["id"],
            "quantity_used": "1",
        },
    )
    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "reagent_inactive"
    remaining = client.get(f"/v1/reagent-lots/{lot['id']}", headers=headers).json()["quantity_remaining"]
    assert float(remaining) == 9


def test_inactive_reagent_refused_on_experiment_and_lims_run(client: TestClient, test_admin_user, db_session):
    from models.flexible_experiment import LimsRun

    headers = _login(client, "admin", "adminpassword")
    reagent = _reagent(client, headers)
    lot = _lot(client, headers, reagent["id"])
    template = _template(client, headers, [reagent["id"]])
    experiment = _experiment(client, headers, template["id"])
    retired = client.patch(f"/v1/reagents/{reagent['id']}", headers=headers, json={"active": False})
    assert retired.status_code == 200, retired.text
    assert retired.json()["active"] is False
    still_usable = client.get(f"/v1/reagent-lots/{lot['id']}", headers=headers)
    assert still_usable.status_code == 200, still_usable.text
    assert still_usable.json()["usable"] is True
    assert still_usable.json()["active"] is True

    refused = client.post(
        "/v1/reagent-uses",
        headers=headers,
        json={
            "reagent_lot_id": lot["id"],
            "experiment_id": experiment["id"],
            "quantity_used": "1",
        },
    )
    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "reagent_inactive"
    remaining = client.get(f"/v1/reagent-lots/{lot['id']}", headers=headers).json()["quantity_remaining"]
    assert float(remaining) == 10

    run = LimsRun(name=_name("Run"), created_by=test_admin_user.id)
    db_session.add(run)
    db_session.commit()
    on_run = client.post(
        "/v1/reagent-uses",
        headers=headers,
        json={"reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": "1"},
    )
    assert on_run.status_code == 422
    assert on_run.json()["detail"]["code"] == "reagent_inactive"
    remaining = client.get(f"/v1/reagent-lots/{lot['id']}", headers=headers).json()["quantity_remaining"]
    assert float(remaining) == 10
