"""Default document-type schemas, seeded on first startup.

Lifted from the original SIH ``prompt_schema`` (recruitment documents) but
expressed as data so users can edit them or add their own doc types. The product
is general-purpose; these are just a useful starting set.
"""

from datetime import datetime, timezone

from . import db

DEFAULT_DOC_TYPES: list[dict] = [
    {
        "key": "aadhaar",
        "label": "Aadhaar Card",
        "fields": [
            {"name": "name", "type": "string", "description": "Full name of the holder"},
            {"name": "aadhaar_number", "type": "string", "description": "12-digit Aadhaar number"},
            {"name": "date_of_birth", "type": "date", "description": "Date of birth (DD-MM-YYYY)"},
            {"name": "address", "type": "string", "description": "Residential address"},
            {"name": "gender", "type": "string", "description": "Male, Female or Other"},
        ],
    },
    {
        "key": "birth_cert",
        "label": "Birth Certificate",
        "fields": [
            {"name": "name", "type": "string", "description": "Name of the person"},
            {"name": "date_of_birth", "type": "date", "description": "Date of birth (DD-MM-YYYY)"},
            {"name": "father_name", "type": "string", "description": "Father's name"},
            {"name": "mother_name", "type": "string", "description": "Mother's name"},
        ],
    },
    {
        "key": "marksheet",
        "label": "Marksheet",
        "fields": [
            {"name": "name", "type": "string", "description": "Student name"},
            {"name": "date_of_birth", "type": "date", "description": "Date of birth (DD-MM-YYYY)"},
            {"name": "father_name", "type": "string", "description": "Father's name"},
            {"name": "mother_name", "type": "string", "description": "Mother's name"},
            {"name": "roll_number", "type": "string", "description": "Roll / registration number"},
        ],
    },
    {
        "key": "degree_cert",
        "label": "Degree Certificate",
        "fields": [
            {"name": "name", "type": "string", "description": "Name of the graduate"},
            {"name": "university", "type": "string", "description": "Awarding university"},
            {"name": "date_of_birth", "type": "date", "description": "Date of birth (DD-MM-YYYY)"},
            {"name": "degree", "type": "string", "description": "Degree awarded"},
            {"name": "cgpa", "type": "number", "description": "CGPA, if present", "required": False},
            {"name": "percentage", "type": "number", "description": "Percentage, if present", "required": False},
            {"name": "qualification_degree", "type": "string", "description": "Qualification / specialization"},
        ],
    },
    {
        "key": "provisional_cert",
        "label": "Provisional Certificate",
        "fields": [
            {"name": "name", "type": "string", "description": "Name of the graduate"},
            {"name": "degree", "type": "string", "description": "Degree awarded"},
            {"name": "university", "type": "string", "description": "Awarding university"},
            {"name": "passing_year", "type": "integer", "description": "Year of passing (YYYY)"},
            {"name": "qualification_degree", "type": "string", "description": "Qualification / specialization"},
        ],
    },
    {
        "key": "gate_score_card",
        "label": "GATE Score Card",
        "fields": [
            {"name": "name", "type": "string", "description": "Candidate name"},
            {"name": "registration_number", "type": "string", "description": "Registration number"},
            {"name": "year", "type": "integer", "description": "Year of the GATE examination (YYYY)"},
            {"name": "marks_out_of_100", "type": "number", "description": "Marks out of 100"},
            {"name": "all_india_rank", "type": "integer", "description": "All India Rank in this paper"},
            {"name": "gate_score", "type": "integer", "description": "GATE score (0-1000)"},
        ],
    },
    {
        "key": "experience_cert",
        "label": "Experience Certificate",
        "fields": [
            {"name": "name", "type": "string", "description": "Employee name"},
            {"name": "organization", "type": "string", "description": "Employer / organization"},
            {"name": "from_date", "type": "date", "description": "Start date (YYYY-MM-DD)"},
            {"name": "to_date", "type": "date", "description": "End date (YYYY-MM-DD)"},
        ],
    },
]


async def seed_doc_types() -> None:
    """Insert any default doc type that isn't already present (idempotent)."""
    existing = {d["key"] async for d in db.doc_types().find({}, {"key": 1})}
    now = datetime.now(timezone.utc)
    to_insert = [
        {**dt, "created_by": None, "created_at": now}
        for dt in DEFAULT_DOC_TYPES
        if dt["key"] not in existing
    ]
    if to_insert:
        await db.doc_types().insert_many(to_insert)
