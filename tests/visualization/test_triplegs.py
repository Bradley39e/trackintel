import pytest
import os
import matplotlib as mpl

mpl.use("Agg")

import trackintel as ti
from trackintel.visualization.util import regular_figure


@pytest.fixture
def test_data():
    """Read tests data from files."""
    pfs_file = os.path.join("tests", "data", "positionfixes.csv")
    pfs = ti.read_positionfixes_csv(pfs_file, sep=";", index_col="id", crs="EPSG:4326")

    tpls_file = os.path.join("tests", "data", "triplegs.csv")
    tpls = ti.read_triplegs_csv(tpls_file, sep=";", index_col="id", crs="EPSG:4326")
    return pfs, tpls


class TestPlot_triplegs:
    """Tests for plot_triplegs() method."""

    def test_triplegs_plot(self, test_data):
        """Use trackintel visualization function to plot triplegs and check if the file exists."""
        pfs, tpls = test_data

        tmp_file = os.path.join("tests", "data", "triplegs_plot.png")
        tpls.as_triplegs.plot(out_filename=tmp_file, positionfixes=pfs, plot_osm=False)
        assert os.path.exists(tmp_file)
        os.remove(tmp_file)

    def test_axis(self, test_data):
        """Test the use of regular_figure() to create axis."""
        _, tpls = test_data
        tmp_file = os.path.join("tests", "data", "triplegs_plot.png")
        _, ax = regular_figure()

        tpls.as_triplegs.plot(out_filename=tmp_file, axis=ax)
        assert os.path.exists(tmp_file)
        os.remove(tmp_file)

    def test_parameter(self, test_data):
        """Test other parameter configurations."""
        _, tpls = test_data
        tmp_file = os.path.join("tests", "data", "triplegs_plot.png")

        # test plot_osm
        tpls.as_triplegs.plot(out_filename=tmp_file, plot_osm=True)
        assert os.path.exists(tmp_file)
        os.remove(tmp_file)
