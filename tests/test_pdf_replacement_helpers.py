from src.deliverynotechg.pdf_contact import (
    build_pdf_replacement_plan,
    build_weight_replacement_text,
    extract_company_name_from_pdf,
    extract_handling_units_from_pdf,
    find_hu_info_in_excel,
    _is_english_company_pdf,
    _pick_font_from_chars,
)


def test_build_weight_replacement_text_keeps_right_side_of_slash():
    result = build_weight_replacement_text("520.000 / 400.000 KG", 470.5)

    assert result == "470.500   /400.000    KG"


def test_extract_handling_units_from_pdf_finds_second_number():
    handling_units = extract_handling_units_from_pdf("archive/ZSD_DELIVERY_NOTE_SF.pdf")

    assert handling_units == ["553977534", "553977533"]


def test_extract_company_name_from_pdf_handles_chinese_delivery_address():
    company_name = extract_company_name_from_pdf("archive/ZSD_DELIVERY_NOTE_SF.pdf")

    assert company_name == {"chinese": "河南海威新能源科技有限公司", "english": None}


def test_find_hu_info_in_excel_uses_exact_handling_unit_match_and_sums_weight():
    hu_info = find_hu_info_in_excel(["553977534", "553977533"], "EXPORT_20260604132137-hu.xlsx")

    assert hu_info == {
        "hu_info_list": [
            {
                "handling_unit": "553977534",
                "batch_number": "2026050704",
                "hu_identification_2": "2026050704",
                "total_weight": 270.0,
            },
            {
                "handling_unit": "553977533",
                "batch_number": "2026050703",
                "hu_identification_2": "2026050703",
                "total_weight": 270.0,
            },
        ],
        "total_weight_sum": 540.0,
    }


def test_build_pdf_replacement_plan_finds_batch_and_weight_targets():
    hu_info = find_hu_info_in_excel(["553977534", "553977533"], "EXPORT_20260604132137-hu.xlsx")

    plan = build_pdf_replacement_plan("archive/ZSD_DELIVERY_NOTE_SF.pdf", hu_info)

    assert [item["text"] for item in plan["batch_replacements"]] == ["2026050704", "2026050703"]
    assert plan["gross_weight_replacement"]["text"] == "540.000 /400.000 KG"
    assert plan["gross_weight_replacement"]["x"] == 394.0


def test_build_pdf_replacement_plan_preserves_weight_style_for_other_pdf():
    hu_info = find_hu_info_in_excel(
        ["510767009", "510767008", "510767004", "510767002", "510740568", "510740566"],
        "EXPORT_20260606051036.xlsx",
    )

    plan = build_pdf_replacement_plan("archive/ZSD_DELIVERY_NOTE_SF (6)_1554_1711.pdf", hu_info)

    assert plan["gross_weight_replacement"]["text"] == "3.810,000 /3.258,000 KG"


def test_is_english_company_pdf_prefers_pdf_language_over_company_name_shape():
    assert _is_english_company_pdf("archive/dn_0626_0639_0644.pdf") is True
    assert _is_english_company_pdf("archive/ZSD_DELIVERY_NOTE_SF (6)_1554_1711.pdf") is False


def test_pick_font_from_chars_prefers_main_chinese_font_and_brackets_font():
    assert _pick_font_from_chars([{"fontname": "CIDFont+F1"}], "海德鲁铝业科技") == "SimHei"
    assert _pick_font_from_chars([{"fontname": "CIDFont+F2"}], "（") == "NSimSun"
