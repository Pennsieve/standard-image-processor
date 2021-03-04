#!/usr/bin/env python
import os
import glob

import pytest
from moto import mock_dynamodb2
from moto import mock_s3
from moto import mock_ssm
# our module(s)
from standard_image_processor import StandardImageProcessor

from base_processor.tests import init_ssm, setup_processor

test_processor_data = [
    'sample_tiff.tiff',
    'sample_tif.TIF',
    'cat_tiff.tiff'  # RGBA image
]


@pytest.fixture(
    scope='function'
)
def task(request):
    yield tsk

    tsk._cleanup()

    mock_dynamodb2().stop()


@pytest.mark.parametrize("filename", test_processor_data)
def test_sub_region_standard_image_processor(filename):
    mock_ssm().start()
    mock_s3().start()

    init_ssm()

    # init task
    for a in range(1):
        for b in range(1):
            open('{}_{}.txt'.format(a,b,),'w').write("4,4")
            inputs = {
                'file': os.path.join('/test-resources', filename),
                'sub_region_file': '{}_{}.txt'.format(a,b,)
            }
            task = StandardImageProcessor(inputs=inputs)

            setup_processor(task)

            # run
            task.run()

            assert os.path.isdir('view')
            assert os.path.isfile('view/slide.dzi')


