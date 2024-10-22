import os
from typing import Dict, List

from genmypy import cli

from .utils import assert_output_equals, message_path, temporary_directory


def test_std_msgs(expected_dir, std_msgs_path):
    # type: (str, str) -> None
    package = "std_msgs"  # type: str
    package_files = [
        message_path(std_msgs_path, "Byte"),
        message_path(std_msgs_path, "Duration"),
        message_path(std_msgs_path, "Header"),
        message_path(std_msgs_path, "Time"),
    ]  # type: List[str]
    search_paths = {
        "std_msgs": [message_path(std_msgs_path)],
    }  # type: Dict[str, List[str]]
    expected_dir = os.path.join(expected_dir, package, "msg")

    with temporary_directory() as td:
        cli.run_message(package, package_files, td, search_paths)

        assert_output_equals(expected_dir, td, "_Byte.pyi")
        assert_output_equals(expected_dir, td, "_Duration.pyi")
        assert_output_equals(expected_dir, td, "_Header.pyi")
        assert_output_equals(expected_dir, td, "_Time.pyi")


def test_sensor_msgs(expected_dir, std_msgs_path, sensor_msgs_path):
    # type: (str, str, str) -> None
    package = "sensor_msgs"  # type: str
    package_files = [
        message_path(sensor_msgs_path, "JoyFeedback"),
        message_path(sensor_msgs_path, "PointCloud2"),
        message_path(sensor_msgs_path, "Image"),
    ]  # type: List[str]
    search_paths = {
        "std_msgs": [message_path(std_msgs_path)],
        "sensor_msgs": [message_path(sensor_msgs_path)],
    }  # type: Dict[str, List[str]]
    expected_dir = os.path.join(expected_dir, package, "msg")

    with temporary_directory() as td:
        cli.run_message(package, package_files, td, search_paths)

        assert_output_equals(expected_dir, td, "_JoyFeedback.pyi")
        assert_output_equals(expected_dir, td, "_PointCloud2.pyi")
        assert_output_equals(expected_dir, td, "_Image.pyi")
