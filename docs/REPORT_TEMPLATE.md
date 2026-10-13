# Report template

The Markdown report is rendered from **`corp_income/templates/corp-income-structure.md`**.
Replace that file with your own layout (keep the name) — no Python change needed. The Excel
output does not depend on it.

- Write a placeholder as a name in double curly braces: `{{tax_code}}`.
- `<!-- … -->` notes are removed from the report.
- An unknown name renders as `—` and is listed in `result.meta["unknown_placeholders"]`.
- Delete the file to use the built-in layout, or pass `template_path=` to `run_corp_income`.

| Group | Placeholders |
|---|---|
| General | `as_of`, `borrowers`, `summary_table`, `documents_table`, `scope_note` |
| Item 1 — blocks | `item1_title`, `item1_table`, `item1_findings`, `item1_conclusion` |
| Item 1 — fields (each also has `<name>_source`) | `company_name`, `company_name_foreign`, `abbreviation`, `tax_code`, `legal_form`, `establishment_date`, `registration_change_number`, `latest_change_date`, `charter_capital`, `head_office_address`, `legal_representatives`, `operating_status` |
| Item 2 | `item2_title`, `members_table`, `borrower_ownership`, `item2_findings`, `item2_conclusion` |
| Item 3 | `item3_title`, `legal_rep_table`, `actual_operator`, `item3_findings`, `item3_conclusion` |
| Item 4 | `item4_title`, `tax_debts_table`, `social_insurance_debts_table`, `administrative_penalties_table`, `enforcement_actions_table`, `disputes_table`, `item4_findings`, `item4_conclusion` |

`*_table` = a whole Markdown table · `*_findings` = the 🔴🟠🔵🟢 list with evidence ·
`*_conclusion` = one line.

Check a template before a run:

```python
from pathlib import Path
from corp_income.report import unknown_placeholders
print(unknown_placeholders(Path("corp_income/templates/corp-income-structure.md").read_text()))  # [] = OK
```
