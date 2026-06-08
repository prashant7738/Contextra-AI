import unittest

from app.services.flashcard_parsing import parse_flashcard_marker_output


class FlashcardParserTests(unittest.TestCase):
    def test_parses_flashcards_without_trailing_end_marker(self):
        output = """noise before
<<<FLASHCARD>>>
TOPIC: Cache Memory
SUMMARY: Fast memory for frequent data
EXPLANATION: Cache stores frequently used data to reduce access time.

<<<FLASHCARD>>>
TOPIC: Crossbar Switch
SUMMARY: Interconnect for communication
EXPLANATION: A crossbar switch connects multiple inputs to outputs.
"""

        cards = parse_flashcard_marker_output(output)

        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["topic"], "Cache Memory")
        self.assertEqual(cards[1]["summary"], "Interconnect for communication")


if __name__ == "__main__":
    unittest.main()
