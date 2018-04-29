# ABC codes adopted from https://github.com/rcmorehead/simpleabc/blob/master/simple_abc.py
import matplotlib.pyplot as plt
import random
import settings
import numpy as np
from models_single_product_mcmc_replaced import market
import copy
random.seed()

SENTINEL = object()


class ABC_GenerativeModel(market):
    """
    Base class for constructing models for approximate bayesian computing
    inherits the market and implements the following additional methods:
    * Model.draw_theta
    * Model.generate_data
    * Model.summary_stats
    * Model.distance_function
    """

    def __init__(self, params={}, prior=np.linspace(0,2,100), conditioning=False, direction=None):
        """
        params dict for the generative model.
        if conditioning is True, then direction should be 'above' or 'below'
        """
        super(ABC_GenerativeModel, self).__init__(params)
        self.fixed_params['input_type'] = 'histograms'
        self.fixed_params['input_histograms_are_normalized'] = True
        self.params['input_type'] = 'histograms'
        self.params['input_histograms_are_normalized'] = True
        self.conditioning = conditioning
        self.direction = direction
        self.prior = prior


    def set_data(self, data):
        self.data = data # this is the observed data
        self.data_summary_stats = self.summary_stats(self.data)

    def set_epsilon(self, epsilon):
        """
        A method to give the model object the value of epsilon if your model
        code needs to know it.
        """
        self.epsilon = epsilon

    # def generate_data_and_reduce(self, theta):
    #     """
    #     A combined method for
    #     (i) generating data,
    #     (ii) calculating summary statistics
    #     (iii) and evaluating the distance function
    #     """
    #     synthetic_data = self.generate_data(theta)
    #     synthetic_summary_stats = self.summary_stats(synthetic_data)
    #     distance = self.distance_function(synthetic_summary_stats, self.data_summary_stats)
    #
    #     return distance

    def draw_theta(self):
        """
        Sub-classable method for drawing from a prior distribution.
        This method should return an array-like iterable that is a vector of
        proposed model parameters from your prior distribution.
        """
        # print('prior is:', self.prior)
        theta = np.random.choice(self.prior)
        # print('drawn theta:', theta)
        return theta

    def generate_data(self, theta):
        """
        Sub-classable method for generating synthetic data sets from forward
        model.
        This method should return an array/matrix/table of simulated data
        taking vector theta as an argument.
        """
        # self.fixed_params['rate_decision_threshold'] = theta
        data = self.generateTimeseries(theta, raw=True, get_percieved_qualities_and_avg_reviews=False, do_not_return_df=True)
        # print('synthetic', data)
        return data

    def summary_stats(self, data):
        """
        Sub-classable method for computing summary statistics.
        This method should return an array-like iterable of summary statistics
        taking an array/matrix/table as an argument
        """
        # return np.asarray(data.iloc[-1])
        summary = np.asarray(self.process_raw_timeseries(data, processed_output='histogram'))
        # print('summary', summary)
        return summary

    def distance_function(self, summary_stats, summary_stats_synth):
        """
        Sub-classable method for computing a distance function.
        This method should return a distance D of for comparing to the
        acceptance tolerance (epsilon) taking two array-like iterables of
        summary statistics as an argument (nominally the observed summary
        statistics and .
        """
        distance = 0.2*sum(abs(summary_stats-summary_stats_synth))
        return distance

    def process_raw_timeseries(self,raw_timeseries, processed_output='histogram'):
        """Returns the histogram can be applied to the the output of generateTimeseries(raw=True)
        should do all_ratings = list(raw_timeseries['Rating']) before applying process_raw_timeseries() on the data from
        tablets.
        """
        if self.conditioning:
            assert self.direction is not None, "The direction for conditioning is not provided."

            raw_averages = []
            for i in range(1,len(raw_timeseries)+1):
                raw_averages.append(np.mean(raw_timeseries[:i]))


            print('raw_averages' , raw_averages)

            conditioned_timeseries = [raw_timeseries[0]]

            for i in range(1, len(raw_timeseries)):
                if self.direction is 'above' and raw_timeseries[i] < raw_averages[i-1]:
                    # print('raw_timeseries[i]', raw_timeseries[i])
                    # print('raw_averages[i-1]', raw_averages[i-1])
                    continue
                elif self.direction is 'below' and raw_timeseries[i] > raw_averages[i-1]:
                    continue
                else:
                    conditioned_timeseries.append(raw_timeseries[i])

            print('conditioned_timeseries', conditioned_timeseries)

        if self.conditioning:
            all_ratings = conditioned_timeseries
        else:
            all_ratings = raw_timeseries

        if processed_output == 'histogram':
            current_histogram = [0] * self.params['number_of_rating_levels']
            # histogram_timeseries = [[0] * self.params['number_of_rating_levels']]
            # print()
            for rating in all_ratings:
                # print(rating)
                current_histogram[rating - 1] += 1
                # append_histogram = copy.deepcopy(current_histogram)
                # histogram_timeseries.append(append_histogram)
        # df = pd.DataFrame(histogram_timeseries)
        output_histogram = copy.deepcopy(current_histogram)
        if self.params['input_histograms_are_normalized'] and (sum(output_histogram) > 0):
            output_histogram = list(np.array(output_histogram) / (1.0 * sum(output_histogram)))
        # print('output_histogram', output_histogram)
        return output_histogram




################################################################################
#########################    ABC Algorithms   ##################################
################################################################################

def basic_abc(model, data, epsilon=1, min_samples=10,verbose=False):
    # ,
    #           parallel=False, n_procs='all', pmc_mode=False,
    #           weights='None', theta_prev='None', tau_squared='None'):
    """
    Perform Approximate Bayesian Computation (ABC) on a data set given a
    forward model.
    ABC is a likelihood-free method of Bayesian inference that uses simulation
    to approximate the true posterior distribution of a parameter. It is
    appropriate to use in situations where:
    The likelihood function is unknown or is too computationally
    expensive to compute.
    There exists a good forward model that can produce data sets
    like the one of interest.
    It is not a replacement for other methods when a likelihood
    function is available!
    Parameters
    ----------
    model : object
        A model that is a subclass of simpleabc.Model
    data  : object, array_like
        The "observed" data set for inference.
    epsilon : float, optional
        The tolerance to accept parameter draws, default is 1.
    min_samples : int, optional
        Minimum number of posterior samples.
    parallel : bool, optional
        Run in parallel mode. Default is a single thread.
    n_procs : int, str, optional
        Number of subprocesses in parallel mode. Default is 'all' one for each
        available core.
    pmc_mode : bool, optional
        Population Monte Carlo mode on or off. Default is False. This is not
        meant to be called by the user, but is set by simple_abc.pmc_abc.
    weights : object, array_like, str, optional
        Importance sampling weights from previous PMC step. Used  by
        simple_abc.pmc_abc only.
    theta_prev : object, array_like, str, optional
        Posterior draws from previous PMC step.  Used by simple_abc.pmc_abc
        only.
    tau_squared : object, array_like, str, optional
        Previous Gaussian kernel variances. for importance sampling. Used by
        simple_abc.pmc_abc only.
    Returns
    -------
    posterior : numpy array
        Array of posterior samples.
    distances : object
        Array of accepted distances.
    accepted_count : float
        Number of  posterior samples.
    trial_count : float
        Number of total samples attempted.
    epsilon : float
        Distance tolerance used.
    weights : numpy array
        Importance sampling weights. Returns an array of 1s where
        size = posterior.size when not in pmc mode.
    tau_squared : numpy array
        Gaussian kernel variances. Returns an array of 0s where
        size = posterior.size when not in pmc mode.
    eff_sample : numpy array
        Effective sample size. Returns an array of 1s where
        size = posterior.size when not in pmc mode.
    Examples
    --------
    Forth coming.
    """

    posterior, rejected, distances = [], [], []
    trial_count, accepted_count = 0, 0

    data_summary_stats = model.summary_stats(data)
    model.set_epsilon(epsilon)

    while accepted_count < min_samples:
        trial_count += 1

        # if pmc_mode:
        #     theta_star = theta_prev[:, np.random.choice(
        #                             xrange(0, theta_prev.shape[1]),
        #                             replace=True, p=weights/weights.sum())]
        #
        #     theta = stats.multivariate_normal.rvs(theta_star, tau_squared)
        #     if np.isscalar(theta) == True:
        #         theta = [theta]
        #
        #
        # else:
        #     theta = model.draw_theta()

        theta = model.draw_theta()

        synthetic_data = model.generate_data(theta)

        synthetic_summary_stats = model.summary_stats(synthetic_data)

        distance = model.distance_function(data_summary_stats,
                                           synthetic_summary_stats)

        if distance < epsilon:
            accepted_count += 1
            posterior.append(theta)
            distances.append(distance)
            print('ACCEPTED!!',  accepted_count, 'out of', trial_count, theta)

        else:
            if verbose:
                print('REJECTED!!', trial_count - accepted_count, theta)
                # pass
            #rejected.append(theta)

    posterior = np.asarray(posterior).T

    if len(posterior.shape) > 1:
        n = posterior.shape[1]
    else:
        n = posterior.shape[0]


    # weights = np.ones(n)
    # tau_squared = np.zeros((posterior.shape[0], posterior.shape[0]))
    # eff_sample = n

    return (posterior, distances,
            accepted_count, trial_count,
            epsilon)#, weights, tau_squared, eff_sample)



# error type can be 'MSE' or 'MAE'
# estimator types can be 'posterior_mean', 'posterior_median', 'MAP'
class Estimator():
    def __init__(self, model, epsilon, n_posterior_samples=10, n_samples=10,
                 estimator_type='posterior_mean', bin_size=10, error_type='MSE'):
        self.model = model
        self.n_samples = n_samples # number of samples generated for each true theta to test the estimator for
        # the given theta
        self.n_posterior_samples = n_posterior_samples # number of samples from the posterior toi construct an estimator
        self.estimator_type=estimator_type # estimator_type can be 'posterior_mean', 'MAP', 'median'
        self.bin_size = bin_size
        self.error_type = error_type  # error type can be MSE or MAE
        self.epsilon = epsilon

    def get_estimates(self, true_theta, bin_size=5, do_hist=False):
        theta_estimates = np.zeros(self.n_samples)
        for i in range(self.n_samples):
            data = self.model.generate_data(true_theta)
            (posterior_samples, _, _, _, _) = basic_abc(self.model, data, self.epsilon, self.n_posterior_samples)
            posterior_samples = np.asarray(posterior_samples)
            # print('sampled_thetas:',sampled_thetas)
            if do_hist:
                plt.hist(posterior_samples)
                plt.show()
                plt.title('Posterior Samples for theta = '+str(true_theta))
            # print(self.estimator_type)
            if self.estimator_type == 'posterior_mean':
                theta_estimates[i] = posterior_samples.mean()
            elif self.estimator_type == 'MAP':
                hist, bin_edges = np.histogram(posterior_samples, bins=bin_size)
                j = np.argmax(hist)
                theta_estimates[i] = (bin_edges[j] + bin_edges[j+1]) / 2.0
            elif self.estimator_type == 'posterior_median':
                theta_estimates[i] = np.median(posterior_samples)
        error = 0
        if self.error_type == 'MSE':
            error = np.sum((selected_theta - true_theta)**2 for selected_theta in theta_estimates)
        elif self.error_type == 'MAE':
            error = np.sum(abs(selected_theta - true_theta) for selected_theta in theta_estimates)
        error /= self.n_samples
        return error, theta_estimates

    def get_estimates_for_true_thetas(self, true_thetas=[2,4,6], do_plot=True, do_hist=False,
                                      symmetric=False,verbose=True):
        estimated_thetas = [] # a list of theta_estimated for each true_theta
        mean_estimated_thetas = []
        errors = []
        for true_theta in true_thetas:
            if verbose:
                print('true theta:', true_theta)
            theta_error, theta_estimates = self.get_estimates(true_theta, do_hist=do_hist)
            estimated_thetas += [theta_estimates]
            mean_estimated_thetas += [np.mean(theta_estimates)]
            errors += [theta_error]
            if verbose:
                print('theta estimates:', theta_estimates)
        if do_plot:
            if symmetric:
                plt.figure()
                plt.errorbar(true_thetas, mean_estimated_thetas, yerr=errors)
                plt.title(self.estimator_type + 'performance')
                plt.xlabel('true theta')
                plt.ylabel(self.estimator_type)
                plt.show()
            else: # not symmetric
                lower_errors = []
                upper_errors = []
                for i in range(len(true_thetas)):
                    theta_estimates = estimated_thetas[i]
                    lower_errors += [abs(np.min(theta_estimates) - true_thetas[i])]
                    upper_errors += [abs(np.max(theta_estimates) - - true_thetas[i])]
                asymmetric_errors = [lower_errors, upper_errors]
                plt.figure()
                plt.errorbar(true_thetas, mean_estimated_thetas, yerr=asymmetric_errors)
                plt.title(self.estimator_type + 'performance')
                plt.xlabel('true theta')
                plt.ylabel(self.estimator_type)
                plt.show()


# Replaced with the Estimator class:
# def eval_ABC_posterior(true_theta, model, epsilon, n_posterior_samples=10, n_estimates=10,
#                    estimator_type='posterior_mean', bin_size=10):
#     '''Given true theta generates data and uses the generated in ABC to get posteriors samples and evaluates the quality
#     of posteriors samples as estimators for true theta. Two modes of estimation: MAP and Bayes estimator (mean_posterior)
#     '''
#     theta_estimates = np.zeros(n_estimates)
#     for i in range(n_estimates):
#         print('i:',i)
#         data = model.generate_data(true_theta)
#         (posterior_samples, _, _, _, _) = basic_abc(model, data, epsilon, n_posterior_samples)
#         posterior_samples = np.asarray(posterior_samples)
#         plt.hist(posterior_samples)
#         plt.show()
#         if estimator_type == 'posterior_mean':
#             theta_estimates[i] = posterior_samples.mean()
#         elif estimator_type == 'MAP':
#             hist, bin_edges = np.histogram(posterior_samples, bins=bin_size)
#             j = np.argmax(hist)
#             theta_estimates[i] = (bin_edges[j] + bin_edges[j + 1]) / 2.
#     error = 0
#     if estimator_type == 'posterior_mean':
#         error = np.sum((estimated_theta - true_theta) ** 2 for estimated_theta in theta_estimates)
#     elif estimator_type == 'MAP':
#         error = np.sum(abs(estimated_theta - true_theta) for estimated_theta in theta_estimates)
#     error /= n_estimates
#
#     return error, theta_estimates