# Implementation and validation

1. Bind official model manifest to shared validator.
2. Route runtime/source selection and vendor through validator; retain pinned Hub revision and diagnostics.
3. Stage and validate package before atomically replacing old ZIP.
4. Add stdlib synthetic asset/loader/pack failure tests; keep fake trust explicit.
5. Run full stdlib unittest and synthetic dialogue, check manifest trust and immutable historical source/results.
6. Update repository offline spec and result boundaries, commit locally.
7. Apply only public technical files to the private branch, add complete module whitelist, repeat its offline checks and freeze.

Completed local checks: public full stdlib suite 163 tests (162 pass, 1 real-ZIP skip),
synthetic dialogue and transaction tests pass. New code does not run an encoder
forward. Official pinned metadata provenance is in the manifest; historical
rank/config/evaluator/data/report bytes remain unchanged. No push/publication.
