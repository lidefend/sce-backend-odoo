ARG ODOO_BASE_IMAGE=odoo:17.0@sha256:f88f646a0f5fc0b225995ee28953d9ce7367cc731b1756765114691fb97d18e5
ARG APT_MIRROR=default

FROM ${ODOO_BASE_IMAGE}

ARG APT_MIRROR
ARG SOURCE_SHA
LABEL org.opencontainers.image.revision=${SOURCE_SHA} \
      io.sce.runtime.rtl="unsupported-ltr-only"

USER root

# Odoo 17 compiles the supported LTR web bundle through Python/libsass.  The
# product does not offer RTL locales, so the legacy Node/less/rtlcss toolchain
# is not part of the production runtime.  The custom frontend is a separate
# static artifact served by its own nginx image; it is never baked into this
# Odoo image.
RUN if [ "${APT_MIRROR}" = "huaweicloud" ]; then \
        for source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do \
            [ ! -f "${source}" ] || sed -i \
                -e 's#deb.debian.org#repo.huaweicloud.com#g' \
                -e 's#security.debian.org#repo.huaweicloud.com#g' \
                -e 's#archive.ubuntu.com#repo.huaweicloud.com#g' \
                -e 's#security.ubuntu.com#repo.huaweicloud.com#g' \
                "${source}"; \
        done; \
    fi \
    && apt-get purge -y nodejs npm node-less libnode-dev libnode72 \
    && apt-get autoremove -y --purge \
    && rm -rf /usr/local/bin/rtlcss /usr/local/lib/node_modules/rtlcss \
    && rm -f /usr/share/java/libintl-*.jar \
    && ! command -v node \
    && ! command -v lessc \
    && ! command -v rtlcss \
    && ! find /usr/share/java -type f -name '*.jar' -print -quit | grep -q . \
    && ! dpkg-query -W -f='${binary:Package}\t${db:Status-Status}\n' 'node-*' 'libnode*' 2>/dev/null \
        | awk '$2 == "installed" { found=1 } END { exit(found ? 0 : 1) }' \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（工程化：集中在 requirements-odoo.txt）
COPY requirements-odoo.txt /tmp/requirements-odoo.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements-odoo.txt

# Product addons are copied explicitly. Customer, demo, acceptance-fixture and
# migration payload modules must be mounted as separate delivery artifacts.
RUN mkdir -p /mnt/product-addons /mnt/customer-addons /mnt/test-addons /mnt/source-addons /mnt/demo-addons \
    && ln -s /mnt/product-addons /mnt/extra-addons
COPY --chown=odoo:odoo addons/sc_norm_engine/ /mnt/product-addons/sc_norm_engine/
COPY --chown=odoo:odoo addons/smart_core/ /mnt/product-addons/smart_core/
COPY --chown=odoo:odoo addons/smart_scene/ /mnt/product-addons/smart_scene/
COPY --chown=odoo:odoo addons/smart_license_core/ /mnt/product-addons/smart_license_core/
COPY --chown=odoo:odoo addons/smart_construction_bootstrap/ /mnt/product-addons/smart_construction_bootstrap/
COPY --chown=odoo:odoo addons/smart_construction_core/ /mnt/product-addons/smart_construction_core/
COPY --chown=odoo:odoo addons/smart_construction_portal/ /mnt/product-addons/smart_construction_portal/
COPY --chown=odoo:odoo addons/smart_construction_scene/ /mnt/product-addons/smart_construction_scene/
COPY --chown=odoo:odoo addons/smart_construction_bundle/ /mnt/product-addons/smart_construction_bundle/
COPY --chown=odoo:odoo addons/smart_construction_seed/ /mnt/product-addons/smart_construction_seed/
COPY --chown=odoo:odoo addons/smart_owner_core/ /mnt/product-addons/smart_owner_core/
COPY --chown=odoo:odoo addons/smart_owner_bundle/ /mnt/product-addons/smart_owner_bundle/
COPY --chown=odoo:odoo addons_external/oca_server_ux/ /mnt/addons_external/oca_server_ux/

USER odoo
