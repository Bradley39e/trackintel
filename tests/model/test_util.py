from functools import WRAPPER_ASSIGNMENTS

import pandas as pd
import pytest
from geopandas import GeoDataFrame
from shapely.geometry import Point

import trackintel as ti
from trackintel.io.postgis import read_trips_postgis
from trackintel.model.util import (
    NonCachedAccessor,
    _copy_docstring,
    _register_trackintel_accessor,
    _wrapped_gdf_method,
    TrackintelGeoDataFrame,
    TrackintelDataFrame,
)


@pytest.fixture
def example_positionfixes():
    """Positionfixes for tests."""
    p1 = Point(8.5067847, 47.4)
    p2 = Point(8.5067847, 47.5)
    p3 = Point(8.5067847, 47.6)

    t1 = pd.Timestamp("1971-01-01 00:00:00", tz="utc")
    t2 = pd.Timestamp("1971-01-01 05:00:00", tz="utc")
    t3 = pd.Timestamp("1971-01-02 07:00:00", tz="utc")

    list_dict = [
        {"user_id": 0, "tracked_at": t1, "geometry": p1},
        {"user_id": 0, "tracked_at": t2, "geometry": p2},
        {"user_id": 1, "tracked_at": t3, "geometry": p3},
    ]
    pfs = GeoDataFrame(data=list_dict, geometry="geometry", crs="EPSG:4326")
    pfs.index.name = "id"

    # assert validity of positionfixes.
    pfs.as_positionfixes
    return pfs


class Test_copy_docstring:
    def test_default(self):
        @_copy_docstring(read_trips_postgis)
        def bar(b: int) -> int:
            """Old docstring."""
            pass

        old_docs = """Old docstring."""
        for wa in WRAPPER_ASSIGNMENTS:
            attr_foo = getattr(read_trips_postgis, wa)
            attr_bar = getattr(bar, wa)
            if wa == "__doc__":
                assert attr_foo == attr_bar
                assert attr_bar != old_docs
            else:
                assert attr_foo != attr_bar


class Test_wrapped_gdf_method:
    """Test if _wrapped_gdf_method conditionals work"""

    def test_no_dataframe(self, example_positionfixes):
        """Test if function return value does not subclass DataFrame then __class__ is not touched"""

        @_wrapped_gdf_method
        def foo(gdf: GeoDataFrame) -> pd.Series:
            return pd.Series(gdf.iloc[0])

        assert type(foo(example_positionfixes)) is pd.Series

    def test_failed_check(self, example_positionfixes):
        """Test if _check fails then __class__ is not touched"""

        class A(GeoDataFrame):
            fallback_class = None

            @staticmethod
            def _check(obj, validate_geometry=True):
                return False

        @_wrapped_gdf_method
        def foo(a: A) -> GeoDataFrame:
            return GeoDataFrame(a)

        a = A(example_positionfixes)
        assert type(foo(a)) is GeoDataFrame

    def test_keep_class(self, example_positionfixes):
        """Test if original class is restored if return value subclasses GeoDataFarme and fulfills _check"""

        class A(GeoDataFrame):
            fallback_class = None

            @staticmethod
            def _check(obj, validate_geometry=True):
                return True

        @_wrapped_gdf_method
        def foo(a: A) -> GeoDataFrame:
            return GeoDataFrame(a)

        a = A(example_positionfixes)
        assert type(foo(a)) is A

    def test_fallback(self, example_positionfixes):
        """Test if fallback to fallback_class if _check succeeds but not subclasses GeoDataFrame"""

        class B(pd.DataFrame):
            pass

        class A(GeoDataFrame):
            fallback_class = B

            @staticmethod
            def _check(obj, validate_geometry=True):
                return True

        @_wrapped_gdf_method
        def foo(a: A) -> pd.DataFrame:
            return pd.DataFrame(a)

        a = A(example_positionfixes)
        assert type(foo(a)) is B

    def test_no_fallback(self, example_positionfixes):
        """Test if fallback_class is not set then fallback_class is not used."""

        class A(GeoDataFrame):
            fallback_class = None

            @staticmethod
            def _check(obj, validate_geometry=True):
                return True

        @_wrapped_gdf_method
        def foo(a: A) -> pd.DataFrame:
            return pd.DataFrame(a)

        a = A(example_positionfixes)
        assert type(foo(a)) is pd.DataFrame


class TestTrackintelGeoDataFrame:
    """Test helper class TrackintelGeoDataFrame."""

    class A(TrackintelGeoDataFrame):
        """Mimic TrackintelGeoDataFrame subclass by taking the same arguments"""

        class AFallback(TrackintelDataFrame):
            pass

        fallback_class = AFallback

        def __init__(self, *args, validate_geometry=True, **kwargs):
            super().__init__(*args, **kwargs)

        @staticmethod
        def _check(obj, validate_geometry=True):
            return "user_id" in obj.columns

    def test_getitem(self, example_positionfixes):
        """Test if loc on all columns returns original class."""
        a = self.A(example_positionfixes)
        b = a.loc[[True for _ in a.columns]]
        assert type(b) is self.A

    def test_copy(self, example_positionfixes):
        """Test if copy maintains class."""
        a = self.A(example_positionfixes)
        b = a.copy()
        assert type(b) is self.A

    def test_merge(self, example_positionfixes):
        """Test if merge maintains class"""
        a = self.A(example_positionfixes)
        b = a.merge(a, on="user_id", suffixes=("", "_other"))
        assert type(b) is self.A

    def test_constructor_fails_check(self, example_positionfixes):
        """Test if falls through if _check fails"""
        a = self.A(example_positionfixes)
        # a.drop(columns=geometryname, inplace=True) fails
        # this is also true for geopandas their motivation can be found here:
        # https://github.com/geopandas/geopandas/pull/2060#issuecomment-899802955
        a = a.drop(columns="user_id")
        assert type(a) is GeoDataFrame

    def test_constructor_fallback_class(self, example_positionfixes):
        """Test if _constructor gets can fallback to fallback_class"""
        a = self.A(example_positionfixes)
        a = a.drop(columns=a.geometry.name)
        assert type(a) is self.A.fallback_class

    def test_constructor_no_fallback_class(self, example_positionfixes):
        """Test if _constructor does not fallback to fallback_class if not set"""
        a = self.A(example_positionfixes)
        a.fallback_class = None  # unset it again
        a = a.drop(columns=a.geometry.name)
        assert type(a) is pd.DataFrame

    def test_constructor_calls_init(self, example_positionfixes):
        """Test if _constructor gets GeoDataFrame and fulfills test then builds class"""
        a = self.A(example_positionfixes)
        assert type(a._constructor(a)) is self.A


class TestTrackintelDataFrame:
    """Test helper class TrackintelDataFrame."""

    class A(TrackintelDataFrame):
        """Mimic TrackintelDataFrame subclass by taking the same arguments"""

        @staticmethod
        def _check(obj):
            return "user_id" in obj.columns

    def test_constructor_fails_check(self, example_positionfixes):
        """Test if falls through if _check fails"""
        a = self.A(example_positionfixes)
        a = a.drop(columns="user_id")
        assert type(a) is pd.DataFrame

    def test_constructor_calls_init(self, example_positionfixes):
        """Test if _constructor gets GeoDataFrame and fulfills test then builds class"""
        a = self.A(example_positionfixes)
        assert type(a._constructor(a)) is self.A


class TestNonCachedAccessor:
    """Test if NonCachedAccessor works"""

    def test_accessor(self):
        """Test accessor on class object and class instance."""

        def foo(val):
            return val

        class A:
            nca = NonCachedAccessor("nca_test", foo)

        a = A()
        assert A.nca == foo  # class object
        assert a.nca == a  # class instance


class Test_register_trackintel_accessor:
    """Test if accessors are correctly registered."""

    def test_register(self):
        """Test if accessor is registered in DataFrame"""

        def foo(val):
            return val

        bar = _register_trackintel_accessor("foo")(foo)
        assert foo == bar
        assert "foo" in pd.DataFrame._accessors
        assert foo == pd.DataFrame.foo
        # remove accessor again to make tests independent
        pd.DataFrame._accesors = pd.DataFrame._accessors.remove("foo")
        del pd.DataFrame.foo

    def test_duplicate_name_warning(self):
        """Test that duplicate name raises warning"""

        def foo(val):
            return val

        _register_trackintel_accessor("foo")(foo)
        with pytest.warns(UserWarning):
            _register_trackintel_accessor("foo")(foo)
        # remove accessor again to make tests independent
        pd.DataFrame._accesors = pd.DataFrame._accessors.remove("foo")
        del pd.DataFrame.foo
