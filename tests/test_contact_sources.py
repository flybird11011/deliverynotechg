import pandas as pd

from src.deliverynotechg.pdf_contact import find_contact_in_excels


def test_find_contact_in_excels_falls_back_to_second_file(tmp_path):
    pt_excel = tmp_path / "customer_combined.xlsx"
    ge_excel = tmp_path / "customer_combined-ge.xlsx"

    pd.DataFrame(
        [
            {
                "english_name": "PT Company",
                "chinese_name": "PT公司",
                "contact": "PT Contact",
                "mobile": "111111",
            }
        ]
    ).to_excel(pt_excel, index=False)

    pd.DataFrame(
        [
            {
                "english_name": "GE Company",
                "chinese_name": "GE公司",
                "contact": "GE Contact",
                "mobile": "222222",
            }
        ]
    ).to_excel(ge_excel, index=False)

    company_name = {"english": "GE Company", "chinese": None}

    result = find_contact_in_excels(company_name, [str(pt_excel), str(ge_excel)])

    assert result == {"contact": "GE Contact", "mobile": "222222"}
