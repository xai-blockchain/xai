from click.testing import CliRunner

from xai.cli.enhanced_cli import cli


def test_cli_completion_generates_script():
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "--shell", "bash"])
    assert result.exit_code == 0
    assert "_completion" in result.output or "complete" in result.output.lower()
