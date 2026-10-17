from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from stages.stage_04_model_packaging_reproducibility.run import promote_final_champion


def test_promotes_champion_and_archives_previous_packaging_tags():
    client = Mock()
    client.get_model_version.side_effect = [
        SimpleNamespace(tags={"model_status": "champion"}, run_id="new-run"),
        SimpleNamespace(run_id="old-run"),
    ]
    client.get_registered_model.return_value.aliases = {"final-champion": "1"}
    promote_final_champion(client, "classifier", "2")
    client.set_registered_model_alias.assert_called_once_with("classifier", "final-champion", "2")
    client.set_model_version_tag.assert_any_call("classifier", "2", "packaging_status", "final-champion")
    client.set_model_version_tag.assert_any_call("classifier", "1", "packaging_status", "archived")
    client.set_tag.assert_any_call("new-run", "packaging_status", "final-champion")
    client.set_tag.assert_any_call("old-run", "packaging_status", "archived")


def test_rejects_challenger_promotion():
    client = Mock()
    client.get_model_version.return_value.tags = {"model_status": "challenger"}
    with pytest.raises(ValueError, match="Only a champion"):
        promote_final_champion(client, "classifier", "2")
    client.set_registered_model_alias.assert_not_called()


def test_same_final_champion_is_not_archived():
    client = Mock()
    client.get_model_version.return_value = SimpleNamespace(
        tags={"model_status": "champion"}, run_id="current-run",
    )
    client.get_registered_model.return_value.aliases = {"final-champion": "2"}
    promote_final_champion(client, "classifier", "2")
    client.set_model_version_tag.assert_called_once_with(
        "classifier", "2", "packaging_status", "final-champion",
    )