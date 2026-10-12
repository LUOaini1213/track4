# Design

Use a stdlib contest_checkpoint module and a code-bound committed manifest with official pinned Hub provenance. The manifest contains SHA256/bytes for required weights/config/tokenizer files. Small metadata downloads were checked against Git blob IDs; weight identity came only from official LFS metadata, not a local file.

Local/env snapshots validate before loading. Cache/Hub resolving uses the fixed revision and minimal required-file allowlist, followed by the same validator and local-only Transformers load. Invalid explicit local source is terminal nodense; it must not silently switch to Hub. Diagnostics contain only bounded generic reasons and allowlisted filenames.

Build the fixed ZIP contents in a temporary directory inside the verified submission_dist. Validate copied model bytes and run the stdlib Agent import there. Publish by atomic ZIP replacement after all checks, with bounded stage renames and rollback. Never delete submission_dist wholesale.
