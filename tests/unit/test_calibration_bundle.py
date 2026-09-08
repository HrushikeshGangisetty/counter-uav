"""tools.calibration: the CalibrationBundle representation, YAML round-trip, and the
down-conversion into the pod_config intrinsics shape.

Deterministic; synthetic calibration data only. [PRD 4.1, 5.4] OD-02 stays OPEN ---
an uncalibrated or unclean bundle must convert to an all-OPEN runtime config.
"""

from __future__ import annotations

import pytest

from pod_config import is_open, load_pod_config
from tools.calibration import (
    CalibrationBoard,
    CalibrationBundle,
    CalibrationError,
    bundle_from_opencv,
    load_calibration,
    save_calibration,
    to_intrinsics_config,
    write_intrinsics_config,
)

W, H = 1456, 1088


def _synthetic_board() -> CalibrationBoard:
    return CalibrationBoard(pattern="checkerboard", rows=8, cols=11, square_size_mm=25.0)


def _synthetic_calibrated_bundle(**overrides: object) -> CalibrationBundle:
    """Obviously-synthetic, fully-populated, structurally clean. NOT a measurement."""
    base = dict(
        camera_id=0,
        image_width_px=W,
        image_height_px=H,
        distortion_model="pinhole_radtan",
        camera_matrix=((1000.0, 0.0, W / 2), (0.0, 1000.0, H / 2), (0.0, 0.0, 1.0)),
        distortion_coeffs=(0.0, 0.0, 0.0, 0.0, 0.0),
        reprojection_error_px=0.21,
        per_view_errors_px=(0.2, 0.19, 0.23),
        num_views=3,
        board=_synthetic_board(),
        calibration_id="synthetic-0001",
        created="2026-09-08",
        tool="synthetic-test",
        calibrated=True,
    )
    base.update(overrides)
    return CalibrationBundle(**base)  # type: ignore[arg-type]


# --- validation ------------------------------------------------------------


def test_clean_calibrated_bundle_validates() -> None:
    bundle = _synthetic_calibrated_bundle()
    assert bundle.hard_problems() == []
    assert bundle.is_acceptable_for_geometry() is True
    bundle.require_valid()


def test_uncalibrated_bundle_is_not_an_error_but_not_acceptable() -> None:
    bundle = CalibrationBundle(camera_id=0, image_width_px=W, image_height_px=H)
    assert bundle.hard_problems() == []
    assert bundle.is_acceptable_for_geometry() is False


@pytest.mark.parametrize(
    "overrides,needle",
    [
        (dict(camera_matrix=None), "no camera_matrix"),
        (dict(distortion_coeffs=None), "no distortion_coeffs"),
        (dict(distortion_model="wobble"), "not one of"),
        (dict(distortion_model="fisheye_equidistant"), "fisheye_equidistant needs 4"),
        (dict(reprojection_error_px=None), "no reprojection_error_px"),
        (dict(reprojection_error_px=-1.0), "negative"),
        (dict(num_views=0, per_view_errors_px=()), "no calibration views"),
        (
            dict(camera_matrix=((1000.0, 0.0, W / 2), (0.0, 1000.0, H / 2), (0.0, 0.0, 2.0))),
            "bottom row",
        ),
        (
            dict(camera_matrix=((-1.0, 0.0, W / 2), (0.0, 1000.0, H / 2), (0.0, 0.0, 1.0))),
            "fx/fy must be positive",
        ),
        (
            dict(camera_matrix=((1000.0, 0.0, 9999.0), (0.0, 1000.0, H / 2), (0.0, 0.0, 1.0))),
            "cx",
        ),
    ],
)
def test_calibrated_bundle_hard_problems(overrides: dict[str, object], needle: str) -> None:
    problems = _synthetic_calibrated_bundle(**overrides).hard_problems()
    assert any(needle in p for p in problems), problems


def test_require_valid_raises_on_hard_problem() -> None:
    with pytest.raises(CalibrationError, match="no camera_matrix"):
        _synthetic_calibrated_bundle(camera_matrix=None).require_valid()


def test_unmeasured_square_size_is_advisory_only() -> None:
    bundle = _synthetic_calibrated_bundle(
        board=CalibrationBoard(pattern="checkerboard", rows=8, cols=11, square_size_mm=None)
    )
    assert bundle.is_acceptable_for_geometry() is True  # pixel intrinsics still valid
    assert any("square_size_mm is unmeasured" in p for p in bundle.validate())


def test_derived_pinhole_terms() -> None:
    bundle = _synthetic_calibrated_bundle()
    assert (bundle.fx_px, bundle.fy_px, bundle.cx_px, bundle.cy_px) == (
        1000.0,
        1000.0,
        W / 2,
        H / 2,
    )


# --- YAML round-trip ------------------------------------------------------------


def test_yaml_round_trip_preserves_the_bundle(tmp_path) -> None:
    bundle = _synthetic_calibrated_bundle()
    path = tmp_path / "cal.yaml"
    save_calibration(bundle, str(path))
    assert load_calibration(str(path)) == bundle


def test_load_missing_file_raises() -> None:
    with pytest.raises(CalibrationError, match="not found"):
        load_calibration("does/not/exist.yaml")


def test_open_tokens_become_none(tmp_path) -> None:
    path = tmp_path / "open.yaml"
    path.write_text(
        "camera_id: 0\n"
        "image_width_px: 1456\n"
        "image_height_px: 1088\n"
        "distortion_model: OPEN\n"
        "camera_matrix: OPEN\n"
        "distortion_coeffs: OPEN\n"
        "reprojection_error_px: OPEN\n"
        "board: OPEN\n"
        "calibrated: false\n",
        encoding="utf-8",
    )
    bundle = load_calibration(str(path))
    assert bundle.distortion_model is None
    assert bundle.camera_matrix is None
    assert bundle.board is None
    assert bundle.calibrated is False


# --- down-conversion into pod_config's intrinsics shape ----------------------


def test_uncalibrated_bundle_converts_to_all_open() -> None:
    bundle = CalibrationBundle(camera_id=0, image_width_px=W, image_height_px=H)
    cfg = to_intrinsics_config(bundle)
    assert cfg["calibrated"] is False
    for key in ("fx_px", "fy_px", "cx_px", "cy_px", "distortion_model", "distortion_coeffs"):
        assert cfg[key] == "OPEN"


def test_unclean_calibrated_bundle_also_converts_to_all_open() -> None:
    bundle = _synthetic_calibrated_bundle(camera_matrix=None)  # calibrated=True but broken
    cfg = to_intrinsics_config(bundle)
    assert cfg["calibrated"] is False
    assert cfg["fx_px"] == "OPEN"


def test_clean_bundle_converts_to_real_values() -> None:
    cfg = to_intrinsics_config(_synthetic_calibrated_bundle(), lens_description="synthetic lens")
    assert cfg["calibrated"] is True
    assert cfg["fx_px"] == 1000.0
    assert cfg["cx_px"] == W / 2
    assert cfg["distortion_model"] == "pinhole_radtan"
    assert cfg["lens_description"] == "synthetic lens"


def test_written_intrinsics_load_through_pod_config(tmp_path, configs_dir) -> None:
    """End to end: a clean synthetic bundle -> intrinsics YAML -> pod_config."""
    cam_path = tmp_path / "intrinsics_cam0.yaml"
    write_intrinsics_config(
        _synthetic_calibrated_bundle(), str(cam_path), lens_description="synthetic"
    )
    cfg = load_pod_config(
        str(configs_dir / "pod.yaml"),
        str(configs_dir / "airframes" / "_template.yaml"),
        (str(cam_path),),
    )
    intr = cfg.camera(0)
    assert intr.calibrated is True
    assert intr.fx_px == 1000.0
    intr.require_calibrated()  # must not raise


def test_written_intrinsics_from_open_bundle_still_raise_in_pod_config(
    tmp_path, configs_dir
) -> None:
    cam_path = tmp_path / "intrinsics_cam0.yaml"
    write_intrinsics_config(
        CalibrationBundle(camera_id=0, image_width_px=W, image_height_px=H), str(cam_path)
    )
    cfg = load_pod_config(
        str(configs_dir / "pod.yaml"),
        str(configs_dir / "airframes" / "_template.yaml"),
        (str(cam_path),),
    )
    intr = cfg.camera(0)
    assert intr.calibrated is False
    assert is_open(intr.fx_px)


# --- bundle_from_opencv ------------------------------------------------------


def test_bundle_from_opencv_assembles_a_valid_bundle() -> None:
    bundle = bundle_from_opencv(
        camera_id=1,
        image_size=(W, H),
        distortion_model="pinhole_radtan",
        rms_reprojection_error_px=0.3,
        camera_matrix=[[1200.0, 0.0, 700.0], [0.0, 1200.0, 540.0], [0.0, 0.0, 1.0]],
        distortion_coeffs=[0.01, -0.02, 0.0, 0.0, 0.0],
        per_view_errors_px=[0.3, 0.28, 0.31, 0.29],
        board=_synthetic_board(),
        calibration_id="ocv-0001",
        created="2026-09-08",
        tool="opencv-4.8 calibrateCamera",
    )
    assert bundle.calibrated is True
    assert bundle.num_views == 4
    bundle.require_valid()
