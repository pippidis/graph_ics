# Boundary Fine

Same GeoJSON outline and hole. Border visibility, colour and width affect rendering; containment always uses the supplied polygon.

```console
python -m examples.boundary_fine.example
python -m scripts.generate_examples boundary_fine --seed 19 --nodes 120
```

Edit `config.yaml` to explore the illustrated setting. `config.json` is the equivalent starting configuration; both use the same scene schema. Coordinates are `[x, y]` in world units. The Python example reads the adjacent YAML file, resolves relative inputs there, and accepts an optional seed or node-cap override.

Outputs: `output/figure.png`, `output/figure.svg`, and `output/results.json` with achieved counts, growth status and validation. The configured node count is a cap; tight contours, large rings and hard angle rules can leave gaps. Font availability affects text contours.

![Example output](output/figure.png)

[Scene schema](../../scripts/site_content/SCENES.md) | [Example index](../README.md)
