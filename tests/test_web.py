def test_login_page(client):
  response = client.get("/auth/login")
  assert response.status_code == 200
  assert b"Sign in" in response.data


def test_login_redirects_admin(client):
  response = client.post(
    "/auth/login",
    data={"id_number": "01011000001", "password": "TestAdmin123!"},
    follow_redirects=False,
  )
  assert response.status_code == 302
  assert response.location.endswith("/")


def test_admin_dashboard_requires_login(client):
  response = client.get("/admin/")
  assert response.status_code == 302
  assert "/auth/login" in response.location


def test_admin_dashboard(client):
  client.post(
    "/auth/login",
    data={"id_number": "01011000001", "password": "TestAdmin123!"},
  )
  response = client.get("/admin/")
  assert response.status_code == 200
  assert b"Dashboard" in response.data
