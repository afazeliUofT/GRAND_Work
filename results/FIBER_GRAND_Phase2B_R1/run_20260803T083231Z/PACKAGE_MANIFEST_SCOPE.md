# Package-generated result manifest scope

`MANIFEST.sha256` and the local return ZIP exclude `PACKAGE_CONSOLE.log` because the WSL wrapper is still writing that live log while the package finalizes. The wrapper later creates `COMMIT_READY_MANIFEST.sha256`, which covers the final committed console log and every other committed result artifact except the uncommitted return ZIP itself.
