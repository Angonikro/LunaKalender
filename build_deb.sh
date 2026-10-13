#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VERSION=1.3.9
BUILD="$ROOT/build/lunakalender"
DIST="$ROOT/dist"
rm -rf "$BUILD" "$DIST"
mkdir -p "$BUILD/DEBIAN" "$BUILD/usr/lib/lunakalender" "$BUILD/usr/bin" "$BUILD/usr/share/applications" "$BUILD/usr/share/pixmaps" "$DIST"
install -m 0644 "$ROOT/main.py" "$BUILD/usr/lib/lunakalender/main.py"
install -m 0644 "$ROOT/exchange.py" "$BUILD/usr/lib/lunakalender/exchange.py"
printf '%s\n' '#!/bin/sh' 'exec /usr/bin/python3 /usr/lib/lunakalender/main.py "$@"' > "$BUILD/usr/bin/lunakalender"
chmod 0755 "$BUILD/usr/bin/lunakalender"
install -m 0644 "$ROOT/debian/lunakalender.desktop" "$BUILD/usr/share/applications/lunakalender.desktop"
install -m 0644 "$ROOT/debian/lunakalender.svg" "$BUILD/usr/share/pixmaps/lunakalender.svg"
printf '%s\n' 'Package: lunakalender' "Version: $VERSION" 'Section: utils' 'Priority: optional' 'Architecture: all' 'Depends: python3, python3-tk, python3-gi, gir1.2-gtk-3.0, python3-pil, python3-ephem, alsa-utils, pulseaudio-utils' 'Maintainer: LunaKalender Project <maintainer@example.invalid>' 'Description: Grafischer Kalender mit lokaler Terminverwaltung' ' Monatskalender mit Terminen, Mondphasen, Ferien- und Feiertagskalender, Dark Mode, ICS- und VCF-Import und -Export.' > "$BUILD/DEBIAN/control"
chmod 0644 "$BUILD/DEBIAN/control"
chmod 0755 "$BUILD/DEBIAN"
chmod g-s "$BUILD/DEBIAN"
dpkg-deb --build --root-owner-group "$BUILD" "$DIST/lunakalender_${VERSION}_all.deb"
