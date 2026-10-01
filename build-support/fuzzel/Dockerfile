# syntax=docker/dockerfile:1
# Unmodified upstream launcher. New pixman is private, never installed into /usr.
FROM --platform=$BUILDPLATFORM debian@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a AS build
RUN dpkg --add-architecture arm64 && apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
       gcc-aarch64-linux-gnu libc6-dev-arm64-cross meson ninja-build pkg-config \
       ca-certificates libfontconfig-dev:arm64 libfcft-dev:arm64 \
       libpng-dev:arm64 libwayland-dev:arm64 libwayland-bin \
       libxkbcommon-dev:arm64 libtllist-dev:arm64 scdoc
ADD --checksum=sha256:95b6c022fc1f1c7ab586d47c1594417cc311bf41ea8f5f8b5641478da7b5cf3b \
    https://codeberg.org/dnkl/fuzzel/archive/1.15.0.tar.gz /tmp/fuzzel.tar.gz
ADD --checksum=sha256:d09c44ebc3bd5bee7021c79f922fe8fb2fb57f7320f55e97ff9914d2346a591c \
    https://cairographics.org/releases/pixman-0.46.4.tar.gz /tmp/pixman.tar.gz
ADD --checksum=sha256:2786b6b1b79965e313f2c289c12075b9ed700d41844810c51afda10ee329576b \
    https://gitlab.freedesktop.org/wayland/wayland-protocols/-/releases/1.41/downloads/wayland-protocols-1.41.tar.xz /tmp/protocols.tar.xz
COPY build-support/fuzzel/aarch64.ini /tmp/aarch64.ini
COPY build-support/fuzzel/Dockerfile /tmp/build.Dockerfile
COPY build-support/fuzzel/check-artifact.py /tmp/check-artifact.py
RUN mkdir /tmp/fuzzel /tmp/pixman /tmp/protocols \
    && tar -xf /tmp/fuzzel.tar.gz --strip-components=1 -C /tmp/fuzzel \
    && tar -xf /tmp/pixman.tar.gz --strip-components=1 -C /tmp/pixman \
    && tar -xf /tmp/protocols.tar.xz --strip-components=1 -C /tmp/protocols
RUN meson setup /tmp/protocols-build /tmp/protocols --prefix=/usr -Dtests=false \
    && meson install -C /tmp/protocols-build
RUN meson setup /tmp/pixman-build /tmp/pixman --cross-file=/tmp/aarch64.ini \
       --prefix=/opt/rocknix-fuzzel --libdir=lib --buildtype=release \
       -Ddefault_library=shared -Dtests=disabled -Ddemos=disabled \
    && ninja -C /tmp/pixman-build && meson install -C /tmp/pixman-build
RUN meson setup /tmp/fuzzel-build /tmp/fuzzel --cross-file=/tmp/aarch64.ini \
       --prefix=/opt/rocknix-fuzzel --buildtype=release \
       -Denable-cairo=disabled -Dsvg-backend=nanosvg \
       '-Dc_link_args=-Wl,-rpath,/opt/rocknix-fuzzel/lib' \
    && ninja -C /tmp/fuzzel-build && meson install -C /tmp/fuzzel-build \
    && aarch64-linux-gnu-strip /opt/rocknix-fuzzel/bin/fuzzel \
    && mkdir -p /opt/rocknix-fuzzel/share/source \
    && cp /tmp/fuzzel.tar.gz /tmp/pixman.tar.gz /tmp/protocols.tar.xz /tmp/aarch64.ini /tmp/build.Dockerfile /tmp/check-artifact.py /opt/rocknix-fuzzel/share/source/ \
    && cp /tmp/pixman/COPYING /opt/rocknix-fuzzel/share/source/pixman-COPYING
RUN python3 /tmp/check-artifact.py /opt/rocknix-fuzzel
FROM scratch AS artifact
COPY --from=build /opt/rocknix-fuzzel/ /opt/rocknix-fuzzel/
