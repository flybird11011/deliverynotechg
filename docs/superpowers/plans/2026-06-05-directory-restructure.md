# Directory Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the project into a clearer `src/ + scripts/ + tests/` layout without changing runtime behavior.

**Architecture:** Keep the current PDF/Excel workflow intact, but move reusable application code into a Python package under `src/deliverynotechg/`. Leave a thin top-level launcher in place for PyInstaller and local convenience so the existing entry flow stays stable. Move one-off diagnostics into `scripts/` and test helpers into `tests/` so the repository reads like a maintainable application instead of a pile of standalone scripts.

**Tech Stack:** Python, `pandas`, `pdfplumber`, `PyPDF2`, `reportlab`, `PyInstaller`

---

### Task 1: Create the package boundary and move core application code

**Files:**
- Create: `src/deliverynotechg/__init__.py`
- Create: `src/deliverynotechg/customer_excel.py`
- Create: `src/deliverynotechg/pdf_contact.py`
- Create: `src/deliverynotechg/pipeline.py`
- Modify: `app.py`
- Modify: `main.py`

- [ ] **Step 1: Move the Excel aggregation logic into `src/deliverynotechg/customer_excel.py`**

The new module owns `create_customer_excel()` and the fixed source filenames:

```python
file1 = "PT AR001 BP_Customer Master V5 20260226.xlsx"
file2 = "PT International Address - Customer V4 20260225.xlsx"
file3 = "PT AR001_BP_Contact_Person and Relationships V4 20260225.xlsx"
```

It should keep the same output contract and still write `customer_combined.xlsx` in the repository root.

- [ ] **Step 2: Move the PDF parsing and PDF writing helpers into `src/deliverynotechg/pdf_contact.py`**

This module should own the PDF-specific functions currently spread across `app.py`:

```python
extract_company_name_from_pdf(pdf_path)
find_contact_in_excel(company_name, excel_path)
extract_handling_units_from_pdf(pdf_path)
find_hu_info_in_excel(handling_units, excel_path)
update_pdf_with_hu_info(input_pdf, output_pdf, hu_info)
add_contact_to_pdf(input_pdf, output_pdf, contact_info, is_english_company=False)
```

Keep the function names and behavior unchanged so later tasks can wire them together without rewriting logic.

- [ ] **Step 3: Move the orchestration flow into `src/deliverynotechg/pipeline.py`**

The pipeline module should own the high-level workflow currently in `app.py`:

```python
def process_pdf_files():
    ...

def main():
    ...
```

The orchestration should still:

1. Create `customer_combined.xlsx` when missing
2. Scan the current directory for PDFs
3. Write enriched PDFs into `output/`
4. Move processed originals into `archive/`

- [ ] **Step 4: Turn `app.py` and `main.py` into thin launchers**

`app.py` should import and call `src.deliverynotechg.pipeline.main()`.

`main.py` should do the same so the current convenience entry point still works.

This keeps PyInstaller and local execution stable while the real code lives in the package.

### Task 2: Separate ad hoc scripts from maintainable test code

**Files:**
- Create: `scripts/inspect/check_file1.py`
- Create: `scripts/inspect/check_file2_contact.py`
- Create: `scripts/verify_output.py`
- Create: `tests/test_batch.py`
- Create: `tests/test_batch2.py`
- Create: `tests/test_batch3.py`
- Create: `tests/test_font.py`
- Create: `tests/test_pos.py`
- Modify: `test_batch.py`
- Modify: `test_batch2.py`
- Modify: `test_batch3.py`
- Modify: `test_font.py`
- Modify: `test_pos.py`
- Modify: `check_file1.py`
- Modify: `check_file2_contact.py`
- Modify: `verify_output.py`

- [ ] **Step 1: Move the file-inspection helpers under `scripts/inspect/`**

Keep these as one-off diagnostics rather than pretending they are reusable library code:

```text
check_file1.py -> scripts/inspect/check_file1.py
check_file2_contact.py -> scripts/inspect/check_file2_contact.py
```

- [ ] **Step 2: Move the output verification helper into `scripts/`**

```text
verify_output.py -> scripts/verify_output.py
```

This keeps it close to the operational scripts instead of the test suite.

- [ ] **Step 3: Move the batch and formatting checks into `tests/`**

```text
test_batch.py -> tests/test_batch.py
test_batch2.py -> tests/test_batch2.py
test_batch3.py -> tests/test_batch3.py
test_font.py -> tests/test_font.py
test_pos.py -> tests/test_pos.py
```

Keep their contents intact for now. The goal of this pass is directory clarity, not test redesign.

### Task 3: Update packaging and documentation for the new layout

**Files:**
- Modify: `PDFContactTool.spec`
- Modify: `README.md`
- Modify: `.gitignore` if the new structure introduces new generated paths

- [ ] **Step 1: Point PyInstaller at the new launcher path**

Update `PDFContactTool.spec` so the packaged executable still starts from the top-level launcher that imports the pipeline from `src/deliverynotechg/`.

- [ ] **Step 2: Document the new layout in `README.md`**

Add a short tree showing the new split:

```text
src/deliverynotechg/
scripts/
tests/
```

Also update the run instructions so they mention the launcher files and the package entry flow consistently.

- [ ] **Step 3: Add ignores only if the new structure creates new build artifacts**

Keep the ignore rules minimal. Only add paths that are actually generated by the restructure.

### Task 4: Verify the refactor without changing behavior

**Files:**
- No new files expected
- Existing files touched by prior tasks

- [ ] **Step 1: Run a syntax check on the reorganized code**

Run:

```bash
python -m compileall app.py main.py src scripts tests
```

Expected: no syntax errors.

- [ ] **Step 2: Run the existing utility entry points**

Run:

```bash
python app.py
python main.py
```

Expected: both start the same pipeline path as before.

- [ ] **Step 3: Confirm the repository only contains the new intended layout**

Run:

```bash
git status --short
```

Expected: only the planned file moves and documentation updates appear.

- [ ] **Step 4: Commit the restructure**

```bash
git add src scripts tests app.py main.py PDFContactTool.spec README.md .gitignore
git commit -m "refactor: reorganize project structure"
```

---

### Spec Coverage Check

- Core application code is covered by Task 1.
- One-off helpers and tests are covered by Task 2.
- Packaging and documentation are covered by Task 3.
- Verification is covered by Task 4.

### Notes

- This plan intentionally preserves the current filenames at the launcher level so the PyInstaller setup stays simple.
- The first pass does not redesign business logic, normalize function names, or add new features.
- If any import cycle appears during the move, keep the launcher thin and push shared code deeper into `src/deliverynotechg/` instead of expanding the top-level files.
