# UK / colour only

Population controls colour; geometry uses uniform dimensions and spacing.

```console
python -m examples.uk_colors.example
python -m scripts.generate_examples uk_colors --seed 19 --nodes 120
```

The default uses seed 7 and the Porcelain palette. The library recipe is defined in `src/samples.py`; the Python entry point calls that same factory so CLI and Python results stay consistent. Edit the returned graph before building to explore settings.

- `color_map`: A spatial scalar mapped through colour stops; geometry remains independent.

`output/figure.png` and `output/figure.svg` show the same geometry. `output/results.json` records the seed, requested/achieved nodes, edges, stop reason, validation and timing. Large country and panorama recipes can take several minutes; `--nodes 120` is a smoke check, not a representative final composition.

Limit: Colour encodes log population density, not node count.

![Example output](output/figure.png)

[Example index](../README.md) | [User guide](../../docs/guide/index.html)
