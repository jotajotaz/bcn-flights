"""Tests for URL builder."""

from datetime import date

from src.url_builder import skyscanner_url, trainline_url


class TestSkyscannerUrl:
    def test_roundtrip_url(self):
        url = skyscanner_url("MAD", "BCN", date(2026, 1, 28), date(2026, 1, 29))
        assert "skyscanner.es" in url
        assert "mad" in url.lower()
        assert "bcn" in url.lower()
        assert "260128" in url  # fecha ida
        assert "260129" in url  # fecha vuelta

    def test_oneway_url(self):
        url = skyscanner_url("MAD", "BCN", date(2026, 1, 28))
        assert "skyscanner.es" in url
        assert "260128" in url
        assert "260129" not in url  # sin vuelta


class TestTrainlineUrl:
    def test_madrid_barcelona(self):
        url = trainline_url("MAD", "BCN")
        assert "thetrainline.com" in url
        assert "madrid" in url.lower()
        assert "barcelona" in url.lower()

    def test_barcelona_madrid(self):
        url = trainline_url("BCN", "MAD")
        assert "thetrainline.com" in url
        assert "barcelona-to-madrid" in url.lower() or "madrid" in url.lower()

    def test_oviedo_returns_none(self):
        url = trainline_url("OVD", "BCN")
        assert url is None

    def test_unknown_city_returns_none(self):
        url = trainline_url("XXX", "BCN")
        assert url is None
