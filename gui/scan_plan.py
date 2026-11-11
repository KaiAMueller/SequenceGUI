from itertools import product

import numpy as np


def build_scan_plan(dimensions):
    """
    Generate an ordered list of MultiRun scan points.

    Variables within the same dimension change together.
    Different dimensions form a Cartesian product.

    The last dimension changes fastest, matching the
    existing SequenceGUI MultiRun implementation.
    """

    if not dimensions:
        raise ValueError("No scan dimensions defined")

    dimension_points = []

    for dim_name, dim_data in dimensions.items():
        steps = int(dim_data["steps"])

        if steps < 1:
            raise ValueError(
                f"{dim_name}: steps must be positive"
            )

        variable_values = {}

        for var_name, var_data in dim_data["variables"].items():

            mode = var_data["mode"]

            if mode == "linear":
                values = np.linspace(
                    float(var_data["min"]),
                    float(var_data["max"]),
                    steps
                ).tolist()

            elif mode == "data list":
                values = list(var_data["datalist"])

                if len(values) != steps:
                    raise ValueError(
                        f"{var_name}: expected {steps} values, "
                        f"got {len(values)}"
                    )

            else:
                raise ValueError(
                    f"Unsupported scan mode: {mode}"
                )

            variable_values[var_name] = values

        # Construct one parameter dictionary per step.
        points = []

        for i in range(steps):
            point = {
                name: values[i]
                for name, values in variable_values.items()
            }

            points.append(point)

        dimension_points.append(points)

    # Combine dimensions, preserving their existing order.
    scan_plan = []

    for combination in product(*dimension_points):
        point = {}

        for dimension_point in combination:
            for name, value in dimension_point.items():
                if name in point:
                    raise ValueError(
                        f"Variable {name} appears in multiple dimensions"
                    )
                point[name] = value

        scan_plan.append(point)

    return scan_plan
