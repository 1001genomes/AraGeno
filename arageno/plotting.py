import json
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from .models import CrossesJob, FINISHED
sns.set(style="whitegrid", color_codes=True)



def _get_chromosome_ticks(chromosome_regions,windows):
    sorted_chr = sorted(chromosome_regions.keys(), key=lambda t: t,reverse=False)
    ticks =  []
    minor_ticks = []
    num = 1
    for ix,key in enumerate(sorted_chr):
        if ix > 0:
            num += chromosome_regions[sorted_chr[ix-1]]
        min_num = num + chromosome_regions[sorted_chr[ix]]/2
        ticks.append(num)
        minor_ticks.append(min_num)
    return (ticks, minor_ticks, sorted_chr)

def _map_y_data(y_data):
    return y_data


def plot_crosses_data(crosses_job):
    """Creates a plot for the crosses"""

    if crosses_job.status != FINISHED:
        raise ValueError('Job is not finished yet')
    statistics = json.loads(crosses_job.statistics)
    window_data = statistics['genotype_windows']['coordinates']
    chromosome_regions = statistics['genotype_windows']['chr_bins']
    y = map(_map_y_data, window_data['y'])
    d = {'Chromosome':window_data['x'], 'Parent':y}
    df = pd.DataFrame(d)
    categories = sorted(df.Parent.unique())
    ax = sns.stripplot(x='Chromosome', y='Parent', data=df, split=False, alpha=0.8,color='#2196F3',order=categories)
    ax.set_xlim([df.Chromosome.min(),df.Chromosome.max()])
    major_ticks,minor_ticks, chr_labels = _get_chromosome_ticks(chromosome_regions,window_data)
    ax.set_xticks(major_ticks)
    ax.set_xticklabels([])
    ax.set_xticks(minor_ticks, minor=True)
    ax.set_xticklabels(chr_labels,minor=True)

    return plt

