import unittest
from campusflow.duplicates import detect_duplicates


class TestDuplicates(unittest.TestCase):

    def setUp(self):
        self.tickets = [
            {
                "id": "T001",
                "title": "Wi-Fi Down",
                "category": "Network",
                "status": "open"
            },
            {
                "id": "T002",
                "title": "Laptop Fault",
                "category": "Hardware",
                "status": "resolved"
            }
        ]

    def test_duplicate_title(self):
        result = detect_duplicates(
            self.tickets, "Network", " wi-fi   down "
        )
        self.assertEqual(result, ["T001"])

    def test_resolved_ticket(self):
        result = detect_duplicates(
            self.tickets, "Hardware", "Laptop Fault"
        )
        self.assertEqual(result, [])

    def test_different_category(self):
        result = detect_duplicates(
            self.tickets, "Software", "Wi-Fi Down"
        )
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()