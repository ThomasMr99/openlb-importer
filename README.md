# openlb-importer

Load [OpenLB](https://www.openlb.net/) simulation output (VTK) into numpy arrays.

Note: This project uses AI-generated code. Please review the code carefully before using it in production.

## Installation

```bash
pip install "git+https://github.com/ThomasMr99/openlb-importer.git@v0.1.0"
```

## Usage

```python
from openlb_importer import EnsembleManager, load_ensemble_member

# Manage a whole ensemble (every subdirectory is one member)
ensemble = EnsembleManager("path/to/ensemble", use_pickle=False)
member = ensemble.get_ensemble_member("member_name")

# Or load a single member directly
member = load_ensemble_member("path/to/ensemble", "member_name")
```

Each member is a dict with the keys:

| Key            | Description                                          |
|----------------|------------------------------------------------------|
| `identifier`   | Directory name of the member                         |
| `index`        | Position of the member in the ensemble               |
| `n_dims`       | 2 or 3                                               |
| `v_array`      | Velocity per time step, shape `(t, x, y, [z,] dims)` |
| `t_array`      | Physical time of each time step                      |
| `points_array` | Coordinates of the grid points                       |

## Expected directory structure

```
ensemble/
└── member_name/
    ├── <name>.dat        # OpenLB unit converter output (contains physDeltaT)
    └── vtkData/
        ├── <name>.pvd
        └── ...           # .vtm / .vti files referenced by the .pvd
```

The velocity field must be stored as `physVelocity`.

## Caching

With `use_pickle=True` (default), each loaded member is cached as `data.pkl`
inside its member directory. Delete these files with
`EnsembleManager.clear_pickled_ensemble_members_for_path(path)`.

## License

MIT
