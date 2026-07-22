"""Unit-тесты get_campaign_dict — мок HTTP (conftest.api_env), без сети и .env.

Кейсы — из Acceptance Criteria спеки specs/01_spec_get_campaign_dict.md.
"""

import bidease
from bidease import CAMPAIGN_DICT_COLUMNS, get_campaign_dict

# Урезанный, но структурно верный заголовок: метрики, затем группировки
# в нижнем регистре в порядке запроса (факт API; полный заголовок — 35 метрик).
CSV_NORMAL = (
    "conversions,spend,impressions,clicks,campaignid,campaignname,advertiserid,productid\n"
    "0,556.31534,187663,7329,154369,x5_x5_igronik_Пятерочка_МояВыгода_android,2608,29153\n"
    "0,25.98262,8720,602,154402,x5_x5_igronik_Пятерочка_МояВыгода_ios,2608,29154\n"
)
CSV_HEADER_ONLY = (
    "conversions,spend,impressions,clicks,campaignid,campaignname,advertiserid,productid\n"
)
CSV_DUPLICATE = (
    "conversions,spend,impressions,clicks,campaignid,campaignname,advertiserid,productid\n"
    "0,1.0,10,1,154369,name_first,2608,29153\n"
    "0,2.0,20,2,154369,name_second,2608,29153\n"
)
CSV_MISSING_VALUES = (
    "conversions,spend,impressions,clicks,campaignid,campaignname,advertiserid,productid\n"
    "0,1.0,10,1,,no_campaign_id,2608,29153\n"
    "0,2.0,20,2,154402,with_empty_product,2608,\n"
)


def test_normal_csv(api_env):
    calls = api_env(CSV_NORMAL)
    df = get_campaign_dict()

    assert list(df.columns) == CAMPAIGN_DICT_COLUMNS
    assert len(df) == 2
    row = df.iloc[0]
    assert row["campaign_id"] == 154369
    # кириллица из UTF-8-тела не искажена (форс resp.encoding в _parse_csv)
    assert row["campaign_name"] == "x5_x5_igronik_Пятерочка_МояВыгода_android"
    assert row["advertiser_id"] == 2608
    assert row["product_id"] == 29153          # реальный ProductID из API, не константа
    assert row["account_id"] == 1
    assert row["source_type_id"] == 10
    assert row["product_name"] == "prod_test"
    assert row["camp_type"] == "camp_test"
    assert row["camp_category"] == "cat_test"
    assert row["owner_id"] == 1
    assert (df["id_key_camp"] == "1_" + df["campaign_id"].astype(str)).all()

    # запрос: 4 группировки в нужном порядке, api-token присутствует
    params = calls[0]["params"]
    groups = [v for k, v in params if k == "group"]
    assert groups == ["CampaignID", "CampaignName", "AdvertiserID", "ProductID"]
    keys = [k for k, _ in params]
    assert "api-token" in keys and "fromdate" in keys and "todate" in keys


def test_empty_header_only(api_env):
    api_env(CSV_HEADER_ONLY)
    df = get_campaign_dict()
    assert list(df.columns) == CAMPAIGN_DICT_COLUMNS
    assert df.empty


def test_empty_body(api_env):
    api_env("")
    df = get_campaign_dict()
    assert list(df.columns) == CAMPAIGN_DICT_COLUMNS
    assert df.empty


def test_duplicate_campaign_id_keeps_first(api_env):
    api_env(CSV_DUPLICATE)
    df = get_campaign_dict()
    assert len(df) == 1
    assert df.iloc[0]["campaign_name"] == "name_first"


def test_row_without_campaign_id_dropped(api_env):
    api_env(CSV_MISSING_VALUES)
    df = get_campaign_dict()
    # строка без campaign_id отброшена; пустой productid → NaN, строка жива
    assert len(df) == 1
    row = df.iloc[0]
    assert row["campaign_id"] == 154402
    assert bidease.pd.isna(row["product_id"])
