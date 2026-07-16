import unittest

from marathon_catalog import get_race_config, load_marathon_catalog


class MarathonCatalogTests(unittest.TestCase):
    def test_catalog_contains_many_known_races(self):
        catalog = load_marathon_catalog()
        names = [entry["name"] for entry in catalog]

        self.assertIn("Gasparilla Distance Classic Half Marathon", names)
        self.assertIn("Boston Marathon", names)
        self.assertGreaterEqual(len(catalog), 30)

    def test_get_race_config_returns_default_for_unknown_name(self):
        config = get_race_config("Totally Fake Race")

        self.assertEqual(config["name"], "Gasparilla Distance Classic Half Marathon")


if __name__ == "__main__":
    unittest.main()
