"""Tests for Debian venv bundling."""

import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from colcon_uv.debian import build_bundle, prepare_debian
from colcon_uv.dependencies.install import UvPackage, install_dependencies


@pytest.fixture
def project(tmp_path):
    path = tmp_path / "source"
    path.mkdir()
    (path / "package.xml").write_text(
        '<package format="3"><name>bundle_test</name><version>0.1.0</version>'
        "<description>Test bundle</description>"
        '<maintainer email="test@example.com">Test</maintainer><license>MIT</license>'
        "<export><build_type>ament_python</build_type></export></package>"
    )
    (path / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n'
        '[project]\nname = "bundle_test"\nversion = "0.1.0"\n'
        '[project.scripts]\nbundle-test = "bundle_test:main"\n'
        "[tool.colcon-uv-ros]\n"
        '[tool.colcon-uv-ros.data-files]\n"share/bundle_test" = ["config"]\n'
    )
    (path / "bundle_test.py").write_text('def main():\n    print("bundle works")\n')
    (path / "config").mkdir()
    (path / "config/settings.yaml").write_text("test: true\n")
    return path


def test_prepare_preserves_dependencies(project):
    debian = project / "debian"
    debian.mkdir()
    (debian / "control").write_text(
        "Source: ros-jazzy-bundle-test\nBuild-Depends: debhelper, dh-python\n\n"
        "Package: ros-jazzy-bundle-test\nArchitecture: all\n"
        "Depends: ${python3:Depends}, ${misc:Depends}, ros-jazzy-rclpy\n"
    )
    (debian / "rules").write_text(
        'export PYBUILD_INSTALL_ARGS=--prefix "/opt/ros/jazzy"\n'
    )
    prepare_debian(project)
    control = (debian / "control").read_text()
    assert "ros-jazzy-rclpy" in control
    assert "Architecture: any" in control
    assert (
        "debian/ros-jazzy-bundle-test/opt/ros/jazzy" in (debian / "rules").read_text()
    )


def test_bundle_install_is_not_editable(project, tmp_path):
    with patch("colcon_uv.dependencies.install.subprocess.run") as run:
        install_dependencies(
            UvPackage(project), tmp_path / "install", True, bundle=True
        )
    create, install = [call.args[0] for call in run.call_args_list]
    assert "--relocatable" in create
    assert "--system-site-packages" in create
    assert create[create.index("--python") + 1] == "/usr/bin/python3"
    assert "-e" not in install


@pytest.mark.parametrize(
    "old,new",
    [
        (
            "[tool.colcon-uv-ros]",
            '[tool.colcon-uv-ros]\nextra-site-packages = ["/tmp/external"]',
        ),
        ('"share/bundle_test"', '"../outside"'),
        ('["config"]', '["missing"]'),
        ("ament_python", "ament_cmake"),
    ],
)
def test_reject_nonportable_inputs(project, tmp_path, old, new):
    target = project / ("package.xml" if old == "ament_python" else "pyproject.toml")
    target.write_text(target.read_text().replace(old, new))
    with patch("colcon_uv.debian.install_dependencies") as install:
        with pytest.raises(ValueError):
            build_bundle(project, tmp_path / "install")
        install.assert_not_called()


@pytest.mark.skipif(
    os.environ.get("COLCON_UV_TEST_BUNDLE") != "1",
    reason="Set COLCON_UV_TEST_BUNDLE=1 to run uv (may download build dependencies)",
)
def test_bundle_runs_after_source_and_build_are_removed(project, tmp_path):
    output = tmp_path / "build" / "install"
    build_bundle(project, output)
    installed = tmp_path / "installed"
    shutil.copytree(output, installed, symlinks=True)
    shutil.rmtree(project)
    shutil.rmtree(output.parent)
    env = dict(os.environ, PATH="/usr/bin:/bin")
    result = subprocess.check_output(
        [str(installed / "lib/bundle_test/bundle-test")], env=env, text=True, cwd="/"
    )
    assert result.strip() == "bundle works"
    # ros2 run searches recursively and must find exactly one matching executable.
    assert list((installed / "lib/bundle_test").rglob("bundle-test")) == [
        installed / "lib/bundle_test/bundle-test"
    ]
    assert (installed / "share/bundle_test/config/settings.yaml").is_file()
    assert (
        installed / "share/ament_index/resource_index/packages/bundle_test"
    ).is_file()
    python = installed / "lib/colcon_uv/bundle_test/venv/bin/python"
    module = subprocess.check_output(
        [str(python), "-c", "import bundle_test; print(bundle_test.__file__)"],
        text=True,
        cwd="/",
    ).strip()
    assert Path(module).relative_to(installed)
