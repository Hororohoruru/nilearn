import numpy as np

import nibabel
import pytest

from nilearn._utils import testing, as_ndarray, data_gen
from nilearn._utils.exceptions import DimensionError
from nilearn.image import get_data
from nilearn.input_data.multi_nifti_labels_masker import MultiNiftiLabelsMasker
from nilearn.input_data.nifti_labels_masker import NiftiLabelsMasker


def test_multi_nifti_labels_masker():
    # Check working of shape/affine checks
    shape1 = (13, 11, 12)
    affine1 = np.eye(4)

    shape2 = (12, 10, 14)
    affine2 = np.diag((1, 2, 3, 1))

    n_regions = 9
    length = 3

    fmri01_img, mask01_img = data_gen.generate_fake_fmri(shape=shape1, affine=affine1,
                                                         length=length)
    fmri11_img, mask11_img = data_gen.generate_fake_fmri(shape=shape1, affine=affine1,
                                                         length=length)
    fmri12_img, mask12_img = data_gen.generate_fake_fmri(shape=shape1, affine=affine2,
                                                         length=length)
    fmri21_img, mask21_img = data_gen.generate_fake_fmri(shape=shape2, affine=affine1,
                                                         length=length)

    labels11_img = data_gen.generate_labeled_regions(shape1, affine=affine1,
                                                     n_regions=n_regions)

    mask_img_4d = nibabel.Nifti1Image(np.ones((2, 2, 2, 2), dtype=np.int8),
                                      affine=np.diag((4, 4, 4, 1)))

    # verify that 4D mask arguments are refused
    masker = NiftiLabelsMasker(labels11_img, mask_img=mask_img_4d)
    with pytest.raises(DimensionError,
                       match="Input data has incompatible dimensionality: "
                             "Expected dimension is 3D and you provided "
                             "a 4D image."):
        masker.fit()

    # check exception when transform() called without prior fit()
    masker11 = MultiNiftiLabelsMasker(labels11_img, resampling_target='data')
    with pytest.raises(ValueError, match='has not been fitted. '):
        masker11.transform(fmri11_img)

    # No exception raised here
    signals11 = masker11.fit().transform(fmri11_img)
    assert signals11.shape == (length, n_regions)

    # Should work with 4D + 1D input too (also test fit_transform)
    signals_input = [fmri01_img, fmri11_img]
    signals_list = masker11.fit_transform(signals_input)
    assert len(signals_list) == len(signals_input)
    for signals in signals_list:
        assert signals.shape == (length, n_regions)

    # No exception should be raised either
    masker11 = NiftiLabelsMasker(labels11_img, resampling_target=None)
    masker11.fit()
    masker11.inverse_transform(signals11)

    masker11 = NiftiLabelsMasker(labels11_img, mask_img=mask11_img,
                                 resampling_target=None)
    signals11 = masker11.fit().transform(fmri11_img)
    assert signals11.shape == (length, n_regions)

    # Test all kinds of mismatch between shapes and between affines
    masker11 = NiftiLabelsMasker(labels11_img, resampling_target=None)
    masker11.fit()
    pytest.raises(ValueError, masker11.transform, fmri12_img)
    pytest.raises(ValueError, masker11.transform, fmri21_img)

    masker11 = NiftiLabelsMasker(labels11_img, mask_img=mask12_img,
                                 resampling_target=None)
    pytest.raises(ValueError, masker11.fit)

    masker11 = NiftiLabelsMasker(labels11_img, mask_img=mask21_img,
                                 resampling_target=None)
    pytest.raises(ValueError, masker11.fit)

    # Transform, with smoothing (smoke test)
    masker11 = NiftiLabelsMasker(labels11_img, smoothing_fwhm=3,
                                 resampling_target=None)
    signals11 = masker11.fit().transform(fmri11_img)
    assert signals11.shape == (length, n_regions)

    masker11 = NiftiLabelsMasker(labels11_img, smoothing_fwhm=3,
                                 resampling_target=None)
    signals11 = masker11.fit_transform(fmri11_img)
    assert signals11.shape == (length, n_regions)

    with pytest.raises(ValueError, match='has not been fitted. '):
        NiftiLabelsMasker(labels11_img).inverse_transform(signals11)

    # Call inverse transform (smoke test)
    fmri11_img_r = masker11.inverse_transform(signals11)
    assert fmri11_img_r.shape == fmri11_img.shape
    np.testing.assert_almost_equal(fmri11_img_r.affine, fmri11_img.affine)
