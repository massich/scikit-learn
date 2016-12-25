"""Forest covertype dataset.

A classic dataset for classification benchmarks, featuring categorical and
real-valued features.

The dataset page is available from UCI Machine Learning Repository

    http://archive.ics.uci.edu/ml/datasets/Covertype

Courtesy of Jock A. Blackard and Colorado State University.
"""

# Author: Lars Buitinck
#         Peter Prettenhofer <peter.prettenhofer@gmail.com>
# License: BSD 3 clause

from gzip import GzipFile
import logging
from os.path import exists, join
from os import remove

import numpy as np

from .base import get_data_home, Bunch
from .base import _fetch_and_verify_dataset, _validate_file_md5
from .base import _pkl_filepath
from ..utils.fixes import makedirs
from ..externals import joblib
from ..utils import check_random_state


URL = 'https://ndownloader.figshare.com/files/5976039'

logger = logging.getLogger(__name__)


def fetch_covtype(data_home=None, download_if_missing=True,
                  random_state=None, shuffle=False):
    """Load the covertype dataset, downloading it if necessary.

    Read more in the :ref:`User Guide <datasets>`.

    Parameters
    ----------
    data_home : string, optional
        Specify another download and cache folder for the datasets. By default
        all scikit learn data is stored in '~/scikit_learn_data' subfolders.

    download_if_missing : boolean, default=True
        If False, raise a IOError if the data is not locally available
        instead of trying to download the data from the source site.

    random_state : int, RandomState instance or None, optional (default=None)
        Random state for shuffling the dataset.
        If int, random_state is the seed used by the random number generator;
        If RandomState instance, random_state is the random number generator;
        If None, the random number generator is the RandomState instance used
        by `np.random`.

    shuffle : bool, default=False
        Whether to shuffle dataset.

    Returns
    -------
    dataset : dict-like object with the following attributes:

    dataset.data : numpy array of shape (581012, 54)
        Each row corresponds to the 54 features in the dataset.

    dataset.target : numpy array of shape (581012,)
        Each value corresponds to one of the 7 forest covertypes with values
        ranging between 1 to 7.

    dataset.DESCR : string
        Description of the forest covertype dataset.

    """

    data_home = get_data_home(data_home=data_home)
    covtype_dir = join(data_home, "covertype")
    samples_path = _pkl_filepath(covtype_dir, "samples")
    targets_path = _pkl_filepath(covtype_dir, "targets")
    available = exists(samples_path)

    if download_if_missing and not available:
        makedirs(covtype_dir, exist_ok=True)
        logger.info("Downloading %s" % URL)

        archive_path = join(covtype_dir, "covtype.data.gz")
        expected_checksum = "99670d8d942f09d459c7d4486fca8af5"
        _fetch_and_verify_dataset(URL, archive_path, expected_checksum)
        Xy = np.genfromtxt(GzipFile(filename=archive_path), delimiter=',')
        # delete archive
        remove(archive_path)

        X = Xy[:, :-1]
        y = Xy[:, -1].astype(np.int32)

        joblib.dump(X, samples_path, compress=9)
        joblib.dump(y, targets_path, compress=9)

        # check md5 of dumped samples and targets
        expected_samples_checksum = "19b80d5fa6590346b357b4cb75562f0e"
        _validate_file_md5(expected_samples_checksum, samples_path)

        expected_targets_checksum = "b79a24223e6a55bd486b7f796e8e5305"
        _validate_file_md5(expected_targets_checksum, targets_path)

    elif not available and not download_if_missing:
        raise IOError("Data not found and `download_if_missing` is False")
    try:
        X, y
    except NameError:
        X = joblib.load(samples_path)
        y = joblib.load(targets_path)

    if shuffle:
        ind = np.arange(X.shape[0])
        rng = check_random_state(random_state)
        rng.shuffle(ind)
        X = X[ind]
        y = y[ind]

    return Bunch(data=X, target=y, DESCR=__doc__)
