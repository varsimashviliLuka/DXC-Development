from datetime import date

from app.utils.payment_matching import build_payment_reference


def test_pay_page_shows_payment_reference(client, admin_headers, registered_user):
  building = client.post(
    "/api/v1/buildings",
    json={"building_number": "500", "name": "Pay Building"},
    headers=admin_headers,
  ).get_json()
  users = client.get("/api/v1/users", headers=admin_headers).get_json()["items"]
  user_id = next(u["id"] for u in users if u["id_number"] == registered_user["id_number"])
  client.post(
    "/api/v1/subscriptions",
    json={
      "user_id": user_id,
      "building_id": building["id"],
      "door_number": "12A",
      "monthly_fee": 30,
      "next_payment_due": date.today().isoformat(),
    },
    headers=admin_headers,
  )

  client.post("/auth/login", data={
    "id_number": registered_user["id_number"],
    "password": registered_user["password"],
  })
  html = client.get("/dashboard/pay").get_data(as_text=True)

  assert "How to pay" in html
  assert build_payment_reference(building["id"], "500", "12A") in html
  assert "12A" in html


def test_admin_dashboard_switches_language(client):
  client.post("/auth/login", data={"id_number": "01011000001", "password": "TestAdmin123!"})
  client.get("/lang/ka", query_string={"next": "/admin/"})

  html = client.get("/admin/").get_data(as_text=True)
  assert "მომხმარებლები" in html
  assert 'lang="ka"' in html
  assert "KA" in html


def test_user_dashboard_switches_language(client, registered_user):
  client.post("/auth/login", data={
    "id_number": registered_user["id_number"],
    "password": registered_user["password"],
  })
  client.get("/lang/ka", query_string={"next": "/dashboard/"})

  html = client.get("/dashboard/").get_data(as_text=True)
  assert "როგორ გადავიხადო" in html
  assert 'lang="ka"' in html
