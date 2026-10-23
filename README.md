# colcon-uv

[![CI](https://github.com/nzlz/colcon-uv/actions/workflows/ci.yml/badge.svg)](https://github.com/nzlz/colcon-uv/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-70%25-brightgreen)](https://github.com/nzlz/colcon-uv/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/colcon-uv.svg)](https://pypi.org/project/colcon-uv/)

A **colcon extension** for building and testing Python packages that use **[uv](https://github.com/astral-sh/uv)** for dependency management, and C++ `ament_cmake` packages whose dependencies come from PyPI.

Intended, but not limited, to use with **ROS 2**. This extension provides a modern alternative to traditional setuptools-based or even poetry-based Python package management in ROS environments.

## Features

- **Fast Dependency Management**: Leverages UV's lightning-fast dependency resolution and installation
- **Modern Python Packaging**: Support for `pyproject.toml`-based packages following PEP 517/518 standards
- **ROS Integration**: Seamless integration with colcon build system and ROS package management
- **Dependency Isolation**: Prevents dependency conflicts between packages
- **C++ packages with PyPI dependencies**: an `ament_cmake` package can take libraries that ship as wheels (CasADi, cmeel-packaged Eigen, ...) from its own venv

## Installation

**Important**: This extension must be installed in the same environment as colcon to be discoverable by colcon's plugin system. Typically this means system-wide installation.

### Install from PyPi (last tagged version)

```bash
# Using pip
pip install colcon-uv --break-system-packages

# Using uv
uv pip install --system --break-system-packages colcon-uv
```

### Install from GitHub (development version)

```bash
# Using pip
pip install git+https://github.com/nzlz/colcon-uv.git#subdirectory=colcon_uv --break-system-packages

# Using uv
uv pip install --system --break-system-packages git+https://github.com/nzlz/colcon-uv.git#subdirectory=colcon_uv
```

### Install from cloned source (local development)

```bash
pip install --break-system-packages --target /usr/lib/python3/dist-packages -e colcon_uv
```

## Quick Start

For practical examples, see the test examples in this repository:

- **Python packages** built by colcon-uv: [`tests/examples/uv_ament_python_example`](tests/examples/uv_ament_python_example/pyproject.toml), and [`tests/examples/uv_ament_cmake_example`](tests/examples/uv_ament_cmake_example/pyproject.toml) (a Python package that also carries a `CMakeLists.txt`; colcon-uv builds it as Python and the CMake file is not used)
- **C++ packages built by ament_cmake** with PyPI dependencies (`build-type = "ament_cmake"`): [`tests/examples/uv_cpp_example`](tests/examples/uv_cpp_example/pyproject.toml), which builds against Eigen from the `cmeel-eigen` wheel

## Usage

### Automatic Dependency Installation

When you run `colcon build`, dependencies are automatically installed using UV. No additional steps required!

```bash
# Dependencies are automatically installed during build
colcon build --packages-select my_package
```

### Manual Dependency Installation (Optional)

Similar to `rosdep install`, you can optionally install dependencies standalone before building:

```bash
# Install dependencies for all packages in src/
colcon uv install --base-paths src
```

**Note**: This step is optional since `colcon build` automatically handles dependency installation. Use this when you want to pre-install dependencies or troubleshoot dependency issues separately from the build process.

## Build a Python package as a local deb

For a `colcon-uv` **Python package**, bloom's generated build rules can be replaced
with a venv-bundling build, similar to `catkin_virtualenv`:

```bash
# Install build tools; install colcon-uv and uv in the build environment too.
sudo apt install python3-bloom python3-rosdep python3-all python3-setuptools dh-python debhelper fakeroot
cd /path/to/your_python_package
bloom-generate rosdebian --os-name ubuntu --os-version noble --ros-distro jazzy
colcon uv prepare-debian .
dpkg-buildpackage -us -uc -b
```

Use `ament_python` in `package.xml`. Declare ROS and system dependencies there
using resolvable rosdep keys (e.g. `rclpy`); keep bundled PyPI dependencies in
`pyproject.toml`. The build environment must already provide `uv` and `colcon_uv`;
an unresolved `colcon_uv` build dependency in the manifest will stop bloom.
If colcon-uv is in a venv, set `COLCON_UV_PYTHON=/path/to/venv/bin/python` for
`dpkg-buildpackage` (create that venv with `--system-site-packages`).

The deb contains a non-editable, relocatable venv under `lib/colcon_uv/<ROS-package>/venv`,
ROS executable wrappers, the ament index marker, and configured data files.
Neither uv nor the original sources are needed at runtime. Build on the target
OS/architecture with its `/usr/bin/python3`; the deb constrains Python's minor version.
This overrides `.python-version`; the project's `requires-python` must allow it.

This is a local binary packaging workaround, not a ROS build-farm release workflow.
Re-run `prepare-debian` after every bloom generation; it replaces `debian/rules`.
It uses the existing dependency resolution (all extras/groups, no `uv.lock`) and
may access package indexes during the build. `extra-site-packages` and C++ packages
are unsupported. Tests must be run separately. Wheel stripping and automatic
shared-library dependency scanning are disabled; declare any required system
libraries in `package.xml`. Native wheels must themselves support relocation.

## Configuration

Refer to [colcon_uv/README.md](colcon_uv/README.md#configuration), and to [CHANGELOG.md](CHANGELOG.md) for what changed between versions.

## References

This project is inspired by and builds upon:

- [colcon-poetry-ros](https://github.com/UrbanMachine/colcon-poetry-ros) - Poetry integration for ROS packages
- [colcon-ros](https://github.com/colcon/colcon-ros/tree/colcon-python-project) - Experimental ROS support for colcon
- [uv](https://github.com/astral-sh/uv) - An extremely fast Python package installer and resolver
