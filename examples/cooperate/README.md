# Cooperating colonies

Two colored colonies attract and can join through validated component bridges.

```console
python -m examples.cooperate.example
python -m scripts.generate_examples cooperate --seed 19 --nodes 120
```

The default uses seed 7 and the Porcelain palette. The library recipe is defined in `src/samples.py`; the Python entry point calls that same factory so CLI and Python results stay consistent. Edit the returned graph before building to explore settings.

- `Interaction.attraction`: Signed steering: negative repels, positive attracts.
- `allow_join`: Permit bridges between the specified colonies.
- `target_bridges`: Requested number of validated inter-colony connections.

`output/figure.png` and `output/figure.svg` show the same geometry. `output/results.json` records the seed, requested/achieved nodes, edges, stop reason, validation and timing. Large country and panorama recipes can take several minutes; `--nodes 120` is a smoke check, not a representative final composition.

Limit: Joining is a permission, not a guaranteed connection; ownership survives a join.

![Example output](output/figure.png)

[Example index](../README.md) | [User guide](../../docs/guide/index.html)
