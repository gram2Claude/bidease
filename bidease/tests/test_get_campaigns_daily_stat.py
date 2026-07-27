"""Unit-тесты get_campaigns_daily_stat — мок HTTP (conftest.api_env).

Кейсы — из Acceptance Criteria спеки specs/02_spec_get_campaigns_daily_stat.md.
"""

import pytest

from bidease import CAMPAIGNS_STAT_COLUMNS, get_campaigns_daily_stat

CSV_NORMAL = (
    "conversions,spend,impressions,clicks,day,campaignid\n"
    "0,556.31534,187663,7329,07/21/2026 00:00:00,154369\n"
    "0,25.98262,8720,602,07/21/2026 00:00:00,154402\n"
    "0,21.85532,7335,208,07/22/2026 00:00:00,154369\n"
)
CSV_YEAR_BOUNDARY = (
    "conversions,spend,impressions,clicks,day,campaignid\n"
    "0,100.0,10,1,12/31/2025 00:00:00,154369\n"
    "0,100.0,20,2,01/01/2026 00:00:00,154369\n"
)
CSV_MISSING_ID = (
    "conversions,spend,impressions,clicks,day,campaignid\n"
    "0,1.0,10,1,07/21/2026 00:00:00,\n"
    "0,2.0,20,2,07/21/2026 00:00:00,154369\n"
)
CSV_HEADER_ONLY = "conversions,spend,impressions,clicks,day,campaignid\n"
CSV_BAD_SPEND = (                 # пустой и нечисловой spend — не должны ронять функцию
    "conversions,spend,impressions,clicks,day,campaignid\n"
    "0,,100,5,07/21/2026 00:00:00,154369\n"
    "0,n/a,200,7,07/21/2026 00:00:00,154402\n"
    "0,12.345,300,9,07/22/2026 00:00:00,154369\n"
)


def test_normal_csv(api_env):
    calls = api_env(CSV_NORMAL)
    df = get_campaigns_daily_stat("2026-07-21", "2026-07-22")

    assert list(df.columns) == CAMPAIGNS_STAT_COLUMNS
    assert len(df) == 3
    row = df.iloc[0]
    assert row["date"] == "2026-07-21"                       # MM/DD/YYYY → YYYY-MM-DD
    assert row["campaign_id"] == 154369
    assert row["impressions"] == 187663 and row["clicks"] == 7329
    # расход — единственное поле costs_usd: spend как есть (доллары), round(2)
    assert row["costs_usd"] == pytest.approx(556.32)                  # round(spend, 2)
    assert row["account_id"] == 1 and row["source_type_id"] == 10
    assert (df["id_key_camp"] == "1_" + df["campaign_id"].astype(str)).all()

    # запрос: группировки Day+CampaignID; todate = date_to + 1 день (эксклюзивна)
    params = calls[0]["params"]
    assert [v for k, v in params if k == "group"] == ["Day", "CampaignID"]
    assert dict(params)["fromdate"] == "2026-07-21"
    assert dict(params)["todate"] == "2026-07-23"


def test_no_vat_across_year_boundary(api_env):
    """Расход не пересчитывается: НДС/комиссия не применяются ни в каком году."""
    api_env(CSV_YEAR_BOUNDARY)
    df = get_campaigns_daily_stat("2025-12-31", "2026-01-01")
    by_date = df.set_index("date")
    assert by_date.loc["2025-12-31", "costs_usd"] == pytest.approx(100.0)
    assert by_date.loc["2026-01-01", "costs_usd"] == pytest.approx(100.0)
    # старые costs-поля и ak в контракте отсутствуют
    for gone in ("costs_nds", "costs_without_nds", "costs_nds_ak", "costs_without_nds_ak", "ak"):
        assert gone not in df.columns


def test_bad_spend_becomes_zero(api_env):
    """Пустой/нечисловой spend → costs_usd = 0.0 (строка не теряется, исключения нет).

    Поведение зафиксировано контрактом: строки с битым расходом остаются в выгрузке
    с нулём, метрики показов/кликов при этом сохраняются.
    """
    api_env(CSV_BAD_SPEND)
    df = get_campaigns_daily_stat("2026-07-21", "2026-07-22")

    assert len(df) == 3                                   # ни одна строка не отброшена
    assert df.iloc[0]["costs_usd"] == 0.0                 # spend пустой
    assert df.iloc[1]["costs_usd"] == 0.0                 # spend = "n/a"
    # ⚠️ округление — numpy/pandas .round(2): half-to-even по двоичному float,
    # поэтому 12.345 → 12.34 (НЕ 12.35). Поведение унаследовано от прежней схемы
    # (так же округлялся costs_without_nds) и зафиксировано контрактом осознанно.
    assert df.iloc[2]["costs_usd"] == pytest.approx(12.34)
    assert df["impressions"].tolist() == [100, 200, 300]
    assert df["costs_usd"].dtype.kind == "f"              # тип остаётся float


def test_empty_header_only(api_env):
    api_env(CSV_HEADER_ONLY)
    df = get_campaigns_daily_stat("2026-07-21", "2026-07-22")
    assert list(df.columns) == CAMPAIGNS_STAT_COLUMNS
    assert df.empty


def test_empty_body(api_env):
    api_env("")
    df = get_campaigns_daily_stat("2026-07-21", "2026-07-22")
    assert list(df.columns) == CAMPAIGNS_STAT_COLUMNS
    assert df.empty


def test_row_without_campaign_id_dropped(api_env):
    api_env(CSV_MISSING_ID)
    df = get_campaigns_daily_stat("2026-07-21", "2026-07-22")
    assert len(df) == 1
    assert df.iloc[0]["campaign_id"] == 154369


def test_invalid_period_no_request(api_env):
    calls = api_env(CSV_HEADER_ONLY)
    with pytest.raises(ValueError):
        get_campaigns_daily_stat("2026-07-22", "2026-07-21")   # date_to < date_from
    with pytest.raises(ValueError):
        get_campaigns_daily_stat("2020-01-01", "2026-07-21")   # за лимитом года
    assert calls == []                                          # запросы не уходили
