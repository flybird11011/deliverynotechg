from src.deliverynotechg.pdf_contact import (
    build_pdf_replacement_plan,
    build_weight_replacement_text,
    extract_company_name_from_pdf,
    extract_handling_units_from_pdf,
    find_hu_info_in_excel,
    _extract_total_package_count_from_pdf,
    _is_english_company_pdf,
    _pick_font_from_chars,
)


def test_build_weight_replacement_text_keeps_right_side_of_slash():
    result = build_weight_replacement_text("520.000 / 400.000 KG", 470.5)

    assert result == "470.500   /400.000    KG"


def test_extract_handling_units_from_pdf_finds_second_number():
    handling_units = extract_handling_units_from_pdf("archive/ZSD_DELIVERY_NOTE_SF.pdf")

    assert handling_units == ["553977534", "553977533"]


def test_extract_total_package_count_from_pdf_reads_21():
    assert _extract_total_package_count_from_pdf("archive/ZSD_DELIVERY_NOTE_SF (7).pdf") == 21


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

    plan = build_pdf_replacement_plan("archive/ZSD_DELIVERY_NOTE_SF (6)_2259.pdf", hu_info)

    assert plan["gross_weight_replacement"]["text"] == "3.810,000 /3.258,000 KG"


def test_build_pdf_replacement_plan_skips_weight_when_value_is_same():
    hu_info = {
        "hu_info_list": [],
        "total_weight_sum": 3840.0,
    }

    plan = build_pdf_replacement_plan("archive/ZSD_DELIVERY_NOTE_SF (6)_2259.pdf", hu_info)

    assert plan["gross_weight_replacement"] is None


def test_build_pdf_replacement_plan_only_updates_first_page_weight():
    hu_info = find_hu_info_in_excel(
        [
            "510716196",
            "510716195",
            "510716194",
            "510716193",
            "510716192",
            "510716191",
            "510716190",
            "510716189",
            "510716188",
            "510716187",
            "510716186",
            "510716185",
            "510716184",
            "510716183",
            "510716182",
            "510716181",
            "510716180",
            "510716179",
            "510716178",
            "510716177",
            "510716176",
        ],
        "EXPORT_20260606051036.xlsx",
    )

    plan = build_pdf_replacement_plan("archive/ZSD_DELIVERY_NOTE_SF (7).pdf", hu_info)

    assert plan["total_package_count"] == 21
    assert len(plan["batch_replacements"]) == 21
    assert plan["gross_weight_replacement"] is None
    assert plan["batch_replacements"][0]["text"] == "P27-Q5MB"
    assert plan["batch_replacements"][-1]["text"] == "P27-Q5K6"


def test_build_pdf_replacement_plan_logs_when_weight_is_unchanged(caplog):
    hu_info = {
        "hu_info_list": [],
        "total_weight_sum": 3840.0,
    }

    caplog.clear()
    with caplog.at_level("INFO"):
        plan = build_pdf_replacement_plan("archive/ZSD_DELIVERY_NOTE_SF (6)_2259.pdf", hu_info)

    assert plan["gross_weight_replacement"] is None
    assert "重量相同，跳过替换" in caplog.text


def test_build_pdf_replacement_plan_warns_when_package_count_mismatch(caplog):
    hu_info = {
        "hu_info_list": [],
        "total_weight_sum": 0.0,
    }

    caplog.clear()
    with caplog.at_level("WARNING"):
        plan = build_pdf_replacement_plan("archive/ZSD_DELIVERY_NOTE_SF (7).pdf", hu_info)

    assert plan["total_package_count"] == 21
    assert "搬运单元数量与总包装数不一致" in caplog.text


def test_is_english_company_pdf_prefers_pdf_language_over_company_name_shape():
    assert _is_english_company_pdf("archive/dn_0626_0639_0644.pdf") is True
    assert _is_english_company_pdf("archive/ZSD_DELIVERY_NOTE_SF (6)_2259.pdf") is False


def test_pick_font_from_chars_prefers_main_chinese_font_and_brackets_font():
    assert _pick_font_from_chars([{"fontname": "CIDFont+F1"}], "海德鲁铝业科技") == "SimHei"
    assert _pick_font_from_chars([{"fontname": "CIDFont+F2"}], "（") == "NSimSun"
