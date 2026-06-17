"""
Backend tests for CrowdMap.
Run with: pytest -v  (from the backend/ directory)
No external services required — Redis and CV server are mocked.
"""
from main import get_level


# ── Unit tests: get_level ─────────────────────────────────────────────────────

class TestGetLevel:
    def test_low_boundary(self):
        assert get_level(0, 10) == "low"
        assert get_level(3, 10) == "low"   # 30% — just under medium threshold

    def test_medium_boundary(self):
        assert get_level(4, 10) == "medium"  # 40%
        assert get_level(6, 10) == "medium"  # 60%

    def test_high_boundary(self):
        assert get_level(7, 10) == "high"    # 70% — just over high threshold
        assert get_level(10, 10) == "high"   # 100%

    def test_full_capacity_is_high(self):
        assert get_level(8, 8) == "high"


# ── Endpoint tests ────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_areas_returns_four_zones(client):
    r = client.get("/api/areas")
    assert r.status_code == 200
    assert len(r.json()) == 4


def test_areas_response_fields(client):
    r = client.get("/api/areas")
    area = r.json()[0]
    assert {"area_id", "name", "count", "capacity", "level"}.issubset(area.keys())


def test_areas_level_values(client):
    r = client.get("/api/areas")
    for area in r.json():
        assert area["level"] in ("low", "medium", "high")


def test_recommend_sorted_by_ratio(client):
    r = client.get("/api/recommend")
    assert r.status_code == 200
    ratios = [a["count"] / a["capacity"] for a in r.json()]
    assert ratios == sorted(ratios)


def test_history_valid_area(client):
    r = client.get("/api/areas/area_225_2f_1/history")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_history_invalid_area_returns_404(client):
    r = client.get("/api/areas/nonexistent_area/history")
    assert r.status_code == 404


def test_viewers_returns_count(client):
    r = client.get("/api/viewers")
    assert r.status_code == 200
    assert "count" in r.json()
    assert isinstance(r.json()["count"], int)
