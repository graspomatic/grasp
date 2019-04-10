DESCRIPTION = "Test GPIO application"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://digout_periodic.c"
DEPENDS = "\
    libgpiod \
"

S = "${WORKDIR}"

do_compile() {
    ${CC} digout_periodic.c ${LDFLAGS} -o digout_periodic -lgpiod
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 digout_periodic ${D}${bindir}
}

