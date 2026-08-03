# Package-generated manifest scope

`MANIFEST.sha256` covers the package-created result artifacts except the local return ZIP, its sidecar, and `PACKAGE_CONSOLE.log`. The console log is a live stream owned by the parent WSL wrapper and receives final status lines after this child creates its manifest. The wrapper's later `COMMIT_READY_MANIFEST.sha256` covers the exact committed console log and sidecar.
