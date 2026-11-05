import pathlib
import re
import xml.etree.ElementTree as Et

import numpy as np
import pyvista as pv


def load_ensemble_member(ensemble_dir_path, member_identifier, index=0):
    """
    Load a single ensemble member from an OpenLB ensemble.

    This importer supports 2d as well as 3d ensembles generated with OpenLB.

    :param ensemble_dir_path: The path to the ensemble directory.
    :param member_identifier: The member identifier of the member to load.
        The member identifier refers to the directory name of the ensemble member in the parent directory.
    :param index: Optional index of the member in the ensemble.
        This index can later be used to sort the ensemble members.
    :return: The ensemble member as a dict of the member data.
    """
    ensemble_dir_path = pathlib.Path(ensemble_dir_path)
    ensemble_member_path = ensemble_dir_path / member_identifier
    ensemble_member_data_path = ensemble_member_path / "vtkData"

    # Extract the time step delta from the unit converter factors file
    member_unit_converter_factors_file = next(ensemble_member_path.glob("*.dat"), None)
    with open(member_unit_converter_factors_file, 'r') as file:
        member_unit_converter_factors = file.read()
    match = re.search(r"physDeltaT=\s+([0-9.eE+-]+)\n", member_unit_converter_factors)
    t_step_delta = float(match.group(1))

    # The pvd file contains the DataSet for each timestep in the ensemble
    pvd_file = next(ensemble_member_data_path.glob("*.pvd"), None)
    pvd_tree = Et.parse(pvd_file)
    pvd_root = pvd_tree.getroot()

    v_array = []
    t_array = []
    points_array = None
    n_dims = None

    for data_set in pvd_root.iter("DataSet"):
        # The vtm file contains the DataSet for the current timestep
        vtm_file = data_set.attrib["file"]
        vtm_file = ensemble_member_data_path / vtm_file
        vtm_tree = Et.parse(vtm_file)
        vtm_root = vtm_tree.getroot()

        vti_data_list = []
        min_x_index = float("inf")
        max_x_index = float("-inf")
        min_y_index = float("inf")
        max_y_index = float("-inf")
        min_z_index = float("inf")
        max_z_index = float("-inf")

        for vtm_data_set in vtm_root.iter("DataSet"):
            # The vti file contains the data of the current timestep
            vti_file = vtm_data_set.attrib["file"]
            vti_file = vtm_file.parent / vti_file

            data = pv.read(str(vti_file))

            # Extract the number of dimensions and shapes of the data and points arrays
            if len(data.dimensions) == 3 and data.dimensions[2] > 1:
                n_dims = 3
                data_shape = (data.dimensions[0], data.dimensions[1], data.dimensions[2], 3)
                points_shape = (data.dimensions[0], data.dimensions[1], data.dimensions[2], 3)
            else:
                n_dims = 2
                data_shape = (data.dimensions[0], data.dimensions[1], 2)
                points_shape = (data.dimensions[0], data.dimensions[1], 3)

            bounds = list(data.bounds)
            for i in range(len(bounds)):
                bounds[i] = round(bounds[i] / data.spacing[i // 2])
            min_x_index = min(bounds[0], min_x_index)
            max_x_index = max(bounds[1], max_x_index)
            min_y_index = min(bounds[2], min_y_index)
            max_y_index = max(bounds[3], max_y_index)
            min_z_index = min(bounds[4], min_z_index)
            max_z_index = max(bounds[5], max_z_index)

            velocity_data = data.point_data["physVelocity"]
            velocity_array = np.array(velocity_data).reshape(data_shape, order="F")

            points_array = np.array(data.points).reshape(points_shape, order="F")
            if n_dims == 2:
                points_array = points_array[:, :, :n_dims]

            vti_data_list.append({
                "bounds": bounds,
                "velocity_array": velocity_array,
                "points_array": points_array
            })

        if n_dims == 3:
            data_shape = (
                max_x_index - min_x_index + 1, max_y_index - min_y_index + 1, max_z_index - min_z_index + 1, 3)
        else:
            data_shape = (max_x_index - min_x_index + 1, max_y_index - min_y_index + 1, 2)

        velocity_array = np.zeros(data_shape)
        points_array = np.zeros(data_shape)

        for vti_data in vti_data_list:
            if n_dims == 3:
                x_slice = slice(vti_data["bounds"][0] - min_x_index, vti_data["bounds"][1] - min_x_index + 1)
                y_slice = slice(vti_data["bounds"][2] - min_y_index, vti_data["bounds"][3] - min_y_index + 1)
                z_slice = slice(vti_data["bounds"][4] - min_z_index, vti_data["bounds"][5] - min_z_index + 1)
                velocity_array[x_slice, y_slice, z_slice, :] = vti_data["velocity_array"]
                points_array[x_slice, y_slice, z_slice, :] = vti_data["points_array"]
            else:
                x_slice = slice(vti_data["bounds"][0] - min_x_index, vti_data["bounds"][1] - min_x_index + 1)
                y_slice = slice(vti_data["bounds"][2] - min_y_index, vti_data["bounds"][3] - min_y_index + 1)
                velocity_array[x_slice, y_slice, :] = vti_data["velocity_array"]
                points_array[x_slice, y_slice, :] = vti_data["points_array"]

        v_array.append(velocity_array)

        timestep = int(data_set.attrib["timestep"])
        t_array.append(timestep * t_step_delta)

    # If the first time step is missing add a zeros
    if t_array[0] > 0:
        v_array.insert(0, np.zeros(v_array[0].shape))
        t_array.insert(0, 0.0)

    v_array = np.array(v_array)
    t_array = np.array(t_array)

    ensemble_member = {"identifier": member_identifier,
                       "index": index,
                       "n_dims": n_dims,
                       "v_array": v_array,
                       "t_array": t_array,
                       "points_array": points_array}

    return ensemble_member
