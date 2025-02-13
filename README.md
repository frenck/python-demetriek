# Python: LaMetric Device API Client

[![GitHub Release][releases-shield]][releases]
[![Python Versions][python-versions-shield]][pypi]
![Project Stage][project-stage-shield]
![Project Maintenance][maintenance-shield]
[![License][license-shield]](LICENSE.md)

[![Build Status][build-shield]][build]
[![Code Coverage][codecov-shield]][codecov]
[![Quality Gate Status][sonarcloud-shield]][sonarcloud]
[![Open in Dev Containers][devcontainer-shield]][devcontainer]

[![Sponsor Frenck via GitHub Sponsors][github-sponsors-shield]][github-sponsors]

[![Support Frenck on Patreon][patreon-shield]][patreon]

Asynchronous Python client for LaMetric TIME devices.

## About

This package allows you to control and monitor an LaMetric TIME device
programmatically, directly on your local network. It is mainly created to allow
third-party programs to automate the behavior of the LaMetric device.

## Installation

```bash
pip install demetriek
```

## Usage

```python
"""Asynchronous Python client for LaMetric TIME devices."""

import asyncio

from demetriek import LaMetricDevice
from demetriek.models import (
    Goal,
    GoalData,
    Chart,
    Model,
    Notification,
    NotificationIconType,
    NotificationSound,
    Simple,
    Sound,
)


async def main():
    """Show example on controlling your LaMetric device."""

    # Create a alert notification, with 3 message frames.
    # First frame is a text, the second is a goal, last one
    # shows a chart. Additionally, the Win! notification sound
    # is played.
    notification = Notification(
        icon_type=NotificationIconType.ALERT,
        model=Model(
            frames=[
                Simple(text="Yeah", icon=18815),
                Goal(
                    icon=7956,
                    data=GoalData(
                        current=65,
                        end=100,
                        start=0,
                        unit="%",
                    ),
                ),
                Chart(data=[1, 2, 3, 4, 5, 4, 3, 2, 1]),
            ],
            sound=Sound(id=NotificationSound.WIN),
        ),
    )

    async with LaMetricDevice(
        "192.168.1.2",
        api_key="device_api_key",
    ) as lametric:
        # Raise audio volume... so we can hear the notification
        await lametric.audio(volume=100)
        await lametric.notify(notification=notification)


if __name__ == "__main__":
    asyncio.run(main())
```

## Changelog & Releases

This repository keeps a change log using [GitHub's releases][releases]
functionality.

Releases are based on [Semantic Versioning][semver], and use the format
of `MAJOR.MINOR.PATCH`. In a nutshell, the version will be incremented
based on the following:

- `MAJOR`: Incompatible or major changes.
- `MINOR`: Backwards-compatible new features and enhancements.
- `PATCH`: Backwards-compatible bugfixes and package updates.

## Contributing

This is an active open-source project. We are always open to people who want to
use the code or contribute to it.

We've set up a separate document for our
[contribution guidelines](.github/CONTRIBUTING.md).

Thank you for being involved! :heart_eyes:

## Setting up development environment

The easiest way to start, is by opening a CodeSpace here on GitHub, or by using
the [Dev Container][devcontainer] feature of Visual Studio Code.

[![Open in Dev Containers][devcontainer-shield]][devcontainer]

This Python project is fully managed using the [Poetry][poetry] dependency
manager. But also relies on the use of NodeJS for certain checks during
development.

You need at least:

- Python 3.11+
- [Poetry][poetry-install]
- NodeJS 18+ (including NPM)

To install all packages, including all development requirements:

```bash
npm install
poetry install
```

As this repository uses the [pre-commit][pre-commit] framework, all changes
are linted and tested with each commit. You can run all checks and tests
manually, using the following command:

```bash
poetry run pre-commit run --all-files
```

To run just the Python tests:

```bash
poetry run pytest
```

## Authors & contributors

The original setup of this repository is by [Franck Nijhof][frenck].

For a full list of all authors and contributors,
check [the contributor's page][contributors].

## License

MIT License

Copyright (c) 2022 - 2025 Franck Nijhof

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

[build-shield]: https://github.com/frenck/python-demetriek/actions/workflows/tests.yaml/badge.svg
[build]: https://github.com/frenck/python-demetriek/actions/workflows/tests.yaml
[codecov-shield]: https://codecov.io/gh/frenck/python-demetriek/branch/main/graph/badge.svg
[codecov]: https://codecov.io/gh/frenck/python-demetriek
[contributors]: https://github.com/frenck/python-demetriek/graphs/contributors
[devcontainer-shield]: https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode
[devcontainer]: https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/frenck/python-demetriek
[frenck]: https://github.com/frenck
[github-sponsors-shield]: https://frenck.dev/wp-content/uploads/2019/12/github_sponsor.png
[github-sponsors]: https://github.com/sponsors/frenck
[license-shield]: https://img.shields.io/github/license/frenck/python-demetriek.svg
[maintenance-shield]: https://img.shields.io/maintenance/yes/2025.svg
[patreon-shield]: https://frenck.dev/wp-content/uploads/2019/12/patreon.png
[patreon]: https://www.patreon.com/frenck
[poetry-install]: https://python-poetry.org/docs/#installation
[poetry]: https://python-poetry.org
[pre-commit]: https://pre-commit.com/
[project-stage-shield]: https://img.shields.io/badge/project%20stage-experimental-yellow.svg
[pypi]: https://pypi.org/project/demetriek/
[python-versions-shield]: https://img.shields.io/pypi/pyversions/demetriek
[releases-shield]: https://img.shields.io/github/release/frenck/python-demetriek.svg
[releases]: https://github.com/frenck/python-demetriek/releases
[semver]: http://semver.org/spec/v2.0.0.html
[sonarcloud-shield]: https://sonarcloud.io/api/project_badges/measure?project=frenck_python-demetriek&metric=alert_status
[sonarcloud]: https://sonarcloud.io/summary/new_code?id=frenck_python-demetriek
