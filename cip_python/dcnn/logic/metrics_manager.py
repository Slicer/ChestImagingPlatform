"""
Different metrics used in deep learning algorithms
"""
import inspect
import tensorflow as tf
import tensorflow.keras.backend as K


class MetricsManager(object):
    """
    MetricsManager class contains the logic to use common metrics,
    as well as to extend the class to create new metrics than can be directly parsed from a string.
    It also implements some general metrics
    """
    @classmethod
    def get_metric(cls, metric_name, *args, **kwargs):
        """
        Get a "pointer to a metric function" defined in this class (or any child class), based on a metric name and
        a set of optional parameters
        :param metric_name: str. Name of the metric
        :param args: positional parameters
        :param kwargs: named parameters
        :return: "Pointer" to a function that can be used by Keras
        """
        metrics = dict(inspect.getmembers(cls, inspect.ismethod))
        if metric_name not in metrics:
            raise Exception("Metric '{}' not found".format(metric_name))
        metric = metrics[metric_name]
        param_names = inspect.getargspec(metric).args
        try:
            if param_names != ['cls', 'y_true', 'y_pred']:
                # Parametric metric. Return a call to the function with all the positional and named parameters
                metric = metrics[metric_name](*args, **kwargs)
                # This code is not compatible with Python 3.6
                # param_names = metric.__code__.co_varnames
                # internal_function = metric.__code__.co_name
                # if param_names != ('y_true', 'y_pred'):
                #     warnings.warn("The internal function '{0}' in metric '{1}' does not match the expected signature. "
                #                   "Use the signature {0}(y_true, y_pred) in the internal function to remove this warning" \
                #                   .format(internal_function, metric_name))
            return metric
        except:
            raise Exception("There is not a valid signature for the metric '{0}'. Please make sure that the metric "
                           "(or an internal function of it) matches the signature 'my_function(y_true, y_pred)', ".format(metric_name))

    @classmethod
    def contains_metric(cls, metric_name):
        """
        Indicate if the passed metric belongs to the class
        :param metric_name: str. Metric name
        :return: Boolean
        """
        metrics = dict(inspect.getmembers(cls, inspect.ismethod))
        return metric_name in metrics


    ###########################################################################################################
    # METRICS #
    ###########################################################################################################
    @classmethod
    def dice_coef(cls, y_true, y_pred):
        smooth = 1.0
        y_true_f = K.flatten(y_true)
        y_pred_f = K.flatten(y_pred)
        intersection = K.sum(y_true_f * y_pred_f)
        return (2. * intersection + smooth) / (K.sum(y_true_f) + K.sum(y_pred_f) + smooth)

    @classmethod
    def dice_coef_loss(cls, y_true, y_pred):
        return 1.0-cls.dice_coef(y_true, y_pred)

    @classmethod
    def multiclass_2D_dice_coef(cls, smooth=1.0):
        smooth = float(smooth)

        def _multiclass_2D_dice_coef_(y_true, y_pred):
            y_true = K.permute_dimensions(y_true, (3, 1, 2, 0))
            y_pred = K.permute_dimensions(y_pred, (3, 1, 2, 0))

            y_true_pos = K.batch_flatten(y_true)
            y_pred_pos = K.batch_flatten(y_pred)

            true_pos = K.sum(y_true_pos * y_pred_pos, 1)
            false_neg = K.sum(y_true_pos * (1 - y_pred_pos), 1)
            false_pos = K.sum((1 - y_true_pos) * y_pred_pos, 1)
            return K.mean((2. * true_pos + smooth) / (2. * true_pos + false_pos + false_neg + smooth))

        return _multiclass_2D_dice_coef_

    @classmethod
    def multiclass_2D_dice_loss(cls, smooth=1.):
        smooth = float(smooth)

        def _multiclass_2D_dice_loss_(y_true, y_pred):
            y_true = K.permute_dimensions(y_true, (3, 1, 2, 0))
            y_pred = K.permute_dimensions(y_pred, (3, 1, 2, 0))

            y_true_pos = K.batch_flatten(y_true)
            y_pred_pos = K.batch_flatten(y_pred)
            true_pos = K.sum(y_true_pos * y_pred_pos, 1)
            false_neg = K.sum(y_true_pos * (1 - y_pred_pos), 1)
            false_pos = K.sum((1 - y_true_pos) * y_pred_pos, 1)
            dice_coef = (2. * true_pos + smooth) / (2. * true_pos + false_pos + false_neg + smooth)
            return K.mean(1 - dice_coef)

        return _multiclass_2D_dice_loss_

    @classmethod
    def l2(cls, y_true, y_pred):
        """
        L2 loss (squared L2 norm). One value per data point (reduce all the possible dimensions)
        :param y_true: Tensor (tensorflow). Ground truth tensor
        :param y_pred: Tensor (tensorflow). Prediction tensor
        :return: Tensor (tensorflow)
        """
        shape = y_pred.get_shape()
        axis = tuple(range(1, len(shape)))
        result = K.sum((y_true - y_pred) ** 2, axis=axis)
        return result

    @classmethod
    def l1(cls, y_true, y_pred):
        """
        L1 norm  (one value per data point, that will be a 1-D tensor)
        :param y_true: Tensor (tensorflow). Ground truth tensor
        :param y_pred: Tensor (tensorflow). Prediction tensor
        :return: Tensor (tensorflow)
        """
        result = K.sum(K.abs(y_true - y_pred), axis=1)
        return result

    @classmethod
    def focal_loss(cls, gamma=2.0, alpha=1.0):
        """
        Implement focal loss as described in https://arxiv.org/abs/1708.02002
        :param gamma: float
        :param alpha: float
        :return: Tensor (tensorflow)
        """
        gamma = float(gamma)
        alpha = float(alpha)

        def _focal_loss_(y_true, y_pred):
            eps = 1e-12
            y_pred = K.clip(y_pred, eps, 1. - eps)  # improve the stability of the focal loss
            pt_1 = tf.where(tf.equal(y_true, 1), y_pred, tf.ones_like(y_pred))
            pt_0 = tf.where(tf.equal(y_true, 0), y_pred, tf.zeros_like(y_pred))
            return -K.sum(alpha * K.pow(1. - pt_1, gamma) * K.log(pt_1)) - K.sum(
                (1 - alpha) * K.pow(pt_0, gamma) * K.log(1. - pt_0))
        return _focal_loss_

    @classmethod
    def categorical_crossentropy_after_softmax(cls, y_true, y_pred):
        return K.categorical_crossentropy(y_true, y_pred, from_logits=True)

    @classmethod
    def tversky_index(cls, smooth=1., alpha=0.7):
        smooth = float(smooth)
        alpha = float(alpha)

        def _tversky_index_(y_true, y_pred):
            y_true_pos = K.flatten(y_true)
            y_pred_pos = K.flatten(y_pred)
            true_pos = K.sum(y_true_pos * y_pred_pos)
            false_neg = K.sum(y_true_pos * (1 - y_pred_pos))
            false_pos = K.sum((1 - y_true_pos) * y_pred_pos)
            return (true_pos + smooth) / (true_pos + alpha * false_neg + (1 - alpha) * false_pos + smooth)

        return _tversky_index_

    @classmethod
    def tversky_loss(cls, smooth=1., alpha=0.7):
        smooth = float(smooth)
        alpha = float(alpha)

        def _tversky_loss_(y_true, y_pred):
            y_true_pos = K.flatten(y_true)
            y_pred_pos = K.flatten(y_pred)
            true_pos = K.sum(y_true_pos * y_pred_pos)
            false_neg = K.sum(y_true_pos * (1 - y_pred_pos))
            false_pos = K.sum((1 - y_true_pos) * y_pred_pos)
            tversky_index = (true_pos + smooth) / (true_pos + alpha * false_neg + (1 - alpha) * false_pos + smooth)
            return 1 - tversky_index

        return _tversky_loss_

    @classmethod
    def focal_tversky_loss(cls, smooth=1., alpha=0.7, gamma=0.75):
        smooth = float(smooth)
        alpha = float(alpha)

        def _focal_tversky_loss_(y_true, y_pred):
            y_true_pos = K.flatten(y_true)
            y_pred_pos = K.flatten(y_pred)
            true_pos = K.sum(y_true_pos * y_pred_pos)
            false_neg = K.sum(y_true_pos * (1 - y_pred_pos))
            false_pos = K.sum((1 - y_true_pos) * y_pred_pos)
            tversky_index = (true_pos + smooth) / (true_pos + alpha * false_neg + (1 - alpha) * false_pos + smooth)
            return K.pow((1 - tversky_index), gamma)

        return _focal_tversky_loss_

    @classmethod
    def multiclass_2D_tversky_index(cls, smooth=1., alpha=0.7):
        smooth = float(smooth)
        alpha = float(alpha)

        def _multiclass_2D_tversky_index_(y_true, y_pred):
            y_true = K.permute_dimensions(y_true, (3, 1, 2, 0))
            y_pred = K.permute_dimensions(y_pred, (3, 1, 2, 0))

            y_true_pos = K.batch_flatten(y_true)
            y_pred_pos = K.batch_flatten(y_pred)
            true_pos = K.sum(y_true_pos * y_pred_pos, 1)
            false_neg = K.sum(y_true_pos * (1 - y_pred_pos), 1)
            false_pos = K.sum((1 - y_true_pos) * y_pred_pos, 1)
            return K.mean((true_pos + smooth) / (true_pos + alpha * false_neg + (1 - alpha) * false_pos + smooth))

        return _multiclass_2D_tversky_index_

    @classmethod
    def multiclass_2D_tversky_loss(cls, smooth=1., alpha=0.7):
        smooth = float(smooth)
        alpha = float(alpha)

        def _multiclass_2D_tversky_loss_(y_true, y_pred):
            y_true = K.permute_dimensions(y_true, (3, 1, 2, 0))
            y_pred = K.permute_dimensions(y_pred, (3, 1, 2, 0))

            y_true_pos = K.batch_flatten(y_true)
            y_pred_pos = K.batch_flatten(y_pred)
            true_pos = K.sum(y_true_pos * y_pred_pos, 1)
            false_neg = K.sum(y_true_pos * (1 - y_pred_pos), 1)
            false_pos = K.sum((1 - y_true_pos) * y_pred_pos, 1)
            tversky_index = (true_pos + smooth) / (true_pos + alpha * false_neg + (1 - alpha) * false_pos + smooth)
            return K.mean(1 - tversky_index)

        return _multiclass_2D_tversky_loss_

    def multiclass_2D_focal_tversky_loss(cls, smooth=1., alpha=0.7, gamma=0.75):
        smooth = float(smooth)
        alpha = float(alpha)

        def _multiclass_2D_tversky_loss_(y_true, y_pred):
            y_true = K.permute_dimensions(y_true, (3, 1, 2, 0))
            y_pred = K.permute_dimensions(y_pred, (3, 1, 2, 0))

            y_true_pos = K.batch_flatten(y_true)
            y_pred_pos = K.batch_flatten(y_pred)
            true_pos = K.sum(y_true_pos * y_pred_pos, 1)
            false_neg = K.sum(y_true_pos * (1 - y_pred_pos), 1)
            false_pos = K.sum((1 - y_true_pos) * y_pred_pos, 1)
            tversky_index = (true_pos + smooth) / (true_pos + alpha * false_neg + (1 - alpha) * false_pos + smooth)
            return K.mean(K.pow((1 - tversky_index), gamma))

        return _multiclass_2D_tversky_loss_
