import pytest
from SCNIC.general import simulate_correls, get_metadata_from_table, filter_table, sparcc_paper_filter,\
                          bonferroni_adjust, bh_adjust, correls_to_net
from biom.table import Table
import numpy as np
from numpy.testing import assert_allclose
from SCNIC.correlation_analysis import paired_correlations_from_table
import networkx as nx

# TODO: simulate sparse table to test filtering
# TODO: include HMP table to test filtering?


@pytest.fixture()
def biom_table1():
    table1 = simulate_correls()
    assert isinstance(table1, Table)
    return table1


@pytest.fixture()
def correls1(biom_table1):
    correls = paired_correlations_from_table(biom_table1)
    return correls


@pytest.fixture()
def net1(correls1):
    net = correls_to_net(correls1, min_r=.6)
    return net


@pytest.fixture()
def unadj_ps():
    return [.01, .05, .5]


def test_get_metadata_from_table(biom_table1):
    metadata = get_metadata_from_table(biom_table1)
    assert isinstance(metadata, dict)


def test_filter_table(biom_table1):
    table_filt = filter_table(biom_table1, min_samples=10)
    assert isinstance(table_filt, Table)


def test_sparcc_paper_filter(biom_table1):
    table_filt = sparcc_paper_filter(biom_table1)
    assert isinstance(table_filt, Table)


def test_bonferroni_adjust(unadj_ps):
    adj_ps = np.array([.03, .15, 1.5])
    bon_ps = bonferroni_adjust(unadj_ps)
    assert isinstance(bon_ps, np.ndarray)
    assert_allclose(adj_ps, bon_ps)


def test_bh_adjust(unadj_ps):
    adj_ps = np.array([.03, .075, .5])
    bh_ps = bh_adjust(unadj_ps)
    assert isinstance(bh_ps, np.ndarray)
    assert_allclose(adj_ps, bh_ps)


def test_correls_to_net(net1):
    assert isinstance(net1, nx.Graph)
    assert len(net1.edges()) == 4
    assert len(net1.nodes()) == 5
