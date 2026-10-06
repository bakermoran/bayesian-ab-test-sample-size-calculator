"""sample_size REST API."""

from sample_size.api.v1 import index, loss_function, sample_size

blueprints = [index.bp, sample_size.bp, loss_function.bp]
