import json
import tempfile
import unittest
from pathlib import Path

from campusflow.knowledge_lab import (
    QUESTIONS,
    ANSWER_EXPLANATIONS,
    calculate_score,
    get_revision_topics,
    save_session,
    run_knowledge_lab,
)


class TestKnowledgeLab(unittest.TestCase):

    def test_question_count(self):
        self.assertEqual(len(QUESTIONS), 10)

    def test_explanation_count(self):
        self.assertEqual(len(ANSWER_EXPLANATIONS), 10)

    def test_perfect_score(self):
        answers = [question[2] for question in QUESTIONS]
        self.assertEqual(calculate_score(answers), 10)

    def test_zero_score(self):
        answers = [
            next(letter for letter in "ABCD" if letter != question[2])
            for question in QUESTIONS
        ]
        self.assertEqual(calculate_score(answers), 0)

    def test_no_revision_topics(self):
        answers = [question[2] for question in QUESTIONS]
        self.assertEqual(get_revision_topics(answers), [])

    def test_wrong_answer_revision(self):
        answers = [question[2] for question in QUESTIONS]
        answers[0] = next(
            letter for letter in "ABCD" if letter != QUESTIONS[0][2]
        )
        self.assertIn(QUESTIONS[0][3], get_revision_topics(answers))

    def test_save_session(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sessions.json"

            save_session({"participant": "B", "score": 8}, path)

            sessions = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["score"], 8)

    def test_multiple_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sessions.json"

            save_session({"score": 7}, path)
            save_session({"score": 9}, path)

            sessions = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(sessions), 2)

    def test_complete_quiz(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sessions.json"

            inputs = ["B"]

            for index, question in enumerate(QUESTIONS):
                inputs.append(question[2])
                inputs.append("My explanation" if index < 3 else "")

            responses = iter(inputs)
            output = []

            session = run_knowledge_lab(
                input_func=lambda prompt: next(responses),
                output_func=output.append,
                session_path=path,
            )

            self.assertEqual(session["score"], 10)
            self.assertEqual(session["participant"], "B")
            self.assertEqual(len(session["explanations"]), 3)
            self.assertTrue(path.exists())

    def test_wrong_answer_explanation_displayed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sessions.json"

            inputs = ["B"]

            for index, question in enumerate(QUESTIONS):
                answer = question[2]

                if index == 0:
                    answer = next(
                        letter for letter in "ABCD" if letter != answer
                    )

                inputs.append(answer)
                inputs.append("My explanation" if index < 3 else "")

            responses = iter(inputs)
            output = []

            session = run_knowledge_lab(
                input_func=lambda prompt: next(responses),
                output_func=output.append,
                session_path=path,
            )

            self.assertEqual(session["score"], 9)
            self.assertTrue(
                any(ANSWER_EXPLANATIONS[0] in line for line in output)
            )


if __name__ == "__main__":
    unittest.main()