import pandas as pd

from mlops.entity_linking import EntityLinker, evaluate_entity_linking


def test_entity_linker_exact_and_alias_matching():
    linker = EntityLinker(
        company_to_symbol={"Tata Consultancy Services": "TCS", "Infosys": "INFY"},
        aliases={"TCS": "Tata Consultancy Services"},
    )

    matches = linker.link_text("TCS wins a major cloud contract")

    assert len(matches) == 1
    assert matches[0].symbol == "TCS"
    assert matches[0].score == 1.0


def test_entity_linker_adds_columns_to_dataframe():
    linker = EntityLinker(company_to_symbol={"Infosys": "INFY"})
    df = pd.DataFrame(
        [
            {
                "Headline": "Infosys beats estimates",
                "Summary": "Shares jump on strong guidance",
            }
        ]
    )

    out = linker.link_dataframe(df)

    assert out.loc[0, "Linked_Symbols"] == "INFY"
    assert out.loc[0, "Entity_Link_Score"] == 1.0


def test_evaluate_entity_linking_accuracy():
    pred = pd.Series(["TCS", "INFY", None])
    labels = pd.Series(["TCS", "WIPRO", None])

    metrics = evaluate_entity_linking(pred, labels)

    assert metrics["accuracy"] == 2 / 3
