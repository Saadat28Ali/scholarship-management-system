import re
import sys
from pathlib import Path

EDUCATION_RANK = {
    "10th": 1,
    "12th": 2,
    "graduation": 3,
    "postgraduation": 4,
}

EDUCATION_ALIASES = {
    "10th": ["10th", "class 10", "10th pass", "tenth", "matric"],
    "12th": ["12th", "class 12", "12th pass", "twelfth", "higher secondary"],
    "graduation": ["graduation", "graduate", "undergraduate", "bachelor", "bca", "btech", "b.tech", "ba", "b.sc"],
    "postgraduation": [
        "postgraduation", "post graduation", "postgraduate", "post graduate",
        "masters", "master's", "mca", "m.tech", "mtech", "mba", "m.sc", "msc",
    ],
}

CATEGORY_ALIASES = {
    "Muslim": ["muslim"],
    "Christian": ["christian"],
    "Sikh": ["sikh"],
    "Buddhist": ["buddhist"],
    "Jain": ["jain"],
    "Parsi": ["parsi"],
}

STANDARD_GREETING = (
    "Hi! I can help you explore scholarship options, check the conditions recorded in our dataset, "
    "and narrow results using your education, marks, age and family income. What are you studying currently?"
)


SCHEMA_INFO = {
    "scholarship_id": "Unique ID for each scholarship record.",
    "name": "Name of the scholarship.",
    "min_education_level": "Minimum education level required.",
    "min_passing_percentage": "Minimum passing percentage required.",
    "max_age": "Maximum eligible age.",
    "max_income": "Maximum permitted annual family income.",
    "one_child_req": "Whether being an only child is required (1=yes, 0=no, NULL=unspecified).",
    "minority_category_req": "Required minority category, if any.",
    "benefit_amount": "Scholarship benefit amount.",
    "deadline": "Deadline value stored as TIME in the current database schema; it is not a calendar date.",
    "timestamp": "Record creation timestamp.",
}


def get_scholarships():
   
    
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from db.connection import getConnection

    connection = None
    cursor = None
    try:
        connection = getConnection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                scholarship_id,
                name,
                min_education_level,
                min_passing_percentage,
                max_age,
                max_income,
                one_child_req,
                minority_category_req,
                benefit_amount,
                deadline,
                timestamp
            FROM Scholarships
            ORDER BY scholarship_id
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def parse_amount(text):
    """Parse common Indian income formats: 200000, 2 lakh, 2L, 50k."""
    patterns = [
        r"(?:family\s+income|annual\s+income|income|earning|earnings)"
        r"\D{0,35}(?:₹\s*)?(\d+(?:\.\d+)?)\s*"
        r"(lakh|lakhs|lac|lacs|l|k|thousand)?\b",
        r"(?:₹\s*)?(\d+(?:\.\d+)?)\s*(lakh|lakhs|lac|lacs|l|k|thousand)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = (match.group(2) or "").lower()
            if unit in ("lakh", "lakhs", "lac", "lacs", "l"):
                value *= 100_000
            elif unit in ("k", "thousand"):
                value *= 1_000
            return int(value)

    # A plain number is accepted only when the whole message is a number/currency
    # amount. This supports short answers like "180000" to an income follow-up.
    plain_number = re.fullmatch(r"\s*₹?\s*(\d+(?:\.\d+)?)\s*\b", text.strip())
    if plain_number:
        return int(float(plain_number.group(1)))

    return None


def extract_income_intent(text):
    """Distinguish applicant-income eligibility from scholarship-limit comparisons."""
    lower = text.lower()
    amount = parse_amount(lower)
    if amount is None:
        return None, None

    limit_phrases = [
        "scholarships with income limit",
        "scholarship income limit",
        "maximum income limit below",
        "income limit below",
        "income limit less than",
        "max income below",
        "max income less than",
        "schemes with limit below",
    ]
    if any(phrase in lower for phrase in limit_phrases):
        return "scholarship_limit", amount

    # Normal applicant income, including "income below 2 lakh".
    if re.search(r"\b(income|earning|earnings)\b", lower) or re.search(
        r"\b\d+(?:\.\d+)?\s*(lakh|lakhs|lac|lacs|l|k|thousand)\b", lower
    ):
        return "applicant_income", amount

    return None, None


def understand(message):
    text = message.lower()
    result = {}

    # Prefer longer phrases to avoid matching a shorter alias inside a longer one.
    for level, aliases in EDUCATION_ALIASES.items():
        if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text) for alias in aliases):
            result["education"] = level
            break

    for category, aliases in CATEGORY_ALIASES.items():
        if any(alias in text for alias in aliases):
            result["category"] = category
            break

    income_intent, amount = extract_income_intent(text)
    if income_intent:
        result["income_intent"] = income_intent
        result["income_amount"] = amount

    age_match = re.search(
        r"\b(?:age|aged)\s*(?:(?:is|of|:)?\s*)(\d{1,3})\b",
        text,
    )
    if not age_match:
        age_match = re.search(r"\b(\d{1,3})\s*(?:years old|yrs old)\b", text)
    if age_match and 0 <= int(age_match.group(1)) <= 120:
        result["age"] = int(age_match.group(1))

    
    percentage_match = re.search(
        r"\b(\d{1,3}(?:\.\d+)?)\s*%", text
    )

    if not percentage_match:
        percentage_match = re.search(
            r"\b(?:marks?|percentage|score)\s*"
            r"(?:are|is|of|:)?\s*(\d{1,3}(?:\.\d+)?)\b",
            text
        )

    if percentage_match:
        score = float(percentage_match.group(1))
        if 0 <= score <= 100:
            result["percentage"] = score


    # Check negation first because "not an only child" contains "only child".
    if re.search(r"\bnot an only child\b|\bnot the only child\b", text):
        result["only_child"] = False
    elif re.search(r"\bonly child\b|\bsingle child\b", text):
        result["only_child"] = True

    if any(term in text for term in [
        "highest benefit", "highest amount", "maximum benefit", "most money",
        "sort by benefit", "sort them by benefit", "benefit amount",
        "largest scholarship", "highest scholarship amount",
    ]):
        result["sort"] = "benefit_amount"

    return result


def schema_answer(message):
    lower = message.lower()
    if any(term in lower for term in [
        "schema", "columns", "fields", "what information",
        "what data", "eligibility criteria", "database structure",
    ]):
        return (
            "The scholarships table stores education requirements, passing "
            "percentage, maximum age and income, only-child requirements, "
            "minority category, benefit amount and deadline.\nFields: "
            + ", ".join(SCHEMA_INFO.keys())
        )

    for field, description in SCHEMA_INFO.items():
        if field.lower() in lower:
            return f"{field}: {description}"
    return None


def format_money(value):
    return "Not specified" if value is None else f"₹{value:,.0f}"


def evaluate_scholarship(scholarship, profile):
    """Return ('exclude'|'possible'|'matches', reasons) using known facts only."""
    reasons = []
    unknown = []

    # Education: scholarship minimum must be no higher than student's current level.
    user_level = profile.get("education")
    required_level = scholarship["min_education_level"]
    if user_level and required_level:
        if EDUCATION_RANK[required_level] > EDUCATION_RANK[user_level]:
            return "exclude", [f"requires {required_level}"]
    elif not required_level:
        unknown.append("minimum education level is not specified")
    elif not user_level:
        unknown.append("your education level is not known")

    # Applicant income must be at or below the scholarship's maximum.
    user_income = profile.get("income")
    max_income = scholarship["max_income"]
    if user_income is not None and max_income is not None:
        if user_income > max_income:
            return "exclude", ["family income exceeds the listed limit"]
    elif max_income is None:
        unknown.append("maximum family income is not specified")
    elif user_income is None:
        unknown.append("your family income is not known")

    user_age = profile.get("age")
    max_age = scholarship["max_age"]
    if user_age is not None and max_age is not None:
        if user_age > max_age:
            return "exclude", ["age exceeds the listed limit"]
    elif max_age is None:
        unknown.append("maximum age is not specified")
    elif user_age is None:
        unknown.append("your age is not known")

    user_percentage = profile.get("percentage")
    min_percentage = scholarship["min_passing_percentage"]
    if user_percentage is not None and min_percentage is not None:
        if user_percentage < min_percentage:
            return "exclude", ["marks are below the listed minimum"]
    elif min_percentage is None:
        unknown.append("minimum marks are not specified")
    elif user_percentage is None:
        unknown.append("your marks are not known")

    required_category = scholarship["minority_category_req"]
    user_category = profile.get("category")
    if required_category and user_category and required_category != user_category:
        return "exclude", [f"restricted to {required_category} category"]
    if required_category and not user_category:
        unknown.append(f"required category is {required_category}")

    child_requirement = scholarship["one_child_req"]
    user_only_child = profile.get("only_child")
    if child_requirement == 1 and user_only_child is False:
        return "exclude", ["only-child requirement is not met"]
    if child_requirement == 1 and user_only_child is None:
        unknown.append("only-child status is not known")

    if unknown:
        return "possible", unknown
    return "matches", ["all stored checks passed"]


def search_scholarships(filters):
    """Search live database records using either a profile or a scholarship-limit query."""
    results = []

    if filters.get("income_intent") == "scholarship_limit":
        amount = filters["income_amount"]
        for scholarship in get_scholarships():
            maximum = scholarship["max_income"]
            # Unknown limits cannot satisfy a strict numeric comparison.
            if maximum is not None and maximum < amount:
                results.append((
                    scholarship,
                    "matches",
                    [f"listed maximum income {format_money(maximum)} is below {format_money(amount)}"]
                ))
        return results

    profile = {
        "education": filters.get("education"),
        "income": filters.get("income_amount")
        if filters.get("income_intent") == "applicant_income" else None,
        "age": filters.get("age"),
        "percentage": filters.get("percentage"),
        "category": filters.get("category"),
        "only_child": filters.get("only_child"),
    }

    for scholarship in get_scholarships():
        status, reasons = evaluate_scholarship(scholarship, profile)
        if status != "exclude":
            results.append((scholarship, status, reasons))

    if filters.get("sort") == "benefit_amount":
        results.sort(
            key=lambda item: item[0]["benefit_amount"] or 0,
            reverse=True,
        )

    return results


def choose_follow_up(filters):
    """Choose one useful missing detail based on the remaining candidate records."""
    results = search_scholarships(filters)
    candidates = [
        scholarship for scholarship, status, _ in results
        if status in ("matches", "possible")
    ]

    if not candidates:
        return None, None

    if filters.get("income_amount") is None and any(
        s["max_income"] is not None for s in candidates
    ):
        return (
            "income",
            "What is your approximate annual family income? "
            "You can answer, for example, '2 lakh' or '₹180000'.",
        )

    if filters.get("percentage") is None and any(
        s["min_passing_percentage"] is not None for s in candidates
    ):
        return (
            "percentage",
            "What percentage did you score in your last qualifying exam? "
            "You can reply with just a number, such as 60.",
        )

    if filters.get("age") is None and any(
        s["max_age"] is not None for s in candidates
    ):
        return (
            "age",
            "How old are you? You can reply with just your age, such as 20.",
        )

    if filters.get("only_child") is None and any(
        s["one_child_req"] == 1 for s in candidates
    ):
        return (
            "only_child",
            "Are you the only child in your family? Please answer yes or no.",
        )

    return None, None


def build_results_reply(filters, offset=0, page_size=3):
    """Return structured scholarship data instead of formatting records into a string."""
    results = search_scholarships(filters)
    profile_state = filters.get("_profile_state")

    if not results:
        if profile_state is not None:
            profile_state["_last_results"] = []
            profile_state["_last_offset"] = 0
            profile_state["_last_total"] = 0
            profile_state["_last_filters"] = {}

        if filters.get("income_intent") == "scholarship_limit":
            message = (
                "I couldn't find any scholarships whose specified maximum "
                "family-income limit is strictly below "
                f"{format_money(filters.get('income_amount'))}. "
                "Unknown limits are excluded from this comparison."
            )
        else:
            message = "I couldn't find any scholarships matching the information provided in the database."

        return {
            "message": message,
            "total": 0,
            "offset": 0,
            "has_more": False,
            "scholarships": [],
        }

    matches = [item for item in results if item[1] == "matches"]
    possible = [item for item in results if item[1] == "possible"]

    criteria = []
    if filters.get("education"):
        criteria.append(f"education: {filters['education']}")
    if filters.get("category"):
        criteria.append(f"category: {filters['category']}")
    if filters.get("income_intent") == "applicant_income":
        criteria.append(f"family income: {format_money(filters['income_amount'])}")
    elif filters.get("income_intent") == "scholarship_limit":
        criteria.append(
            "scholarship maximum income limit strictly below "
            f"{format_money(filters['income_amount'])}"
        )
    if filters.get("age") is not None:
        criteria.append(f"age: {filters['age']}")
    if filters.get("percentage") is not None:
        criteria.append(f"marks: {filters['percentage']:g}%")

    heading = "Search results"
    if criteria:
        heading += " for " + ", ".join(criteria)
    heading += (
        f". Potential matches: {len(possible)} | Checks passed: {len(matches)}. "
        "Results reflect conditions currently stored in the database; verify "
        "official scheme details before applying."
    )

    page = results[offset:offset + page_size]
    scholarship_items = []
    for scholarship, status, reasons in page:
        # Keep the database fields (including integer scholarship_id) as fields,
        # not embedded in a formatted text string.
        item = dict(scholarship)
        timestamp = item.get("timestamp")
        deadline = item.get("deadline")
        if timestamp is not None:
            item["timestamp"] = str(timestamp)
        if deadline is not None:
            item["deadline"] = str(deadline)

        item["status"] = status
        item["reasons"] = reasons
        scholarship_items.append(item)

    if profile_state is not None:
        profile_state["_last_results"] = [
            item[0]["scholarship_id"] for item in page
        ]
        profile_state["_last_offset"] = offset
        profile_state["_last_total"] = len(results)
        profile_state["_last_filters"] = {
            key: value for key, value in filters.items()
            if not key.startswith("_")
        }

    shown_end = offset + len(page)
    has_more = shown_end < len(results)
    if has_more:
        heading += f" Showing {offset + 1}-{shown_end} of {len(results)} results."
    else:
        heading += f" Showing {shown_end} of {len(results)} results."

    return {
        "message": heading,
        "total": len(results),
        "offset": offset,
        "has_more": has_more,
        "scholarships": scholarship_items,
    }


def _make_profile_filters(profile, sort=None):
    return {
        "education": profile.get("education"),
        "category": profile.get("category"),
        "income_intent": "applicant_income" if profile.get("income") is not None else None,
        "income_amount": profile.get("income"),
        "age": profile.get("age"),
        "percentage": profile.get("percentage"),
        "only_child": profile.get("only_child"),
        "sort": sort,
    }


def _apply_pending_answer(message, profile):
    """Interpret short answers using the question asked in the previous turn."""
    pending = profile.get("_pending_question")
    text = message.strip()
    lower = text.lower()

    # Do not consume a fresh, explicit query as an answer to the old question.
    if any(phrase in lower for phrase in (
        "show scholarships", "show more", "compare", "maximum income limit",
        "income limit below", "what fields", "schema", "columns", "exit", "quit",
    )):
        return False

    if pending == "income":
        amount = parse_amount(lower)
        if amount is not None:
            profile["income"] = amount
            profile["_pending_question"] = None
            return True

    elif pending == "percentage":
        match = re.search(r"\b(\d{1,3}(?:\.\d+)?)\s*%?\b", lower)
        if match:
            value = float(match.group(1))
            if 0 <= value <= 100:
                profile["percentage"] = value
                profile["_pending_question"] = None
                return True

    elif pending == "age":
        match = re.search(r"\b(\d{1,3})\b", lower)
        if match:
            value = int(match.group(1))
            if 0 <= value <= 120:
                profile["age"] = value
                profile["_pending_question"] = None
                return True

    elif pending == "only_child":
        if re.search(r"\b(yes|yeah|yep|i am|correct)\b", lower):
            profile["only_child"] = True
            profile["_pending_question"] = None
            return True
        if re.search(r"\b(no|nope|i am not)\b", lower):
            profile["only_child"] = False
            profile["_pending_question"] = None
            return True

    return False


def _selected_result(message, profile):
    """Resolve references such as 'the second one' against the last displayed page."""
    lower = message.lower()
    if not any(term in lower for term in (
        "first one", "second one", "third one", "first scholarship",
        "second scholarship", "third scholarship", "details of", "tell me about",
        "more about", "number 1", "number 2", "number 3",
    )):
        return None

    number = None
    if re.search(r"\b(first|number 1|no\.? 1)\b", lower):
        number = 1
    elif re.search(r"\b(second|number 2|no\.? 2)\b", lower):
        number = 2
    elif re.search(r"\b(third|number 3|no\.? 3)\b", lower):
        number = 3

    ids = profile.get("_last_results", [])
    if number is None or number > len(ids):
        return make_response("I couldn't identify that item in the last results. Please say 'first one', 'second one', or run a search again.")

    scholarship_id = ids[number - 1]
    scholarship = next(
        (s for s in get_scholarships() if s["scholarship_id"] == scholarship_id),
        None,
    )
    if not scholarship:
        return make_response("I couldn't find that scholarship in the current database records.")

    item = dict(scholarship)
    if item.get("timestamp") is not None:
        item["timestamp"] = str(item["timestamp"])
    if item.get("deadline") is not None:
        item["deadline"] = str(item["deadline"])
    return make_response(
        f"Details for {item.get('name', 'the selected scholarship')}.",
        scholarships=[item],
        total=1,
    )


def make_response(message, scholarships=None, total=0, offset=0, has_more=False, follow_up=None):
    """Return a consistent dictionary suitable for Flask/JSON responses."""
    response = {
        "message": message,
        "total": total,
        "offset": offset,
        "has_more": has_more,
        "scholarships": scholarships or [],
    }
    if follow_up:
        response["follow_up"] = follow_up
    return response


def respond(message, profile):
    text = message.strip()
    lower = text.lower()

    if not text:
        return make_response("Please type a question.")

    if lower in {"exit", "quit"}:
        return None

    if lower in {"hi", "hello", "hey", "good morning", "good evening"}:
        return make_response(STANDARD_GREETING)

    if lower in {"clear", "reset", "start over", "reset profile"}:
        for key in list(profile):
            if not key.startswith("_"):
                profile.pop(key)
        profile["_pending_question"] = None
        profile["_last_results"] = []
        profile["_last_offset"] = 0
        profile["_last_total"] = 0
        profile["_last_filters"] = {}
        return make_response("I've cleared your student profile and search context for this session.")

    schema = schema_answer(text)
    if schema:
        return make_response(schema)

    
    if lower in {"show more", "more", "next", "next results", "show me more"}:
        previous_filters = profile.get("_last_filters", {})
        if not previous_filters:
            return make_response("There isn't a previous search to continue. Tell me what scholarships you're looking for.")
        next_offset = profile.get("_last_offset", 0) + 3
        if next_offset >= profile.get("_last_total", 0):
            return make_response("You've already seen all results from the last search.")
        filters = dict(previous_filters)
        filters["_profile_state"] = profile
        profile["_pending_question"] = None
        return build_results_reply(filters, offset=next_offset)

    selected = _selected_result(text, profile)
    if selected is not None:
        return selected

    
    answered_pending = _apply_pending_answer(text, profile)

    extracted = understand(text)
    profile.update({
        key: value for key, value in extracted.items()
        if key in {"education", "category", "age", "percentage", "only_child"}
    })

    if extracted.get("income_intent") == "applicant_income":
        profile["income"] = extracted["income_amount"]

    
    if extracted.get("income_intent") == "scholarship_limit":
        profile["_pending_question"] = None
        comparison_filters = dict(extracted)
        comparison_filters["_profile_state"] = profile
        return build_results_reply(comparison_filters)

    
    sort = extracted.get("sort")
    filters = _make_profile_filters(profile, sort=sort)

    if not filters["education"]:
        profile["_pending_question"] = "education"
        known_bits = []
        if filters["category"]:
            known_bits.append(filters["category"])
        if filters["income_amount"] is not None:
            known_bits.append(f"family income {format_money(filters['income_amount'])}")
        detail = " and ".join(known_bits)
        prefix = f"I've noted {detail}. " if detail else ""
        return make_response(
            prefix + "What is your current education level: 10th pass, 12th pass, "
            "graduation, or postgraduation?"
        )

    filters["_profile_state"] = profile
    reply = build_results_reply(filters)

    question_key, question = choose_follow_up(filters)
    if question:
        profile["_pending_question"] = question_key
        if isinstance(reply, dict):
            reply["follow_up"] = question
        else:
            reply = {
                "message": reply,
                "total": 0,
                "offset": 0,
                "has_more": False,
                "scholarships": [],
                "follow_up": question,
            }
        return reply

    profile["_pending_question"] = None
    return reply

def main():
    print("=" * 60)
    print("Scholarship NLP — Database Mode")
    print("Fetching scholarship records from MySQL. Type 'exit' to quit.")
    print("Profile details are remembered only during this terminal session.")
    print("=" * 60)
    try:
        records = get_scholarships()
        print(f"Connected to database. Scholarship records available: {len(records)}")
        if not records:
            print("Note: the Scholarships table is empty. Add verified scholarship data to enable meaningful results.")
    except Exception as exc:
        print(f"Could not load scholarship records: {exc}")
        print("Check the database connection and Scholarships table before continuing.")
        return

    print("\nBot:", STANDARD_GREETING)

    profile = {
        "_pending_question": None,
        "_last_results": [],
        "_last_offset": 0,
        "_last_total": 0,
        "_last_filters": {},
    }

    while True:
        try:
            message = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        reply = respond(message, profile)
        if reply is None:
            print("Goodbye!")
            break
        if isinstance(reply, dict):
            print("\nBot:", reply.get("message", ""))
            for index, scholarship in enumerate(reply.get("scholarships", []), start=1):
                print(f"\\n{index}. {scholarship.get('name', 'Unnamed scholarship')}")
                print(f"   Scholarship ID: {scholarship.get('scholarship_id')}")
                print(f"   Benefit: {format_money(scholarship.get('benefit_amount'))}")
                print(f"   Status: {scholarship.get('status', 'unknown')}")
                print(f"   Reasons: {', '.join(scholarship.get('reasons', []))}")
            if reply.get("follow_up"):
                print("\nTo narrow these results further:", reply["follow_up"])
        else:
            print("Bot:", reply.get("message", ""))


if __name__ == "__main__":
    main()
