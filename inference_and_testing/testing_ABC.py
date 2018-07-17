# This is to test the performance of the estimators that use ABC posterior samples.
# We plot the estimated parameter versus the true values.

import settings
from inference_ABC import *



random.seed()


if __name__ == '__main__':

    true_thetas = [0.5, 0.75, 1, 1.25, 1.5, 1.75]#, 1, 1.25, 1.5, 1.75, 2]
    prior_theta = np.linspace(0, 2.5, 100)
    gen_model = ABC_GenerativeModel(params=settings.params, prior=prior_theta,
                                    conditioning=False, direction=None)

    estimator = Estimator(gen_model, epsilons=[0.05], n_posterior_samples=500, n_samples=1,
                 estimator_type='All', bin_size=10, error_type='MSE')

    # estimator.get_estimates_for_true_thetas(true_thetas, do_plot=settings.do_plots, symmetric=True,
    #                                         verbose=True, do_hist=False,
    #                                         compute_estimates=False,
    #                                         save_estimates=False,
    #                                         load_estimates=True)
    estimator.get_estimates_for_observed_data(observed_data=settings.data,
                                              do_hist=True,
                                              compute_posterior_samples=True,
                                              save_posterior_samples=True,
                                              load_posterior_samples=False)







