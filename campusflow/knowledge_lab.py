import json
from datetime import datetime, timezone
from pathlib import Path


# ==================================================
# ENGINEERING KNOWLEDGE LAB QUESTIONS
# ==================================================

QUESTIONS = [
    (
        "A critical ticket is due at 11:00 UTC. Is it overdue at exactly 11:00?",
        ["Yes", "No, only after 11:00", "Only if assigned", "Only if reopened"],
        "B",
        "SLA boundaries",
    ),
    (
        "Urgency is low and affected users are 10. What priority applies?",
        ["Critical", "High", "Medium", "Low"],
        "B",
        "Priority rules",
    ),
    (
        "An unassigned open ticket moves to in_progress. What happens?",
        ["Allow", "Change status without history", "Reject without changes", "Delete ticket"],
        "C",
        "Workflow invariants",
    ),
    (
        "A resolved high-priority ticket is reopened. What happens?",
        ["Keep old deadline", "Start new SLA cycle", "Reset creation date", "Delete history"],
        "B",
        "Reopening",
    ),
    (
        "An overdue ticket is checked three times in one SLA cycle. How many escalation events?",
        ["Three", "Two", "One", "Zero"],
        "C",
        "Idempotency",
    ),
    (
        "Saved JSON is corrupted. What is safest?",
        ["Replace with empty data", "Use eval", "Load partial data", "Reject and preserve state"],
        "D",
        "Data integrity",
    ),
    (
        "A PR changes SLA calculations without boundary tests. What should a reviewer do?",
        ["Approve", "Request tests and explanation", "Merge immediately", "Ask AI to approve"],
        "B",
        "Code review",
    ),
    (
        "AI suggests using eval() for JSON. What should you do?",
        ["Copy it", "Disable tests", "Reject and use validated JSON parsing", "Publish the file"],
        "C",
        "AI verification",
    ),
    (
        "Two unresolved tickets have matching normalized titles and categories. What happens?",
        ["Delete original", "Warn and request confirmation", "Block forever", "Ignore normalization"],
        "B",
        "Duplicate detection",
    ),
    (
        "An invalid status operation is rejected. What happens to event count?",
        ["Increase once", "Increase twice", "Reset to zero", "Remain unchanged"],
        "D",
        "Audit history",
    ),
]


# ==================================================
# EXPLANATIONS FOR INCORRECT ANSWERS
# ==================================================

ANSWER_EXPLANATIONS = [
    "A ticket becomes overdue only when the current time is later than its deadline. "
    "At exactly 11:00 UTC, it is not overdue.",

    "According to the priority rules, 10 affected users qualify for high priority, "
    "even when urgency is low.",

    "An unassigned ticket cannot move to in_progress. The operation must be rejected "
    "without changing the ticket or its history.",

    "Reopening a resolved ticket begins a new SLA cycle. Its deadline must be "
    "recalculated according to its priority.",

    "Escalation must be idempotent. An overdue ticket can generate only one "
    "escalation event during the same SLA cycle.",

    "Corrupted JSON must not overwrite existing records. The application should "
    "reject invalid data and preserve the original file.",

    "A reviewer should request tests covering SLA deadline boundaries before "
    "approving changes that affect SLA calculations.",

    "Using eval() to parse JSON is unsafe. Use json.load() or json.loads() "
    "and validate the resulting data.",

    "Tickets with matching normalized titles and categories should trigger "
    "a duplicate warning. The user must confirm before creating another ticket.",

    "Rejected operations must not create audit events. The event count should "
    "remain unchanged.",
]


# ==================================================
# CALCULATE QUIZ SCORE
# ==================================================

def calculate_score(answers):
    """Calculate the number of correct answers."""

    return sum(
        answer == question[2]
        for answer, question in zip(answers, QUESTIONS)
    )


# ==================================================
# GET REVISION TOPICS
# ==================================================

def get_revision_topics(answers):
    """Return topics associated with incorrect answers."""

    return [
        question[3]
        for answer, question in zip(answers, QUESTIONS)
        if answer != question[2]
    ]


# ==================================================
# SAVE QUIZ SESSION TO JSON
# ==================================================

def save_session(session, path="data/knowledge_lab_sessions.json"):
    """Save a completed quiz session without deleting previous sessions."""

    destination = Path(path)

    destination.parent.mkdir(parents=True, exist_ok=True)

    sessions = []

    if destination.exists():

        with destination.open("r", encoding="utf-8") as file:
            sessions = json.load(file)

        if not isinstance(sessions, list):
            raise ValueError("Invalid knowledge lab session file.")

    sessions.append(session)

    temporary = destination.with_suffix(".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(sessions, file, indent=4)

    temporary.replace(destination)


# ==================================================
# RUN ENGINEERING KNOWLEDGE LAB
# ==================================================

def run_knowledge_lab(
    input_func=input,
    output_func=print,
    session_path="data/knowledge_lab_sessions.json"
):
    """Run the interactive engineering knowledge quiz."""

    output_func("\n========== ENGINEERING KNOWLEDGE LAB ==========")

    # ----------------------------------------------
    # SELECT PARTICIPANT
    # ----------------------------------------------

    while True:

        participant = input_func("Participant (A/B): ").strip().upper()

        if participant in ("A", "B"):
            break

        output_func("Invalid participant. Enter A or B.")

    answers = []
    explanations = {}

    # ----------------------------------------------
    # ASK TEN QUESTIONS
    # ----------------------------------------------

    for index, question in enumerate(QUESTIONS, start=1):

        text, options, correct, topic = question

        output_func(f"\nQuestion {index}/10: {text}")

        for letter, option in zip("ABCD", options):
            output_func(f"{letter}. {option}")

        while True:

            answer = input_func("Answer (A/B/C/D): ").strip().upper()

            if answer in ("A", "B", "C", "D"):
                break

            output_func("Invalid answer. Enter A, B, C or D.")

        answers.append(answer)

        explanation = input_func(
            "Explain your answer (optional): "
        ).strip()

        if explanation:
            explanations[str(index)] = explanation

    # ----------------------------------------------
    # REQUIRE AT LEAST THREE EXPLANATIONS
    # ----------------------------------------------

    while len(explanations) < 3:

        output_func("\nAt least 3 written explanations are required.")

        number = input_func(
            "Choose a question number to explain (1-10): "
        ).strip()

        if not number.isdigit() or not 1 <= int(number) <= 10:
            output_func("Invalid question number.")
            continue

        if number in explanations:
            output_func("You already explained this question.")
            continue

        explanation = input_func("Your explanation: ").strip()

        if not explanation:
            output_func("Explanation cannot be empty.")
            continue

        explanations[number] = explanation

    # ----------------------------------------------
    # CALCULATE RESULTS
    # ----------------------------------------------

    score = calculate_score(answers)

    revision_topics = get_revision_topics(answers)

    # ----------------------------------------------
    # REVIEW INCORRECT ANSWERS
    # ----------------------------------------------

    output_func("\n========== QUIZ REVIEW ==========")

    wrong_answers = 0

    for index, (answer, question) in enumerate(
        zip(answers, QUESTIONS)
    ):

        question_text, options, correct, topic = question

        if answer != correct:

            wrong_answers += 1

            your_answer = options["ABCD".index(answer)]

            correct_answer = options["ABCD".index(correct)]

            output_func(f"\nQuestion {index + 1}: {question_text}")

            output_func(f"Your answer: {answer}. {your_answer}")

            output_func(
                f"Correct answer: {correct}. {correct_answer}"
            )

            output_func(
                f"Explanation: {ANSWER_EXPLANATIONS[index]}"
            )

            output_func(f"Topic to revise: {topic}")

    if wrong_answers == 0:

        output_func(
            "\nExcellent! You answered all questions correctly."
        )

    # ----------------------------------------------
    # PREPARE QUIZ SESSION
    # ----------------------------------------------

    session = {
        "participant": participant,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "answers": answers,
        "score": score,
        "explanations": explanations,
        "revision_topics": revision_topics,
    }

    # ----------------------------------------------
    # SAVE QUIZ SESSION
    # ----------------------------------------------

    save_session(session, session_path)

    # ----------------------------------------------
    # DISPLAY FINAL RESULTS
    # ----------------------------------------------

    output_func("\n========== FINAL RESULTS ==========")

    output_func(f"Participant: Engineer {participant}")

    output_func(f"Final Score: {score}/10")

    output_func(f"Correct Answers: {score}")

    output_func(f"Incorrect Answers: {wrong_answers}")

    if revision_topics:

        output_func("\nTopics to revise:")

        for topic in revision_topics:
            output_func(f"- {topic}")

    else:

        output_func("\nNo revision topics. Excellent work!")

    output_func(
        "\nKnowledge Lab session saved successfully."
    )

    return session