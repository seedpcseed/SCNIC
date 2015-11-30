import shutil
import glob
import os

import general
import pysurvey as ps
from functools import partial
from scipy.spatial.distance import squareform
import numpy as np
import pandas as pd
from pysurvey import SparCC as sparcc

__author__ = 'shafferm'


def permute_w_replacement(frame):
    '''
    ***STOLEN FROM https://bitbucket.org/yonatanf/pysurvey and adapted***
    Permute the frame values across the given axis.
    Create simulated dataset were the counts of each component (column)
    in each sample (row), are randomly sampled from the all the
    counts of that component in all samples.

    Parameters
    ----------
    frame : DataFrame
        Frame to permute.
    axis : {0, 1}
        - 0 - Permute row values across columns
        - 1 - Permute column values across rows

    Returns
    -------
    Permuted DataFrame (new instance).
    '''
    from numpy.random import randint
    s = frame.shape[0]
    fun = lambda x: x.values[randint(0,s,(1,s))][0]
    perm = frame.apply(fun, axis=0)
    return perm


def make_bootstraps(counts, nperm):
    '''
    ***STOLEN FROM https://bitbucket.org/yonatanf/pysurvey and adapted***
    Make n simulated datasets used to get pseudo p-values.
    Simulated datasets are generated by assigning each OTU in each sample
    an abundance that is randomly drawn (w. replacement) from the
    abundances of the OTU in all samples.
    Simulated datasets are either written out as txt files.

    Parameters
    ----------
    counts : DataFrame
        Inferred correlations whose p-values are to be computed.
    nperm : int
        Number of permutations to produce.
    '''
    bootstraps = []
    for i in xrange(nperm):
        bootstraps.append(ps.permute_w_replacement(counts))
    return bootstraps

def boostrapped_correlation_multi(tup, temp_folder, cor_temp):
    """tup is a tuple where tup[0] is num and tup[1] is the file name"""
    df = ps.read_txt(tup[1], verbose=False)
    cor = ps.basis_corr(df, oprint=False)[0]
    ps.write_txt(cor, temp_folder+cor_temp+str(tup[0])+".txt", T=False)


def sparcc_correlations_multi(table, p_adjust=general.bh_adjust, temp_folder=os.getcwd()+"/temp/",
                              boot_temp="bootstrap_", cor_temp="cor_", table_temp="temp_table.txt",
                              bootstraps=100, procs=None):
    """Calculate correlations with sparcc"""
    import multiprocessing

    os.mkdir(temp_folder)
    if procs == None:
        pool = multiprocessing.Pool(multiprocessing.cpu_count()-1)
    else:
        pool = multiprocessing.Pool(procs)

    # make tab delimited, delete first line and reread in
    with open(temp_folder+table_temp, 'w') as f:
        f.write('\n'.join(table.to_tsv().split("\n")[1:]))
    df = ps.read_txt(temp_folder+table_temp, verbose=False)

    sparcc.make_bootstraps(df, bootstraps, boot_temp+"#.txt", temp_folder)
    cor, cov = ps.basis_corr(df, oprint=False)

    pfun = partial(boostrapped_correlation_multi, temp_folder=temp_folder, cor_temp=cor_temp)
    tups = enumerate(glob.glob(temp_folder+boot_temp+"*.txt"))
    pool.map(pfun, tups)
    pool.close()
    pool.join()

    p_vals = sparcc.get_pvalues(cor, temp_folder+cor_temp+"#.txt", bootstraps)
    # generate correls
    correls = list()
    for i in xrange(len(cor.index)):
        for j in xrange(i+1, len(cor.index)):
            correls.append([str(cor.index[i]), str(cor.index[j]), cor.iat[i, j], p_vals.iat[i, j]])

    # adjust p-value if desired
    if p_adjust is not None:
        p_adjusted = p_adjust([i[3] for i in correls])
        for i in xrange(len(correls)):
            correls[i].append(p_adjusted[i])

    header = ['feature1', 'feature2', 'r', 'p']
    if p_adjust is not None:
        header.append('adjusted_p')

    # cleanup, remove all of bootstraps folder
    shutil.rmtree(temp_folder)

    return correls, header


def boostrapped_correlation(in_file, temp_folder, cor_temp, num):
    df = ps.read_txt(in_file, verbose=False)
    cor = ps.basis_corr(df, oprint=False)[0]
    ps.write_txt(cor, temp_folder+cor_temp+str(num)+".txt", T=False)


def sparcc_correlations(table, p_adjust=general.bh_adjust, temp_folder=os.getcwd()+"/temp/",
                        boot_temp="bootstrap_", cor_temp="cor_", table_temp="temp_table.txt",
                        bootstraps=100):
    """"""
    # setup
    os.mkdir(temp_folder)

    # make tab delimited, delete first line and reread in
    with open(temp_folder+table_temp, 'w') as f:
        f.write('\n'.join(table.to_tsv().split("\n")[1:]))
    df = ps.read_txt(temp_folder+table_temp, verbose=False)

    # calculate correlations
    cor, cov = ps.basis_corr(df, oprint=False)

    # calculate p-values
    sparcc.make_bootstraps(df, bootstraps, boot_temp+"#.txt", temp_folder)
    for i, _file in enumerate(glob.glob(temp_folder+boot_temp+"*.txt")):
        boostrapped_correlation(_file, temp_folder, cor_temp, i)

    p_vals = sparcc.get_pvalues(cor, temp_folder+cor_temp+"#.txt", bootstraps)
    # generate correls
    correls = list()
    for i in xrange(len(cor.index)):
        for j in xrange(i+1, len(cor.index)):
            correls.append([str(cor.index[i]), str(cor.index[j]), cor.iat[i, j], p_vals.iat[i, j]])

    # adjust p-value if desired
    if p_adjust is not None:
        p_adjusted = p_adjust([i[3] for i in correls])
        for i in xrange(len(correls)):
            correls[i].append(p_adjusted[i])

    header = ['feature1', 'feature2', 'r', 'p']
    if p_adjust is not None:
        header.append('adjusted_p')

    # cleanup, remove all of bootstraps folder
    shutil.rmtree(temp_folder)
    return correls, header


def boostrapped_correlation_lowmem(in_file):
    df = ps.read_txt(in_file, verbose=False)
    cor = ps.basis_corr(df, oprint=False)[0]
    cor = squareform(cor, checks=False)
    return cor


def sparcc_correlations_lowmem(table, p_adjust=general.bh_adjust, temp_folder=os.getcwd()+"/temp/",
                               boot_temp="bootstrap_", table_temp="temp_table.txt", bootstraps=100):
    """"""
    # setup
    os.mkdir(temp_folder)

    # make tab delimited, delete first line and reread in
    # TODO: Convert to making pandas dataframe directly
    with open(temp_folder+table_temp, 'w') as f:
        f.write('\n'.join(table.to_tsv().split("\n")[1:]))
    df = ps.read_txt(temp_folder+table_temp, verbose=False)

    # calculate correlations
    cor, cov = ps.basis_corr(df, oprint=False)

    # calculate p-values
    abs_cor = np.abs(squareform(cor, checks=False))
    n_sig = np.zeros(abs_cor.shape)
    # TODO: Convert to making bootstraps directly, eliminate read/write
    sparcc.make_bootstraps(df, bootstraps, boot_temp+"#.txt", temp_folder)
    for i in glob.glob(temp_folder+boot_temp+"*.txt"):
        n_sig[np.abs(boostrapped_correlation_lowmem(i)) >= abs_cor] += 1
    p_vals = squareform(1.*n_sig/bootstraps, checks=False)

    # generate correls
    correls = list()
    for i in xrange(len(cor.index)):
        for j in xrange(i+1, len(cor.index)):
            correls.append([str(cor.index[i]), str(cor.index[j]), cor.iat[i, j], p_vals[i, j]])

    # adjust p-value if desired
    if p_adjust is not None:
        p_adjusted = p_adjust([i[3] for i in correls])
        for i in xrange(len(correls)):
            correls[i].append(p_adjusted[i])

    header = ['feature1', 'feature2', 'r', 'p']
    if p_adjust is not None:
        header.append('adjusted_p')

    # cleanup, remove all of bootstraps folder
    shutil.rmtree(temp_folder)

    return correls, header


def boostrapped_correlation_lowmem_multi(bootstrap, cor):
    in_cor = ps.basis_corr(bootstrap, oprint=False)[0]
    in_cor = squareform(in_cor, checks=False)
    return np.abs(in_cor) >= cor


def sparcc_correlations_lowmem_multi(table, p_adjust=general.bh_adjust, temp_folder=os.getcwd()+"/temp/",
                                     table_temp="temp_table.txt", bootstraps=100, procs=None):
    """"""
    # setup
    import multiprocessing

    os.mkdir(temp_folder)
    if procs is None:
        pool = multiprocessing.Pool(multiprocessing.cpu_count()-1)
    else:
        pool = multiprocessing.Pool(procs)

    # convert to pandas dataframe
    df = pd.DataFrame(np.transpose(table.matrix_data.todense()), index=table.ids(), columns=table.ids(axis="observation"))

    # calculate correlations
    cor, cov = ps.basis_corr(df, oprint=False)

    # calculate p-values
    ##take absolute value of all values in cor for calculating two-sided p-value
    abs_cor = np.abs(squareform(cor, checks=False))
    ##create an empty array of significant value counts in same shape as abs_cor
    n_sig = np.zeros(abs_cor.shape)
    ## make bootstraps
    bootstrap_frames = make_bootstraps(df, bootstraps)
    ## make partial function for use in multiprocessing
    pfun = partial(boostrapped_correlation_lowmem_multi, cor=abs_cor)
    ## run multiprocessing
    multi_results = pool.map(pfun, bootstrap_frames)
    pool.close()
    pool.join()

    # find number of significant results across all bootstraps
    for i in multi_results:
        n_sig[i] += 1
    p_vals = squareform(1.*n_sig/bootstraps, checks=False)

    # generate correls array
    correls = list()
    for i in xrange(len(cor.index)):
        for j in xrange(i+1, len(cor.index)):
            correls.append([str(cor.index[i]), str(cor.index[j]), cor.iat[i, j], p_vals[i, j]])

    # adjust p-value if desired
    if p_adjust is not None:
        p_adjusted = p_adjust([i[3] for i in correls])
        for i in xrange(len(correls)):
            correls[i].append(p_adjusted[i])

    header = ['feature1', 'feature2', 'r', 'p']
    if p_adjust is not None:
        header.append('adjusted_p')

    # cleanup, remove all of bootstraps folder
    shutil.rmtree(temp_folder)

    return correls, header
