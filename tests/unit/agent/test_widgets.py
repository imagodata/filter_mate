# -*- coding: utf-8 -*-
"""Widgets the agent makes: their description, and the filter they write."""
import json

import pytest

from core.agent.widgets import (
    CATEGORIES, CHART, HISTOGRAM, MAX_BARS, MAX_VALUES, MAX_WIDGETS, NOTHING, RANGE, STAT, VALUES, WidgetError,
    category_bars, condition, dumps, histogram_bars, layer_filter, make, parse, replaced, summary, without,
)

pytestmark = pytest.mark.unit


def qf(name):
    return '"' + name.replace('"', '""') + '"'


def qv(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def a_range(widgets=(), **changes):
    values = dict(kind=RANGE, layer_id="L1", layer_name="communes", base="", field="pop", minimum=0, maximum=1000)
    values.update(changes)
    return make(list(widgets), **values)


def some_values(widgets=(), **changes):
    values = dict(kind=VALUES, layer_id="L1", layer_name="communes", base="", field="dep", values=["31", "09", "11"])
    values.update(changes)
    return make(list(widgets), **values)


class TestMake:
    def test_range(self):
        widget = a_range(title="  Population ")
        assert widget["id"] == "w1" and widget["title"] == "Population"
        assert (widget["minimum"], widget["maximum"], widget["low"], widget["high"]) == (0, 1000, 0, 1000)

    def test_values_sorted_and_all_ticked(self):
        widget = some_values()
        assert widget["values"] == ["09", "11", "31"] and widget["chosen"] == ["09", "11", "31"]

    def test_values_with_null_and_numbers(self):
        widget = some_values(values=[3, None, 1])
        assert widget["values"] == [1, 3, None]

    def test_stat(self):
        assert make([], STAT, "L1", "communes", "")["aggregate"] == "count"
        assert make([], STAT, "L1", "communes", "", field="pop", aggregate="sum")["aggregate"] == "sum"

    @pytest.mark.parametrize("changes, words", [
        (dict(kind="pie"), "kind"),
        (dict(minimum=None), "numeric"),
        (dict(minimum=5, maximum=5), "same value"),
        (dict(minimum=float("nan")), "numeric"),
    ])
    def test_range_refused(self, changes, words):
        with pytest.raises(WidgetError, match=words):
            a_range(**changes)

    def test_too_many_values(self):
        with pytest.raises(WidgetError, match="range widget"):
            some_values(values=[str(n) for n in range(MAX_VALUES + 1)])
        with pytest.raises(WidgetError, match="no values"):
            some_values(values=[])

    def test_stat_needs_a_field_but_for_count(self):
        with pytest.raises(WidgetError, match="numeric field"):
            make([], STAT, "L1", "communes", "", aggregate="mean")
        with pytest.raises(WidgetError, match="aggregate"):
            make([], STAT, "L1", "communes", "", field="pop", aggregate="median")

    def test_at_most_so_many(self):
        widgets = []
        for number in range(MAX_WIDGETS):
            widgets.append(make(widgets, STAT, "L1", "communes", ""))
        with pytest.raises(WidgetError, match="remove one"):
            make(widgets, STAT, "L1", "communes", "")

    def test_one_filtering_widget_per_field_of_a_layer(self):
        first = a_range()
        with pytest.raises(WidgetError, match="already"):
            some_values([first], field="pop")
        assert some_values([first])["id"] == "w2"
        assert make([first], STAT, "L1", "communes", "", field="pop", aggregate="sum")  # a number filters nothing

    def test_the_second_widget_of_a_layer_keeps_the_filter_from_before_the_first(self):
        first = a_range(base='"dep" = \'31\'')
        second = some_values([first], field="type", base='"pop" >= 100 AND "dep" = \'31\'')
        assert second["base"] == first["base"]


class TestCondition:
    def test_a_range_left_wide_open_filters_nothing(self):
        assert condition(a_range(), qf, qv) == ""

    def test_range_bounds(self):
        widget = dict(a_range(), low=100.0, high=500.0)
        assert condition(widget, qf, qv) == '"pop" >= 100.0 AND "pop" <= 500.0'
        assert condition(dict(widget, integer=True), qf, qv) == '"pop" >= 100 AND "pop" <= 500'
        assert condition(dict(a_range(), high=10.0), qf, qv) == '"pop" <= 10.0'

    def test_values(self):
        widget = some_values()
        assert condition(widget, qf, qv) == ""
        assert condition(dict(widget, chosen=["31"]), qf, qv) == '"dep" IN (\'31\')'
        assert condition(dict(widget, chosen=[]), qf, qv) == NOTHING

    def test_quotes_are_quoted(self):
        widget = some_values(field='na"me', values=["l'Isle", "x"])
        assert condition(dict(widget, chosen=["l'Isle"]), qf, qv) == '"na""me" IN (\'l\'\'Isle\')'

    def test_null_is_a_value(self):
        widget = some_values(values=["a", None, "b"])
        assert condition(dict(widget, chosen=[None]), qf, qv) == '"dep" IS NULL'
        assert condition(dict(widget, chosen=["a", None]), qf, qv) == '("dep" IN (\'a\') OR "dep" IS NULL)'


class TestLayerFilter:
    def test_widgets_of_a_layer_narrow_it_together_after_its_filter(self):
        first = dict(a_range(base='"dep" = \'31\''), low=100.0)
        second = some_values([first], field="type", values=["a", "b"])
        second = dict(second, chosen=["a"])
        other = make([first, second], RANGE, "L2", "routes", "", field="len", minimum=0, maximum=9)
        widgets = [first, second, other]
        assert layer_filter(widgets, "L1", qf, qv) == '("dep" = \'31\') AND ("pop" >= 100.0) AND ("type" IN (\'a\'))'
        assert layer_filter(widgets, "L2", qf, qv) == ""
        assert layer_filter(widgets, "L9", qf, qv) == ""

    def test_back_to_the_filter_from_before(self):
        assert layer_filter([a_range(base='"x" = 1')], "L1", qf, qv) == '"x" = 1'

    def test_stat_widgets_never_filter(self):
        assert layer_filter([make([], STAT, "L1", "communes", '"x" = 1')], "L1", qf, qv) == ""


class TestStore:
    def test_round_trip(self):
        widgets = [a_range(), ]
        widgets.append(some_values(widgets))
        widgets.append(make(widgets, STAT, "L1", "communes", "", field="pop", aggregate="mean"))
        assert parse(dumps(widgets)) == widgets

    @pytest.mark.parametrize("stored", ["", "nope", "{}", "[1, 2]", json.dumps([{"kind": "range"}])])
    def test_what_cannot_be_read_is_left_out(self, stored):
        assert parse(stored) == []

    def test_damaged_state_is_put_back_in_bounds(self):
        widget = dict(a_range(), low=-5, high=99999)
        assert parse(dumps([widget]))[0]["low"] == 0 and parse(dumps([widget]))[0]["high"] == 1000
        values = dict(some_values(), chosen=["31", "nope"])
        assert parse(dumps([values]))[0]["chosen"] == ["31"]

    def test_duplicate_ids_kept_once(self):
        widget = a_range()
        assert len(parse(dumps([widget, widget]))) == 1

    def test_summary_without_the_values(self):
        widgets = [a_range(title="Pop")]
        widgets.append(some_values(widgets))
        rows = summary(widgets)
        assert rows[0] == {"widget_id": "w1", "kind": "range", "layer": "communes", "title": "Pop", "field": "pop",
                           "low": 0, "high": 1000}
        assert rows[1]["values"] == 3 and rows[1]["ticked"] == 3 and "09" not in json.dumps(rows)

    def test_without_and_replaced(self):
        widgets = [a_range()]
        widgets.append(some_values(widgets))
        assert [widget["id"] for widget in without(widgets, "w1")] == ["w2"]
        with pytest.raises(WidgetError, match="w1, w2"):
            without(widgets, "w9")
        moved = replaced(widgets, dict(widgets[0], low=10.0))
        assert moved[0]["low"] == 10.0 and moved[1] == widgets[1]
        assert replaced(widgets, {"id": "w1"}) == widgets  # a broken state changes nothing


class TestChart:
    def test_a_numeric_field_makes_a_histogram_a_text_field_categories(self):
        assert make([], CHART, "L1", "communes", "", field="pop", numeric=True)["mode"] == HISTOGRAM
        assert make([], CHART, "L1", "communes", "", field="dep")["mode"] == CATEGORIES

    def test_a_chart_needs_a_field(self):
        with pytest.raises(WidgetError, match="needs a field"):
            make([], CHART, "L1", "communes", "")

    def test_a_chart_filters_nothing_and_takes_no_field_from_a_filtering_widget(self):
        first = a_range()
        chart = make([first], CHART, "L1", "communes", "", field="pop", numeric=True)
        assert layer_filter([first, chart], "L1", qf, qv) == ""
        assert condition(chart, qf, qv) == ""
        assert some_values([chart], field="pop", values=[1, 2])["kind"] == VALUES  # a chart is no filter on pop

    def test_round_trip_and_summary(self):
        chart = make([], CHART, "L1", "communes", "", field="dep", title="Par département")
        assert parse(dumps([chart])) == [chart]
        assert summary([chart])[0]["mode"] == CATEGORIES
        assert parse(dumps([dict(chart, mode="pie")])) == []

    def test_category_bars_most_frequent_then_the_others(self):
        counts = [(f"v{index}", index) for index in range(1, 12)]  # 66 features in 11 values
        bars = category_bars(counts, total=66)
        assert [bar["value"] for bar in bars[:3]] == ["v11", "v10", "v9"] and len(bars) == MAX_BARS + 1
        assert bars[-1] == {"value": None, "count": 6, "others": True}  # v1 + v2 + v3
        assert category_bars([("a", 2), (None, 1)], total=3)[1] == {"value": None, "count": 1, "others": False}

    def test_histogram_bars(self):
        bars = histogram_bars([0, 1, 2, 9, 10, None, "x"], bins=5)
        assert [bar["count"] for bar in bars] == [2, 1, 0, 0, 2]
        assert bars[0]["low"] == 0 and bars[-1]["high"] == 10
        assert histogram_bars([3, 3]) == [{"low": 3.0, "high": 3.0, "count": 2}]
        assert histogram_bars([None]) == []
