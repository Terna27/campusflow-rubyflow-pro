def normalize_title(title):
    return " ".join(title.casefold().split())


def detect_duplicates(tickets, category, title):
    matches = []

    normalized_title = normalize_title(title)
    normalized_category = category.strip().casefold()

    for ticket in tickets:
        if ticket["status"] == "resolved":
            continue

        existing_title = normalize_title(ticket["title"])
        existing_category = ticket["category"].strip().casefold()

        if (
            normalized_title == existing_title
            and normalized_category == existing_category
        ):
            matches.append(ticket["id"])

    return matches