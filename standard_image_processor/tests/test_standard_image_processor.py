#!/usr/bin/env python
import os
import json

import pytest
from moto import mock_s3
from moto import mock_ssm
# our module(s)
from standard_image_processor import StandardImageProcessor, StandardImageOutputFile

from base_processor.tests import init_ssm
from base_processor.tests import setup_processor

test_processor_data = [
    'sample_gif.gif',
    'sample_jpeg.jpeg',
    'sample_jpeg2000.jp2',
    'sample_png.png'
]


@pytest.mark.parametrize("filename", test_processor_data)
def test_standard_image_processor(filename):
    mock_ssm().start()
    mock_s3().start()

    init_ssm()

    # init task
    inputs = {'file': os.path.join('/test-resources', filename)}
    task = StandardImageProcessor(inputs=inputs)

    setup_processor(task)

    # run
    task.run()

    # Check outputs
    assert os.path.isfile('view_asset_info.json')
    json_dict = json.load(open('view_asset_info.json'))
    print json_dict

    if 'huge' in filename or 'tif' in filename.lower():
        assert os.path.isdir('view')
        assert os.path.isfile('view/slide.dzi')
        assert os.path.isfile('view/dimensions.json')
    elif filename.endswith('.jp2'):
        assert os.path.isfile('output.png')
    else:
        assert not os.path.isdir('view')
        assert not os.path.isfile('view/slide.dzi')
    assert os.path.isfile('metadata.json')
