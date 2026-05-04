# Student Management

An Odoo 18 module for managing students, teachers, courses, and staff within an educational institution.

---

## Features

- Create and manage student records with date-of-birth-based age validation
- Manage teachers, staff, and their assignments
- Link each teacher to a system user for direct inbox and activity notifications
- Link students to courses with automatic average age tracking
- Chatter notifications when students are enrolled in a course; direct message + To-Do activity sent to the teacher's linked user
- Public Search wizard to find students, teachers, or staff by name from a single dialog

---

## Models

| Model | Description |
|---|---|
| `base.person` | Abstract base with shared `name` and `age` fields |
| `student.student` | Extends base.person; age computed from date of birth |
| `teacher.teacher` | Extends base.person; holds subject and required linked system user (`user_id`) |
| `staff.staff` | Extends base.person; holds position and salary |
| `course.course` | Links a teacher, optional staff, and many students |
| `student.search.service` | Service layer for cross-model name search |
| `student.search.wizard` | Transient wizard UI for the Public Search feature |
| `student.search.result` | Transient result rows displayed in the wizard |

---

## Key Functionalities

### Student Management

Students require a date of birth. Age is computed and stored automatically. A `@api.constrains` check enforces the 18–60 age range on both create and write paths, not just the form view.

### Course Management

Courses require a teacher. The `average_age` field is a stored computed field that recalculates whenever any enrolled student's age changes. Enrolment is tracked via a Many2many relation with an explicit join table (`course_student_rel`).

### Notifications

When students are added to a course — either at creation or via a subsequent write — enrolment triggers two notification paths:

1. **Internal note** (`mt_note`) posted to the course chatter, visible to all followers.
2. **Direct message + activity** — if the course's teacher has a linked system user (`user_id`), a second chatter message (`mt_comment`) is sent directly to that user's inbox, and a To-Do activity is created on the course and assigned to them.

The logic lives in `_notify_teacher_on_enrolment`, a dedicated method that other modules can safely override without touching `create()` or `write()`.

### Public Search

A wizard (`student.search.wizard`) lets users search across students, teachers, and staff by name from a single popup. The search logic is in `student.search.service` (an AbstractModel), keeping the wizard as a pure UI layer. Results are shown inline in the same dialog.

---

## Technical Highlights

**Abstract base model**
`base.person` provides `name` (required, indexed) and `age` to all three person models. Student overrides `age` as a stored computed field; Teacher and Staff leave it as a plain editable integer.

**Computed fields with store=True**
`student.age` and `course.average_age` are both stored so they can be sorted and filtered in list views without a full-table function scan.

**Age validation on two paths**
`create()` validates age from `vals` before calling `super()` to give a clear error before any DB write. `@api.constrains` catches writes that come through `write()` or direct ORM calls.

**Odoo 18 Many2many cache issue**
In Odoo 18, `super().create()` writes M2M rows directly to the relation table without updating the ORM cache for new records. Course's `create()` extracts student IDs from `vals_list` before calling `super()` to work around this.

**Service layer**
`student.search.service` is an `AbstractModel` — no DB table, no ACL entry needed. It holds the ORM domain logic for cross-model search, making it independently testable and extendable.

---

## Installation

1. Copy the `student_management` folder into your `custom_addons` directory.
2. Restart the Odoo server with `--addons-path` pointing to both `addons` and `custom_addons`.
3. Go to **Settings → General Settings → Developer Tools → Activate developer mode** (or append `?debug=1` to the URL).
4. Go to **Apps → Update Apps List**, search for *Student Management*, and install.

---

## Running Tests

```bash
# Install and run all module tests
python odoo-bin -d <your_db> \
  --addons-path=addons,custom_addons \
  --test-enable -i student_management --stop-after-init

# Show chatter/notification debug output
python odoo-bin -d <your_db> \
  --addons-path=addons,custom_addons \
  --test-enable -i student_management --stop-after-init \
  --log-level=debug

# Run only this module's tests after it's already installed
python odoo-bin -d <your_db> \
  --addons-path=addons,custom_addons \
  --test-tags student_management --stop-after-init
```

Tests are in `tests/test_student_management.py` and cover:

- Age computation and boundary validation (18 / 60)
- Course creation constraints
- Average age recalculation on enrolment changes
- Chatter notification on create and write
- Case-insensitive name search across all person models
- Public Search wizard: type filters, blank input, empty results, result metadata

**If a test fails:**

- Call `record.invalidate_recordset()` before asserting stored computed fields — the ORM cache can lag behind a write.
- Never mutate `setUpClass` records inside a test method; state bleeds into the tests that run after it.
- M2M command `(6, 0, [ids])` replaces the full set; `(4, id)` appends one record. Mixing both in the same `write()` gives unexpected set sizes.

---

## Architecture and Design Logic

```
student_management/
├── models/       # Permanent models + abstract service layer
├── wizard/       # Transient wizard and result models
├── views/        # XML views and menus
├── tests/        # Unit tests (TransactionCase)
└── security/     # Access control rules
```

The three person models share a common abstract base (`base.person`) for `name` and `age`. Student overrides `age` as a stored computed field driven by `date_of_birth`; Teacher and Staff keep it as a plain editable integer.

`course.course` is the central model — required `Many2one` to Teacher, optional `Many2one` to Staff, and a `Many2many` to Students. `average_age` is stored so it can be sorted and filtered in list views without a Python-side scan on every render.

Cross-model search lives in `student.search.service`, an `AbstractModel` with no DB table. The wizard only handles input/output and delegates ORM queries to the service, keeping both independently testable.

**Why `_notify_teacher_on_enrolment` is a separate method**
Notification logic inside `write()` is hard for other modules to extend cleanly. A dedicated method is the standard Odoo extension point — other modules override the method, not the write path.

**Why `super()` is always called in overrides**
Odoo's MRO chains every installed module's override. Skipping `super()` silently drops all logic below yours in the chain. The rule: capture what `super()` returns, do your extra work, return the captured value.

**Why `average_age` uses `store=True`**
Without it, every list render triggers a Python computation for each row. Stored means the value lives in Postgres and is ready for SQL filtering, ordering, and indexing.

---

## Inheritance, Conflicts, and Debugging

**Extending methods safely**
Every `create()` / `write()` override must call `super()` and return its value:

```python
def create(self, vals_list):
    records = super().create(vals_list)
    # your logic here
    return records
```

Skipping `super()` silently drops every other module's override in the chain — that bug only shows up when multiple modules are installed together and is slow to trace.

**Field naming conflicts**
If two modules define the same field name on the same model, the last one installed wins. The other breaks silently — no error at startup. Prefix field names with a short module identifier (`sm_staff_id`) to avoid it. If you control load order, an explicit dependency in `__manifest__.py` is enough. Don't redefine a field owned by another module unless you're taking full ownership.

**Debugging failed notifications**
Run with `--log-level=debug` and grep for the logger output in `course.py`. If the debug line never appears, `added_student_ids` was empty before `_notify_teacher_on_enrolment` was called — check the M2M command format in `create()` or `write()`. If `message_post()` raises `AttributeError`, the model is missing `mail.thread` in `_inherit`.

**Debugging stale computed fields**
In tests, call `record.invalidate_recordset()` before asserting a stored computed field — the cache doesn't always flush after a write. In production, if a stored field never updates, check that `@api.depends` lists every dependency and that the field has `store=True`.
