from priority import calculate_priority

def create_ticket(title, category, urgency, affected_users, new_id):

    title = title.strip()
    
    if title == "" :
        raise ValueError("Empty Text")

   
    categories = ("Network", "Hardware", "Software", "Other")
    category = category.title()

    if category not in categories:
        raise ValueError("Supplied Category is invalid")
    
    urgencies = ["low", "medium", "high"]
    urgency = urgency.lower()

    if urgency not in urgencies:
        raise ValueError("Urgencies level does not exist")
    

    if not isinstance(affected_users, int) or isinstance(affected_users, bool)or affected_users < 1 :
        raise ValueError("Incorrect input; user must be atleast 1 written in number")
    
    priority = calculate_priority(urgency, affected_users)

    my_ticket = {
    "id": new_id,
    "title": title,
    "category": category,
    "urgency": urgency,
    "affected_users": affected_users,
    "priority": priority,
    "status": "open",
    "assigned_to": None
    }

    return my_ticket

# This is fake to test our generate_ticket_id function
records = [
    {
        "id": "T007",
        "title": "Wi-Fi is down",
        "category": "Network",
        "urgency": "high",
        "affected_users": 15,
        "priority": "critical",
        "status": "open",
        "assigned_to": None
    },
    {
        "id": "T003",
        "title": "Laptop is faulty",
        "category": "Hardware",
        "urgency": "medium",
        "affected_users": 2,
        "priority": "medium",
        "status": "open",
        "assigned_to": None
    },
    {
        "id": "T001",
        "title": "Cannot access learning platform",
        "category": "Software",
        "urgency": "low",
        "affected_users": 1,
        "priority": "low",
        "status": "open",
        "assigned_to": None
    }
]

# records = []
# print(create_ticket("", "network", "high", 15))
# print(create_ticket("Wi-Fi is down", "finance", "high", 15))
# print(create_ticket("Wi-Fi is down", "network", "high", "five"))
# print(create_ticket("Wi-Fi is down", "network", "high", True))


def generate_ticket_id(records): 
    numbers = [] 
    if len(records) == 0:
        return "T001"
    for record in records: 
        ticket_id = record["id"]
        numbers.append(int(ticket_id[1:])) 
    max_id = max(numbers) 
    new_id = f"T{max_id + 1:03d}" 
    return new_id


def create_and_store_ticket(records, title, category, urgency, affected_users):
    new_id = generate_ticket_id(records)
    new_ticket = create_ticket(title, category, urgency, affected_users, new_id)
    records.append(new_ticket)
    return new_ticket

print(create_and_store_ticket(records, "Faulty mouse", "network", "high", 4))
print(records[-1])
print(generate_ticket_id(records))