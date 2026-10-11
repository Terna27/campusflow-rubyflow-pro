import unittest
from campusflow.priority import calculate_priority


class TestPriority(unittest.TestCase):

    def test_priority_calculations(self):
        self.assertEqual(calculate_priority("high", 10), "critical")
        self.assertEqual(calculate_priority("high", 2), "high")
        self.assertEqual(calculate_priority("low", 10), "high")
        self.assertEqual(calculate_priority("medium", 1), "medium")
        self.assertEqual(calculate_priority("low", 3), "medium")
        self.assertEqual(calculate_priority("low", 1), "low")


if __name__ == "__main__":
    unittest.main()