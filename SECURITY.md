# Security and tool provenance

For this private review, report a suspected problem through a private repository issue, with a minimal sample you may share. Do not include credentials or unrelated personal/model-pack data.

The verified installer bundles the original, unmodified OGRE 13.3.2 converter/upgrader and zlib 1.2.11. Versions, source links and redistribution notices are documented in `io_ogre/THIRD_PARTY_NOTICES.txt`. Retaining these compatibility binaries does not claim they are current or free of vulnerabilities. A toolchain update needs compatibility and regression testing before replacing them.

Import conversion uses temporary copies and process timeouts. Export stages its output and failed imports roll back created Blender data. These safeguards do not replace review of untrusted assets or of externally configured executables. Keep Blender and your operating system maintained.

This repository has not been presented as an independent security audit, Linux validation or OGRENext engine certification. Release artifacts are checked against SHA-256 manifests so reviewers can identify the exact tested bytes.
