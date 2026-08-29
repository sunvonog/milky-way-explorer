from pathlib import Path

import pytest

from app.domain.gaia import GaiaBackgroundBatch, GaiaHostBatch
from app.sources.gaia import (
    GAIA_BACKGROUND_COLUMNS,
    GAIA_HOST_COLUMNS,
    GAIA_SOURCE_TABLE,
    GaiaBatchDownload,
    download_gaia_background_batch,
    download_gaia_host_batch,
    gaia_background_query,
    gaia_host_query,
)


class FakeGaiaJob:
    def __init__(self, phase: str = "COMPLETED"):
        self.jobid = "fake-job-123"
        self._phase = phase

    def get_phase(self) -> str:
        return self._phase


class FakeGaiaClient:
    def __init__(
        self,
        *,
        phase: str = "COMPLETED",
        write_output: bool = True,
        submission_error: str | None = None,
    ):
        self.phase = phase
        self.write_output = write_output
        self.submission_error = submission_error
        self.calls: list[dict[str, object]] = []

    def launch_job_async(
        self,
        query: str,
        *,
        output_file: str,
        output_format: str,
        dump_to_file: bool,
        background: bool,
        verbose: bool,
    ) -> FakeGaiaJob:
        self.calls.append(
            {
                "query": query,
                "output_file": output_file,
                "output_format": output_format,
                "dump_to_file": dump_to_file,
                "background": background,
                "verbose": verbose,
            }
        )

        if self.submission_error is not None:
            Path(f"{output_file}.error").write_text(self.submission_error, encoding="utf-8")
            raise RuntimeError("500")

        if self.write_output:
            Path(output_file).write_text("source_id,designation\n7,Gaia DR3 7\n", encoding="utf-8")

        return FakeGaiaJob(self.phase)


def test_gaia_host_columns_match_enrichment_contract() -> None:
    assert GAIA_HOST_COLUMNS == (
        "source_id",
        "designation",
        "ref_epoch",
        "ra",
        "dec",
        "l",
        "b",
        "parallax",
        "parallax_error",
        "parallax_over_error",
        "pm",
        "pmra",
        "pmra_error",
        "pmdec",
        "pmdec_error",
        "radial_velocity",
        "radial_velocity_error",
        "phot_g_mean_mag",
        "phot_bp_mean_mag",
        "phot_rp_mean_mag",
        "bp_rp",
        "ruwe",
        "duplicated_source",
        "astrometric_params_solved",
        "visibility_periods_used",
        "phot_variable_flag",
        "non_single_star",
        "teff_gspphot",
        "distance_gspphot",
        "distance_gspphot_lower",
        "distance_gspphot_upper",
    )


def test_gaia_host_query_selects_one_exact_batch() -> None:
    batch = GaiaHostBatch(
        batch_number=3,
        source_ids=(7, 42),
    )

    query = gaia_host_query(batch)

    assert "SELECT *" not in query
    assert query.startswith("SELECT source_id,designation,ref_epoch")
    assert f"FROM {GAIA_SOURCE_TABLE}" in query
    assert "WHERE source_id IN (7,42)" in query
    assert query.endswith("ORDER BY source_id")


def test_gaia_host_query_has_no_duplicate_columns() -> None:
    assert len(GAIA_HOST_COLUMNS) == len(set(GAIA_HOST_COLUMNS))


def test_gaia_host_query_rejects_empty_batch() -> None:
    batch = GaiaHostBatch(batch_number=1, source_ids=())

    with pytest.raises(ValueError, match="Gaia host batch must not be empty"):
        gaia_host_query(batch)


def test_download_gaia_host_batch_uses_async_file_output(tmp_path: Path) -> None:
    batch = GaiaHostBatch(batch_number=3, source_ids=(7, 42))
    destination = tmp_path / "gaia-host-0003.csv"
    partial = tmp_path / ".gaia-host-0003.csv.part"
    client = FakeGaiaClient()

    result = download_gaia_host_batch(batch, destination, client=client)

    assert result == GaiaBatchDownload(batch_number=3, job_id="fake-job-123", path=destination)
    assert destination.is_file()
    assert not partial.exists()

    assert client.calls == [
        {
            "query": gaia_host_query(batch),
            "output_file": str(partial),
            "output_format": "csv",
            "dump_to_file": True,
            "background": False,
            "verbose": True,
        }
    ]


def test_download_gaia_host_batch_cleans_up_failed_job(tmp_path: Path) -> None:
    batch = GaiaHostBatch(batch_number=2, source_ids=(7,))
    destination = tmp_path / "gaia-host-0002.csv"
    partial = tmp_path / ".gaia-host-0002.csv.part"
    client = FakeGaiaClient(phase="ERROR")

    with pytest.raises(RuntimeError, match="ended in phase ERROR"):
        download_gaia_host_batch(
            batch,
            destination,
            client=client,
        )

    assert not destination.exists()
    assert not partial.exists()


def test_download_gaia_host_batch_rejects_missing_output(tmp_path: Path) -> None:
    batch = GaiaHostBatch(batch_number=4, source_ids=(7,))
    destination = tmp_path / "gaia-host-0004.csv"
    partial = tmp_path / ".gaia-host-0004.csv.part"
    client = FakeGaiaClient(write_output=False)

    with pytest.raises(RuntimeError, match="did not produce an output file"):
        download_gaia_host_batch(batch, destination, client=client)

    assert not destination.exists()
    assert not partial.exists()


def test_download_gaia_host_batch_reports_submission_response(tmp_path: Path) -> None:
    batch = GaiaHostBatch(batch_number=1, source_ids=(7,))
    destination = tmp_path / "gaia-host-0001.csv"
    error_output = tmp_path / ".gaia-host-0001.csv.part.error"
    client = FakeGaiaClient(submission_error="Gaia TAP service unavailable")

    with pytest.raises(RuntimeError, match="500") as raised:
        download_gaia_host_batch(batch, destination, client=client)

    assert raised.value.__notes__ == ["Gaia TAP response: Gaia TAP service unavailable"]
    assert not destination.exists()
    assert not error_output.exists()


def test_gaia_background_query_selects_exact_random_index_range() -> None:
    batch = GaiaBackgroundBatch(
        batch_number=2,
        random_index_start=2_000,
        random_index_stop=3_000,
    )

    query = gaia_background_query(batch)

    assert (
        query
        == f"""SELECT {",".join(GAIA_BACKGROUND_COLUMNS)}
FROM {GAIA_SOURCE_TABLE}
WHERE random_index >= 2000
AND random_index < 3000
AND (
    distance_gspphot > 0
    OR parallax > 0
)
ORDER BY source_id"""
    )


@pytest.mark.parametrize(("start", "stop"), [(-1, 10), (10, 10), (11, 10)])
def test_gaia_background_query_rejects_invalid_ranges(start: int, stop: int) -> None:
    batch = GaiaBackgroundBatch(batch_number=1, random_index_start=start, random_index_stop=stop)

    with pytest.raises(ValueError, match="random-index range"):
        gaia_background_query(batch)


def test_download_gaia_background_batch_uses_async_file_output(tmp_path: Path) -> None:
    batch = GaiaBackgroundBatch(batch_number=2, random_index_start=2_000, random_index_stop=3_000)
    destination = tmp_path / "gaia-background-0002.csv"
    partial = tmp_path / ".gaia-background-0002.csv.part"
    client = FakeGaiaClient()

    result = download_gaia_background_batch(batch, destination, client=client)

    assert result == GaiaBatchDownload(batch_number=2, job_id="fake-job-123", path=destination)
    assert destination.is_file()
    assert not partial.exists()

    assert client.calls == [
        {
            "query": gaia_background_query(batch),
            "output_file": str(partial),
            "output_format": "csv",
            "dump_to_file": True,
            "background": False,
            "verbose": True,
        }
    ]
