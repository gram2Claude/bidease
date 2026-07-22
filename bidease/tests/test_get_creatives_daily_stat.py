"""Unit-тесты get_creatives_daily_stat — мок HTTP (conftest.api_env).

Кейсы — из Acceptance Criteria спеки specs/03_spec_get_creatives_daily_stat.md.
"""

import pytest

from bidease import CREATIVES_STAT_COLUMNS, get_creatives_daily_stat

CSV_NORMAL = (
    "conversions,spend,impressions,clicks,day,campaignid,creativeid\n"
    "0,480.95412,161895,6032,07/21/2026 00:00:00,154369,647445\n"
    "0,50.91032,17085,1031,07/21/2026 00:00:00,154369,647446\n"
    "0,2.59558,872,59,07/22/2026 00:00:00,154369,647446\n"
)
CSV_MISSING_CREATIVE = (
    "conversions,spend,impressions,clicks,day,campaignid,creativeid\n"
    "0,1.0,10,1,07/21/2026 00:00:00,154369,\n"
    "0,2.0,20,2,07/21/2026 00:00:00,154369,647445\n"
)
CSV_SHARED_CREATIVE = (
    "conversions,spend,impressions,clicks,day,campaignid,creativeid\n"
    "0,1.0,10,1,07/21/2026 00:00:00,154369,647445\n"
    "0,2.0,20,2,07/21/2026 00:00:00,154402,647445\n"
)
CSV_HEADER_ONLY = "conversions,spend,impressions,clicks,day,campaignid,creativeid\n"


def test_normal_csv(api_env):
    calls = api_env(CSV_NORMAL)
    df = get_creatives_daily_stat("2026-07-21", "2026-07-22")

    assert list(df.columns) == CREATIVES_STAT_COLUMNS
    assert len(df) == 3
    row = df.iloc[0]
    assert row["date"] == "2026-07-21"
    assert row["campaign_id"] == 154369 and row["creative_id"] == 647445
    assert row["costs_without_nds"] == pytest.approx(480.95)
    assert row["costs_nds"] == pytest.approx(480.95 * 1.22)
    assert row["id_key_camp"] == "1_154369"
    assert row["id_key_ad"] == "1_154369_647445"      # без group-звена (групп нет)
    assert (df["id_key_ad"] == df["id_key_camp"] + "_" + df["creative_id"].astype(str)).all()

    params = calls[0]["params"]
    assert [v for k, v in params if k == "group"] == ["Day", "CampaignID", "CreativeID"]


def test_row_without_creative_id_dropped(api_env):
    api_env(CSV_MISSING_CREATIVE)
    df = get_creatives_daily_stat("2026-07-21", "2026-07-22")
    assert len(df) == 1
    assert df.iloc[0]["creative_id"] == 647445


def test_shared_creative_two_campaigns(api_env):
    api_env(CSV_SHARED_CREATIVE)
    df = get_creatives_daily_stat("2026-07-21", "2026-07-22")
    assert len(df) == 2
    assert set(df["id_key_ad"]) == {"1_154369_647445", "1_154402_647445"}


def test_empty(api_env):
    api_env(CSV_HEADER_ONLY)
    df = get_creatives_daily_stat("2026-07-21", "2026-07-22")
    assert list(df.columns) == CREATIVES_STAT_COLUMNS
    assert df.empty
