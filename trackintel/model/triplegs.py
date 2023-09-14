import pandas as pd

import trackintel as ti
from trackintel.analysis.labelling import predict_transport_mode
from trackintel.analysis.modal_split import calculate_modal_split
from trackintel.analysis.tracking_quality import temporal_tracking_quality
from trackintel.geogr.distances import calculate_distance_matrix
from trackintel.io.file import write_triplegs_csv
from trackintel.io.postgis import write_triplegs_postgis
from trackintel.model.util import (
    TrackintelBase,
    TrackintelGeoDataFrame,
    _copy_docstring,
    _register_trackintel_accessor,
    get_speed_triplegs,
)
from trackintel.preprocessing.filter import spatial_filter
from trackintel.preprocessing.triplegs import generate_trips

_required_columns = ["user_id", "started_at", "finished_at"]


@_register_trackintel_accessor("as_triplegs")
class Triplegs(TrackintelBase, TrackintelGeoDataFrame):
    """A pandas accessor to treat a GeoDataFrame as a collections of `Tripleg`.

    This will define certain methods and accessors, as well as make sure that the DataFrame
    adheres to some requirements.

    Requires at least the following columns:
    ['user_id', 'started_at', 'finished_at']

    Requires valid line geometries; the 'index' of the GeoDataFrame will be treated as unique identifier
    of the `triplegs`

    For several usecases, the following additional columns are required:
    ['mode', 'trip_id']

    Notes
    -----
    A `Tripleg` (also called `stage`) is defined as continuous movement without changing the mode of transport.

    'started_at' and 'finished_at' are timezone aware pandas datetime objects.

    Examples
    --------
    >>> df.as_triplegs.generate_trips()
    """

    def __init__(self, *args, validate_geometry=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._validate(self, validate_geometry=validate_geometry)

    # create circular reference directly -> avoid second call of init via accessor
    @property
    def as_triplegs(self):
        return self

    @staticmethod
    def _validate(obj, validate_geometry=True):
        assert obj.shape[0] > 0, f"Geodataframe is empty with shape: {obj.shape}"
        # check columns
        if any([c not in obj.columns for c in _required_columns]):
            raise AttributeError(
                "To process a DataFrame as a collection of triplegs, it must have the properties"
                f" {_required_columns}, but it has [{', '.join(obj.columns)}]."
            )

        # check timestamp dtypes
        assert isinstance(
            obj["started_at"].dtype, pd.DatetimeTZDtype
        ), f"dtype of started_at is {obj['started_at'].dtype} but has to be datetime64 and timezone aware"
        assert isinstance(
            obj["finished_at"].dtype, pd.DatetimeTZDtype
        ), f"dtype of finished_at is {obj['finished_at'].dtype} but has to be datetime64 and timezone aware"

        # check geometry
        if validate_geometry:
            assert (
                obj.geometry.is_valid.all()
            ), "Not all geometries are valid. Try x[~ x.geometry.is_valid] where x is you GeoDataFrame"
            if obj.geometry.iloc[0].geom_type != "LineString":
                raise AttributeError("The geometry must be a LineString (only first checked).")

    @staticmethod
    def _check(obj, validate_geometry=True):
        """Check does the same as _validate but returns bool instead of potentially raising an error."""
        if any([c not in obj.columns for c in _required_columns]):
            return False
        if obj.shape[0] <= 0:
            return False
        if not isinstance(obj["started_at"].dtype, pd.DatetimeTZDtype):
            return False
        if not isinstance(obj["finished_at"].dtype, pd.DatetimeTZDtype):
            return False
        if validate_geometry:
            return obj.geometry.is_valid.all() and obj.geometry.iloc[0].geom_type == "LineString"
        return True

    @_copy_docstring(write_triplegs_csv)
    def to_csv(self, filename, *args, **kwargs):
        """
        Store this collection of triplegs as a CSV file.

        See :func:`trackintel.io.file.write_triplegs_csv`.
        """
        ti.io.file.write_triplegs_csv(self, filename, *args, **kwargs)

    @_copy_docstring(write_triplegs_postgis)
    def to_postgis(
        self, name, con, schema=None, if_exists="fail", index=True, index_label=None, chunksize=None, dtype=None
    ):
        """
        Store this collection of triplegs to PostGIS.

        See :func:`trackintel.io.postgis.store_positionfixes_postgis`.
        """
        ti.io.postgis.write_triplegs_postgis(self, name, con, schema, if_exists, index, index_label, chunksize, dtype)

    @_copy_docstring(calculate_distance_matrix)
    def calculate_distance_matrix(self, *args, **kwargs):
        """
        Calculate pair-wise distance among triplegs or to other triplegs.

        See :func:`trackintel.geogr.distances.calculate_distance_matrix`.
        """
        return ti.geogr.distances.calculate_distance_matrix(self, *args, **kwargs)

    @_copy_docstring(spatial_filter)
    def spatial_filter(self, *args, **kwargs):
        """
        Filter triplegs with a geo extent.

        See :func:`trackintel.preprocessing.filter.spatial_filter`.
        """
        return ti.preprocessing.filter.spatial_filter(self, *args, **kwargs)

    @_copy_docstring(generate_trips)
    def generate_trips(self, *args, **kwargs):
        """
        Generate trips based on staypoints and triplegs.

        See :func:`trackintel.preprocessing.triplegs.generate_trips`.
        """
        # if staypoints in kwargs: 'staypoints' can not be in args as it would be the first argument
        if "staypoints" in kwargs:
            return ti.preprocessing.triplegs.generate_trips(triplegs=self, **kwargs)
        # if 'staypoints' no in kwargs it has to be the first argument in 'args'
        else:
            assert len(args) <= 1, (
                "All arguments except 'staypoints' have to be given as keyword arguments. You gave"
                f" {args[1:]} as positional arguments."
            )
            return ti.preprocessing.triplegs.generate_trips(staypoints=args[0], triplegs=self, **kwargs)

    @_copy_docstring(predict_transport_mode)
    def predict_transport_mode(self, *args, **kwargs):
        """
        Predict/impute the transport mode with which each tripleg was likely covered.

        See :func:`trackintel.analysis.labelling.predict_transport_mode`.
        """
        return ti.analysis.labelling.predict_transport_mode(self, *args, **kwargs)

    @_copy_docstring(calculate_modal_split)
    def calculate_modal_split(self, *args, **kwargs):
        """
        Calculate the modal split of the triplegs.

        See :func:`trackintel.analysis.modal_split.calculate_modal_split`.
        """
        return ti.analysis.modal_split.calculate_modal_split(self, *args, **kwargs)

    @_copy_docstring(temporal_tracking_quality)
    def temporal_tracking_quality(self, *args, **kwargs):
        """
        Calculate per-user temporal tracking quality (temporal coverage).

        See :func:`trackintel.analysis.tracking_quality.temporal_tracking_quality`.
        """
        return ti.analysis.tracking_quality.temporal_tracking_quality(self, *args, **kwargs)

    @_copy_docstring(get_speed_triplegs)
    def get_speed(self, *args, **kwargs):
        """
        Compute the average speed for each tripleg, given by overall distance and duration (in m/s)

        See :func:`trackintel.model.util.get_speed_triplegs`.
        """
        return ti.model.util.get_speed_triplegs(self, *args, **kwargs)
