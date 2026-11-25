# Plasma Ions China — COPR packaging

This repository contains the [COPR](https://copr.fedorainfracloud.org/) packaging for
[arenekosreal/plasma-ions-china](https://github.com/arenekosreal/plasma-ions-china).
Only the RPM spec, COPR metadata, README and license are kept here; the source
archive is downloaded from the upstream GitHub repository during the build.

The upstream project description and developer documentation are preserved at
the bottom of this file.

## Build targets

| Distribution | Chroots |
| --- | --- |
| Fedora 44 | `fedora-44-x86_64`, `fedora-44-aarch64` |
| Fedora 45 | `fedora-45-x86_64`, `fedora-45-aarch64` |
| Fedora Rawhide | `fedora-rawhide-x86_64`, `fedora-rawhide-aarch64` |
| openSUSE Tumbleweed | `opensuse-tumbleweed-x86_64`, `opensuse-tumbleweed-aarch64` |

The chroot list lives in `copr/chroots.txt` and is the single source of truth for
both the setup script and the GitHub Actions workflow.

## Local build

The source RPM can be created without installing the package build
dependencies. You only need the RPM build tools (`rpm-build`, plus `curl` or
`rpmdevtools`):

```bash
# Auto-detects the host Plasma version
ci/build-srpm.sh plasma-ions-china.spec out/

# Or set it explicitly
PLASMA_VERSION=6.8.3 ci/build-srpm.sh plasma-ions-china.spec out/
```

Or use the COPR Makefile method:

```bash
make -f .copr/Makefile srpm outdir=out
```

Submit the result with:

```bash
copr-cli build owner/plasma-ions-china -r fedora-rawhide-x86_64 out/plasma-ions-china-*.src.rpm
```

## COPR setup

1. Create the COPR project with all required chroots:

   ```bash
   copr/setup-project.sh owner/plasma-ions-china
   ```

   The script is idempotent and adds the chroots to an existing project.

2. Add these GitHub repository settings:

   - Variable `COPR_PROJECT`: the project name, for example `owner/plasma-ions-china`.
   - Secret `COPR_API_TOKEN`: the full contents of your `~/.config/copr` file.

3. Allow GitHub Actions to push to `main` (or adjust the workflow to open a pull
   request instead). The workflow commits updated version and release metadata
   back to the repository.

## Automation

`.github/workflows/copr.yml` runs on every push to `main`, on a daily schedule
and on manual dispatch. On each run it:

1. Resolves the upstream `main` commit and the newest release tag. Commits after
   the tag are packaged as `X.Y.Z^YYYYMMDDHHMMSSgitHASH` snapshots, so every
   mainline update is picked up.
2. Checks the current KDE Plasma version from download.kde.org and every
   Fedora/openSUSE family present in `copr/chroots.txt`.
3. Updates `Version`, `%global commit` and the source checksum in the spec when
   needed, and stores the last seen Plasma versions in `packaging/state.json`.
4. Groups the chroots by their Plasma version, builds one source RPM per
   distinct version and submits each SRPM only to its matching chroots.

The scheduled run only submits a build when the upstream `main` commit or a KDE
version changes. A manual dispatch always submits a build. Commits made by the
workflow use the `[skip ci]` marker, so the workflow does not loop on its own
push.

## Packaging notes

- The RPM `Release` is the target Plasma version, for example
  `0.1.3-6.8.3.fc44` (no literal `plasma` prefix). A rebuild against a newer
  Plasma ABI therefore always sorts as an upgrade.
- Only the `nmccn` ion is built. The `qweather` ion needs per-user QWeather API
  credentials at configure time, so it is skipped by upstream CMake when those
  credentials are absent.
- The package uses the system `libplasmaweatherion` headers from
  `kdeplasma-addons-devel` / `kdeplasma6-addons-devel` instead of downloading
  the kdeplasma-addons tarball during the build.
- Legacy ions for KDE < 6.5 are disabled.

---

# Plasma Weather China Sources

> This section is the upstream README, kept for reference. The source tree is
> not part of this packaging repository; see the upstream project for building
> from source.

<p align="center">
   <br>
   <img src="https://raw.githubusercontent.com/arenekosreal/plasma-ions-china/main/image/search.png" alt="Search Weather Station" height="300" />
   <img src="https://raw.githubusercontent.com/arenekosreal/plasma-ions-china/main/image/weather.png" alt="Weather Report Page" height="300" />
   <br>
</p>

A collection of ions for Chinese users.

## What is Ion

Ion is KDE's weather source engine, which can provide weather data to its weather widget (org.kde.plasma.weather).
KDE itself has some Ions, like `wetter.com`, `noaa`, etc. If you have used the weather widget, you will not miss them.

## Why create this

Although KDE itself has some Ions, they are not suitable for Chinese users. Only a few cities can be found and their reports are too brief.
That's why this project is created. We collect some weather apis focus on Chinese cities so we can have a better experience when using KDE's weather widget.

## Usage

### Installing

You can find if your distribution has this project packaged here.
If so, you are in luck to install it directly using the related package manager, instead [building](#building) it yourself.

**DISCLAIMER:** Those packages are not maintained by us, use it at your own risk.

[![Packaging status](https://repology.org/badge/vertical-allrepos/plasma-ions-china.svg)](https://repology.org/project/plasma-ions-china/versions)

#### Other Repositories

They are not indexed above for various reasons, you can consider using them if you are using those repository.

- [archlinuxcn/plasma-ions-china-git](https://github.com/archlinuxcn/repo/tree/master/archlinuxcn/plasma-ions-china-git)
- [kde-misc/plasma-ions-china](https://github.com/gentoo-zh/overlay/tree/master/kde-misc/plasma-ions-china)

### Building

1. Install [dependencies](#dependencies)
2. Clone this repository using git or downloading archive
3. Build and install the project:

   ```bash
   cmake -B build -S "/path/to/plasma-ions-china" -DCMAKE_BUILD_TYPE=Release
   cmake --build  build
   cmake --install build
   ```

   Available cmake options to control configuring:
   - `PLASMA_IONS_CHINA_ENABLE_MODERN`: If enable modern ions used for KDE >= 6.5, defaults to `ON`.
   - `PLASMA_IONS_CHINA_ENABLE_LEGACY`: If enable legacy ions used for KDE < 6.5, defaults to `OFF`.
   - `PLASMA_IONS_CHINA_USE_SYSTEM_HEADERS`: If use system headers for libplasmaweatherion and libplasmaweatherdata, defaults to `OFF`.

      Most of the time the default value works well. If you want to set to `ON`,
      please ensure you have those headers installed in `<prefix>/include/plasma/weather`.
      See [here](https://invent.kde.org/plasma/kdeplasma-addons/-/merge_requests/933) for more info.

   - `EXTERNAL_PROJECT_URL_KDEPLASMA_ADDONS`: Custom url to `kdeplasma-addons`' source tarball.

      Useful for offline building. Provide `file://` url to point to local file.
      You need to ensure your tarball is valid and passes checksum.

   - `PLASMA_IONS_CHINA_QWEATHER_PRIVATE_KEY`: The path to the private key of your QWeather project token.
   
      Technical detail: It should be PEM format and looks like this:
      ```
      -----BEGIN PRIVATE KEY-----
      ....<base64>....
      -----END PRIVATE KEY-----
      ```
      The private key must **NOT** have a password, the last 32 byes of the decoded private key must be the seed.
      You can use `openssl genpkey -algorithm ED25519 -out ed25519-private.pem` to generate the private key.
      Use `openssl pkey -pubout -in ed25519-private.pem > ed25519-public.pem` to get the public key to be registered to QWeather.
      
      If this option is missing, the qweather ion will be skipped.
      
   - `PLASMA_IONS_CHINA_QWEATHER_KID`: The key ID given by QWeather after you registered the public key. 
   
      If this option is missing, the qweather ion will be skipped.

   - `PLASMA_IONS_CHINA_QWEATHER_ISS`: The developer ID given by QWeather after you registered an account.

      If this option is missing, the qweather ion will be skipped.

   - `PLASMA_IONS_CHINA_QWEATHER_SUB`: The project ID given by QWeather after you created the project.
   
      If this option is missing, the qweather ion will be skipped.
      
   - `PLASMA_IONS_CHINA_QWEATHER_API_HOST`: The api host given by QWeather after you registered an account.
   
      If this option is missing, the qweather ion will be skipped.

   There is no need to set `CMAKE_INSTALL_PREFIX`, because it will follow KDE's and not be configurable. That means most of the time it is `/usr`.
   Because of this, it is strongly recommended that you should create a package for your Linux Distribution.

4. Open KDE's weather widget (org.kde.plasma.weather) and search Chinese cities like Beijing, etc.

   For just experiencing, you can run `plasmoidviewer -a org.kde.plasma.weather` after you installed `plasma-sdk`.

### Dependencies

These dependencies are archlinux's names, for other distributions, please adjust them as you like.
For example, the runtime dependencies still need their development files at buildtime, on those distributions that split them into independent packages like Debian/Fedora, etc, you may need to install them, too.
But those development files are just buildtime dependencies, you can remove them as you like after building.

#### Runtime dependencies

- qt6-base
- plasma-workspace (If you enabled the legacy ions)
- kdeplasma-addons (If you enabled the modern ions)
- libsodium (If you enabled the qweather ion)

#### Buildtime extra dependencies

- cmake
- extra-cmake-modules
- git (If you want to automatically set project version from git tag)

## Ions

|Name|Data Source|Reverse Engineered|Modern|Legacy|Anoymous Accessable|
|----|-----------|------------------|------|------|---------------------|
|nmccn|[National Meteorological Center of China](https://www.nmc.cn)|Y|[Y](./src/nmccn)|[Y](./src/plasma_engine_nmccn)|Y|
|qweather|[QWeather](https://www.qweather.com)|N|[Y](./src/qweather)|N|N|

### Notes for the Ions

#### National Meteorological Center of China

The passed daytime report is not available when is night. There is no cache mechanism, so you'll find that the daytime's report is missing at night.

#### QWeather

We only need to access [GeoAPI](https://dev.qweather.com/docs/api/geoapi/), [Current Weather](https://dev.qweather.com/docs/api/weather/weather-current/), [Daily Weather](https://dev.qweather.com/docs/api/weather/weather-daily-forecast/) and [Warning](https://dev.qweather.com/docs/api/warning/) apis, you may limit the key's permission for security reasons. 
Please also note [QWeather's pricing tiers](https://dev.qweather.com/docs/finance/pricing/) so you will not have unexpected payments.

## Adding new ion

We take `nmccn` as an example here about how to add a new ion:

1. Prepare a id for your ion.

   We are using `nmccn` here.

2. Add your ions to cmake.

   Modify [src/CMakeLists.txt](./src/CMakeLists.txt), add the id you chosen to the list `ION_NAMES`.

   See [CMake Documentation](https://cmake.org/cmake/help/latest/command/set.html#set-normal-variable) for how to update it correctly. 

3. Create directory to storage sources in [src](./src).

   We created `nmccn` and `plasma_engine_nmccn` here to storage modern and legacy versions of ion.
   Modern ions should use the id, while legacy ions must prefix id with `plasma_engine_`.

   Both directories are optional, we only add your directory if it really exists.

4. Create `CMakeLists.txt` for your directories.

   Directories created at step above are added only when they have a `CMakeLists.txt` file.
   You must create a target which name is the directory in the file.
   For example, [`nmccn/CMakeLists.txt`](./src/nmccn/CMakeLists.txt) will create a target named `nmccn`,
   while [`plasma_engine_nmccn/CMakeLists.txt`](./src/plasma_engine_nmccn/CMakeLists.txt) will create a target named `plasma_engine_nmccn`.

   We add target definition `KDE_WEATHER_TRANSLATION_DOMAIN` to the ion target based on the ion type.

   In the `CMakeLists.txt` of modern ion, you must add target by using instruction `kcoreaddons_add_plugin` and set `INSTALL_NAMESPACE` to `${ION_INSTALL_NAMESPACE}`.
   The added target must link to target `Plasma::Weather::Ion`.

   In the `CMakeLists.txt` of legacy ion, you can use the standard `add_library` command to add target.
   But you must set `DESTINATION` to `${PLASMA5SUPPORT_DATAENGINES_PLUGINDIR}` in `install` instruction.
   The added target must link to target `Plasma::Weather::IonLegacy`.

   In the `CMakeLists.txt` of both ions, you can use `ecm_qt_declare_logging_category` to generate logger function for using in `qDebug`, `qWarning`, etc.
   You can also use commands like `find_package`, `target_link_libraries`, etc to customize your ions targets.

5. Create metadata for your ions.

   Metadata is a json file, which will be used by macro `K_PLUGIN_CLASS_WITH_JSON`.

   For modern ion, it looks like this like in [nmccn/metadata.json](./src/nmccn/metadata.json):
   ```json
   {
      "KPlugin": {
         "Description": "My custom ion",
         "Description[$LANG]": "Translated into $LANG of `My custom ion`",
         "Icon": "example-icon-name",
         "Name": "Custom",
         "Name[$LANG]": "Translated into $LANG of `Custom`"
      },
      "Comment": "Some comments about the ion",
      "Quality": 1
   }
   ```
   The `$LANG` is the language code like `zh_CN`, etc and optional.

   For legacy ion, it looks like this like in [plasma_engine_nmccn/metadata.json](./src/plasma_engine_nmccn/metadata.json):
   ```json
   {
      "KPlugin": {
         "Description": "My custom ion",
         "Description[$LANG]": "Translated into $LANG of `My custom ion`",
         "Icon": "example-icon-name",
         "Name": "Custom",
         "Name[$LANG]": "Translated into $LANG of `Custom`"
      },
      "X-KDE-ParentApp": "weatherengine"
   }
   ```
   The `$LANG` is the language code like `zh_CN`, etc and optional.

   Save the metadata in a json file, like `metadata.json`.

6. Add source code.

   You need to use `#include <ion.h>` to introduce `IonInterface` or `Ion` based on the target you link your ion to.
   This file is provided by `Plasma::Weather::IonLegacy` or `Plasma::Weather::Ion` based on your cmake instruction.

   You need to use `K_PLUGIN_CLASS_WITH_JSON` after added `#include <KPluginFactory>` in your source code to embed the metadata created above into library.

   For modern ion, see [ion.h](./include/plasma/weather/ion.h) for more about `Ion`.
   You need to implement those methods:
   - `void Ion::findPlaces(std::shared_ptr<QPromise<std::shared_ptr<Location>>> promise, const QString &searchString)`
   - `void Ion::fetchForecast(std::shared_ptr<QPromise<std::shared_ptr<Forecast>>> promise, const QString &placeInfo)`


   For legacy ion, see [ion.h](/usr/include/plasma5support/weather/ion.h) for more about `IonInterface`,
   see [Ions](https://techbase.kde.org/Projects/Plasma/Weather/Ions) for more about the `source` and how to respond.
   You need to implement those methods:
   - `void IonInterface::reset()`
   - `bool IonInterface::updateIonSource(const QString &source)`

   After installed built libraries, you can use `plasmoidviewer -a org.kde.plasma.weather` to see if your ion works in actual situation.
   If you just want to check your legacy ion, you can use `plasmaengineexplorer` to do that.
   Both tools are provided by `plasma-sdk`.

   If you need to see your log outputs, you can set environment variable `QT_LOGGING_RULES=${LOGGING_CATEGORY}.debug=true` to `plasmaengineexplorer` or `plasmoidviewer`.
   `${LOGGING_CATEGORY}` is the `CATEGORY_NAME` when you use `ecm_qt_declare_logging_category` to generate logger function.

7. Update translation template and the translations

   We use gettext to provide a localized user interface.
   You need to run command like `xgettext -o po/plasma_ions_china.pot -d plasma_ions_china -C -ki18n src/**/*.cpp` to update translation template.
   If you are familiar with some languages, it is also recommended to update the corresponding `po` files.

   We have also added 2 cmake targets: `update-pot` and `update-po` to update them accordingly.
   Feel free to use `cmake --build <build-dir> --target <target-name>` to let cmake generate updated translation files.
   But they just update existing files, you still have to work manually if you are going to translate for a new locale.

8. Update documentation

   You need to update [Ions](#ions) table in this README by following existing entries.

## Star History

<a href="https://www.star-history.com/?repos=arenekosreal%2Fplasma-ions-china&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=arenekosreal/plasma-ions-china&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=arenekosreal/plasma-ions-china&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=arenekosreal/plasma-ions-china&type=date&legend=top-left" />
 </picture>
</a>
