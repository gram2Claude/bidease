"""Unit-тесты get_admin_audit — мок HTTP с диспетчеризацией (conftest.api_env).

Функция делает 2 запроса: статистика кампаний (group=Day+CampaignID) и справочник
(group с AdvertiserID) — диспетчер различает их по параметрам.
Кейсы — из Acceptance Criteria спеки specs/04_spec_get_admin_audit.md.
"""

import pytest

from bidease import ADMIN_AUDIT_COLUMNS, get_admin_audit

CSV_STATS = (
    "conversions,spend,impressions,clicks,day,campaignid\n"
    "0,100.0,10,1,07/21/2026 00:00:00,154369\n"
    "0,50.0,20,2,07/21/2026 00:00:00,154402\n"
    "0,10.5,5,0,07/22/2026 00:00:00,154369\n"
)
CSV_DICT = (
    "conversions,spend,impressions,clicks,campaignid,campaignname,advertiserid,productid\n"
    "0,160.5,35,3,154369,camp_a,2608,29153\n"
    "0,50.0,20,2,154402,camp_b,2608,29154\n"
)
CSV_DICT_PARTIAL = (      # кампании 154402 нет в справочнике → owner_id NaN → 1
    "conversions,spend,impressions,clicks,campaignid,campaignname,advertiserid,productid\n"
    "0,160.5,35,3,154369,camp_a,2608,29153\n"
)
CSV_STATS_EMPTY = "conversions,spend,impressions,clicks,day,campaignid\n"


def _dispatcher(dict_body: str, stats_body: str):
    def handler(params):
        groups = [v for k, v in params if k == "group"]
        return dict_body if "AdvertiserID" in groups else stats_body
    return handler


def test_normal_aggregate(api_env):
    calls = api_env(_dispatcher(CSV_DICT, CSV_STATS))
    df = get_admin_audit("2026-07-21", "2026-07-22")

    assert list(df.columns) == ADMIN_AUDIT_COLUMNS
    assert len(df) == 2                                   # 2 дня → 2 строки агрегата
    by_date = df.set_index("date")
    # суммы по дню 21.07: две кампании
    assert by_date.loc["2026-07-21", "impressions"] == 30
    assert by_date.loc["2026-07-21", "clicks"] == 3
    assert by_date.loc["2026-07-21", "costs_without_nds"] == pytest.approx(150.0)
    assert by_date.loc["2026-07-21", "costs_nds"] == pytest.approx(150.0 * 1.22)
    # 22.07: одна кампания
    assert by_date.loc["2026-07-22", "impressions"] == 5
    assert by_date.loc["2026-07-22", "costs_without_nds"] == pytest.approx(10.5)
    assert (df["chef_flag"] == 1).all()
    assert (df["owner_id"] == 1).all()
    assert (df["account_id"] == 1).all() and (df["source_type_id"] == 10).all()
    assert len(calls) == 2                                # статистика + справочник


def test_empty_stats_no_dict_request(api_env):
    calls = api_env(_dispatcher(CSV_DICT, CSV_STATS_EMPTY))
    df = get_admin_audit("2026-07-21", "2026-07-22")
    assert list(df.columns) == ADMIN_AUDIT_COLUMNS
    assert df.empty
    assert len(calls) == 1                                # справочник НЕ запрашивался


def test_campaign_missing_in_dict_not_lost(api_env):
    api_env(_dispatcher(CSV_DICT_PARTIAL, CSV_STATS))
    df = get_admin_audit("2026-07-21", "2026-07-22")
    # кампания 154402 вне справочника: owner_id → 1, её метрики НЕ потеряны
    by_date = df.set_index("date")
    assert by_date.loc["2026-07-21", "impressions"] == 30  # 10 + 20 (обе кампании)
    assert (df["owner_id"] == 1).all()
