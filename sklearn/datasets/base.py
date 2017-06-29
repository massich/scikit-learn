"""
Base IO code for all datasets
"""

# Copyright (c) 2007 David Cournapeau <cournape@gmail.com>
#               2010 Fabian Pedregosa <fabian.pedregosa@inria.fr>
#               2010 Olivier Grisel <olivier.grisel@ensta.org>
# License: BSD 3 clause
from __future__ import print_function

import os
import csv
import sys
import shutil
from os import environ, listdir, makedirs, rename, remove
from os.path import dirname, exists, expanduser, getsize, isdir, join, splitext
import hashlib

try:
    import urllib.request as urllib  # for backwards compatibility
except ImportError:
    import urllib

from ..utils import Bunch

import numpy as np

from ..utils import check_random_state


def get_data_home(data_home=None):
    """Return the path of the scikit-learn data dir.

    This folder is used by some large dataset loaders to avoid
    downloading the data several times.

    By default the data dir is set to a folder named 'scikit_learn_data'
    in the user home folder.

    Alternatively, it can be set by the 'SCIKIT_LEARN_DATA' environment
    variable or programmatically by giving an explicit folder path. The
    '~' symbol is expanded to the user home folder.

    If the folder does not already exist, it is automatically created.
    """
    if data_home is None:
        data_home = environ.get('SCIKIT_LEARN_DATA',
                                join('~', 'scikit_learn_data'))
    data_home = expanduser(data_home)
    if not exists(data_home):
        makedirs(data_home)
    return data_home


def clear_data_home(data_home=None):
    """Delete all the content of the data home cache."""
    data_home = get_data_home(data_home)
    shutil.rmtree(data_home)


def load_files(container_path, description=None, categories=None,
               load_content=True, shuffle=True, encoding=None,
               decode_error='strict', random_state=0):
    """Load text files with categories as subfolder names.

    Individual samples are assumed to be files stored a two levels folder
    structure such as the following:

        container_folder/
            category_1_folder/
                file_1.txt
                file_2.txt
                ...
                file_42.txt
            category_2_folder/
                file_43.txt
                file_44.txt
                ...

    The folder names are used as supervised signal label names. The
    individual file names are not important.

    This function does not try to extract features into a numpy array or
    scipy sparse matrix. In addition, if load_content is false it
    does not try to load the files in memory.

    To use text files in a scikit-learn classification or clustering
    algorithm, you will need to use the `sklearn.feature_extraction.text`
    module to build a feature extraction transformer that suits your
    problem.

    If you set load_content=True, you should also specify the encoding of
    the text using the 'encoding' parameter. For many modern text files,
    'utf-8' will be the correct encoding. If you leave encoding equal to None,
    then the content will be made of bytes instead of Unicode, and you will
    not be able to use most functions in `sklearn.feature_extraction.text`.

    Similar feature extractors should be built for other kind of unstructured
    data input such as images, audio, video, ...

    Read more in the :ref:`User Guide <datasets>`.

    Parameters
    ----------
    container_path : string or unicode
        Path to the main folder holding one subfolder per category

    description : string or unicode, optional (default=None)
        A paragraph describing the characteristic of the dataset: its source,
        reference, etc.

    categories : A collection of strings or None, optional (default=None)
        If None (default), load all the categories.
        If not None, list of category names to load (other categories ignored).

    load_content : boolean, optional (default=True)
        Whether to load or not the content of the different files. If
        true a 'data' attribute containing the text information is present
        in the data structure returned. If not, a filenames attribute
        gives the path to the files.

    encoding : string or None (default is None)
        If None, do not try to decode the content of the files (e.g. for
        images or other non-text content).
        If not None, encoding to use to decode text files to Unicode if
        load_content is True.

    decode_error : {'strict', 'ignore', 'replace'}, optional
        Instruction on what to do if a byte sequence is given to analyze that
        contains characters not of the given `encoding`. Passed as keyword
        argument 'errors' to bytes.decode.

    shuffle : bool, optional (default=True)
        Whether or not to shuffle the data: might be important for models that
        make the assumption that the samples are independent and identically
        distributed (i.i.d.), such as stochastic gradient descent.

    random_state : int, RandomState instance or None, optional (default=0)
        If int, random_state is the seed used by the random number generator;
        If RandomState instance, random_state is the random number generator;
        If None, the random number generator is the RandomState instance used
        by `np.random`.

    Returns
    -------
    data : Bunch
        Dictionary-like object, the interesting attributes are: either
        data, the raw text data to learn, or 'filenames', the files
        holding it, 'target', the classification labels (integer index),
        'target_names', the meaning of the labels, and 'DESCR', the full
        description of the dataset.
    """
    target = []
    target_names = []
    filenames = []

    folders = [f for f in sorted(listdir(container_path))
               if isdir(join(container_path, f))]

    if categories is not None:
        folders = [f for f in folders if f in categories]

    for label, folder in enumerate(folders):
        target_names.append(folder)
        folder_path = join(container_path, folder)
        documents = [join(folder_path, d)
                     for d in sorted(listdir(folder_path))]
        target.extend(len(documents) * [label])
        filenames.extend(documents)

    # convert to array for fancy indexing
    filenames = np.array(filenames)
    target = np.array(target)

    if shuffle:
        random_state = check_random_state(random_state)
        indices = np.arange(filenames.shape[0])
        random_state.shuffle(indices)
        filenames = filenames[indices]
        target = target[indices]

    if load_content:
        data = []
        for filename in filenames:
            with open(filename, 'rb') as f:
                data.append(f.read())
        if encoding is not None:
            data = [d.decode(encoding, decode_error) for d in data]
        return Bunch(data=data,
                     filenames=filenames,
                     target_names=target_names,
                     target=target,
                     DESCR=description)

    return Bunch(filenames=filenames,
                 target_names=target_names,
                 target=target,
                 DESCR=description)


def load_data(module_path, data_file_name):
    """Loads data from module_path/data/data_file_name.

    Parameters
    ----------
    data_file_name : String. Name of csv file to be loaded from
    module_path/data/data_file_name. For example 'wine_data.csv'.

    Returns
    -------
    data : Numpy Array
        A 2D array with each row representing one sample and each column
        representing the features of a given sample.

    target : Numpy Array
        A 1D array holding target variables for all the samples in `data.
        For example target[0] is the target varible for data[0].

    target_names : Numpy Array
        A 1D array containing the names of the classifications. For example
        target_names[0] is the name of the target[0] class.
    """
    with open(join(module_path, 'data', data_file_name)) as csv_file:
        data_file = csv.reader(csv_file)
        temp = next(data_file)
        n_samples = int(temp[0])
        n_features = int(temp[1])
        target_names = np.array(temp[2:])
        data = np.empty((n_samples, n_features))
        target = np.empty((n_samples,), dtype=np.int)

        for i, ir in enumerate(data_file):
            data[i] = np.asarray(ir[:-1], dtype=np.float64)
            target[i] = np.asarray(ir[-1], dtype=np.int)

    return data, target, target_names


def load_wine(return_X_y=False):
    """Load and return the wine dataset (classification).

    .. versionadded:: 0.18

    The wine dataset is a classic and very easy multi-class classification
    dataset.

    =================   ==============
    Classes                          3
    Samples per class        [59,71,48]
    Samples total                  178
    Dimensionality                  13
    Features            real, positive
    =================   ==============

    Read more in the :ref:`User Guide <datasets>`.

    Parameters
    ----------
    return_X_y : boolean, default=False.
        If True, returns ``(data, target)`` instead of a Bunch object.
        See below for more information about the `data` and `target` object.

    Returns
    -------
    data : Bunch
        Dictionary-like object, the interesting attributes are:
        'data', the data to learn, 'target', the classification labels,
        'target_names', the meaning of the labels, 'feature_names', the
        meaning of the features, and 'DESCR', the
        full description of the dataset.

    (data, target) : tuple if ``return_X_y`` is True

    The copy of UCI ML Wine Data Set dataset is
    downloaded and modified to fit standard format from:
    https://archive.ics.uci.edu/ml/machine-learning-databases/wine/wine.data

    Examples
    --------
    Let's say you are interested in the samples 10, 80, and 140, and want to
    know their class name.

    >>> from sklearn.datasets import load_wine
    >>> data = load_wine()
    >>> data.target[[10, 80, 140]]
    array([0, 1, 2])
    >>> list(data.target_names)
    ['class_0', 'class_1', 'class_2']
    """
    module_path = dirname(__file__)
    data, target, target_names = load_data(module_path, 'wine_data.csv')

    with open(join(module_path, 'descr', 'wine_data.rst')) as rst_file:
        fdescr = rst_file.read()

    if return_X_y:
        return data, target

    return Bunch(data=data, target=target,
                 target_names=target_names,
                 DESCR=fdescr,
                 feature_names=['alcohol',
                                'malic_acid',
                                'ash',
                                'alcalinity_of_ash',
                                'magnesium',
                                'total_phenols',
                                'flavanoids',
                                'nonflavanoid_phenols',
                                'proanthocyanins',
                                'color_intensity',
                                'hue',
                                'od280/od315_of_diluted_wines',
                                'proline'])


def load_iris(return_X_y=False):
    """Load and return the iris dataset (classification).

    The iris dataset is a classic and very easy multi-class classification
    dataset.

    =================   ==============
    Classes                          3
    Samples per class               50
    Samples total                  150
    Dimensionality                   4
    Features            real, positive
    =================   ==============

    Read more in the :ref:`User Guide <datasets>`.

    Parameters
    ----------
    return_X_y : boolean, default=False.
        If True, returns ``(data, target)`` instead of a Bunch object.
        See below for more information about the `data` and `target` object.

        .. versionadded:: 0.18

    Returns
    -------
    data : Bunch
        Dictionary-like object, the interesting attributes are:
        'data', the data to learn, 'target', the classification labels,
        'target_names', the meaning of the labels, 'feature_names', the
        meaning of the features, and 'DESCR', the
        full description of the dataset.

    (data, target) : tuple if ``return_X_y`` is True

        .. versionadded:: 0.18

    Examples
    --------
    Let's say you are interested in the samples 10, 25, and 50, and want to
    know their class name.

    >>> from sklearn.datasets import load_iris
    >>> data = load_iris()
    >>> data.target[[10, 25, 50]]
    array([0, 0, 1])
    >>> list(data.target_names)
    ['setosa', 'versicolor', 'virginica']
    """
    module_path = dirname(__file__)
    data, target, target_names = load_data(module_path, 'iris.csv')

    with open(join(module_path, 'descr', 'iris.rst')) as rst_file:
        fdescr = rst_file.read()

    if return_X_y:
        return data, target

    return Bunch(data=data, target=target,
                 target_names=target_names,
                 DESCR=fdescr,
                 feature_names=['sepal length (cm)', 'sepal width (cm)',
                                'petal length (cm)', 'petal width (cm)'])


def load_breast_cancer(return_X_y=False):
    """Load and return the breast cancer wisconsin dataset (classification).

    The breast cancer dataset is a classic and very easy binary classification
    dataset.

    =================   ==============
    Classes                          2
    Samples per class    212(M),357(B)
    Samples total                  569
    Dimensionality                  30
    Features            real, positive
    =================   ==============

    Parameters
    ----------
    return_X_y : boolean, default=False
        If True, returns ``(data, target)`` instead of a Bunch object.
        See below for more information about the `data` and `target` object.

        .. versionadded:: 0.18

    Returns
    -------
    data : Bunch
        Dictionary-like object, the interesting attributes are:
        'data', the data to learn, 'target', the classification labels,
        'target_names', the meaning of the labels, 'feature_names', the
        meaning of the features, and 'DESCR', the
        full description of the dataset.

    (data, target) : tuple if ``return_X_y`` is True

        .. versionadded:: 0.18

    The copy of UCI ML Breast Cancer Wisconsin (Diagnostic) dataset is
    downloaded from:
    https://goo.gl/U2Uwz2

    Examples
    --------
    Let's say you are interested in the samples 10, 50, and 85, and want to
    know their class name.

    >>> from sklearn.datasets import load_breast_cancer
    >>> data = load_breast_cancer()
    >>> data.target[[10, 50, 85]]
    array([0, 1, 0])
    >>> list(data.target_names)
    ['malignant', 'benign']
    """
    module_path = dirname(__file__)
    data, target, target_names = load_data(module_path, 'breast_cancer.csv')

    with open(join(module_path, 'descr', 'breast_cancer.rst')) as rst_file:
        fdescr = rst_file.read()

    feature_names = np.array(['mean radius', 'mean texture',
                              'mean perimeter', 'mean area',
                              'mean smoothness', 'mean compactness',
                              'mean concavity', 'mean concave points',
                              'mean symmetry', 'mean fractal dimension',
                              'radius error', 'texture error',
                              'perimeter error', 'area error',
                              'smoothness error', 'compactness error',
                              'concavity error', 'concave points error',
                              'symmetry error', 'fractal dimension error',
                              'worst radius', 'worst texture',
                              'worst perimeter', 'worst area',
                              'worst smoothness', 'worst compactness',
                              'worst concavity', 'worst concave points',
                              'worst symmetry', 'worst fractal dimension'])

    if return_X_y:
        return data, target

    return Bunch(data=data, target=target,
                 target_names=target_names,
                 DESCR=fdescr,
                 feature_names=feature_names)


def load_digits(n_class=10, return_X_y=False):
    """Load and return the digits dataset (classification).

    Each datapoint is a 8x8 image of a digit.

    =================   ==============
    Classes                         10
    Samples per class             ~180
    Samples total                 1797
    Dimensionality                  64
    Features             integers 0-16
    =================   ==============

    Read more in the :ref:`User Guide <datasets>`.

    Parameters
    ----------
    n_class : integer, between 0 and 10, optional (default=10)
        The number of classes to return.

    return_X_y : boolean, default=False.
        If True, returns ``(data, target)`` instead of a Bunch object.
        See below for more information about the `data` and `target` object.

        .. versionadded:: 0.18

    Returns
    -------
    data : Bunch
        Dictionary-like object, the interesting attributes are:
        'data', the data to learn, 'images', the images corresponding
        to each sample, 'target', the classification labels for each
        sample, 'target_names', the meaning of the labels, and 'DESCR',
        the full description of the dataset.

    (data, target) : tuple if ``return_X_y`` is True

        .. versionadded:: 0.18

    This is a copy of the test set of the UCI ML hand-written digits datasets
    http://archive.ics.uci.edu/ml/datasets/Optical+Recognition+of+Handwritten+Digits

    Examples
    --------
    To load the data and visualize the images::

        >>> from sklearn.datasets import load_digits
        >>> digits = load_digits()
        >>> print(digits.data.shape)
        (1797, 64)
        >>> import matplotlib.pyplot as plt #doctest: +SKIP
        >>> plt.gray() #doctest: +SKIP
        >>> plt.matshow(digits.images[0]) #doctest: +SKIP
        >>> plt.show() #doctest: +SKIP
    """
    module_path = dirname(__file__)
    data = np.loadtxt(join(module_path, 'data', 'digits.csv.gz'),
                      delimiter=',')
    with open(join(module_path, 'descr', 'digits.rst')) as f:
        descr = f.read()
    target = data[:, -1].astype(np.int)
    flat_data = data[:, :-1]
    images = flat_data.view()
    images.shape = (-1, 8, 8)

    if n_class < 10:
        idx = target < n_class
        flat_data, target = flat_data[idx], target[idx]
        images = images[idx]

    if return_X_y:
        return flat_data, target

    return Bunch(data=flat_data,
                 target=target,
                 target_names=np.arange(10),
                 images=images,
                 DESCR=descr)


def load_diabetes(return_X_y=False):
    """Load and return the diabetes dataset (regression).

    ==============      ==================
    Samples total       442
    Dimensionality      10
    Features            real, -.2 < x < .2
    Targets             integer 25 - 346
    ==============      ==================

    Read more in the :ref:`User Guide <datasets>`.

    Parameters
    ----------
    return_X_y : boolean, default=False.
        If True, returns ``(data, target)`` instead of a Bunch object.
        See below for more information about the `data` and `target` object.

        .. versionadded:: 0.18

    Returns
    -------
    data : Bunch
        Dictionary-like object, the interesting attributes are:
        'data', the data to learn and 'target', the regression target for each
        sample.

    (data, target) : tuple if ``return_X_y`` is True

        .. versionadded:: 0.18
    """

    module_path = dirname(__file__)
    base_dir = join(module_path, 'data')
    data = np.loadtxt(join(base_dir, 'diabetes_data.csv.gz'))
    target = np.loadtxt(join(base_dir, 'diabetes_target.csv.gz'))

    with open(join(module_path, 'descr', 'diabetes.rst')) as rst_file:
        fdescr = rst_file.read()

    if return_X_y:
        return data, target

    return Bunch(data=data, target=target, DESCR=fdescr,
                 feature_names=['age', 'sex', 'bmi', 'bp',
                                's1', 's2', 's3', 's4', 's5', 's6'])


def load_linnerud(return_X_y=False):
    """Load and return the linnerud dataset (multivariate regression).

    ==============    ============================
    Samples total     20
    Dimensionality    3 (for both data and target)
    Features          integer
    Targets           integer
    ==============    ============================

    Parameters
    ----------
    return_X_y : boolean, default=False.
        If True, returns ``(data, target)`` instead of a Bunch object.
        See below for more information about the `data` and `target` object.

        .. versionadded:: 0.18

    Returns
    -------
    data : Bunch
        Dictionary-like object, the interesting attributes are: 'data' and
        'targets', the two multivariate datasets, with 'data' corresponding to
        the exercise and 'targets' corresponding to the physiological
        measurements, as well as 'feature_names' and 'target_names'.

    (data, target) : tuple if ``return_X_y`` is True

        .. versionadded:: 0.18
    """
    base_dir = join(dirname(__file__), 'data/')
    # Read data
    data_exercise = np.loadtxt(base_dir + 'linnerud_exercise.csv', skiprows=1)
    data_physiological = np.loadtxt(base_dir + 'linnerud_physiological.csv',
                                    skiprows=1)
    # Read header
    with open(base_dir + 'linnerud_exercise.csv') as f:
        header_exercise = f.readline().split()
    with open(base_dir + 'linnerud_physiological.csv') as f:
        header_physiological = f.readline().split()
    with open(dirname(__file__) + '/descr/linnerud.rst') as f:
        descr = f.read()

    if return_X_y:
        return data_exercise, data_physiological

    return Bunch(data=data_exercise, feature_names=header_exercise,
                 target=data_physiological,
                 target_names=header_physiological,
                 DESCR=descr)


def load_boston(return_X_y=False):
    """Load and return the boston house-prices dataset (regression).

    ==============     ==============
    Samples total                 506
    Dimensionality                 13
    Features           real, positive
    Targets             real 5. - 50.
    ==============     ==============

    Parameters
    ----------
    return_X_y : boolean, default=False.
        If True, returns ``(data, target)`` instead of a Bunch object.
        See below for more information about the `data` and `target` object.

        .. versionadded:: 0.18

    Returns
    -------
    data : Bunch
        Dictionary-like object, the interesting attributes are:
        'data', the data to learn, 'target', the regression targets,
        and 'DESCR', the full description of the dataset.

    (data, target) : tuple if ``return_X_y`` is True

        .. versionadded:: 0.18

    Examples
    --------
    >>> from sklearn.datasets import load_boston
    >>> boston = load_boston()
    >>> print(boston.data.shape)
    (506, 13)
    """
    module_path = dirname(__file__)

    fdescr_name = join(module_path, 'descr', 'boston_house_prices.rst')
    with open(fdescr_name) as f:
        descr_text = f.read()

    data_file_name = join(module_path, 'data', 'boston_house_prices.csv')
    with open(data_file_name) as f:
        data_file = csv.reader(f)
        temp = next(data_file)
        n_samples = int(temp[0])
        n_features = int(temp[1])
        data = np.empty((n_samples, n_features))
        target = np.empty((n_samples,))
        temp = next(data_file)  # names of features
        feature_names = np.array(temp)

        for i, d in enumerate(data_file):
            data[i] = np.asarray(d[:-1], dtype=np.float64)
            target[i] = np.asarray(d[-1], dtype=np.float64)

    if return_X_y:
        return data, target

    return Bunch(data=data,
                 target=target,
                 # last column is target value
                 feature_names=feature_names[:-1],
                 DESCR=descr_text)


def load_sample_images():
    """Load sample images for image manipulation.
    Loads both, ``china`` and ``flower``.

    Returns
    -------
    data : Bunch
        Dictionary-like object with the following attributes :
        'images', the two sample images, 'filenames', the file
        names for the images, and 'DESCR'
        the full description of the dataset.

    Examples
    --------
    To load the data and visualize the images:

    >>> from sklearn.datasets import load_sample_images
    >>> dataset = load_sample_images()     #doctest: +SKIP
    >>> len(dataset.images)                #doctest: +SKIP
    2
    >>> first_img_data = dataset.images[0] #doctest: +SKIP
    >>> first_img_data.shape               #doctest: +SKIP
    (427, 640, 3)
    >>> first_img_data.dtype               #doctest: +SKIP
    dtype('uint8')
    """
    # Try to import imread from scipy. We do this lazily here to prevent
    # this module from depending on PIL.
    try:
        try:
            from scipy.misc import imread
        except ImportError:
            from scipy.misc.pilutil import imread
    except ImportError:
        raise ImportError("The Python Imaging Library (PIL) "
                          "is required to load data from jpeg files")
    module_path = join(dirname(__file__), "images")
    with open(join(module_path, 'README.txt')) as f:
        descr = f.read()
    filenames = [join(module_path, filename)
                 for filename in os.listdir(module_path)
                 if filename.endswith(".jpg")]
    # Load image data for each image in the source folder.
    images = [imread(filename) for filename in filenames]

    return Bunch(images=images,
                 filenames=filenames,
                 DESCR=descr)


def load_sample_image(image_name):
    """Load the numpy array of a single sample image

    Parameters
    -----------
    image_name : {`china.jpg`, `flower.jpg`}
        The name of the sample image loaded

    Returns
    -------
    img : 3D array
        The image as a numpy array: height x width x color

    Examples
    ---------

    >>> from sklearn.datasets import load_sample_image
    >>> china = load_sample_image('china.jpg')   # doctest: +SKIP
    >>> china.dtype                              # doctest: +SKIP
    dtype('uint8')
    >>> china.shape                              # doctest: +SKIP
    (427, 640, 3)
    >>> flower = load_sample_image('flower.jpg') # doctest: +SKIP
    >>> flower.dtype                             # doctest: +SKIP
    dtype('uint8')
    >>> flower.shape                             # doctest: +SKIP
    (427, 640, 3)
    """
    images = load_sample_images()
    index = None
    for i, filename in enumerate(images.filenames):
        if filename.endswith(image_name):
            index = i
            break
    if index is None:
        raise AttributeError("Cannot find sample image: %s" % image_name)
    return images.images[index]


def _pkl_filepath(*args, **kwargs):
    """Ensure different filenames for Python 2 and Python 3 pickles

    An object pickled under Python 3 cannot be loaded under Python 2.
    An object pickled under Python 2 can sometimes not be loaded
    correctly under Python 3 because some Python 2 strings are decoded as
    Python 3 strings which can be problematic for objects that use Python 2
    strings as byte buffers for numerical data instead of "real" strings.

    Therefore, dataset loaders in scikit-learn use different files for pickles
    manages by Python 2 and Python 3 in the same SCIKIT_LEARN_DATA folder so
    as to avoid conflicts.

    args[-1] is expected to be the ".pkl" filename. Under Python 3, a
    suffix is inserted before the extension to s

    _pkl_filepath('/path/to/folder', 'filename.pkl') returns:
      - /path/to/folder/filename.pkl under Python 2
      - /path/to/folder/filename_py3.pkl under Python 3+

    """
    py3_suffix = kwargs.get("py3_suffix", "_py3")
    basename, ext = splitext(args[-1])
    if sys.version_info[0] >= 3:
        basename += py3_suffix
    new_args = args[:-1] + (basename + ext,)
    return join(*new_args)


class PartialURLOpener(urllib.FancyURLopener):
    """A class to override urllib.FancyURLopener and
    ignore HTTP error 206 (partial file being sent), since
    that is what we expect when we resume the download
    of a partial file
    """

    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        """
        Override HTTP Error 206 (partial file being sent). This error
        indicates that the Range header is supported
        """
        # Ignore the expected "error" code
        pass


def _md5(path):
    """Calculate the md5 hash of the file at path.

    Parameters
    -----------
    path: String
        Path of file to calculate MD5 hash of.

    Returns
    -------
    md5hash : String
        MD5 hash of the file at the provided path.

    """

    md5hash = hashlib.md5()
    chunk_size = 8192
    with open(path, "rb") as f:
        while 1:
            buffer = f.read(chunk_size)
            if not buffer:
                break
            md5hash.update(buffer)
    return md5hash.hexdigest()


def _validate_file_md5(expected_checksum, path):
    """Compare the MD5 checksum of a file at a path with
    an expected MD5 checksum. If they do not match,
    remove the file at path and throw a ValueError.

    Parameters
    -----------
    expected_checksum: String
        Expected MD5 checksum of file at path.

    path: String
        Path of file to compare MD5 hash of.

    """

    if expected_checksum != _md5(path):
        # remove the corrupted file
        remove(path)
        raise IOError("{} has an MD5 hash differing "
                      "from expected, file may be "
                      "corrupted.".format(path))


def _fetch_url(url, path, checksum):
    """
    Fetch a dataset from a URL and check the MD5 checksum to ensure
    fetch was completed and the correct file was downloaded

    Parameters
    -----------
    URL: String
        URL to fetch the download from.

    path: String
        Path to save the file to.

    checksum: String
        MD5 checksum to verify against the data

    """

    resume_url_downloader = PartialURLOpener()
    path_temp = path + ".part"
    if exists(path_temp):
        # since path_temp exists, resume download
        temp_file = open(path_temp, "ab")
        # get the amount of path_temp we've downloaded
        existing_size = getsize(path_temp)
        request_range = 'bytes={}-'.format(existing_size)

        print("Resuming download from {}, "
              "already have {} bytes".format(url, existing_size),
              file=sys.stderr)
        resume_url_downloader.addheader("Range", request_range)

        try:
            # Try to download only the remainder of the file
            dataset_url = resume_url_downloader.open(url)
            # get the content range of the request
            content_range = dataset_url.info().get('Content-Range')
            if (content_range is None or
                    not content_range.startswith(request_range)):
                raise IOError("Server does not support the HTTP Range "
                              "header, cannot resume download.")
        except Exception:
            # delete the temp file and retry download of whole file
            remove(path_temp)
            print("Attempting to re-download file after {!r}.".format(exec),
                  file=sys.stderr)
            _fetch_url(url, path, checksum)
    else:
        # no path_temp, so download from scratch
        temp_file = open(path_temp, "wb")
        dataset_url = resume_url_downloader.open(url)
    while 1:
        chunk = dataset_url.read(8192)
        if not chunk:
            break
        temp_file.write(chunk)

    dataset_url.close()
    temp_file.close()
    # verify checksum of downloaded temp file
    _validate_file_md5(checksum, path_temp)

    # move temporary file to the expected location
    rename(path_temp, path)
