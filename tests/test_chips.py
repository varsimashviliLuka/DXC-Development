def test_chip_activate_deactivate(client, admin_headers, registered_user):
  users = client.get("/api/v1/users", headers=admin_headers).get_json()["items"]
  user_id = next(u["id"] for u in users if u["phone_number"] == registered_user["phone_number"])

  chip_resp = client.post(
    "/api/v1/chips",
    json={"user_id": user_id, "chip_number": "CHIP-ACTIVATE-1"},
    headers=admin_headers,
  )
  assert chip_resp.status_code == 201
  chip_id = chip_resp.get_json()["id"]

  deactivate = client.post(f"/api/v1/chips/{chip_id}/deactivate", headers=admin_headers)
  assert deactivate.status_code == 200
  assert deactivate.get_json()["status"] == "inactive"

  activate = client.post(f"/api/v1/chips/{chip_id}/activate", headers=admin_headers)
  assert activate.status_code == 200
  assert activate.get_json()["status"] == "active"
