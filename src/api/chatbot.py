import re

"""
Scholarship chatbot (rule-based, standard-library only).

Run:       python chatbot.py
Data mode: dummy records, no database required.
SQL later: replace get_scholarships() with a repository/database implementation
           returning dictionaries with the same field names.

Conversation state is supplied by the caller, so a Flask route can keep a
separate state dictionary per user/session rather than sharing one global state.
"""

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

# Dummy records shaped like the current scholarships table.
SCHOLARSHIPS = [
    {
        "scholarship_id": 1,
        "name": "Bright Future Scholarship",
        "min_education_level": "graduation",
        "min_passing_percentage": 60,
        "max_age": 25,
        "max_income": 200000,
        "one_child_req": 0,
        "minority_category_req": None,
        "benefit_amount": 30000,
        "deadline": "2026-11-30",
    },
    {
        "scholarship_id": 2,
        "name": "Merit Support Award",
        "min_education_level": "12th",
        "min_passing_percentage": 75,
        "max_age": 22,
        "max_income": 300000,
        "one_child_req": None,
        "minority_category_req": None,
        "benefit_amount": 15000,
        "deadline": "2026-12-15",
    },
    {
        "scholarship_id": 3,
        "name": "Minority Education Grant",
        "min_education_level": "graduation",
        "min_passing_percentage": 50,
        "max_age": 30,
        "max_income": 250000,
        "one_child_req": 0,
        "minority_category_req": "Muslim",
        "benefit_amount": 50000,
        "deadline": "2026-11-20",
    },
    {
        "scholarship_id": 4,
        "name": "Postgraduate Excellence Scholarship",
        "min_education_level": "postgraduation",
        "min_passing_percentage": 70,
        "max_age": 28,
        "max_income": 500000,
        "one_child_req": 0,
        "minority_category_req": None,
        "benefit_amount": 60000,
        "deadline": "2026-12-31",
    },
    {
        "scholarship_id": 5,
        "name": "Open Access Student Aid",
        "min_education_level": None,
        "min_passing_percentage": None,
        "max_age": None,
        "max_income": None,
        "one_child_req": None,
        "minority_category_req": None,
        "benefit_amount": 10000,
        "deadline": None,
    },
]

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
    "deadline": "The screenshot showed TIME type; confirm the real schema before using it as a calendar date.",
    "timestamp": "Record creation timestamp.",
}


def get_scholarships():
    """
    Data-access boundary.

    This version returns dummy records. When SQL is ready, replace this function
    with a repository/database query that returns records using the same keys.
    Keep database credentials and SQL queries out of the conversation logic.
    """
    return SCHOLARSHIPS


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
    """Extract profile facts and simple intents from natural-language messages."""
    text = message.lower().strip()
    result = {}

    # Pick the last-mentioned education level. This makes corrections such as
    # "not MCA, I am doing BCA" resolve to BCA instead of MCA.
    education_hits = []
    for level, aliases in EDUCATION_ALIASES.items():
        for alias in aliases:
            pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
            for match in re.finditer(pattern, text):
                # Ignore a level explicitly negated by phrases such as "not MCA".
                prefix = text[max(0, match.start() - 14):match.start()]
                if re.search(r"\bnot\s+(?:doing\s+|studying\s+|pursuing\s+)?$", prefix):
                    continue
                education_hits.append((match.start(), level))
    if education_hits:
        result["education"] = max(education_hits, key=lambda item: item[0])[1]

    for category, aliases in CATEGORY_ALIASES.items():
        if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text) for alias in aliases):
            result["category"] = category
            break

    income_intent, amount = extract_income_intent(text)
    if income_intent:
        result["income_intent"] = income_intent
        result["income_amount"] = amount

    # Prefer explicit age wording, but also accept conversational forms like "I'm 21".
    age_patterns = [
        r"\b(?:age|aged)\s*(?:(?:is|of|:)?\s*)(\d{1,3})\b",
        r"\b(\d{1,3})\s*(?:years old|yrs old)\b",
        r"\b(?:i am|i'm|im)\s+(\d{1,3})\b",
    ]
    for pattern in age_patterns:
        age_match = re.search(pattern, text)
        if age_match:
            age = int(age_match.group(1))
            if 0 <= age <= 120:
                result["age"] = age
            break

    percentage_match = re.search(r"\b(\d{1,3}(?:\.\d+)?)\s*%", text)
    if not percentage_match:
        percentage_match = re.search(
            r"\b(?:marks?|percentage|score|scored|got|secured)\s*"
            r"(?:are|is|of|:)?\s*(\d{1,3}(?:\.\d+)?)\b",
            text,
        )
    if not percentage_match:
        percentage_match = re.search(
            r"\b(\d{1,3}(?:\.\d+)?)\s*(?:percent|per cent)\b",
            text,
        )
    if percentage_match:
        score = float(percentage_match.group(1))
        if 0 <= score <= 100:
            result["percentage"] = score

    if re.search(r"\bnot an only child\b|\bnot the only child\b|\bnot a single child\b", text):
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


def detect_intent(message):
    """Lightweight intent detection; scholarship eligibility remains rule-based."""
    text = message.lower().strip()
    if re.search(r"\b(hi|hello|hey|namaste)\b|good morning|good afternoon|good evening", text):
        return "greeting"
    if re.search(r"\b(thanks|thank you|thankyou)\b", text):
        return "thanks"
    if any(p in text for p in ["compare", "difference between", "which is better"]):
        return "compare"
    if any(p in text for p in ["why this", "why was this", "explain eligibility", "how did you decide", "why am i eligible"]):
        return "explain"
    if text in {"show more", "more", "next", "next results", "show me more", "more scholarships"}:
        return "show_more"
    if any(p in text for p in ["scholarship", "scholarships", "scheme", "schemes", "financial aid", "student aid", "apply for"]):
        return "scholarship_search"
    return "other"


def explain_reasons(reasons):
    """Turn internal eligibility reasons into student-friendly explanations."""
    if not reasons:
        return "There are not enough details to explain this option yet."
    if "all stored checks passed" in reasons:
        return "You meet all eligibility conditions currently recorded for this scheme; verify the official rules before applying."

    translations = {
        "your family income is not known": "we still need your annual family income",
        "your age is not known": "we still need your age",
        "your marks are not known": "we still need your qualifying-exam marks",
        "minimum education level is not specified": "the minimum education requirement is not listed",
        "maximum family income is not specified": "the maximum family-income limit is not listed",
        "maximum age is not specified": "the maximum age is not listed",
        "minimum marks are not specified": "the minimum marks requirement is not listed",
        "only-child status is not known": "we need to know whether you are an only child",
    }
    readable = [translations.get(reason, reason) for reason in reasons]
    return "This option needs a little more checking: " + "; ".join(readable) + "."


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
    """Search dummy records using either a profile or a scholarship-limit query."""
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
    """Render a conversational page of results and remember displayed IDs."""
    results = search_scholarships(filters)
    profile_state = filters.get("_profile_state")

    if not results:
        if profile_state is not None:
            profile_state["_last_results"] = []
            profile_state["_last_offset"] = 0
            profile_state["_last_total"] = 0
            profile_state["_last_filters"] = {}
        if filters.get("income_intent") == "scholarship_limit":
            return (
                "I couldn't find any records whose listed maximum family-income limit is strictly below "
                f"{format_money(filters.get('income_amount'))}. Schemes without a stated limit were left out."
            )
        return (
            "I couldn't find a scholarship in the current dataset that fits all the details you've shared. "
            "You can change a profile detail or try a broader search."
        )

    matches = [item for item in results if item[1] == "matches"]
    possible = [item for item in results if item[1] == "possible"]

    criteria = []
    if filters.get("education"):
        criteria.append(filters["education"])
    if filters.get("category"):
        criteria.append(filters["category"])
    if filters.get("income_intent") == "applicant_income":
        criteria.append(f"annual family income {format_money(filters['income_amount'])}")
    elif filters.get("income_intent") == "scholarship_limit":
        criteria.append(f"listed income limit below {format_money(filters['income_amount'])}")
    if filters.get("age") is not None:
        criteria.append(f"age {filters['age']}")
    if filters.get("percentage") is not None:
        criteria.append(f"marks {filters['percentage']:g}%")

    if filters.get("income_intent") == "scholarship_limit":
        heading = "Here are the records that meet that income-limit comparison."
    elif criteria:
        heading = "Based on what you've shared" + (f" ({', '.join(criteria)})" if criteria else "") + ", here are some options worth exploring."
    else:
        heading = "Here are some scholarship options from the current dataset."

    heading += (
        f"\n\nI found {len(results)} potential option(s): {len(matches)} pass all recorded checks, "
        f"and {len(possible)} need more information."
    )
    heading += "\nThese are illustrative dummy records, not verified real-world offers or final eligibility decisions."

    page = results[offset:offset + page_size]
    lines = [heading]
    for index, (scholarship, status, reasons) in enumerate(page, start=1):
        label = "Recorded checks passed" if status == "matches" else "Potential match — verify details"
        minimum_education = scholarship["min_education_level"] or "Not specified"
        minimum_marks = scholarship["min_passing_percentage"]
        maximum_age = scholarship["max_age"]
        lines.append(
            f"\n{index}. {scholarship['name']} — {label}"
            f"\n   Listed benefit: {format_money(scholarship['benefit_amount'])}"
            f"\n   Education requirement: {minimum_education}"
            f"\n   Minimum marks: {minimum_marks if minimum_marks is not None else 'Not specified'}"
            f"\n   Maximum age: {maximum_age if maximum_age is not None else 'Not specified'}"
            f"\n   Maximum family income: {format_money(scholarship['max_income'])}"
            f"\n   Why it appears here: {explain_reasons(reasons)}"
        )

    if profile_state is not None:
        profile_state["_last_results"] = [item[0]["scholarship_id"] for item in page]
        profile_state["_last_offset"] = offset
        profile_state["_last_total"] = len(results)
        profile_state["_last_filters"] = {
            key: value for key, value in filters.items() if not key.startswith("_")
        }

    shown_end = offset + len(page)
    if shown_end < len(results):
        lines.append(f"\nShowing {offset + 1}–{shown_end} of {len(results)}. You can say 'show more' to continue.")
    else:
        lines.append(f"\nThat's all {len(results)} result(s) in this search.")

    return "\n".join(lines)


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
    """Interpret a short reply in the context of the last question asked."""
    pending = profile.get("_pending_question")
    text = message.strip()
    lower = text.lower()

    # An explicit new request should not be swallowed as an answer to an old question.
    if any(phrase in lower for phrase in (
        "show scholarships", "show more", "compare", "maximum income limit",
        "income limit below", "what fields", "schema", "columns", "exit", "quit",
        "actually", "instead", "change my", "i am doing", "i'm doing", "i study",
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
        if re.search(r"\b(yes|yeah|yep|correct|i am the only child)\b", lower):
            profile["only_child"] = True
            profile["_pending_question"] = None
            return True
        if re.search(r"\b(no|nope|i am not|i'm not)\b", lower):
            profile["only_child"] = False
            profile["_pending_question"] = None
            return True
    elif pending == "education":
        extracted = understand(text)
        if extracted.get("education"):
            profile["education"] = extracted["education"]
            profile["_pending_question"] = None
            return True

    return False


def _selected_result(message, profile):
    """Resolve references such as 'the second one' against the last displayed page."""
    lower = message.lower()
    if not any(term in lower for term in (
        "first one", "second one", "third one", "first scholarship",
        "second scholarship", "third scholarship", "details of", "tell me about",
        "more about", "number 1", "number 2", "number 3", "first option",
        "second option", "third option",
    )):
        return None

    number = None
    if re.search(r"\b(first|number 1|no\.? 1|option 1)\b", lower):
        number = 1
    elif re.search(r"\b(second|number 2|no\.? 2|option 2)\b", lower):
        number = 2
    elif re.search(r"\b(third|number 3|no\.? 3|option 3)\b", lower):
        number = 3

    ids = profile.get("_last_results", [])
    if number is None or number > len(ids):
        return "I couldn't tell which option you mean from the last results. Try 'tell me about the first one' or run another search."

    scholarship_id = ids[number - 1]
    scholarship = next((s for s in get_scholarships() if s["scholarship_id"] == scholarship_id), None)
    if not scholarship:
        return "I couldn't find that scholarship in the current dataset."

    return (
        f"Here's a closer look at {scholarship['name']}.\n"
        f"Listed benefit: {format_money(scholarship['benefit_amount'])}\n"
        f"Minimum education: {scholarship['min_education_level'] or 'Not specified'}\n"
        f"Minimum marks: {scholarship['min_passing_percentage'] if scholarship['min_passing_percentage'] is not None else 'Not specified'}\n"
        f"Maximum age: {scholarship['max_age'] if scholarship['max_age'] is not None else 'Not specified'}\n"
        f"Maximum family income: {format_money(scholarship['max_income'])}\n"
        f"Required minority category: {scholarship['minority_category_req'] or 'Not specified'}\n"
        f"Deadline in this dummy record: {scholarship['deadline'] or 'Not specified'}\n\n"
        "Please verify the current official scheme notification before relying on these details."
    )


def _compare_last_results(profile):
    """Compare the currently displayed options using fields present in the dataset."""
    ids = profile.get("_last_results", [])
    if len(ids) < 2:
        return "Please search for scholarships first; I need at least two displayed options to compare."
    selected = [s for s in get_scholarships() if s["scholarship_id"] in ids]
    if len(selected) < 2:
        return "I don't have enough previous results to compare. Please run the search again."
    lines = ["Here's a quick comparison of the options from your last results:"]
    for s in selected:
        lines.append(
            f"\n• {s['name']}: benefit {format_money(s['benefit_amount'])}; "
            f"minimum marks {s['min_passing_percentage'] if s['min_passing_percentage'] is not None else 'not specified'}; "
            f"maximum age {s['max_age'] if s['max_age'] is not None else 'not specified'}; "
            f"maximum income {format_money(s['max_income'])}."
        )
    lines.append("\nA larger listed benefit does not automatically mean you are eligible; check all official conditions.")
    return "".join(lines)


def respond(message, profile):
    text = message.strip()
    lower = text.lower()

    if not text:
        return "What would you like to know about scholarships?"
    if lower in {"exit", "quit", "bye", "goodbye"}:
        return None

    if lower in {"clear", "reset", "start over", "reset profile", "clear my profile"}:
        for key in list(profile):
            if not key.startswith("_"):
                profile.pop(key)
        profile["_pending_question"] = None
        profile["_last_results"] = []
        profile["_last_offset"] = 0
        profile["_last_total"] = 0
        profile["_last_filters"] = {}
        return "No problem — I've cleared the profile and previous search for this terminal session."

    intent = detect_intent(text)

    if intent == "greeting" and not any(k in lower for k in ("scholarship", "scheme", "income", "marks", "mca", "bca")):
        return (
            "Hi! I can help you explore scholarship options, check the conditions recorded in our dataset, "
            "and narrow results using your education, marks, age and family income. What are you studying currently?"
        )

    if intent == "thanks":
        return "You're welcome! If you'd like, we can narrow the options further or look at the details of one scholarship."

    schema = schema_answer(text)
    if schema:
        return schema

    if intent == "show_more":
        previous_filters = profile.get("_last_filters", {})
        if not previous_filters:
            return "I don't have a previous search to continue yet. Tell me your education level and I'll start there."
        next_offset = profile.get("_last_offset", 0) + 3
        if next_offset >= profile.get("_last_total", 0):
            return "You've seen all the options returned by that search. You can change a profile detail to run a new search."
        filters = dict(previous_filters)
        filters["_profile_state"] = profile
        profile["_pending_question"] = None
        return build_results_reply(filters, offset=next_offset)

    if intent == "compare":
        return _compare_last_results(profile)

    selected = _selected_result(text, profile)
    if selected is not None:
        return selected

    # Apply a short answer to the last follow-up question before extracting new facts.
    answered_pending = _apply_pending_answer(text, profile)
    extracted = understand(text)

    # Merge only facts actually present in the message. New facts replace old facts,
    # allowing corrections such as "Actually, I'm doing BCA, not MCA".
    for key in ("education", "category", "age", "percentage", "only_child"):
        if key in extracted:
            profile[key] = extracted[key]

    if extracted.get("income_intent") == "applicant_income":
        profile["income"] = extracted["income_amount"]

    # Income-limit comparison is a query about scholarship records, not applicant income.
    if extracted.get("income_intent") == "scholarship_limit":
        profile["_pending_question"] = None
        comparison_filters = dict(extracted)
        comparison_filters["_profile_state"] = profile
        return build_results_reply(comparison_filters)

    # General questions that don't include a search request or new profile facts should
    # not accidentally trigger a fresh search.
    has_profile_facts = any(k in extracted for k in ("education", "category", "age", "percentage", "only_child")) or extracted.get("income_intent") == "applicant_income"
    search_words = any(word in lower for word in (
        "scholarship", "scholarships", "scheme", "schemes", "eligible", "eligibility",
        "apply", "options", "available for me", "what can i get", "show me",
    ))

    filters = _make_profile_filters(profile, sort=extracted.get("sort"))

    if not filters["education"]:
        profile["_pending_question"] = "education"
        if filters["category"] or filters["income_amount"] is not None:
            details = []
            if filters["category"]:
                details.append(f"your {filters['category']} community")
            if filters["income_amount"] is not None:
                details.append(f"annual family income of {format_money(filters['income_amount'])}")
            return "I've noted " + " and ".join(details) + ". What course or education level are you currently pursuing — for example, BCA, MCA, graduation or postgraduation?"
        if intent == "other" and not search_words and not has_profile_facts:
            return (
                "I can help with scholarship searches and eligibility details. Tell me your current course or "
                "education level, and I'll look for relevant options in the dataset."
            )
        return "What course or education level are you currently pursuing — for example, BCA, MCA, graduation or postgraduation?"

    # If the student just answered a follow-up, or shared profile details, re-run the search.
    # Otherwise, only search when the message asks for scholarships or contains useful profile facts.
    if not (search_words or has_profile_facts or answered_pending or extracted.get("sort")):
        if "deadline" in lower:
            return "I can show the deadline stored for a specific scholarship. Say 'tell me about the first one' after a search."
        return "I can help with scholarship options, eligibility, benefits and comparisons. Tell me what you'd like to check, or ask me to show scholarships for your profile."

    filters["_profile_state"] = profile
    reply = build_results_reply(filters)
    question_key, question = choose_follow_up(filters)
    if question:
        profile["_pending_question"] = question_key
        return reply + "\n\nTo narrow these options down, " + question[0].lower() + question[1:]

    profile["_pending_question"] = None
    return reply


def main():
    print("=" * 60)
    print("Scholarship NLP — Dummy Data Mode")
    print("No database connection. Type 'exit' to quit.")
    print("Profile details are remembered only during this terminal session.")
    print("=" * 60)

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
        print("\nBot:", reply)


if __name__ == "__main__":
    main()
