import json

from app.modules.verification.checks import verify_answer
from app.modules.verification.ledger import EvidenceLedger
from app.modules.verification.numbers import extract_claims, parse_finance_answer

TRANSFER = {"AlphaForge calculation": {
    "scenario": {"percentOfPortfolio": 10},
    "sectorExposure": {
        "before": {"sectorsPercent": {"technology": 20.0}},
        "after": {"sectorsPercent": {"technology": 26.32}},
        "changeBySector": {"technology": {"changePoints": 6.32}},
    },
    "concentration": {"before": {"herfindahl": 0.42}},
    "portfolioValue": {"totalCAD": 1000.0},
    "riskDrawdown": {"maxDrawdown": {"percent": -35.12}},
}}


def answer(explanation="", rows=(), title="Résultat"):
    return "root = FinanceAnswer(" + ", ".join(json.dumps(part, ensure_ascii=False) for part in
                                               (title, explanation, [], [list(r) for r in rows])) + ")"


def records(*calls):
    ledger = EvidenceLedger()
    for index, (tool, status, evidence) in enumerate(calls):
        ledger.record(f"t{index}", tool, status, {}, evidence)
    return ledger.records


def transfer_records():
    return records(("simulate_transfer", "completed", [TRANSFER]))


def verdict(text, recs=None, **kwargs):
    return verify_answer(answer(text), transfer_records() if recs is None else recs, **kwargs)


# --- the checks the organisers' figures rely on

def test_every_figure_from_the_tool_is_valid():
    report = verdict("La technologie passe de 20 % à 26,32 % pour un transfert de 10 %.", question="")
    assert report.verdict == "validé"
    assert [r.status for r in report.results] == ["ok", "ok", "ok"]
    assert report.results[1].found[0].source.startswith("simulate_transfer#t0 · AlphaForge calculation.sectorExposure.after")


def test_a_changed_figure_is_rejected():
    report = verdict("La technologie passe de 20 % à 28,3 %.")
    assert report.verdict == "rejeté"
    assert [r.text for r in report.unmatched] == ["28,3 %"]


def test_rounded_figure_is_found_but_a_wrong_rounding_is_not():
    assert verdict("Exposition de 26,3 %.").verdict == "validé"
    assert verdict("Exposition de 26 %.").verdict == "validé"
    assert verdict("Exposition de 26,4 %.").verdict == "rejeté"


def test_french_and_english_separators():
    recs = records(("risk_history", "completed", [{"commonPeriod": {"tradingDays": 1255}, "price": 1255.5}]))
    for text in ("1 255 jours de bourse", "1,255 jours", "1255 jours", "1 255,5 $", "1,255.5 $", "1.255,5 $"):
        assert verdict(text, recs).verdict == "validé", text


def test_citations_dates_years_durations_and_list_numbers_are_ignored():
    text = "Au 13 novembre 2026 (2026-11-13T21:00:00+00:00) sur 5 ans, 1mo ou 30 jours [1] [2, 3].\n1. premier point"
    report = verdict(text, [])
    assert report.verdict == "validé"
    assert report.results == ()


def test_index_names_are_not_figures():
    assert verdict("Les titres du S&P 500 et du Nasdaq 100.", []).results == ()


def test_figure_only_in_the_question_is_found_there():
    report = verdict("Un transfert de 10 % simulé.", [], question="Que se passe-t-il si je transfère 10 % ?")
    assert report.verdict == "validé"
    assert report.results[0].found[0].origin == "question"


def test_figure_only_in_a_reference_is_found_there():
    reference = {"previous_stock": {"price": 123.45, "currency": "USD"}}
    report = verdict("Le cours était de 123,45 USD.", [], references=reference)
    assert report.verdict == "validé"
    assert report.results[0].found[0].origin == "reference"


def test_figure_with_no_tool_call_is_rejected():
    assert verdict("Le cours est de 123,45 $.", []).verdict == "rejeté"


def test_failed_tool_is_not_a_source():
    recs = records(("simulate_transfer", "failed", [{"unavailable": {"percent": 26}}]))
    assert verdict("Exposition de 26 %.", recs).verdict == "rejeté"


def test_answer_without_figures_is_valid():
    report = verdict("Aucun chiffre ici.")
    assert (report.verdict, report.results) == ("validé", ())


def test_unreadable_answer_is_not_evaluated():
    assert verify_answer("Une réponse en texte libre, 26 %.", transfer_records()).verdict == "non évalué"


# --- units, signs, currencies

def test_sign_must_agree_when_written():
    assert verdict("Une baisse maximale de 35,12 %.").verdict == "validé"
    assert verdict("Une baisse maximale de −35,12 %.").verdict == "validé"
    assert verdict("Une baisse maximale de -35,12 %.").verdict == "validé"
    assert verdict("Un gain de +35,12 %.").verdict == "rejeté"


def test_currency_must_agree_with_the_source():
    assert verdict("Valeur de 1 000 CAD.").verdict == "validé"
    assert verdict("Valeur de 1 000 USD.").verdict == "rejeté"
    assert verdict("Valeur de $1,000.").verdict == "validé"


def test_percent_does_not_match_an_amount():
    recs = records(("get_stock", "completed", [{"Yahoo Finance": {"price": 26.0, "currency": "USD"}}]))
    assert verdict("Variation de 26 %.", recs).verdict == "rejeté"
    assert verdict("Cours de 26 USD.", recs).verdict == "validé"


def test_ratio_shown_as_a_percentage_is_found():
    report = verdict("Indice de Herfindahl de 0,42, soit 42 %.")
    assert report.verdict == "validé"
    assert report.results[1].found[0].via == "scaled"


def test_amount_multipliers():
    recs = records(("convert_currency", "completed", [{"total": 1_200_000.0, "currency": "CAD"}]))
    for text in ("1,2 million CAD", "1,2 M$", "$1.2M", "1 200 k$"):
        assert verdict(text, recs).verdict == "validé", text


# --- derived and weak figures

def test_gap_in_points_between_two_sourced_values_is_a_reserve():
    recs = records(("compare_stocks", "completed", [
        {"Yahoo Finance": {"symbol": "AAPL", "percentChange": 5.0}},
        {"Yahoo Finance": {"symbol": "MSFT", "percentChange": 1.8}},
    ]))
    report = verdict("AAPL devance MSFT de 3,2 points.", recs)
    assert report.verdict == "à réserve"
    assert report.results[0].status == "derived"
    assert len(report.results[0].found[0].operands) == 2


def test_a_gap_stated_as_a_percentage_is_not_accepted():
    recs = records(("compare_stocks", "completed", [
        {"Yahoo Finance": {"percentChange": 5.0}}, {"Yahoo Finance": {"percentChange": 1.8}}]))
    assert verdict("L'écart est de 3,2 %.", recs).verdict == "rejeté"


def test_change_between_before_and_after_values_is_a_reserve():
    recs = records(("concentration", "completed", [{"AlphaForge calculation": {
        "concentration": {"before": {"herfindahl": 1.0}, "after": {"herfindahl": 0.82}}}}]))
    report = verdict("L'indice de Herfindahl change de −0,18.", recs)
    assert report.verdict == "à réserve"
    assert report.results[0].status == "derived"
    assert verdict("L'indice de Herfindahl change de +0,18.", recs).verdict == "rejeté"
    assert verdict("L'indice change de −0,2.", recs).verdict == "à réserve"
    assert verdict("L'indice change de −0,25.", recs).verdict == "rejeté"


def test_a_whole_number_change_is_not_accepted_by_chance():
    recs = records(("concentration", "completed", [{"AlphaForge calculation": {
        "weights": {"before": {"percent": 40.0}, "after": {"percent": 32.0}}}}]))
    assert verdict("Une baisse de 8 %.", recs).verdict == "rejeté"
    assert verdict("Une baisse de 8,0 %.", recs).verdict == "à réserve"


def test_arithmetic_on_figures_of_the_question_is_a_reserve():
    report = verdict("15 % de 2 000 $ font 300 $.", [], question="Combien font 15 % de 2000 $ ?")
    assert report.verdict == "à réserve"
    assert [r.status for r in report.results] == ["ok", "ok", "derived"]
    assert verdict("15 % de 2 000 $ font 350 $.", [], question="Combien font 15 % de 2000 $ ?").verdict == "rejeté"


def test_illustrations_for_the_reader_are_not_figures():
    text = "Décrivez vos positions, par exemple : « 40 % en AAPL et 30 % en MSFT » — et je calculerai."
    report = verdict(text, [])
    assert (report.verdict, report.results) == ("validé", ())
    assert verdict("Un transfert de 28 %. Par exemple 3 lignes.", []).verdict == "rejeté"


def test_structural_values_are_weak():
    for text in ("Exposition de 0,0 %.", "Le total fait 100 %.", "Sur un maximum de 1,00."):
        report = verdict(text, [])
        assert report.verdict == "à réserve", text
        assert report.results[0].status == "weak_unmatched"


def test_exchange_rate_next_to_a_currency_is_not_an_amount_in_that_currency():
    recs = records(("convert_currency", "completed", [{"conversions": [
        {"amount": 100, "currency": "EUR", "converted": 114.29, "target": "USD", "rate": 1.142857}]}]))
    assert verdict("1 EUR = 1,1429 USD, donc 114,29 USD.", recs).verdict == "validé"
    assert verdict("100 EUR valent 114,29 EUR.", recs).verdict == "rejeté"


def test_unsourced_small_integer_is_only_a_reserve():
    report = verdict("Le portefeuille compte 3 lignes.")
    assert report.verdict == "à réserve"
    assert report.results[0].status == "weak_unmatched"


def test_figure_in_table_cells_is_checked():
    report = verify_answer(answer("Voir le tableau.", rows=[["Après", "26,32 %"], ["Avant", "21 %"]]), transfer_records())
    assert report.verdict == "rejeté"
    assert [(r.location, r.text) for r in report.unmatched] == [("rows[1][1]", "21 %")]


def test_report_dictionary_is_serialisable():
    report = verdict("Exposition de 28 %.")
    assert json.loads(json.dumps(report.to_dict())) == {
        "verdict": "rejeté", "checked": 1, "derived": [],
        "unmatched": [{"text": "28 %", "location": "explanation", "status": "unmatched"}]}


# --- reading the answer and the text

def test_expression_with_quotes_and_parentheses_inside_strings():
    text = 'root = FinanceAnswer("T (1)", "Il a dit \\"20 %\\" (soit 5)", ["A"], [["x", "y"]])\n\nSource [1]'
    assert parse_finance_answer(text) == {"title": "T (1)", "explanation": 'Il a dit "20 %" (soit 5)',
                                          "headers": ["A"], "rows": [["x", "y"]]}


def test_invalid_expressions_are_not_parsed():
    assert parse_finance_answer("root = FinanceAnswer(\"a\", \"b\")") is None
    assert parse_finance_answer("root = FinanceAnswer(a, b, c, d)") is None
    assert parse_finance_answer('root = FinanceAnswer("a", "b", [], [') is None


def test_extraction_reads_units_signs_and_formats():
    claims = {c.text: c for c in extract_claims("−35,12 % ; +3,2 points ; CAD 1 255,00 ; 12 pp ; 0,42")}
    assert claims["−35,12 %"].sign == "-" and claims["−35,12 %"].unit == "percent"
    assert claims["+3,2 points"].unit == "points" and claims["+3,2 points"].strong
    assert claims["CAD 1 255,00"].unit == "amount" and claims["CAD 1 255,00"].currency == "CAD"
    assert claims["CAD 1 255,00"].values[0][0] == 1255.0
    assert claims["12 pp"].strong
    assert not extract_claims("3")[0].strong
