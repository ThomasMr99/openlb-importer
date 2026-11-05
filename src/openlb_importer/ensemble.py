import concurrent.futures
import pathlib
import pickle

from . import importer
from . import sorting

class EnsembleManager:
    """
    Class to manage an OpenLB ensemble.

    This class provides methods to load the ensemble or individual ensemble members.
    """

    def __init__(self, ensemble_dir_path, member_identifiers=None, use_pickle=True, keep_in_memory=False):
        """
        Construct an EnsembleManager instance.

        The EnsembleManager provides methods to load an ensemble or individual ensemble members.

        :param ensemble_dir_path: The path to the ensemble directory.
        :param member_identifiers: Optional list of member identifiers to load.
            A member identifier refers to the directory name of the ensemble member in the parent directory.
            If not provided, all available subdirectories are considered ensemble members and are loaded.
        :param use_pickle: Optional boolean whether to use pickle.
            Pickle can be used to serialize the ensemble members.
            This increases the performance of loading the ensemble members after the initial serialization.
        :param keep_in_memory: Optional boolean whether to keep the ensemble members in memory.
            Keeping the ensemble members in memory drastically increases the performance of loading the ensemble members
            after the initial loading.
            This is only recommend for rather small ensembles because of the high memory consumption.
        """
        ensemble_dir_path = pathlib.Path(ensemble_dir_path)
        if not ensemble_dir_path.is_dir():
            raise FileNotFoundError("Ensemble directory not found.")
        self._ensemble_dir_path = ensemble_dir_path

        # If member_identifiers are not provided, all available subdirectories are considered ensemble members
        if member_identifiers is None:
            self._member_identifiers = self.get_member_identifiers_for_path(ensemble_dir_path)
        else:
            self._member_identifiers = member_identifiers

        self._ensemble = [None] * len(self._member_identifiers)

        self._use_pickle = use_pickle

        self._keep_in_memory = keep_in_memory

    @staticmethod
    def get_member_identifiers_for_path(ensemble_dir_path):
        """
        Return the list of member identifiers for a given ensemble directory.

        All available subdirectories are considered ensemble members.

        :param ensemble_dir_path: The path to the ensemble directory.
        :return: The list of member identifiers.
        """
        ensemble_dir_path = pathlib.Path(ensemble_dir_path)
        if not ensemble_dir_path.is_dir():
            raise FileNotFoundError("Ensemble directory not found.")

        member_identifiers = sorting.sort_intuitive([p.name for p in ensemble_dir_path.iterdir() if p.is_dir()], reverse=True)
        if not member_identifiers:
            raise ValueError("Ensemble directory has no subdirectories.")

        return member_identifiers

    def get_member_identifiers(self):
        """
        Return the list of member identifiers.

        :return: The list of member identifiers.
        """
        return self._member_identifiers

    def get_ensemble(self):
        """
        Load and return the whole ensemble including all ensemble members.

        :return: The list of all ensemble members.
        """
        ensemble = []

        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = []

            for member_identifier in self._member_identifiers:
                # Check whether the current member can be loaded from memory
                ensemble_member = self._get_ensemble_member_from_memory(member_identifier)
                if ensemble_member is not None:
                    ensemble.append(ensemble_member)
                    continue

                # Check whether the current member can be loaded from a pickled file
                if self._use_pickle:
                    ensemble_member = self._get_ensemble_member_from_pickle(member_identifier)
                    if ensemble_member is not None:
                        ensemble.append(ensemble_member)
                        continue

                # Otherwise load the current member from origin
                futures.append(executor.submit(self._get_ensemble_member, member_identifier))

            for future in concurrent.futures.as_completed(futures):
                ensemble_member = future.result()
                if ensemble_member is not None:
                    ensemble.append(ensemble_member)

        for ensemble_member in ensemble:
            self._save_ensemble_member(ensemble_member)

        ensemble = sorted(ensemble, key=lambda x: x["index"])

        return ensemble

    def get_ensemble_member(self, member_identifier):
        """
        Load and return the ensemble member with the given member identifier.

        :param member_identifier: The member identifier.
        :return: The ensemble member as a dict of the member data or None if the member can not be loaded.
        """
        # Check whether the member can be loaded from memory
        ensemble_member = self._get_ensemble_member_from_memory(member_identifier)
        if ensemble_member is not None:
            self._save_ensemble_member(ensemble_member)

            return ensemble_member

        # Check whether the member can be loaded from a pickled file
        if self._use_pickle:
            ensemble_member = self._get_ensemble_member_from_pickle(member_identifier)
            if ensemble_member is not None:
                self._save_ensemble_member(ensemble_member)

                return ensemble_member

        # Check whether the member can be loaded from origin
        ensemble_member = self._get_ensemble_member(member_identifier)
        if ensemble_member is not None:
            self._save_ensemble_member(ensemble_member)

            return ensemble_member

        return None

    def _get_ensemble_member(self, member_identifier):
        """
        (Internal method) Load and return the ensemble member with the given member identifier.

        This method loads the ensemble member directly from origin without using the memory or pickle.

        :param member_identifier: The member identifier.
        :return: The ensemble member as a dict of the member data or None if the member can not be loaded.
        """
        index = self._member_identifiers.index(member_identifier)

        ensemble_member = importer.load_ensemble_member(self._ensemble_dir_path, member_identifier, index=index)

        return ensemble_member

    def _get_ensemble_member_from_memory(self, member_identifier):
        """
        (Internal method) Load and return the ensemble member with the given member identifier from memory.

        :param member_identifier: The member identifier.
        :return: The ensemble member as a dict of the member data or None if the member can not be loaded.
        """
        index = self._member_identifiers.index(member_identifier)

        if self._ensemble[index] is None:
            return None

        ensemble_member = self._ensemble[index]

        return ensemble_member

    def _get_ensemble_member_from_pickle(self, member_identifier):
        """
        (Internal method) Load and return the ensemble member with the given member identifier from a pickled file.

        :param member_identifier: The member identifier.
        :return: The ensemble member as a dict of the member data or None if the member can not be loaded.
        """
        pickle_file_path = self._ensemble_dir_path / member_identifier / "data.pkl"

        if not pickle_file_path.is_file():
            return None

        with open(pickle_file_path, "rb") as file:
            ensemble_member = pickle.load(file)

        index = self._member_identifiers.index(member_identifier)
        ensemble_member["index"] = index

        return ensemble_member

    def _save_ensemble_member_to_memory(self, ensemble_member):
        """
        (Internal method) Save the ensemble member to memory.

        :param ensemble_member: The ensemble member.
        :return: None.
        """
        member_identifier = ensemble_member["identifier"]
        index = self._member_identifiers.index(member_identifier)
        self._ensemble[index] = ensemble_member

    def _save_ensemble_member_to_pickle(self, ensemble_member):
        """
        (Internal method) Save the ensemble member to a pickled file.

        :param ensemble_member: The ensemble member.
        :return: None.
        """
        member_identifier = ensemble_member["identifier"]
        pickle_file_path = self._ensemble_dir_path / member_identifier / "data.pkl"

        # If the pickled file already exists do not save the file again
        # This prevents saving the file multiple times
        if pickle_file_path.exists():
            return

        with open(pickle_file_path, "wb") as file:
            pickle.dump(ensemble_member, file, protocol=pickle.HIGHEST_PROTOCOL)

    def _save_ensemble_member(self, ensemble_member):
        """
        (Internal method) Save the ensemble member to memory and/or to a pickled file if needed.

        :param ensemble_member: The ensemble member.
        :return: None.
        """
        if self._keep_in_memory:
            self._save_ensemble_member_to_memory(ensemble_member)

        if self._use_pickle:
            self._save_ensemble_member_to_pickle(ensemble_member)

    @staticmethod
    def clear_pickled_ensemble_members_for_path(ensemble_dir_path):
        """
        Clear the pickled ensemble members for a given ensemble directory.

        This deletes all pickled files.

        :param ensemble_dir_path: The ensemble directory path.
        :return: None.
        """
        ensemble_dir_path = pathlib.Path(ensemble_dir_path)
        if not ensemble_dir_path.is_dir():
            raise ValueError("Ensemble directory not found.")

        member_identifiers = EnsembleManager.get_member_identifiers_for_path(ensemble_dir_path)

        for member_identifier in member_identifiers:
            pickle_file_path = ensemble_dir_path / member_identifier / "data.pkl"

            pickle_file_path.unlink(missing_ok=True)
