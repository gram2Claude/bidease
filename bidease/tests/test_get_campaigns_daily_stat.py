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


def test_normal_csv(api_env):
    calls = api_env(CSV_NORMAL)
    df = get_campaigns_daily_stat("2026-07-21", "2026-07-22")

    assert list(df.columns) == CAMPAIGNS_STAT_COLUMNS
    assert len(df) == 3
    row = df.iloc[0]
    assert row["date"] == "2026-07-21"                       # MM/DD/YYYY → YYYY-MM-DD
    assert row["campaign_id"] == 154369
    assert row["impressions"] == 187663 and row["clicks"] == 7329
    # направление НДС обратное avito: база — без НДС (spend), НДС умножением
    assert row["costs_without_nds"] == pytest.approx(556.32)          # round(spend, 2)
    assert row["costs_nds"] == pytest.approx(556.32 * 1.22)           # 2026 → 22%
    assert row["ak"] == 0.5
    assert row["costs_nds_ak"] == pytest.approx(556.32 * 1.22 * 1.5)
    assert row["costs_without_nds_ak"] == pytest.approx(556.32 * 1.5)
    assert row["account_id"] == 1 and row["source_type_id"] == 10
    assert (df["id_key_camp"] == "1_" + df["campaign_id"].astype(str)).all()

    # запрос: группировки Day+CampaignID; todate = date_to + 1 день (эксклюзивна)
    params = calls[0]["params"]
    assert [v for k, v in params if k == "group"] == ["Day", "CampaignID"]
    assert dict(params)["fromdate"] == "2026-07-21"
    assert dict(params)["todate"] == "2026-07-23"


def test_vat_year_boundary(api_env):
    api_env(CSV_YEAR_BOUNDARY)
    df = get_campaigns_daily_stat("2025-12-31", "2026-01-01")
    by_date = df.set_index("date")
    assert by_date.loc["2025-12-31", "costs_nds"] == pytest.approx(100.0 * 1.20)
    assert by_date.loc["2026-01-01", "costs_nds"] == pytest.approx(100.0 * 1.22)


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
