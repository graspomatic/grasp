DESCRIPTION = "Test GPIO application"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://dataserver/*"
DEPENDS = "zeromq paho-mqtt-c paho-mqtt-cpp"
inherit pkgconfig cmake

S = "${WORKDIR}"

do_compile() {
    mkdir build
    cmake -Bbuild
    make -C build
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 build/dserv ${D}${bindir}
    install -m 0755 build/dserv_send ${D}${bindir}
}

