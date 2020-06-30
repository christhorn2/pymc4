"""Test suite for GP Module"""

import tensorflow as tf

import pymc4 as pm

import pytest

from .fixtures.fixtures_gp import get_data, get_batch_shape, get_sample_shape, get_feature_shape
from .fixtures.fixtures_gp import (
    get_gp_model,
    get_mean_func,
    get_cov_func,
    get_unique_cov_func,
    get_all_cov_func,
)


def build_model(model_name, model_kwargs, feature_ndims):
    """Create a gp model from an element in the `GP_MODELS` list"""
    # First, create a mean function
    name = model_kwargs["mean_fn"][0]
    kwargs = model_kwargs["mean_fn"][1]
    MeanClass = getattr(pm.gp.mean, name)
    mean_fn = MeanClass(**kwargs, feature_ndims=feature_ndims)
    # Then, create the kernel function
    name = model_kwargs["cov_fn"][0]
    kwargs = model_kwargs["cov_fn"][1]
    KernelClass = getattr(pm.gp.cov, name)
    cov_fn = KernelClass(**kwargs, feature_ndims=feature_ndims)
    # Now, create the model and return
    GPModel = getattr(pm.gp, model_name)
    model = GPModel(mean_fn=mean_fn, cov_fn=cov_fn)
    return model


def test_gp_models_prior(tf_seed, get_data, get_gp_model):
    """Test the prior method of a GP mode, if present"""
    batch_shape, sample_shape, feature_shape, X = get_data
    gp_model = build_model(get_gp_model[0], get_gp_model[1], len(feature_shape))
    # @pm.model
    # def model(gp, X):
    #     yield gp.prior('f', X)
    try:
        # sampling_model = model(gp_model, X)
        # trace = pm.sample(sampling_model, num_samples=3, num_chains=1, burn_in=10)
        # trace = np.asarray(trace.posterior["model/f"])
        prior_dist = gp_model.prior("prior", X)
    except NotImplementedError:
        pytest.skip("Skipping: prior not implemented")
    # if sample_shape == (1,):
    #     assert trace.shape == (1, 3, ) + batch_shape
    # else:
    #     assert trace.shape == (1, 3, ) + batch_shape + sample_shape
    if sample_shape == (1,):
        assert prior_dist.sample(1).shape == (1,) + batch_shape
    else:
        assert prior_dist.sample(1).shape == (1,) + batch_shape + sample_shape


def test_gp_models_conditional(tf_seed, get_data, get_gp_model):
    """Test the conditional method of a GP mode, if present"""
    batch_shape, sample_shape, feature_shape, X = get_data
    gp_model = build_model(get_gp_model[0], get_gp_model[1], len(feature_shape))
    Xnew = tf.random.normal(batch_shape + sample_shape + feature_shape)

    @pm.model
    def model(gp, X, Xnew):
        f = yield gp.prior("f", X)
        yield gp.conditional("fcond", Xnew, given={"X": X, "f": f})

    try:
        # sampling_model = model(gp_model, X, Xnew)
        # trace = pm.sample(sampling_model, num_samples=3, num_chains=1, burn_in=10)
        # trace = np.asarray(trace.posterior["model/fcond"])
        f = gp_model.prior("f", X).sample(1)[0]
        cond_dist = gp_model.conditional("fcond", Xnew, given={"X": X, "f": f})
        cond_samples = cond_dist.sample(3)
    except NotImplementedError:
        pytest.skip("Skipping: conditional not implemented")
    # if sample_shape == (1,):
    #     assert trace.shape == (1, 3,) + batch_shape
    # else:
    #     assert trace.shape == (1, 3,) + batch_shape + sample_shape
    if sample_shape == (1,):
        assert cond_samples.shape == (3,) + batch_shape
    else:
        assert cond_samples.shape == (3,) + batch_shape + sample_shape


def test_gp_invalid_prior(tf_seed):
    """Test if an error is thrown for invalid model prior"""

    @pm.model
    def invalid_model(gp, X, X_new):
        f = gp.prior("f", X)
        cond = yield gp.conditional("fcond", X_new, given={"X": X, "f": f})

    with pytest.raises(ValueError, match=r"must be a numpy array or tensor"):
        gp = pm.gp.LatentGP(cov_fn=pm.gp.cov.ExpQuad(1.0, 1.0))
        X = tf.random.normal((2, 5, 1))
        X_new = tf.random.normal((2, 2, 1))
        trace = pm.sample(invalid_model(gp, X, X_new), num_samples=1, burn_in=1, num_chains=1)
