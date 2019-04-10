DESCRIPTION = "Test I2C connection to mpr121"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://mpr121.c"

S = "${WORKDIR}"

do_compile() {
    ${CC} mpr121.c ${LDFLAGS} -o mpr121 
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 mpr121 ${D}${bindir}
}

