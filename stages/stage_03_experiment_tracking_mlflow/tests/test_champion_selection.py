from unittest.mock import Mock

import pandas as pd
import pytest

from stages.stage_03_experiment_tracking_mlflow.run import (
    REGISTERED_MODEL_NAME,
    assign_challenger_alias,
    challenger_alias,
    model_alias,
    select_champion,
)


def test_select_champion_uses_highest_cross_validation_roc_auc():
    results = pd.DataFrame([
        {"model": "random_forest", "run_id": "rf", "cv_roc_auc_mean": 0.91},
        {"model": "logistic_regression", "run_id": "lr", "cv_roc_auc_mean": 0.93},
    ])
    assert select_champion(results)["run_id"] == "lr"


def test_select_champion_is_deterministic_for_ties():
    results = pd.DataFrame([
        {"model": "random_forest", "run_id": "rf", "cv_roc_auc_mean": 0.91},
        {"model": "logistic_regression", "run_id": "lr", "cv_roc_auc_mean": 0.91},
    ])
    assert select_champion(results)["run_id"] == "lr"


def test_select_champion_rejects_empty_results():
    with pytest.raises(ValueError, match="At least one"):
        select_champion(pd.DataFrame())


def test_aliases_include_normalized_model_name():
    assert model_alias("random_forest") == "model-random-forest"
    assert challenger_alias("logistic_regression") == "challenger-logistic-regression"


def test_challenger_alias_selects_runner_up():
    client = Mock()
    results = pd.DataFrame([
        {"model": "random_forest", "model_version": "2", "cv_roc_auc_mean": 0.93},
        {"model": "logistic_regression", "model_version": "1", "cv_roc_auc_mean": 0.91},
    ])
    assign_challenger_alias(client, results)
    client.set_registered_model_alias.assert_called_once_with(
        REGISTERED_MODEL_NAME, "challenger", "1",
    )


def test_challenger_alias_removed_when_no_runner_up():
    client = Mock()
    client.get_registered_model.return_value.aliases = {"challenger": "1"}
    results = pd.DataFrame([
        {"model": "random_forest", "model_version": "2", "cv_roc_auc_mean": 0.93},
    ])
    assign_challenger_alias(client, results)
    client.delete_registered_model_alias.assert_called_once_with(
        REGISTERED_MODEL_NAME, "challenger",
    )