"""Request parameters shared by the web form and the REST API."""
from webargs import fields, validate

SAMPLE_SIZE_ARGS = {
    'baseline_conversion_rate': fields.Float(
        required=True,
        validate=validate.Range(min=0, max=1, min_inclusive=False,
                                max_inclusive=False),
        metadata={'description': 'Conversion rate of the control variant (A), '
                                 'as a fraction between 0 and 1.',
                  'example': 0.05}),
    'expected_relative_lift': fields.Float(
        required=True, validate=validate.Range(min=0, min_inclusive=False),
        metadata={'description': 'Relative lift you expect variant B to '
                                 'achieve over A, e.g. 0.1 for +10%.',
                  'example': 0.1}),
    'loss_tolerance': fields.Float(
        load_default=.002, validate=validate.Range(min=0, min_inclusive=False),
        metadata={'description': 'Largest expected loss, in conversion rate, '
                                 'you will accept when choosing the wrong '
                                 'variant.'}),
    'power': fields.Float(
        load_default=.8,
        validate=validate.Range(min=.5, max=1, max_inclusive=False),
        metadata={'description': 'Probability that the experiment reaches the '
                                 'loss tolerance when the expected lift is '
                                 'real.'}),
    'prior_alpha': fields.Int(
        load_default=1, validate=validate.Range(min=1),
        metadata={'description': 'Alpha (prior successes) of the Beta prior '
                                 'on each variant.'}),
    'prior_beta': fields.Int(
        load_default=1, validate=validate.Range(min=1),
        metadata={'description': 'Beta (prior failures) of the Beta prior on '
                                 'each variant.'}),
}
